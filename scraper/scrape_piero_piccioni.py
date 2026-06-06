#!/usr/bin/env python3
"""
Scraper progressioni armoniche di Piero Piccioni.

Metodo 1 (veloce): estrae token anonimo da embed Spotify, chiama Spotify Web API
  per ottenere tutti gli album/tracce in pochi secondi senza credenziali.

Metodo 2 (fallback BFS): se l'API Spotify e' bloccata (rate limit IP),
  usa embed pages + Jamstart get_track_info per trovare album ID via BFS.

Output: songs_progressions.json  (checkpoint ogni 50 tracce, riprendibile)
"""

import json
import random
import re
import sys
import time
from collections import deque
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
TARGET      = 1000
OUTPUT_FILE = "songs_progressions.json"
CHECKPOINT  = 50
DELAY_JAM   = (0.5, 1.0)
DELAY_EMBED = (0.3, 0.7)
DELAY_API   = (0.15, 0.35)
MAX_RETRIES = 4

ARTIST_ID = "2WPn0emjr8XPmMOT0bBcPe"   # Piero Piccioni

KEY_NAMES  = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
MODE_NAMES = {0: "minor", 1: "major"}

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
# Embed utilities
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


def extract_token(session: requests.Session) -> str | None:
    """Estrae l'accessToken anonimo dall'embed Spotify (nessun account richiesto)."""
    urls = [
        f"https://open.spotify.com/embed/artist/{ARTIST_ID}",
        "https://open.spotify.com/embed/track/68wSf9grpSGuK6C1SfG2kG",
    ]
    for url in urls:
        html = fetch_embed(session, url)
        if not html:
            continue
        nd = _next_data(html)
        token = (
            nd.get("props", {})
              .get("pageProps", {})
              .get("state", {})
              .get("settings", {})
              .get("session", {})
              .get("accessToken")
        )
        if token:
            return token
        time.sleep(1)
    return None


# ---------------------------------------------------------------------------
# Metodo 1: Spotify Web API con token anonimo
# ---------------------------------------------------------------------------

def _spotify_get(session: requests.Session, token: str, path: str, params: dict = None) -> dict | None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": EMBED_HEADERS["User-Agent"],
    }
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(
                f"https://api.spotify.com/v1/{path}",
                headers=headers, params=params, timeout=15
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                return None  # token scaduto
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", 0))
                if retry_after > 300:
                    return {"_rate_limit_long": True}
                w = min(retry_after or 5 * (attempt + 1), 30)
                print(f"  [spotify api] rate limit, attendo {w}s")
                time.sleep(w)
            else:
                return None
        except requests.RequestException:
            time.sleep(2)
    return None


def _fetch_all_artist_albums(session, token, include_groups: str) -> list[dict] | None:
    """Scarica tutti gli album di un artista per un dato include_groups."""
    albums = []
    params = {"include_groups": include_groups, "limit": 50, "offset": 0}
    while True:
        data = _spotify_get(session, token, f"artists/{ARTIST_ID}/albums", params)
        if not data:
            return None
        if data.get("_rate_limit_long"):
            return {"_rate_limit_long": True}
        for item in data.get("items", []):
            albums.append({
                "id":           item["id"],
                "name":         item.get("name", ""),
                "release_date": item.get("release_date", ""),
                "total_tracks": item.get("total_tracks", 0),
                "appears_on":   False,
            })
        if not data.get("next") or len(albums) >= data.get("total", 0):
            break
        params["offset"] += 50
        time.sleep(random.uniform(*DELAY_API))
    return albums


def _search_artist_albums(session, token) -> list[dict]:
    """Cerca album con 'Piero Piccioni' nel titolo via Spotify search."""
    albums = []
    seen = set()
    params = {"q": "Piero Piccioni", "type": "album", "limit": 50, "offset": 0}
    for _ in range(6):   # max 300 risultati
        data = _spotify_get(session, token, "search", params)
        if not data or data.get("_rate_limit_long"):
            break
        items = data.get("albums", {}).get("items", [])
        if not items:
            break
        for item in items:
            if item["id"] not in seen:
                seen.add(item["id"])
                albums.append({
                    "id":           item["id"],
                    "name":         item.get("name", ""),
                    "release_date": item.get("release_date", ""),
                    "total_tracks": item.get("total_tracks", 0),
                    "appears_on":   True,
                })
        if not data.get("albums", {}).get("next"):
            break
        params["offset"] += 50
        time.sleep(random.uniform(*DELAY_API))
    return albums


def collect_tracks_via_api(session: requests.Session, token: str) -> list[dict] | None:
    """
    Raccoglie tutti i track IDs via Spotify API (metodo veloce).
    - album/single/compilation: artista principale
    - appears_on: compilation dove compare
    - search: album con 'Piero Piccioni' nel titolo
    Ritorna None se l'API e' bloccata (rate limit lungo).
    """
    print("[*] Metodo veloce: Spotify API con token anonimo")

    # 1. Album come artista principale
    all_albums = []
    seen_album_ids: set[str] = set()

    for group in ["album,single,compilation", "appears_on"]:
        result = _fetch_all_artist_albums(session, token, group)
        if result is None:
            print("    Token scaduto o API non disponibile")
            return None
        if isinstance(result, dict) and result.get("_rate_limit_long"):
            print("    [!] Spotify API bloccata (rate limit IP lungo), passo al metodo BFS")
            return None
        for a in result:
            if a["id"] not in seen_album_ids:
                seen_album_ids.add(a["id"])
                all_albums.append(a)
        print(f"    [{group}] {len(result)} album trovati (tot: {len(all_albums)})")
        time.sleep(random.uniform(*DELAY_API))

    # 2. Ricerca per nome (cattura album non collegati all'artista ID)
    search_albums = _search_artist_albums(session, token)
    added = 0
    for a in search_albums:
        if a["id"] not in seen_album_ids:
            seen_album_ids.add(a["id"])
            all_albums.append(a)
            added += 1
    print(f"    [search] +{added} album aggiuntivi (tot: {len(all_albums)})")

    if not all_albums:
        return None

    # Raccoglie le tracce da ogni album
    print(f"[*] Raccolta tracce da {len(all_albums)} album...")
    all_tracks = []
    seen_ids: set[str] = set()
    PICCIONI_NAMES = {"piero piccioni", "piccioni"}

    for i, album in enumerate(all_albums, 1):
        tparams = {"limit": 50, "offset": 0}
        while True:
            data = _spotify_get(session, token, f"albums/{album['id']}/tracks", tparams)
            if not data:
                break
            if data.get("_rate_limit_long"):
                print("    [!] Rate limit durante raccolta tracce, fermo metodo API")
                return all_tracks if all_tracks else None

            for item in data.get("items", []):
                if item["id"] in seen_ids:
                    continue
                # Per album appears_on/search: filtra tracce senza Piccioni come artista
                if album.get("appears_on"):
                    artists_lc = [a["name"].lower() for a in item.get("artists", [])]
                    if not any(any(p in a for p in PICCIONI_NAMES) for a in artists_lc):
                        continue
                seen_ids.add(item["id"])
                all_tracks.append({
                    "id":           item["id"],
                    "name":         item.get("name", ""),
                    "track_number": item.get("track_number"),
                    "duration_ms":  item.get("duration_ms"),
                    "artists":      ", ".join(a["name"] for a in item.get("artists", []) if a.get("name")),
                    "album_name":   album["name"],
                    "album_year":   (album.get("release_date", "") or "")[:4],
                })

            if not data.get("next"):
                break
            tparams["offset"] += 50
            time.sleep(random.uniform(*DELAY_API))

        if i % 10 == 0:
            print(f"    [{i}/{len(all_albums)}] {len(all_tracks)} tracce raccolte")

        # Rinnova token ogni 30 album
        if i % 30 == 0:
            new_tok = extract_token(session)
            if new_tok:
                token = new_tok

    print(f"    Totale track IDs unici: {len(all_tracks)}")
    return all_tracks


# ---------------------------------------------------------------------------
# Metodo 2: BFS via embed pages + Jamstart
# ---------------------------------------------------------------------------

def get_artist_seed_tracks(session: requests.Session) -> list[str]:
    html = fetch_embed(session, f"https://open.spotify.com/embed/artist/{ARTIST_ID}")
    if not html:
        return []
    nd = _next_data(html)
    tracks = (
        nd.get("props", {}).get("pageProps", {}).get("state", {})
          .get("data", {}).get("entity", {}).get("trackList", [])
    )
    return [t.get("uri", "").split(":")[-1] for t in tracks if t.get("uri", "").startswith("spotify:track:")]


def get_album_tracks_embed(session: requests.Session, album_id: str) -> tuple[list[str], str]:
    html = fetch_embed(session, f"https://open.spotify.com/embed/album/{album_id}")
    if not html:
        return [], ""
    nd = _next_data(html)
    entity = (
        nd.get("props", {}).get("pageProps", {}).get("state", {})
          .get("data", {}).get("entity", {})
    )
    tracks = entity.get("trackList", [])
    album_name = entity.get("name", "")
    ids = [t.get("uri", "").split(":")[-1] for t in tracks if t.get("uri", "").startswith("spotify:track:")]
    return ids, album_name


def _jamstart_post(session: requests.Session, endpoint: str, payload: dict) -> dict | None:
    url = f"https://jamstart.app/api/spotify_utils/{endpoint}"
    for attempt in range(MAX_RETRIES):
        try:
            r = session.post(url, json=payload, headers=JAM_HEADERS, timeout=12)
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


def get_track_info_jam(session: requests.Session, track_id: str) -> dict | None:
    d = _jamstart_post(session, "get_track_info", {"trackID": track_id})
    return d.get("trackData") if d else None


def collect_tracks_via_bfs(session: requests.Session, done_album_ids: set[str]) -> list[dict]:
    """
    BFS: artist embed seed -> Jamstart album ID -> album embed -> nuovi track IDs.
    Ritorna lista di track dict con metadati (album name/year da embed o da Jamstart).
    """
    print("[*] Metodo BFS: embed Spotify + Jamstart get_track_info")
    print("    (piu' lento ma non richiede accesso all'API Spotify)")

    seed_ids = get_artist_seed_tracks(session)
    print(f"    Seed: {len(seed_ids)} track IDs dall'embed artista")
    time.sleep(random.uniform(*DELAY_EMBED))

    track_queue: deque[str] = deque(seed_ids)
    album_queue:  deque[str] = deque()
    seen_track_ids: set[str] = set(seed_ids)
    album_meta: dict[str, dict] = {}      # album_id -> {name, year}
    track_full: dict[str, dict] = {}      # track_id -> full dict (from get_track_info)
    track_partial: dict[str, dict] = {}   # track_id -> partial dict (from album embed)

    while True:
        # Fase A: da track_queue ottieni album IDs via Jamstart get_track_info
        while track_queue:
            tid = track_queue.popleft()
            if tid in track_full:
                continue

            info = get_track_info_jam(session, tid)
            time.sleep(random.uniform(*DELAY_JAM))

            if not info:
                continue

            album = info.get("album") or {}
            album_id = album.get("id", "")
            album_name = album.get("name", "")
            album_year = (album.get("release_date", "") or "")[:4]
            artists = ", ".join(a["name"] for a in info.get("artists", []) if a.get("name")) or "Piero Piccioni"

            if album_id and album_id not in done_album_ids:
                album_queue.append(album_id)
                done_album_ids.add(album_id)
                album_meta[album_id] = {"name": album_name, "year": album_year}

            track_full[tid] = {
                "id":           tid,
                "name":         info.get("name", ""),
                "track_number": info.get("track_number"),
                "duration_ms":  info.get("duration_ms"),
                "artists":      artists,
                "album_name":   album_name,
                "album_year":   album_year,
            }
            print(f"    track {tid[:8]}... -> '{album_name[:30]}'")

        # Fase B: scarica un album embed per ottenere nuovi track IDs
        if not album_queue:
            print("[!] Nessun album in coda. BFS esaurito.")
            break

        album_id = album_queue.popleft()
        print(f"  [album] {album_id[:8]}...", end=" ", flush=True)
        time.sleep(random.uniform(*DELAY_EMBED))

        album_tracks, album_name_embed = get_album_tracks_embed(session, album_id)
        meta = album_meta.get(album_id, {"name": album_name_embed, "year": ""})
        print(f"'{meta['name'][:40]}' -> {len(album_tracks)} tracce")

        for tid in album_tracks:
            if tid not in seen_track_ids:
                seen_track_ids.add(tid)
                track_queue.append(tid)
            # Salva metadati parziali (usati se get_track_info fallisce)
            if tid not in track_partial:
                track_partial[tid] = {
                    "id":           tid,
                    "name":         "",
                    "track_number": None,
                    "duration_ms":  None,
                    "artists":      "Piero Piccioni",
                    "album_name":   meta["name"],
                    "album_year":   meta["year"],
                }

        # Continua finche' non si esauriscono gli album O si supera il doppio del target
        if len(seen_track_ids) >= TARGET * 3 and not album_queue:
            break

    # Costruisci lista finale: usa full info dove disponibile, altrimenti partial
    result_list = []
    seen = set()
    for tid in seen_track_ids:
        if tid in seen:
            continue
        seen.add(tid)
        if tid in track_full:
            result_list.append(track_full[tid])
        elif tid in track_partial:
            result_list.append(track_partial[tid])

    print(f"    BFS completato: {len(result_list)} track IDs trovati")
    return result_list


# ---------------------------------------------------------------------------
# Jamstart audio features
# ---------------------------------------------------------------------------

def get_audio_features(session: requests.Session, track_id: str) -> dict | None:
    d = _jamstart_post(session, "get_single_audio_features", {"trackID": track_id})
    return d.get("trackIdKeyAndMode") if d else None


# ---------------------------------------------------------------------------
# Risultato
# ---------------------------------------------------------------------------

def build_result(track: dict, feat: dict | None) -> dict:
    key_idx  = (feat or {}).get("key")
    mode_idx = (feat or {}).get("mode")
    key_name  = KEY_NAMES[key_idx] if key_idx is not None and 0 <= key_idx <= 11 else None
    mode_name = MODE_NAMES.get(mode_idx)

    return {
        "spotify_id":       track["id"],
        "title":            track.get("name", ""),
        "artists":          track.get("artists") or "Piero Piccioni",
        "album":            track.get("album_name", ""),
        "year":             track.get("album_year", ""),
        "track_number":     track.get("track_number"),
        "duration_ms":      track.get("duration_ms"),
        "jamstart_url":     f"https://jamstart.app/song_info/{track['id']}",
        "key":              key_name,
        "mode":             mode_name,
        "progression":      f"{key_name} {mode_name}" if key_name and mode_name else None,
        "tempo_bpm":        round((feat or {}).get("tempo", 0) or 0, 1) or None,
        "time_signature":   (feat or {}).get("time_signature"),
        "danceability":     (feat or {}).get("danceability"),
        "energy":           (feat or {}).get("energy"),
        "acousticness":     (feat or {}).get("acousticness"),
        "instrumentalness": (feat or {}).get("instrumentalness"),
        "valence":          (feat or {}).get("valence"),
        "loudness_db":      (feat or {}).get("loudness"),
        "speechiness":      (feat or {}).get("speechiness"),
        "liveness":         (feat or {}).get("liveness"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    output_path = Path(OUTPUT_FILE)

    # Carica checkpoint
    results: list[dict] = []
    done_ids: set[str] = set()
    done_album_ids: set[str] = set()

    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                results = existing
                done_ids = {r["spotify_id"] for r in results}
                print(f"[R] Checkpoint: {len(results)} tracce gia' salvate, riprendo...")
        except Exception:
            pass

    def save():
        output_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    session = requests.Session()

    # Estrai token anonimo dall'embed
    print("[*] Estrazione token anonimo da Spotify embed...")
    token = extract_token(session)
    if token:
        print(f"    Token estratto: {token[:30]}...")
    else:
        print("    [!] Token non disponibile, uso solo metodo BFS")

    # Scopri tutti i track IDs
    all_tracks: list[dict] = []

    if token:
        all_tracks = collect_tracks_via_api(session, token) or []

    if not all_tracks:
        all_tracks = collect_tracks_via_bfs(session, done_album_ids)

    if not all_tracks:
        print("[ERR] Nessuna traccia trovata. Controlla la connessione.")
        sys.exit(1)

    # Filtra tracce gia' processate
    pending = [t for t in all_tracks if t["id"] not in done_ids]
    total_available = len(all_tracks)
    print(f"\n[*] Track IDs totali: {total_available}")
    print(f"[*] Da processare: {len(pending)} tracce")
    print(f"[~] Obiettivo: {TARGET} tracce con audio features\n")

    if not pending and len(results) >= TARGET:
        print(f"[OK] Obiettivo gia' raggiunto! {len(results)} tracce in '{OUTPUT_FILE}'")
        _print_summary(results)
        return

    new_since_ckpt = 0

    for track in pending:
        if len(results) >= TARGET:
            break

        name_display = (track.get("name") or track["id"])[:40]
        print(
            f"  [{len(results)+1}/{TARGET}] '{name_display}'",
            end=" ", flush=True
        )

        feat = get_audio_features(session, track["id"])
        time.sleep(random.uniform(*DELAY_JAM))

        done_ids.add(track["id"])

        # Se name e' vuoto, prova a riempirlo da feat (Jamstart restituisce track name a volte)
        if not track.get("name") and feat:
            pass  # feat non ha track name, rimane vuoto per ora

        result = build_result(track, feat)
        results.append(result)
        new_since_ckpt += 1

        prog = result.get("progression") or "N/A"
        bpm  = result.get("tempo_bpm") or 0
        print(f"  {prog:<16}  {bpm:.0f} BPM")

        if new_since_ckpt >= CHECKPOINT:
            save()
            print(f"    [SAVE] {len(results)} tracce salvate")
            new_since_ckpt = 0

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
