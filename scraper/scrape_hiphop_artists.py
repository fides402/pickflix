#!/usr/bin/env python3
"""
Scraper per i 30 brani piu' famosi di 10 artisti hip-hop.
Usa l'API Spotify anonima (token da embed) + Jamstart per audio features.

Artisti: Earl Sweatshirt, Navy Blue, Kanye West, The Alchemist,
         Westside Gunn, Roc Marciano, Conway the Machine, Mick Jenkins,
         Joey Badass, J Cole

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
TOP_N       = 30
CHECKPOINT  = 5    # salva ogni N artisti completati
DELAY       = (0.5, 1.0)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"

ARTISTS = [
    "Earl Sweatshirt",
    "Navy Blue",
    "Kanye West",
    "The Alchemist",
    "Westside Gunn",
    "Roc Marciano",
    "Conway the Machine",
    "Mick Jenkins",
    "Joey Badass",
    "J Cole",
]

# IDs noti per bootstrap del token (basta che uno funzioni)
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
# Token
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
                r.text, re.S
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
            print(f"[WARN] Token da {aid[:8]}: {e}")
    return None


# ---------------------------------------------------------------------------
# Spotify API (anonymous token)
# ---------------------------------------------------------------------------

def _spotify(session, token, endpoint_or_url, params=None, retries=3) -> dict | None:
    url = (endpoint_or_url if endpoint_or_url.startswith("https://")
           else f"https://api.spotify.com/v1/{endpoint_or_url}")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": UA}
    for attempt in range(retries):
        try:
            r = session.get(url, headers=headers, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                print("[WARN] Token scaduto")
                return None
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 10))
                if wait > 120:
                    print(f"[RATE] Spotify 429, pausa lunga ({wait}s) — skip")
                    return None
                print(f"[RATE] 429, attendo {wait}s...")
                time.sleep(wait)
            elif r.status_code == 404:
                return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


def search_artist(session, token, name: str) -> tuple[str | None, str | None]:
    data = _spotify(session, token, "search", {"q": name, "type": "artist", "limit": 5, "market": "US"})
    if not data:
        return None, None
    items = data.get("artists", {}).get("items", [])
    if not items:
        return None, None

    # Pulizia nome per confronto
    def clean(s):
        return re.sub(r"[^a-z0-9]", "", s.lower())

    name_c = clean(name)
    # Match esatto
    for a in items:
        if clean(a["name"]) == name_c:
            return a["id"], a["name"]
    # Match parziale
    for a in items:
        ac = clean(a["name"])
        if name_c in ac or ac in name_c:
            return a["id"], a["name"]
    # Primo con follower significativi
    for a in items:
        if a.get("followers", {}).get("total", 0) > 5000:
            return a["id"], a["name"]
    return items[0]["id"], items[0]["name"]


def get_top_tracks(session, token, artist_id: str) -> list[dict]:
    data = _spotify(session, token, f"artists/{artist_id}/top-tracks", {"market": "US"})
    return data.get("tracks", []) if data else []


def get_album_ids(session, token, artist_id: str) -> list[str]:
    ids = []
    url = f"artists/{artist_id}/albums"
    params = {"include_groups": "album,single", "limit": 50, "market": "US"}
    while url:
        data = _spotify(session, token, url, params)
        if not data:
            break
        ids.extend(item["id"] for item in data.get("items", []))
        url    = data.get("next")
        params = None
    return ids


def get_album_track_ids(session, token, album_id: str) -> list[str]:
    data = _spotify(session, token, f"albums/{album_id}/tracks", {"limit": 50, "market": "US"})
    if not data:
        return []
    return [t["id"] for t in data.get("items", []) if t and t.get("id")]


def batch_full_tracks(session, token, track_ids: list[str]) -> list[dict]:
    results = []
    for i in range(0, len(track_ids), 50):
        batch = track_ids[i:i+50]
        data = _spotify(session, token, "tracks", {"ids": ",".join(batch), "market": "US"})
        if data:
            results.extend(t for t in data.get("tracks", []) if t)
        time.sleep(random.uniform(0.3, 0.6))
    return results


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
# Build result record
# ---------------------------------------------------------------------------

def build_result(artist_name: str, track: dict, feats: dict) -> dict:
    key_n  = feats.get("key", -1)
    mode_n = feats.get("mode", -1)
    key    = NOTE_NAMES[key_n] if 0 <= key_n <= 11 else None
    mode   = "major" if mode_n == 1 else ("minor" if mode_n == 0 else None)

    album  = track.get("album") or {}
    artists_str = ", ".join(a.get("name","") for a in track.get("artists",[]))

    return {
        "spotify_id":       track.get("id",""),
        "title":            track.get("name",""),
        "artist":           artist_name,
        "artists":          artists_str,
        "album":            album.get("name",""),
        "year":             (album.get("release_date") or "")[:4],
        "popularity":       track.get("popularity", 0),
        "duration_ms":      track.get("duration_ms", 0),
        "key":              key,
        "mode":             mode,
        "progression":      f"{key} {mode}" if key and mode else None,
        "tempo_bpm":        round(feats["tempo"], 1) if feats.get("tempo") else None,
        "time_signature":   f"{feats.get('time_signature',4)}/4",
        "danceability":     feats.get("danceability"),
        "energy":           feats.get("energy"),
        "acousticness":     feats.get("acousticness"),
        "instrumentalness": feats.get("instrumentalness"),
        "valence":          feats.get("valence"),
        "loudness_db":      feats.get("loudness"),
        "speechiness":      feats.get("speechiness"),
        "liveness":         feats.get("liveness"),
        "jamstart_url":     f"https://jamstart.app/song_info/{track.get('id','')}",
    }


# ---------------------------------------------------------------------------
# Scraper per singolo artista
# ---------------------------------------------------------------------------

def scrape_artist(session, token, artist_name: str, existing_ids: set) -> list[dict]:
    print(f"\n{'='*55}")
    print(f"  ARTISTA: {artist_name}")
    print(f"{'='*55}")

    artist_id, display = search_artist(session, token, artist_name)
    if not artist_id:
        print(f"  [SKIP] '{artist_name}' non trovato")
        return []
    print(f"  [FIND] '{display}'  (ID: {artist_id})")
    time.sleep(random.uniform(*DELAY))

    # Step 1 — top-tracks (10, con popularity)
    top = get_top_tracks(session, token, artist_id)
    print(f"  [TOP]  {len(top)} top tracks")
    time.sleep(random.uniform(*DELAY))

    track_map: dict[str, dict] = {t["id"]: t for t in top}

    # Step 2 — album tracks per raggiungere TOP_N
    if len(track_map) < TOP_N:
        album_ids = get_album_ids(session, token, artist_id)
        print(f"  [ALBS] {len(album_ids)} album/singoli")
        time.sleep(random.uniform(*DELAY))

        extra_ids: list[str] = []
        for alb in album_ids[:25]:
            for tid in get_album_track_ids(session, token, alb):
                if tid not in track_map:
                    extra_ids.append(tid)
            time.sleep(random.uniform(0.2, 0.4))
            if len(extra_ids) >= TOP_N * 6:
                break

        if extra_ids:
            cap = TOP_N * 6
            print(f"  [BTCH] Fetch popularity per {min(len(extra_ids),cap)} tracce extra...")
            for t in batch_full_tracks(session, token, extra_ids[:cap]):
                if t and t.get("id") and t["id"] not in track_map:
                    track_map[t["id"]] = t

    # Ordina per popularity e prendi top N (escludendo duplicati già salvati)
    sorted_tracks = sorted(
        (t for t in track_map.values() if t["id"] not in existing_ids),
        key=lambda t: t.get("popularity", 0),
        reverse=True,
    )
    best = sorted_tracks[:TOP_N]
    if not best:
        print(f"  [SKIP] Nessuna traccia nuova")
        return []

    pops = [t.get("popularity",0) for t in best]
    print(f"  [BEST] {len(best)} brani  (popularity {max(pops)}..{min(pops)})")

    # Step 3 — audio features via Jamstart
    results = []
    for i, track in enumerate(best):
        title = track.get("name", track["id"][:12])
        print(f"  [{i+1:>2}/{len(best)}] '{title[:42]}'", end=" ", flush=True)

        feats  = jam_features(session, track["id"])
        rec    = build_result(artist_name, track, feats)
        results.append(rec)

        bpm = rec.get("tempo_bpm") or "-"
        key = rec.get("progression") or "-"
        pop = rec.get("popularity", 0)
        spch = round(feats.get("speechiness", 0), 2) if feats else "-"
        print(f"pop={pop}  bpm={bpm}  [{key}]  speech={spch}")
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
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    session = requests.Session()

    print("[*] Estrazione token Spotify...")
    token = extract_token(session)
    if not token:
        print("[ERR] Token non disponibile. Controlla la connessione.")
        sys.exit(1)

    pending = [a for a in ARTISTS if a not in done_artists]
    total   = len(pending)
    print(f"[*] {total} artisti da processare: {', '.join(pending)}\n")

    for i, artist in enumerate(pending):
        artist_results = scrape_artist(session, token, artist, existing_ids)
        results.extend(artist_results)
        existing_ids.update(r["spotify_id"] for r in artist_results)
        done_artists.add(artist)

        save()
        saved = len(results)
        print(f"\n  [SAVE] [{i+1}/{total}] {saved} brani totali salvati")
        time.sleep(random.uniform(1.5, 2.5))

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
            print(f"  {artist:<28}  --")
            continue
        avg_pop  = round(sum(t.get("popularity",0) for t in tracks) / len(tracks))
        avg_bpm  = round(sum(t["tempo_bpm"] for t in tracks if t.get("tempo_bpm")) /
                         max(1, sum(1 for t in tracks if t.get("tempo_bpm"))))
        print(f"  {artist:<28} {len(tracks):>3} brani  pop~{avg_pop}  bpm~{avg_bpm}")


if __name__ == "__main__":
    main()
