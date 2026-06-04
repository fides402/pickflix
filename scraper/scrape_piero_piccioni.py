#!/usr/bin/env python3
"""
Scraper per le progressioni armoniche di Piero Piccioni.

Flusso:
  1. Spotify Client Credentials -> token (no login utente, solo app developer gratuita)
  2. Enumera tutti gli album/singoli di Piero Piccioni -> raccoglie i track ID
  3. Per ogni track ID chiama le due API pubbliche di Jamstart:
       - /api/spotify_utils/get_single_audio_features  -> key, mode, BPM, ecc.
       - /api/spotify_utils/get_track_info             -> titolo, album, anno
  4. Salva tutto in songs_progressions.json con checkpoint ogni 50 tracce
     (riavvia lo script per riprendere dove si era fermato)

Credenziali Spotify (gratis, 2 min):
  1. Vai su https://developer.spotify.com/dashboard
  2. Crea una app (qualsiasi nome, Redirect URI: http://localhost)
  3. Copia Client ID e Client Secret
  4. Esegui:
       SPOTIFY_CLIENT_ID=xxx SPOTIFY_CLIENT_SECRET=yyy python3 scraper/scrape_piero_piccioni.py
"""

import json
import os
import random
import sys
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------

ARTIST_ID = "2WPn0emjr8XPmMOT0bBcPe"   # Piero Piccioni su Spotify
OUTPUT_FILE = "songs_progressions.json"
CHECKPOINT_EVERY = 50                   # salva ogni N tracce nuove
DELAY_MIN = 0.4                         # secondi minimo tra chiamate Jamstart
DELAY_MAX = 0.9                         # secondi massimo
MAX_RETRIES = 4

KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MODE_NAMES = {0: "minor", 1: "major"}

JAMSTART_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Referer": "https://jamstart.app/",
    "Origin": "https://jamstart.app",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}


# ---------------------------------------------------------------------------
# Spotify Client Credentials
# ---------------------------------------------------------------------------

def get_spotify_token(client_id: str, client_secret: str) -> str:
    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def spotify_get(token: str, url: str, params: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    for attempt in range(MAX_RETRIES):
        resp = requests.get(url, headers=headers, params=params or {}, timeout=15)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            print(f"    [Spotify] rate limit, attendo {wait}s...")
            time.sleep(wait)
            continue
        if resp.status_code == 401:
            raise RuntimeError("Token Spotify scaduto — riavvia lo script.")
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Spotify GET fallito dopo {MAX_RETRIES} tentativi: {url}")


# ---------------------------------------------------------------------------
# Raccolta track ID via Spotify Search
# (l'endpoint /artists/{id}/albums è ristretto per le nuove app dal 2025)
# ---------------------------------------------------------------------------

# Query multiple per massimizzare la copertura
SEARCH_QUERIES = [
    'artist:"Piero Piccioni"',
    "Piero Piccioni",
    "Piccioni colonna sonora",
    "Piccioni soundtrack",
]

def search_tracks(token: str, query: str, max_offset: int = 950) -> list[dict]:
    """Cerca tracce con una query. Spotify permette offset 0-999, limit 50."""
    tracks: list[dict] = []
    for offset in range(0, max_offset + 1, 50):
        data = spotify_get(token, "https://api.spotify.com/v1/search", {
            "q": query,
            "type": "track",
            "limit": 50,
            "offset": offset,
        })
        items = data.get("tracks", {}).get("items", [])
        if not items:
            break
        for t in items:
            if not t.get("id"):
                continue
            tracks.append({
                "id": t["id"],
                "name": t["name"],
                "album": (t.get("album") or {}).get("name", ""),
                "year": ((t.get("album") or {}).get("release_date", "") or "")[:4],
                "track_number": t.get("track_number"),
                "duration_ms": t.get("duration_ms"),
            })
        time.sleep(0.15)
    return tracks


def collect_all_tracks(token: str) -> list[dict]:
    """Raccoglie tracce da più query, deduplicando per ID."""
    seen: set[str] = set()
    all_tracks: list[dict] = []
    for query in SEARCH_QUERIES:
        print(f"    Ricerca: {query}")
        found = search_tracks(token, query)
        new = 0
        for t in found:
            if t["id"] not in seen:
                seen.add(t["id"])
                all_tracks.append(t)
                new += 1
        print(f"      {new} nuove tracce (totale: {len(all_tracks)})")
    return all_tracks


# ---------------------------------------------------------------------------
# Chiamate Jamstart (API pubbliche, senza login)
# ---------------------------------------------------------------------------

def jamstart_post(session: requests.Session, endpoint: str, payload: dict) -> dict | None:
    url = f"https://jamstart.app/api/spotify_utils/{endpoint}"
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.post(url, json=payload, headers=JAMSTART_HEADERS, timeout=12)
            if resp.status_code == 200:
                body = resp.json()
                # Controlla che non sia la pagina login HTML
                if isinstance(body, dict):
                    return body
                return None
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1) + random.uniform(0, 1)
                print(f"    [Jamstart] rate limit, attendo {wait:.1f}s...")
                time.sleep(wait)
                continue
            return None
        except (requests.RequestException, ValueError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))
    return None


def get_audio_features(session: requests.Session, track_id: str) -> dict | None:
    data = jamstart_post(session, "get_single_audio_features", {"trackID": track_id})
    return data.get("trackIdKeyAndMode") if data else None


def get_track_info(session: requests.Session, track_id: str) -> dict | None:
    data = jamstart_post(session, "get_track_info", {"trackID": track_id})
    return data.get("trackData") if data else None


# ---------------------------------------------------------------------------
# Formattazione
# ---------------------------------------------------------------------------

def build_result(track: dict, features: dict | None, info: dict | None) -> dict:
    key_idx = (features or {}).get("key")
    mode_idx = (features or {}).get("mode")
    key_name = KEY_NAMES[key_idx] if key_idx is not None and 0 <= key_idx <= 11 else None
    mode_name = MODE_NAMES.get(mode_idx)

    # Artisti dal track info (potrebbe essere "Piero Piccioni" + featuring)
    artists = "Piero Piccioni"
    if info:
        artist_list = info.get("artists", [])
        if artist_list:
            artists = ", ".join(a["name"] for a in artist_list)

    album_name = track["album"]
    album_year = track["year"]
    if info:
        album_info = info.get("album", {})
        album_name = album_info.get("name", album_name)
        album_year = (album_info.get("release_date", "") or "")[:4] or album_year

    return {
        "spotify_id": track["id"],
        "title": track["name"],
        "artists": artists,
        "album": album_name,
        "year": album_year,
        "track_number": track["track_number"],
        "duration_ms": track["duration_ms"],
        "jamstart_url": f"https://jamstart.app/song_info/{track['id']}",
        # Progressione armonica
        "key": key_name,
        "mode": mode_name,
        "progression": f"{key_name} {mode_name}" if key_name and mode_name else None,
        "tempo_bpm": round((features or {}).get("tempo", 0), 1) or None,
        "time_signature": (features or {}).get("time_signature"),
        # Audio features Spotify
        "danceability": (features or {}).get("danceability"),
        "energy": (features or {}).get("energy"),
        "acousticness": (features or {}).get("acousticness"),
        "instrumentalness": (features or {}).get("instrumentalness"),
        "valence": (features or {}).get("valence"),
        "loudness_db": (features or {}).get("loudness"),
        "speechiness": (features or {}).get("speechiness"),
        "liveness": (features or {}).get("liveness"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        print(
            "\nERRORE: Credenziali Spotify mancanti!\n\n"
            "  Come ottenerle (gratis, 2 minuti):\n"
            "    1. Vai su https://developer.spotify.com/dashboard\n"
            "    2. Crea una nuova app (qualsiasi nome)\n"
            "    3. Copia Client ID e Client Secret\n"
            "    4. Esegui:\n\n"
            "       SPOTIFY_CLIENT_ID=<id> SPOTIFY_CLIENT_SECRET=<secret> "
            "python3 scraper/scrape_piero_piccioni.py\n"
        )
        sys.exit(1)

    # --- Token Spotify ---
    print("[*] Ottengo token Spotify...")
    token = get_spotify_token(client_id, client_secret)

    # --- Tracce di Piero Piccioni via search ---
    print("[*] Cerco tracce di Piero Piccioni su Spotify...")
    all_tracks = collect_all_tracks(token)
    print(f"    Tracce uniche trovate: {len(all_tracks)}")

    # --- Carica checkpoint esistente ---
    output_path = Path(OUTPUT_FILE)
    results: list[dict] = []
    done_ids: set[str] = set()
    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                results = existing
                done_ids = {r["spotify_id"] for r in results}
                print(f"[R] Riprendo da checkpoint: {len(results)} tracce gia' processate")
        except (json.JSONDecodeError, KeyError):
            pass

    to_scrape = [t for t in all_tracks if t["id"] not in done_ids]
    print(f"\n[~] Tracce da scrapare: {len(to_scrape)}")

    if not to_scrape:
        print("[OK] Nessuna traccia nuova da scrapare.")
        _print_summary(results)
        return

    # --- Scraping Jamstart ---
    session = requests.Session()
    session.headers.update(JAMSTART_HEADERS)

    failed = 0
    new_since_checkpoint = 0

    for i, track in enumerate(to_scrape, 1):
        tid = track["id"]
        print(f"  [{i}/{len(to_scrape)}] {track['name'][:55]:<55}", end=" ", flush=True)

        features = get_audio_features(session, tid)
        info = get_track_info(session, tid)

        if features is not None:
            result = build_result(track, features, info)
            results.append(result)
            new_since_checkpoint += 1
            progression = result.get("progression") or "N/A"
            bpm = result.get("tempo_bpm") or 0
            print(f"OK  {progression:<14}  {bpm:.0f} BPM")
        else:
            failed += 1
            print("FAIL  nessun dato")

        # Checkpoint
        if new_since_checkpoint >= CHECKPOINT_EVERY:
            _save(results, output_path)
            print(f"    [SAVE] Checkpoint: {len(results)} totali salvate")
            new_since_checkpoint = 0

        # Pausa anti-blocco
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    # Salvataggio finale
    _save(results, output_path)
    print(f"\n[OK] Completato! {len(results)} tracce salvate in '{OUTPUT_FILE}'")
    print(f"[ERR] Fallite: {failed}")
    _print_summary(results)


def _save(results: list[dict], path: Path) -> None:
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


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
