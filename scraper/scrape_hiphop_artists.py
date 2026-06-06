#!/usr/bin/env python3
"""
Scraper per i 30 brani piu' famosi di 10 artisti hip-hop.

Strategia (NO Spotify API — bypassa il rate-limit):
  1. open.spotify.com/embed/artist/{id}  →  seed tracks (top 5-10 di Spotify)
  2. Jamstart get_track_info              →  album ID per ogni seed track
  3. open.spotify.com/embed/album/{id}   →  tutti i brani dell'album
  4. BFS fino a 30 brani per artista
  5. Jamstart get_single_audio_features  →  key, mode, BPM, danceability…

Output: hiphop_tracks.json

Se un artista non viene trovato: cerca il suo profilo su open.spotify.com,
copia l'ID dall'URL (es. open.spotify.com/artist/XXXXXXX) e aggiorna
la lista ARTISTS qui sotto.
"""

import json
import random
import re
import sys
import time
from collections import deque
from pathlib import Path

import requests

OUTPUT_FILE = "hiphop_tracks.json"
TOP_N       = 30         # brani per artista
CHECKPOINT  = 5          # salva ogni N artisti completati
DELAY_JAM   = (0.5, 1.0)
DELAY_EMBED = (0.3, 0.7)
MAX_RETRIES = 4

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
EMBED_HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}
JAM_HEADERS   = {
    "User-Agent": UA, "Content-Type": "application/json",
    "Referer": "https://jamstart.app/", "Origin": "https://jamstart.app",
    "Accept": "application/json, */*",
}

NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

# ---------------------------------------------------------------------------
# Artist IDs Spotify (hardcoded)
# Se un ID e' sbagliato, il validatore stampa il nome trovato — correggilo qui.
# Come trovare l'ID: open.spotify.com → cerca artista → copia ID dall'URL
# ---------------------------------------------------------------------------
ARTISTS = [
    {"name": "Earl Sweatshirt",    "id": "1cnLNGCMhGfnuAOSMCJ8mW"},
    {"name": "Navy Blue",          "id": "3FYpJpFYiJXEXA8EO4cgf0"},
    {"name": "Kanye West",         "id": "5K4W6rqBFWDnAN6FQUkS6x"},
    {"name": "The Alchemist",      "id": "2yzxX7ue8iKSnBDFm9UkQV"},
    {"name": "Westside Gunn",      "id": "3oqwnCMoKxOm9lDfXRFRCe"},
    {"name": "Roc Marciano",       "id": "0c8fZQZH3gBq5aBdHcRZDi"},
    {"name": "Conway the Machine", "id": "5QvXJRXiqaHlvHdJ8cLNlP"},
    {"name": "Mick Jenkins",       "id": "2aRISK0oKkXNniqKGz3vmq"},
    {"name": "Joey Bada$$",        "id": "5BHbNGHsJgr8IYnfBBJgOL"},
    {"name": "J. Cole",            "id": "6l3HvQ5sa6mXTsMTB6okmg"},
]


# ---------------------------------------------------------------------------
# Embed utilities (stesso approccio del scraper Piccioni)
# ---------------------------------------------------------------------------

def _next_data(html: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


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


def get_artist_embed_data(session, artist_id: str) -> tuple[list[str], str]:
    """
    Carica l'embed artista, ritorna (seed_track_ids, artist_name_found).
    I seed tracks sono gia' ordinati per popolarita' (sono i top track di Spotify).
    """
    html = fetch_embed(session, f"https://open.spotify.com/embed/artist/{artist_id}")
    if not html:
        return [], ""
    nd = _next_data(html)
    entity = (
        nd.get("props", {}).get("pageProps", {}).get("state", {})
          .get("data", {}).get("entity", {})
    )
    name   = entity.get("name", "")
    tracks = entity.get("trackList", [])
    ids    = [
        t.get("uri", "").split(":")[-1]
        for t in tracks
        if t.get("uri", "").startswith("spotify:track:")
    ]
    return ids, name


def get_album_embed_data(session, album_id: str) -> tuple[list[str], str, str]:
    """
    Carica l'embed album, ritorna (track_ids, album_name, release_year).
    """
    html = fetch_embed(session, f"https://open.spotify.com/embed/album/{album_id}")
    if not html:
        return [], "", ""
    nd = _next_data(html)
    entity = (
        nd.get("props", {}).get("pageProps", {}).get("state", {})
          .get("data", {}).get("entity", {})
    )
    name  = entity.get("name", "")
    year  = (entity.get("releaseDate") or entity.get("release_date") or "")[:4]
    tracks= entity.get("trackList", [])
    ids   = [
        t.get("uri", "").split(":")[-1]
        for t in tracks
        if t.get("uri", "").startswith("spotify:track:")
    ]
    return ids, name, year


# ---------------------------------------------------------------------------
# Jamstart (no Spotify API, usa il suo token interno)
# ---------------------------------------------------------------------------

def _jam_post(session, endpoint: str, payload: dict) -> dict | None:
    url = f"https://jamstart.app/api/spotify_utils/{endpoint}"
    for attempt in range(MAX_RETRIES):
        try:
            r = session.post(url, json=payload, headers=JAM_HEADERS, timeout=12)
            if r.status_code == 200:
                body = r.json()
                return body if isinstance(body, dict) else None
            if r.status_code == 429:
                w = 2 ** (attempt + 1) + random.uniform(0, 1)
                print(f"  [jam] rate limit, attendo {w:.1f}s")
                time.sleep(w)
            else:
                return None
        except (requests.RequestException, ValueError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(1.5)
    return None


def jam_track_info(session, track_id: str) -> dict | None:
    d = _jam_post(session, "get_track_info", {"trackID": track_id})
    return d.get("trackData") if d else None


def jam_audio_features(session, track_id: str) -> dict:
    d = _jam_post(session, "get_single_audio_features", {"trackID": track_id})
    if not d:
        return {}
    return d.get("audioFeatures") or d.get("trackIdKeyAndMode") or {}


# ---------------------------------------------------------------------------
# Scraper per singolo artista (embed BFS)
# ---------------------------------------------------------------------------

def scrape_artist(session, artist_cfg: dict, existing_ids: set) -> list[dict]:
    artist_name = artist_cfg["name"]
    artist_id   = artist_cfg["id"]

    print(f"\n{'='*55}")
    print(f"  ARTISTA: {artist_name}")
    print(f"  ID:      {artist_id}")
    print(f"{'='*55}")

    # Step 1: artist embed → seed tracks (top-N di Spotify, gia' ordinati)
    seed_ids, found_name = get_artist_embed_data(session, artist_id)
    time.sleep(random.uniform(*DELAY_EMBED))

    if not found_name:
        print(f"  [SKIP] Embed non risponde o ID errato ('{artist_id}')")
        print(f"  [HINT] Vai su open.spotify.com, cerca '{artist_name}',")
        print(f"         copia l'ID dall'URL e aggiornalo in ARTISTS")
        return []

    # Validazione ID
    fn_lower = found_name.lower()
    an_lower = artist_name.lower()
    if an_lower not in fn_lower and fn_lower not in an_lower:
        print(f"  [WARN] ID errato! Trovato '{found_name}', atteso '{artist_name}'")
        print(f"  [HINT] Cerca '{artist_name}' su open.spotify.com e copia l'ID dall'URL")
        return []
    print(f"  [OK]   Artista verificato: '{found_name}'")
    print(f"  [SEED] {len(seed_ids)} top tracks dall'embed")

    # Step 2: BFS attraverso album per raccogliere fino a TOP_N tracks
    seen_ids:   set[str] = set(seed_ids)
    done_albums: set[str] = set()
    ordered_ids: list[str] = [i for i in seed_ids if i not in existing_ids]
    album_queue: deque[str] = deque()

    # Dalla seed, scopri album via Jamstart
    for seed_id in seed_ids:
        if len(ordered_ids) >= TOP_N * 2:
            break
        info = jam_track_info(session, seed_id)
        time.sleep(random.uniform(*DELAY_JAM))
        if not info:
            continue
        album = info.get("album") or {}
        alb_id = album.get("id")
        if alb_id and alb_id not in done_albums:
            done_albums.add(alb_id)
            album_queue.append(alb_id)

    # Vai in profondità negli album
    while album_queue and len(ordered_ids) < TOP_N * 2:
        alb_id = album_queue.popleft()
        track_ids, alb_name, alb_year = get_album_embed_data(session, alb_id)
        time.sleep(random.uniform(*DELAY_EMBED))
        print(f"  [ALBUM] '{alb_name[:45]}' ({alb_year}) → {len(track_ids)} tracce")
        for tid in track_ids:
            if tid not in seen_ids:
                seen_ids.add(tid)
                if tid not in existing_ids:
                    ordered_ids.append(tid)

    # Prendi i primi TOP_N (seed = più famosi vengono prima)
    best_ids = ordered_ids[:TOP_N]
    print(f"  [BEST] {len(best_ids)} brani da processare")

    # Step 3: audio features per ogni brano
    results = []
    for i, tid in enumerate(best_ids):
        # Prova a ottenere info brano (nome, album) da Jamstart se non già nota
        info  = jam_track_info(session, tid)
        time.sleep(random.uniform(*DELAY_JAM))
        feats = jam_audio_features(session, tid)
        time.sleep(random.uniform(*DELAY_JAM))

        rec = _build_result(artist_name, tid, info, feats)
        results.append(rec)

        title = rec.get("title") or tid[:12]
        bpm   = rec.get("tempo_bpm") or "–"
        key   = rec.get("progression") or "–"
        print(f"  [{i+1:>2}/{len(best_ids)}] '{title[:40]}'  [{key}]  bpm={bpm}")

    return results


def _build_result(artist_name: str, track_id: str, info: dict | None, feats: dict) -> dict:
    info = info or {}
    album = info.get("album") or {}
    artists_str = ", ".join(
        a.get("name", "") for a in info.get("artists", [])
    ) or artist_name

    key_n  = feats.get("key", -1)
    mode_n = feats.get("mode", -1)
    key    = NOTE_NAMES[key_n] if 0 <= key_n <= 11 else None
    mode   = "major" if mode_n == 1 else ("minor" if mode_n == 0 else None)

    return {
        "spotify_id":       track_id,
        "title":            info.get("name", ""),
        "artist":           artist_name,
        "artists":          artists_str,
        "album":            album.get("name", ""),
        "year":             (album.get("release_date") or "")[:4],
        "popularity":       info.get("popularity", 0),
        "duration_ms":      info.get("duration_ms", 0),
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
        "jamstart_url":     f"https://jamstart.app/song_info/{track_id}",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    output = Path(OUTPUT_FILE)

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

    # Test embed (non usa l'API Spotify)
    print("[*] Test embed Spotify...")
    test_html = fetch_embed(session, "https://open.spotify.com/embed/artist/5K4W6rqBFWDnAN6FQUkS6x")
    if not test_html:
        print("[ERR] Embed Spotify non raggiungibile. Controlla la connessione.")
        sys.exit(1)
    print("[*] Embed OK — nessuna API Spotify necessaria\n")

    pending = [a for a in ARTISTS if a["name"] not in done_artists]
    total   = len(pending)
    print(f"[*] {total} artisti da processare\n")

    for i, artist_cfg in enumerate(pending):
        artist_results = scrape_artist(session, artist_cfg, existing_ids)
        results.extend(artist_results)
        existing_ids.update(r["spotify_id"] for r in artist_results)
        done_artists.add(artist_cfg["name"])

        save()
        print(f"\n  [SAVE] [{i+1}/{total}] {len(results)} brani totali")
        time.sleep(random.uniform(1.0, 2.0))

    save()
    print(f"\n[OK] Completato! {len(results)} brani in '{OUTPUT_FILE}'")
    _summary(results)


def _summary(results: list[dict]):
    from collections import defaultdict
    print("\nRIEPILOGO PER ARTISTA:")
    by_artist: dict = defaultdict(list)
    for r in results:
        by_artist[r["artist"]].append(r)
    for a in ARTISTS:
        tracks = by_artist.get(a["name"], [])
        if not tracks:
            print(f"  {a['name']:<28}  0 brani  ← verifica ID")
            continue
        bpms = [t["tempo_bpm"] for t in tracks if t.get("tempo_bpm")]
        avg_bpm = round(sum(bpms) / len(bpms)) if bpms else "–"
        pops = [t["popularity"] for t in tracks if t.get("popularity")]
        avg_pop = round(sum(pops) / len(pops)) if pops else "–"
        print(f"  {a['name']:<28} {len(tracks):>3} brani  bpm~{avg_bpm}  pop~{avg_pop}")


if __name__ == "__main__":
    main()
