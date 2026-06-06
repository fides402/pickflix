#!/usr/bin/env python3
"""
Estrae progressioni di accordi dai preview Spotify (30s) usando basic-pitch.

Installazione dipendenze:
  pip install basic-pitch librosa numpy requests

Per GPU (opzionale, ~5x piu' veloce):
  pip install tensorflow[and-cuda]   # Linux/WSL
  oppure installa manualmente CUDA + cuDNN su Windows

Output: songs_chords.json
"""

import json
import os
import sys
import tempfile
import time
import random
from pathlib import Path
from collections import defaultdict

import requests
import numpy as np

OUTPUT_FILE  = "songs_chords.json"
INPUT_FILE   = "songs_progressions.json"
CHECKPOINT   = 20
DELAY        = (0.3, 0.7)
HOP_SIZE     = 0.5    # secondi per finestra accordo
MIN_NOTES    = 2      # note minime per rilevare un accordo

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

CHORD_SUFFIX = {
    "maj":     "",
    "min":     "m",
    "dom7":    "7",
    "maj7":    "maj7",
    "min7":    "m7",
    "dim":     "dim",
    "aug":     "aug",
    "sus2":    "sus2",
    "sus4":    "sus4",
    "hdim7":   "m7b5",
    "dim7":    "dim7",
    "minmaj7": "mM7",
    "add9":    "add9",
    "min_add9":"madd9",
    "dom9":    "9",
    "maj9":    "maj9",
    "min9":    "m9",
}

CHORD_INTERVALS = {
    "maj":     [0, 4, 7],
    "min":     [0, 3, 7],
    "dom7":    [0, 4, 7, 10],
    "maj7":    [0, 4, 7, 11],
    "min7":    [0, 3, 7, 10],
    "dim":     [0, 3, 6],
    "aug":     [0, 4, 8],
    "sus2":    [0, 2, 7],
    "sus4":    [0, 5, 7],
    "hdim7":   [0, 3, 6, 10],
    "dim7":    [0, 3, 6, 9],
    "minmaj7": [0, 3, 7, 11],
    "add9":    [0, 2, 4, 7],
    "min_add9":[0, 2, 3, 7],
    "dom9":    [0, 2, 4, 7, 10],
    "maj9":    [0, 2, 4, 7, 11],
    "min9":    [0, 2, 3, 7, 10],
}

JAM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Referer": "https://jamstart.app/",
    "Origin": "https://jamstart.app",
    "Accept": "application/json, */*",
}


# ---------------------------------------------------------------------------
# Identificazione accordi
# ---------------------------------------------------------------------------

def pitches_to_chord(pitches: list[int]) -> tuple[str, list[str], str]:
    """
    Converte lista di pitch MIDI in label accordo.
    Ritorna (label, note_names, bass_note).
    """
    if len(pitches) < MIN_NOTES:
        return "?", [], ""

    pcs = set(p % 12 for p in pitches)
    bass_pc = min(pitches) % 12
    note_strs = [f"{NOTE_NAMES[p % 12]}{p // 12 - 1}" for p in sorted(set(pitches))]

    best_label = "?"
    best_score = -1.0

    for root in range(12):
        for ctype, intervals in CHORD_INTERVALS.items():
            template = set((root + i) % 12 for i in intervals)
            inter = len(pcs & template)
            union = len(pcs | template)
            if union == 0:
                continue
            score = inter / union
            # Bonus: radice nel basso
            if root == bass_pc:
                score += 0.15
            # Bonus: match esatto
            if pcs == template:
                score += 0.3

            if score > best_score:
                best_score = score
                suffix = CHORD_SUFFIX.get(ctype, ctype)
                best_label = f"{NOTE_NAMES[root]}{suffix}"

    # Aggiungi slash-chord se il basso non e' la radice
    if best_label != "?" and best_score > 0.4:
        # Trova la radice identificata
        root_name = best_label.rstrip("0123456789majmindimaug7sus9mMbadd")
        root_pc_list = [i for i, n in enumerate(NOTE_NAMES) if best_label.startswith(n)]
        if root_pc_list:
            root_pc = max(root_pc_list, key=lambda x: len(NOTE_NAMES[x]))
            if bass_pc != root_pc:
                best_label = f"{best_label}/{NOTE_NAMES[bass_pc]}"

    return (best_label if best_score > 0.35 else "?"), note_strs, NOTE_NAMES[bass_pc]


def extract_chord_sequence(note_events) -> list[dict]:
    """
    Converte note_events di basic-pitch in sequenza di accordi.
    note_events: [(start_s, end_s, pitch_midi, amplitude, pitch_bend), ...]
    """
    if not note_events:
        return []

    max_time = max(e[1] for e in note_events)
    timeline = []

    t = 0.0
    while t < max_time:
        active_notes = [
            e[2] for e in note_events
            if e[0] < t + HOP_SIZE and e[1] > t and e[3] > 0.3  # filtra note deboli
        ]
        if len(set(p % 12 for p in active_notes)) >= MIN_NOTES:
            chord, notes, bass = pitches_to_chord(active_notes)
            if chord != "?":
                timeline.append({
                    "time":  round(t, 2),
                    "chord": chord,
                    "bass":  bass,
                    "notes": notes,
                })
        t = round(t + HOP_SIZE, 3)

    # Compatta: rimuovi duplicati consecutivi
    compact = []
    for item in timeline:
        if not compact or compact[-1]["chord"] != item["chord"]:
            compact.append(item)

    return compact


def chord_sequence_labels(timeline: list[dict]) -> list[str]:
    return [t["chord"] for t in timeline]


# ---------------------------------------------------------------------------
# Scaricamento preview
# ---------------------------------------------------------------------------

def get_preview_url(session: requests.Session, track_id: str) -> str | None:
    """Ottieni preview URL da Jamstart get_track_info."""
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
# Basic-pitch
# ---------------------------------------------------------------------------

_model = None

def get_model():
    global _model
    if _model is None:
        print("[*] Carico modello basic-pitch...", flush=True)
        from basic_pitch.inference import Model
        from basic_pitch import ICASSP_2022_MODEL_PATH
        _model = Model(ICASSP_2022_MODEL_PATH)
        print("    Modello caricato.", flush=True)
    return _model


def run_basic_pitch(audio_path: str) -> list:
    from basic_pitch.inference import predict
    from basic_pitch import ICASSP_2022_MODEL_PATH
    model = get_model()
    try:
        _, _, note_events = predict(
            audio_path,
            model,
            minimum_note_length=0.08,
            minimum_frequency=60.0,   # esclude note troppo basse (artefatti)
            maximum_frequency=2000.0,
        )
        return note_events if note_events is not None else []
    except Exception as e:
        print(f"    [WARN] basic-pitch error: {e}", flush=True)
        return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    input_path  = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)

    if not input_path.exists():
        print(f"[ERR] {INPUT_FILE} non trovato. Avvia prima lo scraper principale.")
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
            elif isinstance(existing, dict):
                results = existing
            print(f"[R] Checkpoint: {len(results)} brani gia' processati")
        except Exception:
            pass

    def save():
        output_path.write_text(
            json.dumps(list(results.values()), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # Verifica basic-pitch
    try:
        import basic_pitch
    except ImportError:
        print("[ERR] basic-pitch non installato.")
        print("      Esegui:  pip install basic-pitch")
        sys.exit(1)

    # Verifica GPU
    try:
        import tensorflow as tf
        gpus = tf.config.list_physical_devices("GPU")
        if gpus:
            print(f"[GPU] {len(gpus)} GPU trovate: {[g.name for g in gpus]}")
        else:
            print("[CPU] Nessuna GPU trovata, uso CPU (piu' lento)")
    except Exception:
        print("[INFO] TensorFlow non disponibile, uso backend alternativo")

    pending = [s for s in songs if s["spotify_id"] not in results]
    print(f"[*] Da processare: {len(pending)} brani")
    print(f"[~] Stimato: ~{len(pending) * 12 // 60} minuti (GPU) / ~{len(pending) * 20 // 60} minuti (CPU)\n")

    session = requests.Session()
    new_since_ckpt = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, song in enumerate(pending):
            tid   = song["spotify_id"]
            title = song.get("title") or tid[:12]
            print(f"  [{i+1}/{len(pending)}] '{title[:45]}'", end=" ", flush=True)

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

            # Estrai note con basic-pitch
            note_events = run_basic_pitch(mp3_path)

            if not note_events:
                print("skip (no notes detected)")
                results[tid] = {
                    "spotify_id": tid, "title": title,
                    "chord_sequence": [], "chord_timeline": [],
                    "error": "no_notes"
                }
                new_since_ckpt += 1
                continue

            # Converti in accordi
            timeline = extract_chord_sequence(note_events)
            sequence = chord_sequence_labels(timeline)

            results[tid] = {
                "spotify_id":    tid,
                "title":         title,
                "album":         song.get("album", ""),
                "year":          song.get("year", ""),
                "key":           song.get("key"),
                "mode":          song.get("mode"),
                "tempo_bpm":     song.get("tempo_bpm"),
                "chord_sequence": sequence,
                "chord_timeline": timeline,
                "total_chords":  len(sequence),
            }

            seq_str = " → ".join(sequence[:8])
            if len(sequence) > 8:
                seq_str += " ..."
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
    print("Top 15 accordi piu' frequenti:")
    for chord, n in counts.most_common(15):
        bar = "#" * (n * 25 // counts.most_common(1)[0][1])
        print(f"    {chord:<12} {n:>5}  {bar}")

    # Transizioni piu' comuni
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
