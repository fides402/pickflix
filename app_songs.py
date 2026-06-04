"""
Server Flask per lo scraper di Piero Piccioni.
Avvia con avvia.bat oppure:  python app_songs.py
Poi apri:  http://localhost:5050
"""

import csv
import io
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file, send_from_directory

app = Flask(__name__, static_folder=".")

# Stato globale dello scraper
_state = {
    "running": False,
    "log": [],
    "process": None,
    "done_count": 0,
    "total": 0,
}


# ---------------------------------------------------------------------------
# Pagine
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(".", "songs.html")


@app.route("/songs_progressions.json")
def serve_json():
    path = Path("songs_progressions.json")
    if not path.exists():
        return jsonify([])
    return send_from_directory(".", "songs_progressions.json")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.route("/api/songs")
def api_songs():
    path = Path("songs_progressions.json")
    if not path.exists():
        return jsonify([])
    try:
        return jsonify(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return jsonify([])


@app.route("/api/status")
def api_status():
    path = Path("songs_progressions.json")
    count = 0
    if path.exists():
        try:
            count = len(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return jsonify({
        "running": _state["running"],
        "saved_count": count,
    })


@app.route("/api/progress")
def api_progress():
    return jsonify({
        "running": _state["running"],
        "log": _state["log"][-120:],
        "done_count": _state["done_count"],
        "total": _state["total"],
    })


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    if _state["running"]:
        return jsonify({"error": "Scraper già in esecuzione."}), 400

    _state["running"] = True
    _state["log"] = []
    _state["done_count"] = 0
    _state["total"] = 0

    def run():
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        python = sys.executable
        proc = subprocess.Popen(
            [python, "scraper/scrape_piero_piccioni.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )
        _state["process"] = proc

        import re as _re
        for raw_line in proc.stdout:
            line = raw_line.rstrip()
            _state["log"].append(line)
            m = _re.search(r"\[(\d+)/(\d+)\]", line)
            if m:
                _state["done_count"] = int(m.group(1))
                _state["total"]      = int(m.group(2))

        proc.wait()
        _state["running"] = False
        _state["process"] = None
        _state["log"].append("[OK] Scraper terminato.")

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/download/json")
def download_json():
    path = Path("songs_progressions.json")
    if not path.exists():
        return jsonify({"error": "Nessun file da scaricare. Avvia prima lo scraper."}), 404
    return send_file(
        path.resolve(),
        as_attachment=True,
        download_name="piero_piccioni_progressioni.json",
        mimetype="application/json",
    )


@app.route("/api/download/csv")
def download_csv():
    path = Path("songs_progressions.json")
    if not path.exists():
        return jsonify({"error": "Nessun file da scaricare. Avvia prima lo scraper."}), 404

    songs = json.loads(path.read_text(encoding="utf-8"))
    if not songs:
        return jsonify({"error": "Il file è vuoto."}), 404

    # Colonne ordinate in modo leggibile
    cols = [
        "title", "artists", "album", "year", "track_number",
        "key", "mode", "progression", "tempo_bpm", "time_signature",
        "danceability", "energy", "acousticness", "instrumentalness",
        "valence", "loudness_db", "speechiness", "liveness",
        "duration_ms", "spotify_id", "jamstart_url",
    ]
    # Includi solo le colonne presenti
    available = [c for c in cols if c in songs[0]]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=available, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(songs)

    return Response(
        "﻿" + output.getvalue(),   # BOM per Excel italiano
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                'attachment; filename="piero_piccioni_progressioni.csv"'
        },
    )


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
# Avvio
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = 5050
    print(f"[*] Server avviato su  http://localhost:{port}")
    print("    Premi CTRL+C per uscire.\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
