#!/usr/bin/env python3
"""
Analisi statistica dei dati Piccioni per generare il profilo armonico
da incollare nelle istruzioni del Custom GPT.

Usa: songs_progressions.json + songs_chords.json (se disponibile)
Output: piccioni_gpt_profile.txt
"""

import json
from pathlib import Path
from collections import Counter, defaultdict

PROG_FILE   = "songs_progressions.json"
CHORDS_FILE = "songs_chords.json"
OUT_FILE    = "piccioni_gpt_profile.txt"

KEY_ORDER = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

def roman(interval: int, mode: str) -> str:
    major_q = ["I","ii","iii","IV","V","vi","vii°"]
    minor_q = ["i","ii°","III","iv","v","VI","VII"]
    q = major_q if mode == "major" else minor_q
    return q[interval % 7] if interval < 7 else str(interval)

def main():
    lines = []
    add = lines.append

    # ── SEZIONE 1: Dati tonali da songs_progressions.json ──
    prog_path = Path(PROG_FILE)
    if not prog_path.exists():
        print(f"[ERR] {PROG_FILE} non trovato")
        return

    songs = json.loads(prog_path.read_text(encoding="utf-8"))
    add("=" * 70)
    add("PROFILO ARMONICO STATISTICO — PIERO PICCIONI")
    add(f"Basato su {len(songs)} brani analizzati da Spotify/Jamstart")
    add("=" * 70)
    add("")

    # Distribuzione tonalità
    key_counts  = Counter(s.get("key")  for s in songs if s.get("key"))
    mode_counts = Counter(s.get("mode") for s in songs if s.get("mode"))
    add("── TONALITÀ PREFERITE ──")
    for key, n in sorted(key_counts.items(), key=lambda x: -x[1])[:8]:
        bar = "█" * (n * 20 // max(key_counts.values()))
        add(f"  {key:<4} {n:>4} brani  {bar}")
    add("")
    add("── MODO ──")
    tot = sum(mode_counts.values())
    for mode, n in mode_counts.most_common():
        add(f"  {mode:<8} {n:>4} brani  ({round(n/tot*100)}%)")
    add("")

    # BPM
    bpms = [s["tempo_bpm"] for s in songs if s.get("tempo_bpm")]
    if bpms:
        add(f"── TEMPO ──")
        add(f"  Media: {round(sum(bpms)/len(bpms))} BPM")
        slow  = sum(1 for b in bpms if b < 80)
        mid   = sum(1 for b in bpms if 80 <= b < 120)
        fast  = sum(1 for b in bpms if b >= 120)
        add(f"  Lento (<80 BPM): {slow} brani ({round(slow/len(bpms)*100)}%)")
        add(f"  Medio (80-120):  {mid} brani ({round(mid/len(bpms)*100)}%)")
        add(f"  Veloce (>120):   {fast} brani ({round(fast/len(bpms)*100)}%)")
        add("")

    # Energia / Acusticità
    energies    = [s["energy"]       for s in songs if s.get("energy") is not None]
    acoustics   = [s["acousticness"] for s in songs if s.get("acousticness") is not None]
    if energies:
        add("── AUDIO FEATURES (media) ──")
        add(f"  Energy:        {round(sum(energies)/len(energies), 2)}")
    if acoustics:
        add(f"  Acousticness:  {round(sum(acoustics)/len(acoustics), 2)}")
    vals = [s["valence"] for s in songs if s.get("valence") is not None]
    if vals:
        add(f"  Valence:       {round(sum(vals)/len(vals), 2)}")
    add("")

    # Top progressioni (key+mode)
    prog_counts = Counter(s.get("progression") for s in songs if s.get("progression"))
    add("── TOP 10 TONALITÀ/MODO PIÙ USATE ──")
    for prog, n in prog_counts.most_common(10):
        bar = "█" * (n * 20 // max(prog_counts.values()))
        add(f"  {prog:<16} {n:>4}  {bar}")
    add("")

    # ── SEZIONE 2: Accordi da songs_chords.json ──
    chords_path = Path(CHORDS_FILE)
    if chords_path.exists():
        try:
            chord_data = json.loads(chords_path.read_text(encoding="utf-8"))
            chord_songs = [c for c in chord_data if c.get("chord_sequence")]
            add("=" * 70)
            add(f"ANALISI ACCORDI — {len(chord_songs)} brani con sequenze estratte")
            add("=" * 70)
            add("")

            all_chords  = []
            transitions = Counter()
            bigrams     = Counter()
            trigrams    = Counter()

            for cs in chord_songs:
                seq = cs["chord_sequence"]
                all_chords.extend(seq)
                for a, b in zip(seq, seq[1:]):
                    transitions[(a, b)] += 1
                for a, b in zip(seq, seq[2:]):
                    bigrams[(a, b)] += 1
                for a, b, c in zip(seq, seq[1:], seq[2:]):
                    trigrams[(a, b, c)] += 1

            chord_freq = Counter(all_chords)
            add(f"── TOP 20 ACCORDI PIÙ USATI ({len(all_chords)} totali) ──")
            for chord, n in chord_freq.most_common(20):
                pct = round(n / len(all_chords) * 100, 1)
                bar = "█" * (n * 20 // chord_freq.most_common(1)[0][1])
                add(f"  {chord:<12} {n:>5} ({pct:>4}%)  {bar}")
            add("")

            add("── TOP 20 TRANSIZIONI (A → B) ──")
            for (a, b), n in transitions.most_common(20):
                add(f"  {a:<12} → {b:<12}  {n}")
            add("")

            add("── TOP 15 TRIGRAMMI (A → B → C) ──")
            for (a, b, c), n in trigrams.most_common(15):
                add(f"  {a} → {b} → {c}  ({n})")
            add("")

            # Matrice Markov per gli accordi più comuni
            top10 = [ch for ch, _ in chord_freq.most_common(10)]
            add("── MATRICE MARKOV (top 10 accordi) ──")
            add("  Dato accordo X, probabilità dei successori più frequenti:")
            add("")
            outgoing = defaultdict(Counter)
            for (a, b), n in transitions.items():
                outgoing[a][b] += n
            for chord in top10:
                if chord in outgoing:
                    total_out = sum(outgoing[chord].values())
                    top_next = outgoing[chord].most_common(4)
                    nexts = "  |  ".join(f"{b} {round(n/total_out*100)}%" for b, n in top_next)
                    add(f"  {chord:<12} →  {nexts}")
            add("")
        except Exception as e:
            add(f"[WARN] Impossibile leggere {CHORDS_FILE}: {e}")
            add("")

    # ── SEZIONE 3: Stile descrittivo (per il GPT) ──
    add("=" * 70)
    add("NOTE STILISTICHE PER IL GPT")
    add("=" * 70)
    add("""
Piero Piccioni (1921–2004) è uno dei più importanti compositori italiani
di musiche da film. Il suo stile armonico è caratterizzato da:

CARATTERISTICHE ARMONICHE PRINCIPALI:
- Prevalenza del modo minore (specialmente Fa minore, La minore, Sol minore)
- Uso frequente di accordi di settima e nona (maj7, m7, dom7, m9)
- Prestito modale: accordi dal modo parallelo (es. IV♭ maggiore in tonalità minore)
- Progressioni di accordi cromatiche e diatoniche miste
- Uso di pedali di basso con armonie mobili sopra
- Influenza jazz: sostituzioni di tritono, accordi di dominante alterati
- Influenza bossa nova e musica latina (anni '60-'70)
- Uso di accordi sospesi (sus2, sus4) per creare tensione
- Finale spesso su accordo di tonica con settima maggiore

PATTERN TIPICI:
- i – VI – III – VII (progressione aeoliana)
- i – iv – V7 – i (progressione classica in minore)
- Imaj7 – IV – iii – vi (progressione jazz in maggiore)
- i – ♭VII – ♭VI – V (progressione andalusa)
- Modulazioni improvvise a tonalità lontane (mediant relationships)

CONTESTI D'USO:
- Brani lenti (<80 BPM): colonne sonore romantiche/drammatiche,
  prevalenza di accordi estesi (maj7, m9, add9)
- Brani medi (80-120 BPM): temi principali, bilanciamento tensione/rilascio
- Brani veloci (>120 BPM): azione, jazz, bossa, accordi più semplici
""")

    out = "\n".join(lines)
    Path(OUT_FILE).write_text(out, encoding="utf-8")
    print(out)
    print(f"\n[OK] Salvato in '{OUT_FILE}'")

if __name__ == "__main__":
    main()
