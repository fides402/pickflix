#!/usr/bin/env python3
"""
Scraper per i 30 brani piu' famosi di 10 artisti hip-hop.
Usa l'API Spotify anonima (token da embed) + Jamstart per audio features.

Strategia: cerca brani con  q=artist:"nome"&type=track
  - funziona col token anonimo (stesso endpoint usato dallo scraper Piccioni)
  - restituisce gia' il campo popularity → nessuna batch-fetch aggiuntiva

Output: hiphop_tracks.json
"""

import json
import re
import sys
import time
import random
from collections import defaultdict
from pathlib import Path

import requests

OUTPUT_FILE = "hiphop_tracks.json"
TOP_N       = 30        # brani per artista
DELAY       = (0.5, 1.0)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"

# Nomi ESATTI come appaiono su Spotify
ARTISTS = [
    "Earl Sweatshirt",
    "Navy Blue",
    "Kanye West",
    "The Alchemist",
    "Westside Gunn",
    "Roc Marciano",
    "Conway the Machine",
    "Mick Jenkins",
    "Joey Bada$$",
    "J. Cole",
]

# IDs noti per bootstrap token (basta che uno sia valido)
TOKEN_BOOTSTRAP = [
    "3TVXtAsR1Inumwj472S9r4",  # Drake
    "5K4W6rqBFWDnAN6FQUkS6x",  # Kanye West
    "1Xyo4u8uXC1ZmMpatF05PJ",  # The Weeknd
]

JAM_HEADERS = {
    "User-Agent": UA,
    "Content-Type": "application/json",
    "Referer": "https://jamstart.app/",
    "Origin": "https://jamstart.app",
    "Accept": "application/json, */*",
}

NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]


# ---------------------------------------------------------------------------
# Token anonimo da embed Spotify
# ---------------------------------------------------------------------------

def extract_token(session: requests.Session) -> str | None:
    for aid in TOKEN_BOOTSTRAP:
        try:
            r = session.get(
                f"https://open.spotify.com/embed/artist/{aid}",
                headers={"User-Agent": UA},
                timeout=15,
            )
            m = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
                r.text, re.S,
            )
            if not m:
                continue
            token = (
                json.loads(m.group(1))
                    .get("props", {})
                    .get("pageProps", {})
                    .get("state", {})
                    .get("settings", {})
                    .get("session", {})
                    .get("accessToken")
            )
            if token:
                print(f"[TOKEN] OK")
                return token
        except Exception as e:
            print(f"[WARN] Token da {aid[:8]}...: {e}")
    return None


# ---------------------------------------------------------------------------
# Spotify API helper
# ---------------------------------------------------------------------------

def _spotify(session, token, endpoint_or_url, params=None, retries=3) -> dict | None:
    url = (endpoint_or_url if endpoint_or_url.startswith("https://")
           else f"https://api.spotify.com/v1/{endpoint_or_url}")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": UA,
    }
    for attempt in range(retries):
        try:
            r = session.get(url, headers=headers, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                print("[WARN] Token scaduto o non valido")
                return None
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 10))
                if wait > 120:
                    print(f"[RATE] 429 con Retry-After={wait}s — skip")
                    return None
                print(f"[RATE] 429, attendo {wait}s...")
                time.sleep(wait)
            elif r.status_code == 404:
                return None
            else:
                print(f"[WARN] HTTP {r.status_code} per {url[:60]}")
                time.sleep(1)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"[ERR] {e}")
    return None


# ---------------------------------------------------------------------------
# Ricerca brani per artista (endpoint che funziona col token anonimo)
# ---------------------------------------------------------------------------

def search_tracks_by_artist(session, token, artist_name: str, n: int = TOP_N) -> list[dict]:
    """
    Usa Spotify Search API con  q=artist:"nome"&type=track.
    Questo endpoint funziona col token anonimo e include gia' popularity.
    Pagina fino a raccogliere n*4 candidati, poi ordina per popularity.
    """
    tracks: dict[str, dict] = {}
    offset = 0
    pages  = 0

    while len(tracks) < n * 4 and offset < 1000 and pages < 10:
        data = _spotify(session, token, "search", {
            "q":      f'artist:"{artist_name}"',
            "type":   "track",
            "limit":  50,
            "market": "US",
            "offset": offset,
        })

        if not data:
            print(f"    [WARN] Search vuota a offset={offset}")
            break

        items = data.get("tracks", {}).get("items", [])
        total = data.get("tracks", {}).get("total", 0)

        if pages == 0:
            print(f"    [SEARCH] '{artist_name}' → {total} risultati totali su Spotify")

        if not items:
            break

        for t in items:
            if not t or not t.get("id"):
                continue
            # Mantieni solo se l'artista target e' tra i crediti
            track_artists = [a.get("name", "").lower() for a in t.get("artists", [])]
            target_lower  = artist_name.lower()
            if any(target_lower in ta or ta in target_lower for ta in track_artists):
                tracks[t["id"]] = t

        if len(items) < 50:
            break

        offset += 50
        pages  += 1
        time.sleep(random.uniform(0.3, 0.6))

    if not tracks:
        # Fallback: ricerca senza virgolette (piu' permissiva)
        print(f"    [RETRY] Riprovo senza virgolette...")
        data = _spotify(session, token, "search", {
            "q":      f'artist:{artist_name}',
            "type":   "track",
            "limit":  50,
            "market": "US",
        })
        if data:
            for t in (data.get("tracks", {}).get("items", []) or []):
                if t and t.get("id"):
                    tracks[t["id"]] = t

    sorted_tracks = sorted(
        tracks.values(),
        key=lambda t: t.get("popularity", 0),
        reverse=True,
    )
    return sorted_tracks[:n]


# ---------------------------------------------------------------------------
# Jamstart audio features
# ---------------------------------------------------------------------------

def jam_features(session, track_id: str) -> dict:
    for attempt in range(2):
        try:
            r = session.post(
                "https://jamstart.app/api/spotify_utils/get_single_audio_features",
                json={"trackID": track_id},
                headers=JAM_HEADERS,
                timeout=12,
            )
            if r.status_code == 200:
                return r.json().get("audioFeatures") or {}
            if r.status_code == 429:
                time.sleep(4)
        except Exception:
            time.sleep(1)
    return {}


# ---------------------------------------------------------------------------
# Costruisce il record finale
# ---------------------------------------------------------------------------

def build_result(artist_name: str, track: dict, feats: dict) -> dict:
    key_n  = feats.get("key", -1)
    mode_n = feats.get("mode", -1)
    key    = NOTE_NAMES[key_n] if 0 <= key_n <= 11 else None
    mode   = "major" if mode_n == 1 else ("minor" if mode_n == 0 else None)
    album  = track.get("album") or {}
    artists_str = ", ".join(a.get("name", "") for a in track.get("artists", []))

    return {
        "spotify_id":       track.get("id", ""),
        "title":            track.get("name", ""),
        "artist":           artist_name,
        "artists":          artists_str,
        "album":            album.get("name", ""),
        "year":             (album.get("release_date") or "")[:4],
        "popularity":       track.get("popularity", 0),
        "duration_ms":      track.get("duration_ms", 0),
        "key":              key,
        "mode":             mode,
        "progression":      f"{key} {mode}" if key and mode else None,
        "tempo_bpm":        round(feats["tempo"], 1) if feats.get("tempo") else None,
        "time_signature":   f"{feats.get('time_signature', 4)}/4",
        "danceability":     feats.get("danceability"),
        "energy":           feats.get("energy"),
        "acousticness":     feats.get("acousticness"),
        "instrumentalness": feats.get("instrumentalness"),
        "valence":          feats.get("valence"),
        "loudness_db":      feats.get("loudness"),
        "speechiness":      feats.get("speechiness"),
        "liveness":         feats.get("liveness"),
        "jamstart_url":     f"https://jamstart.app/song_info/{track.get('id', '')}",
    }


# ---------------------------------------------------------------------------
# Scraper per singolo artista
# ---------------------------------------------------------------------------

def scrape_artist(session, token, artist_name: str, existing_ids: set) -> list[dict]:
    print(f"\n{'='*55}")
    print(f"  ARTISTA: {artist_name}")
    print(f"{'='*55}")

    # Trova i top brani via search
    best = [t for t in search_tracks_by_artist(session, token, artist_name)
            if t["id"] not in existing_ids][:TOP_N]

    if not best:
        print(f"  [SKIP] Nessun brano trovato per '{artist_name}'")
        return []

    pops = [t.get("popularity", 0) for t in best]
    print(f"  [BEST] {len(best)} brani  (popularity {max(pops)}..{min(pops)})")

    # Audio features via Jamstart
    results = []
    for i, track in enumerate(best):
        title = track.get("name", track["id"][:12])
        print(f"  [{i+1:>2}/{len(best)}] '{title[:42]}'", end=" ", flush=True)

        feats = jam_features(session, track["id"])
        rec   = build_result(artist_name, track, feats)
        results.append(rec)

        bpm   = rec.get("tempo_bpm") or "–"
        key   = rec.get("progression") or "–"
        pop   = rec.get("popularity", 0)
        spch  = round(feats.get("speechiness", 0), 2) if feats else "–"
        print(f"  pop={pop}  bpm={bpm}  [{key}]  speech={spch}")
        time.sleep(random.uniform(*DELAY))

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    output = Path(OUTPUT_FILE)

    # Checkpoint
    results: list[dict] = []
    done_artists: set[str] = set()
    if output.exists():
        try:
            results = json.loads(output.read_text(encoding="utf-8"))
            done_artists = {r["artist"] for r in results}
            print(f"[CKPT] {len(results)} brani ({len(done_artists)} artisti completati)")
        except Exception:
            pass

    existing_ids = {r["spotify_id"] for r in results}

    def save():
        output.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    session = requests.Session()

    print("[*] Estrazione token Spotify...")
    token = extract_token(session)
    if not token:
        print("[ERR] Token non disponibile. Controlla la connessione a internet.")
        sys.exit(1)

    # Verifica rapida che la search API funzioni
    print("[*] Test search API...")
    test = _spotify(session, token, "search", {"q": "artist:Drake", "type": "track", "limit": 1, "market": "US"})
    if not test:
        print("[ERR] Search API non risponde. Il token potrebbe non supportare questa funzione.")
        sys.exit(1)
    print(f"[*] Search API OK — trovato: {test.get('tracks',{}).get('items',[{}])[0].get('name','?')}")

    pending = [a for a in ARTISTS if a not in done_artists]
    total   = len(pending)
    print(f"[*] {total} artisti da processare\n")

    for i, artist in enumerate(pending):
        artist_results = scrape_artist(session, token, artist, existing_ids)
        results.extend(artist_results)
        existing_ids.update(r["spotify_id"] for r in artist_results)
        done_artists.add(artist)

        save()
        print(f"\n  [SAVE] [{i+1}/{total}] {len(results)} brani totali in '{OUTPUT_FILE}'")
        time.sleep(random.uniform(1.0, 2.0))

    save()
    print(f"\n[OK] Completato! {len(results)} brani in '{OUTPUT_FILE}'")
    _summary(results)


def _summary(results: list[dict]):
    print("\nRIEPILOGO PER ARTISTA:")
    by_artist = defaultdict(list)
    for r in results:
        by_artist[r["artist"]].append(r)
    for artist in ARTISTS:
        tracks = by_artist.get(artist, [])
        if not tracks:
            print(f"  {artist:<28}  0 brani")
            continue
        avg_pop = round(sum(t.get("popularity", 0) for t in tracks) / len(tracks))
        bpms    = [t["tempo_bpm"] for t in tracks if t.get("tempo_bpm")]
        avg_bpm = round(sum(bpms) / len(bpms)) if bpms else "–"
        print(f"  {artist:<28} {len(tracks):>3} brani  pop~{avg_pop}  bpm~{avg_bpm}")


if __name__ == "__main__":
    main()
