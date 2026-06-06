#!/usr/bin/env python3
"""
Estrae progressioni di accordi dai preview Spotify (30s) usando librosa.

Non richiede basic-pitch ne' TensorFlow — usa librosa (gia' installato).
Metodo: chromagramma CQT + template matching per rilevare accordi.

Installazione (se manca qualcosa):
  pip install librosa requests numpy

Output: songs_chords.json
"""

import json
import os
import sys
import tempfile
import time
import random
from pathlib import Path

import requests
import numpy as np

OUTPUT_FILE = "songs_chords.json"
INPUT_FILE  = "songs_progressions.json"
CHECKPOINT  = 20
DELAY       = (0.3, 0.7)
HOP_SEC     = 0.5      # secondi per finestra accordo
MIN_ENERGY  = 0.15     # soglia minima energia per rilevare un accordo

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Notazione accordi
CHORD_SUFFIX = {
    "maj":     "",       # C
    "min":     "m",      # Cm
    "dom7":    "7",      # C7
    "maj7":    "maj7",   # Cmaj7
    "min7":    "m7",     # Cm7
    "dim":     "dim",    # Cdim
    "aug":     "aug",    # Caug
    "sus2":    "sus2",
    "sus4":    "sus4",
    "hdim7":   "m7b5",
    "dim7":    "dim7",
    "minmaj7": "mM7",
    "dom9":    "9",
    "maj9":    "maj9",
    "min9":    "m9",
    "add9":    "add9",
}

# Template: vettore 12 elementi, 1 = nota presente, 0 = assente
def _tmpl(intervals):
    v = np.zeros(12)
    for i in intervals:
        v[i % 12] = 1.0
    return v / np.linalg.norm(v)

CHORD_TEMPLATES = {
    "maj":     _tmpl([0, 4, 7]),
    "min":     _tmpl([0, 3, 7]),
    "dom7":    _tmpl([0, 4, 7, 10]),
    "maj7":    _tmpl([0, 4, 7, 11]),
    "min7":    _tmpl([0, 3, 7, 10]),
    "dim":     _tmpl([0, 3, 6]),
    "aug":     _tmpl([0, 4, 8]),
    "sus2":    _tmpl([0, 2, 7]),
    "sus4":    _tmpl([0, 5, 7]),
    "hdim7":   _tmpl([0, 3, 6, 10]),
    "dim7":    _tmpl([0, 3, 6, 9]),
    "minmaj7": _tmpl([0, 3, 7, 11]),
    "dom9":    _tmpl([0, 2, 4, 7, 10]),
    "maj9":    _tmpl([0, 2, 4, 7, 11]),
    "min9":    _tmpl([0, 2, 3, 7, 10]),
    "add9":    _tmpl([0, 2, 4, 7]),
}

JAM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Referer": "https://jamstart.app/",
    "Origin": "https://jamstart.app",
    "Accept": "application/json, */*",
}


# ---------------------------------------------------------------------------
# Rilevamento accordi da chromagramma
# ---------------------------------------------------------------------------

def chroma_to_chord(chroma_vec: np.ndarray) -> str | None:
    """
    Dato un vettore chroma 12D, restituisce il label dell'accordo piu' probabile.
    chroma_vec: array (12,) con energie per classe pitch (C, C#, D, ...)
    """
    energy = float(np.max(chroma_vec))
    if energy < MIN_ENERGY:
        return None   # silenzio / nota singola

    # Normalizza
    norm = np.linalg.norm(chroma_vec)
    if norm < 1e-6:
        return None
    c = chroma_vec / norm

    best_label  = None
    best_score  = -1.0

    for root in range(12):
        # Ruota il chroma per testare ogni radice
        rotated = np.roll(c, -root)
        for ctype, tmpl in CHORD_TEMPLATES.items():
            score = float(np.dot(rotated, tmpl))
            if score > best_score:
                best_score  = score
                suffix      = CHORD_SUFFIX.get(ctype, ctype)
                best_label  = f"{NOTE_NAMES[root]}{suffix}"

    return best_label if best_score > 0.7 else None


def extract_chord_sequence(audio_path: str) -> list[dict]:
    """
    Carica l'audio, estrae il chromagramma CQT, rileva accordi per finestre da HOP_SEC.
    Ritorna lista di {time, chord}.
    """
    import librosa

    y, sr = librosa.load(audio_path, sr=22050, mono=True, duration=30.0)
    hop_length = int(sr * HOP_SEC)

    # CQT chromagram — piu' accurato di STFT per accordi
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length, bins_per_octave=36)
    # shape: (12, n_frames)

    # Media su finestre piu' ampie per stabilita'
    window_frames = max(1, int(1.0 / HOP_SEC))   # 2 frame = 1 secondo
    n_windows = chroma.shape[1] // window_frames

    timeline = []
    for w in range(n_windows):
        start_frame = w * window_frames
        end_frame   = start_frame + window_frames
        avg_chroma  = chroma[:, start_frame:end_frame].mean(axis=1)
        t_sec       = round(w * window_frames * HOP_SEC, 2)

        chord = chroma_to_chord(avg_chroma)
        if chord:
            timeline.append({"time": t_sec, "chord": chord})

    # Compatta: elimina ripetizioni consecutive
    compact = []
    for item in timeline:
        if not compact or compact[-1]["chord"] != item["chord"]:
            compact.append(item)

    return compact


# ---------------------------------------------------------------------------
# Preview download
# ---------------------------------------------------------------------------

def get_preview_url(session: requests.Session, track_id: str) -> str | None:
    for attempt in range(3):
        try:
            r = session.post(
                "https://jamstart.app/api/spotify_utils/get_track_info",
                json={"trackID": track_id},
                headers=JAM_HEADERS,
                timeout=12,
            )
            if r.status_code == 200:
                return r.json().get("trackData", {}).get("preview_url")
            if r.status_code == 429:
                time.sleep(3 * (attempt + 1))
        except Exception:
            time.sleep(1)
    return None


def download_preview(session: requests.Session, url: str, dest: str) -> bool:
    try:
        r = session.get(url, timeout=15, stream=True)
        if r.status_code == 200:
            with open(dest, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    input_path  = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)

    if not input_path.exists():
        print(f"[ERR] {INPUT_FILE} non trovato. Avvia prima lo scraper principale.")
        sys.exit(1)

    # Verifica librosa
    try:
        import librosa
        print(f"[*] librosa {librosa.__version__} trovato")
    except ImportError:
        print("[ERR] librosa non installato. Esegui: pip install librosa")
        sys.exit(1)

    songs = json.loads(input_path.read_text(encoding="utf-8"))
    print(f"[*] {len(songs)} brani in {INPUT_FILE}")

    # Carica checkpoint
    results: dict[str, dict] = {}
    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                results = {r["spotify_id"]: r for r in existing}
            print(f"[R] Checkpoint: {len(results)} brani gia' processati")
        except Exception:
            pass

    def save():
        output_path.write_text(
            json.dumps(list(results.values()), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    pending = [s for s in songs if s["spotify_id"] not in results]
    total   = len(pending)
    print(f"[*] Da processare: {total} brani")
    print(f"[~] Stimato: ~{total * 2 // 60} minuti\n")

    session = requests.Session()
    new_since_ckpt = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, song in enumerate(pending):
            tid   = song["spotify_id"]
            title = song.get("title") or tid[:12]
            print(f"  [{i+1}/{total}] '{title[:45]}'", end=" ", flush=True)

            # Ottieni preview URL
            preview_url = song.get("preview_url") or get_preview_url(session, tid)
            time.sleep(random.uniform(*DELAY))

            if not preview_url:
                print("skip (no preview)")
                results[tid] = {
                    "spotify_id": tid, "title": title,
                    "chord_sequence": [], "chord_timeline": [],
                    "error": "no_preview"
                }
                new_since_ckpt += 1
                continue

            # Scarica MP3
            mp3_path = os.path.join(tmpdir, f"{tid}.mp3")
            if not download_preview(session, preview_url, mp3_path):
                print("skip (download failed)")
                results[tid] = {
                    "spotify_id": tid, "title": title,
                    "chord_sequence": [], "chord_timeline": [],
                    "error": "download_failed"
                }
                new_since_ckpt += 1
                continue

            # Estrai accordi con librosa
            try:
                timeline = extract_chord_sequence(mp3_path)
            except Exception as e:
                print(f"skip (errore: {e})")
                results[tid] = {
                    "spotify_id": tid, "title": title,
                    "chord_sequence": [], "chord_timeline": [],
                    "error": str(e)
                }
                new_since_ckpt += 1
                os.remove(mp3_path)
                continue

            sequence = [t["chord"] for t in timeline]

            results[tid] = {
                "spotify_id":     tid,
                "title":          title,
                "album":          song.get("album", ""),
                "year":           song.get("year", ""),
                "key":            song.get("key"),
                "mode":           song.get("mode"),
                "tempo_bpm":      song.get("tempo_bpm"),
                "chord_sequence": sequence,
                "chord_timeline": timeline,
                "total_chords":   len(sequence),
            }

            seq_str = " → ".join(sequence[:8])
            if len(sequence) > 8:
                seq_str += f" ... (+{len(sequence)-8})"
            print(f"  {len(sequence)} accordi: {seq_str}")

            new_since_ckpt += 1
            if new_since_ckpt >= CHECKPOINT:
                save()
                print(f"    [SAVE] {len(results)} brani salvati")
                new_since_ckpt = 0

            os.remove(mp3_path)

    save()
    print(f"\n[OK] Completato! {len(results)} brani in '{OUTPUT_FILE}'")
    _print_summary(list(results.values()))


def _print_summary(results: list[dict]) -> None:
    from collections import Counter
    all_chords = []
    for r in results:
        all_chords.extend(r.get("chord_sequence", []))

    if not all_chords:
        return

    counts = Counter(all_chords)
    print(f"\n[STATS] {len(all_chords)} accordi totali, {len(counts)} accordi unici")
    print("Top 15 accordi piu' frequenti in Piccioni:")
    for chord, n in counts.most_common(15):
        bar = "#" * (n * 25 // counts.most_common(1)[0][1])
        print(f"    {chord:<12} {n:>5}  {bar}")

    transitions = Counter()
    for r in results:
        seq = r.get("chord_sequence", [])
        for a, b in zip(seq, seq[1:]):
            transitions[(a, b)] += 1
    print("\nTop 10 transizioni (A -> B):")
    for (a, b), n in transitions.most_common(10):
        print(f"    {a:<12} -> {b:<12}  {n}")


if __name__ == "__main__":
    main()
