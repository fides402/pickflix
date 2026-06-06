"""
Server Flask per lo scraper hip-hop.
Avvia con:  python app_hiphop.py
Poi apri:   http://localhost:5051
"""

import csv
import io
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, send_file, send_from_directory

app = Flask(__name__, static_folder=".")

DATA_FILE = "hiphop_tracks.json"

_state = {
    "running":    False,
    "log":        [],
    "process":    None,
    "done_count": 0,
    "total":      0,
}


# ---------------------------------------------------------------------------
# Pagine statiche
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(".", "hiphop.html")


# ---------------------------------------------------------------------------
# API dati
# ---------------------------------------------------------------------------

@app.route("/api/tracks")
def api_tracks():
    path = Path(DATA_FILE)
    if not path.exists():
        return jsonify([])
    try:
        return jsonify(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return jsonify([])


@app.route("/api/status")
def api_status():
    path = Path(DATA_FILE)
    count = 0
    if path.exists():
        try:
            count = len(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return jsonify({"running": _state["running"], "saved_count": count})


@app.route("/api/progress")
def api_progress():
    return jsonify({
        "running":    _state["running"],
        "log":        _state["log"][-120:],
        "done_count": _state["done_count"],
        "total":      _state["total"],
    })


# ---------------------------------------------------------------------------
# Controllo scraper
# ---------------------------------------------------------------------------

@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    if _state["running"]:
        return jsonify({"error": "Scraper gia' in esecuzione."}), 400

    _state["running"]    = True
    _state["log"]        = []
    _state["done_count"] = 0
    _state["total"]      = 0

    def run():
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        proc = subprocess.Popen(
            [sys.executable, "scraper/scrape_hiphop_artists.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )
        _state["process"] = proc
        for raw in proc.stdout:
            line = raw.rstrip()
            _state["log"].append(line)
            # "[1/10]" pattern per avanzamento artisti
            m = re.search(r"\[(\d+)/(\d+)\]", line)
            if m:
                _state["done_count"] = int(m.group(1))
                _state["total"]      = int(m.group(2))
        proc.wait()
        _state["running"] = False
        _state["process"] = None
        _state["log"].append("[OK] Scraper terminato.")

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    proc = _state.get("process")
    if proc and _state["running"]:
        proc.terminate()
        _state["running"] = False
        _state["log"].append("[STOP] Scraper fermato dall'utente.")
        return jsonify({"status": "stopped"})
    return jsonify({"status": "not_running"})


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

@app.route("/api/download/json")
def download_json():
    path = Path(DATA_FILE)
    if not path.exists():
        return jsonify({"error": "Nessun dato. Avvia prima lo scraper."}), 404
    return send_file(
        path.resolve(),
        as_attachment=True,
        download_name="hiphop_tracks.json",
        mimetype="application/json",
    )


@app.route("/api/download/csv")
def download_csv():
    path = Path(DATA_FILE)
    if not path.exists():
        return jsonify({"error": "Nessun dato."}), 404

    tracks = json.loads(path.read_text(encoding="utf-8"))
    if not tracks:
        return jsonify({"error": "File vuoto."}), 404

    cols = [
        "artist", "title", "album", "year", "popularity",
        "key", "mode", "tempo_bpm", "danceability", "speechiness",
        "energy", "valence", "acousticness", "instrumentalness",
        "loudness_db", "liveness", "duration_ms", "spotify_id", "jamstart_url",
    ]
    available = [c for c in cols if any(c in t for t in tracks)]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=available, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(tracks)

    return Response(
        "﻿" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="hiphop_tracks.csv"'},
    )


# ---------------------------------------------------------------------------
# Avvio
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = 5051
    print(f"[*] HipHop Scraper UI su  http://localhost:{port}")
    print("    Premi CTRL+C per uscire.\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
