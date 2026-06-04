#!/usr/bin/env python3
"""
Scraper progressioni armoniche di Piero Piccioni.

NON richiede credenziali Spotify. Usa solo:
  - Spotify embed pages  (pubbliche, nessun auth)
  - Jamstart public API  (get_track_info + get_single_audio_features)

Strategia BFS:
  1. Artist embed -> top 10 track IDs
  2. Per ogni track -> album ID (via Jamstart get_track_info)
  3. Album embed  -> tutti i track ID dell'album
  4. Per ogni nuovo track -> album ID -> album embed -> ...
  fino a raggiungere TARGET tracce

Output: songs_progressions.json  (checkpoint ogni 50 tracce, riprendibile)
"""

import json
import random
import sys
import time
from collections import deque
from pathlib import Path

import re
import requests

# ---------------------------------------------------------------------------
TARGET      = 1000           # tracce obiettivo
OUTPUT_FILE = "songs_progressions.json"
CHECKPOINT  = 50             # salva ogni N tracce nuove
DELAY_EMBED = (0.3, 0.6)    # delay tra embed Spotify
DELAY_JAM   = (0.4, 0.8)    # delay tra chiamate Jamstart
MAX_RETRIES = 4

ARTIST_ID   = "2WPn0emjr8XPmMOT0bBcPe"   # Piero Piccioni

KEY_NAMES  = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
MODE_NAMES = {0:"minor", 1:"major"}

EMBED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}
JAM_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Referer": "https://jamstart.app/",
    "Origin": "https://jamstart.app",
    "Accept": "application/json, */*",
}


# ---------------------------------------------------------------------------
# Spotify embed scraping
# ---------------------------------------------------------------------------

def _next_data(html: str) -> dict:
    """Estrae __NEXT_DATA__ dall'HTML dell'embed Spotify."""
    m = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


def _track_list_from_state(state: dict) -> list[dict]:
    """Ritorna trackList dall'oggetto state Spotify embed."""
    return (
        state.get("data", {})
             .get("entity", {})
             .get("trackList", [])
    )


def fetch_embed(session: requests.Session, url: str) -> str | None:
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(url, headers=EMBED_HEADERS, timeout=15)
            if r.status_code == 200:
                return r.text
            if r.status_code == 429:
                w = 5 * (attempt + 1)
                print(f"  [embed] rate limit, attendo {w}s")
                time.sleep(w)
            else:
                return None
        except requests.RequestException:
            time.sleep(2)
    return None


def get_artist_seed_tracks(session: requests.Session) -> list[str]:
    """Track IDs dall'embed artista."""
    html = fetch_embed(
        session, f"https://open.spotify.com/embed/artist/{ARTIST_ID}"
    )
    if not html:
        return []
    nd = _next_data(html)
    state = nd.get("props", {}).get("pageProps", {}).get("state", {})
    tracks = _track_list_from_state(state)
    ids = []
    for t in tracks:
        uri = t.get("uri", "")
        if uri.startswith("spotify:track:"):
            ids.append(uri.split(":")[-1])
    return ids


def get_album_tracks(session: requests.Session, album_id: str) -> tuple[list[str], str]:
    """Track IDs + nome album dall'embed album."""
    html = fetch_embed(
        session, f"https://open.spotify.com/embed/album/{album_id}"
    )
    if not html:
        return [], ""
    nd = _next_data(html)
    state = nd.get("props", {}).get("pageProps", {}).get("state", {})
    entity = state.get("data", {}).get("entity", {})
    tracks = entity.get("trackList", [])
    album_name = entity.get("name", "")
    ids = []
    for t in tracks:
        uri = t.get("uri", "")
        if uri.startswith("spotify:track:"):
            ids.append(uri.split(":")[-1])
    return ids, album_name


# ---------------------------------------------------------------------------
# Jamstart public API
# ---------------------------------------------------------------------------

def _jamstart_post(session: requests.Session, endpoint: str, payload: dict) -> dict | None:
    url = f"https://jamstart.app/api/spotify_utils/{endpoint}"
    for attempt in range(MAX_RETRIES):
        try:
            r = session.post(
                url, json=payload, headers=JAM_HEADERS, timeout=12
            )
            if r.status_code == 200:
                body = r.json()
                return body if isinstance(body, dict) else None
            if r.status_code == 429:
                w = 2 ** (attempt + 1) + random.uniform(0, 1)
                print(f"  [jamstart] rate limit, attendo {w:.1f}s")
                time.sleep(w)
            else:
                return None
        except (requests.RequestException, ValueError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(1.5)
    return None


def get_track_info(session: requests.Session, track_id: str) -> dict | None:
    d = _jamstart_post(session, "get_track_info", {"trackID": track_id})
    return d.get("trackData") if d else None


def get_audio_features(session: requests.Session, track_id: str) -> dict | None:
    d = _jamstart_post(session, "get_single_audio_features", {"trackID": track_id})
    return d.get("trackIdKeyAndMode") if d else None


# ---------------------------------------------------------------------------
# Costruzione record risultato
# ---------------------------------------------------------------------------

def build_result(track_id: str, info: dict | None, feat: dict | None) -> dict:
    key_idx  = (feat or {}).get("key")
    mode_idx = (feat or {}).get("mode")
    key_name  = KEY_NAMES[key_idx] if key_idx is not None and 0 <= key_idx <= 11 else None
    mode_name = MODE_NAMES.get(mode_idx)

    title  = (info or {}).get("name", "")
    album  = (info or {}).get("album", {}) or {}
    a_name = album.get("name", "")
    a_year = (album.get("release_date", "") or "")[:4]
    artists = ", ".join(
        a["name"] for a in (info or {}).get("artists", []) if a.get("name")
    ) or "Piero Piccioni"

    return {
        "spotify_id":      track_id,
        "title":           title,
        "artists":         artists,
        "album":           a_name,
        "year":            a_year,
        "track_number":    (info or {}).get("track_number"),
        "duration_ms":     (info or {}).get("duration_ms"),
        "jamstart_url":    f"https://jamstart.app/song_info/{track_id}",
        "key":             key_name,
        "mode":            mode_name,
        "progression":     f"{key_name} {mode_name}" if key_name and mode_name else None,
        "tempo_bpm":       round((feat or {}).get("tempo", 0) or 0, 1) or None,
        "time_signature":  (feat or {}).get("time_signature"),
        "danceability":    (feat or {}).get("danceability"),
        "energy":          (feat or {}).get("energy"),
        "acousticness":    (feat or {}).get("acousticness"),
        "instrumentalness":(feat or {}).get("instrumentalness"),
        "valence":         (feat or {}).get("valence"),
        "loudness_db":     (feat or {}).get("loudness"),
        "speechiness":     (feat or {}).get("speechiness"),
        "liveness":        (feat or {}).get("liveness"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    output_path = Path(OUTPUT_FILE)

    # --- Carica checkpoint ---
    results: list[dict] = []
    done_track_ids: set[str] = set()
    done_album_ids: set[str] = set()

    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                results = existing
                done_track_ids = {r["spotify_id"] for r in results}
                print(f"[R] Checkpoint: {len(results)} tracce gia' salvate, riprendo...")
        except Exception:
            pass

    session = requests.Session()

    # --- Seed: top tracks dall'embed artista ---
    print("[*] Recupero seed tracks dall'embed artista Spotify...")
    seed_ids = get_artist_seed_tracks(session)
    print(f"    Seed: {len(seed_ids)} track IDs")
    time.sleep(random.uniform(*DELAY_EMBED))

    # BFS: coda di track IDs da esplorare per trovare album
    track_queue: deque[str] = deque(seed_ids)
    album_queue:  deque[str] = deque()

    # Aggiunge album già processati dal checkpoint
    # (non li ri-scartiamo, ma non li riscarichiamo)
    new_since_ckpt = 0

    def save():
        output_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"[~] Obiettivo: {TARGET} tracce uniche")
    print("    Ciclo BFS: track -> album -> track -> album -> ...")
    print()

    iteration = 0
    while len(results) < TARGET:
        iteration += 1

        # ── Fase 1: svuota la track_queue (trova album IDs) ──
        while track_queue and len(results) < TARGET:
            tid = track_queue.popleft()
            if tid in done_track_ids:
                continue

            print(
                f"  [{len(results)+1}/{TARGET}] track {tid[:8]}...",
                end=" ", flush=True
            )

            # Ottieni info (incluso album_id)
            info = get_track_info(session, tid)
            time.sleep(random.uniform(*DELAY_JAM))

            if not info:
                print("skip (no info)")
                done_track_ids.add(tid)
                continue

            # Accoda album se nuovo
            album_id = (info.get("album") or {}).get("id", "")
            if album_id and album_id not in done_album_ids:
                album_queue.append(album_id)
                done_album_ids.add(album_id)

            # Ottieni audio features
            feat = get_audio_features(session, tid)
            time.sleep(random.uniform(*DELAY_JAM))

            done_track_ids.add(tid)

            result = build_result(tid, info, feat)
            results.append(result)
            new_since_ckpt += 1

            prog = result.get("progression") or "N/A"
            bpm  = result.get("tempo_bpm") or 0
            print(f"OK  {prog:<16}  {bpm:.0f} BPM")

            if new_since_ckpt >= CHECKPOINT:
                save()
                print(f"    [SAVE] {len(results)} tracce salvate")
                new_since_ckpt = 0

        # ── Fase 2: scarica un album e mette i suoi track in coda ──
        if not album_queue:
            print("[!] Nessun album in coda. Discografia esaurita.")
            break

        album_id = album_queue.popleft()
        print(f"  [album] {album_id[:8]}...", end=" ", flush=True)
        time.sleep(random.uniform(*DELAY_EMBED))

        album_tracks, album_name = get_album_tracks(session, album_id)
        print(f"'{album_name[:40]}' -> {len(album_tracks)} tracce")

        for tid in album_tracks:
            if tid not in done_track_ids:
                track_queue.append(tid)

    # --- Salvataggio finale ---
    save()
    print(f"\n[OK] Completato! {len(results)} tracce in '{OUTPUT_FILE}'")
    _print_summary(results)


def _print_summary(results: list[dict]) -> None:
    if not results:
        return
    from collections import Counter
    counts = Counter(r.get("progression") for r in results if r.get("progression"))
    print("\n[STATS] Top 10 progressioni:")
    for prog, n in counts.most_common(10):
        bar = "#" * (n * 20 // max(counts.values()))
        print(f"    {prog:<18} {n:>4}  {bar}")


if __name__ == "__main__":
    main()
