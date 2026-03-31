#!/usr/bin/env python3
"""Flask web server for mahjong game review."""

from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path
import atexit
import json
import subprocess
import sys
import time

import requests as http_requests

from mj_parse import parse_game
from mj_games import compute_summary, CATEGORY_INFO

DIR = Path(__file__).parent
GAMES_FILE = DIR / "games.json"
NANIKIRU_BIN = DIR / "mahjong-cpp" / "build" / "install" / "bin" / "nanikiru"
NANIKIRU_PORT = 50000

app = Flask(__name__, static_folder="static")

# --- nanikiru server management ---

_nanikiru_proc = None


def start_nanikiru():
    """Start the local mahjong-cpp tile efficiency server."""
    global _nanikiru_proc

    if not NANIKIRU_BIN.exists():
        print(f"Warning: nanikiru binary not found at {NANIKIRU_BIN}", file=sys.stderr)
        return

    # Check if already running
    try:
        resp = http_requests.post(
            f"http://127.0.0.1:{NANIKIRU_PORT}/",
            json={"version": "0.9.1", "hand": [0], "wall": [0]*37},
            timeout=1,
        )
        print(f"nanikiru already running on port {NANIKIRU_PORT}", file=sys.stderr)
        return
    except (http_requests.ConnectionError, http_requests.Timeout):
        pass

    print(f"Starting nanikiru on 127.0.0.1:{NANIKIRU_PORT}...", file=sys.stderr)
    _nanikiru_proc = subprocess.Popen(
        [str(NANIKIRU_BIN), str(NANIKIRU_PORT)],
        cwd=str(NANIKIRU_BIN.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for it to be ready
    for _ in range(20):
        time.sleep(0.25)
        try:
            http_requests.post(
                f"http://127.0.0.1:{NANIKIRU_PORT}/",
                json={"version": "0.9.1", "hand": [0], "wall": [0]*37},
                timeout=1,
            )
            print(f"nanikiru ready (pid {_nanikiru_proc.pid})", file=sys.stderr)
            return
        except (http_requests.ConnectionError, http_requests.Timeout):
            continue

    print("Warning: nanikiru started but not responding", file=sys.stderr)


def stop_nanikiru():
    """Stop the nanikiru server if we started it."""
    global _nanikiru_proc
    if _nanikiru_proc and _nanikiru_proc.poll() is None:
        _nanikiru_proc.terminate()
        _nanikiru_proc.wait(timeout=5)
        print("nanikiru stopped", file=sys.stderr)


def load_games():
    with open(GAMES_FILE) as f:
        return json.load(f)


def save_games(data):
    with open(GAMES_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/tiles/<path:filename>")
def tiles(filename):
    return send_from_directory(DIR / "riichi-mahjong-tiles" / "Regular", filename)


@app.route("/api/categories")
def api_categories():
    return jsonify(CATEGORY_INFO)


@app.route("/api/trends")
def api_trends():
    data = load_games()
    games = []
    for i, g in enumerate(data["games"]):
        s = g.get("summary", {})
        by_cat = s.get("by_category", {})
        # Group categories by skill area
        by_group = {}
        for cat, info in by_cat.items():
            grp = CATEGORY_INFO.get(cat, {}).get("group", cat)
            if grp not in by_group:
                by_group[grp] = {"count": 0, "ev": 0.0}
            by_group[grp]["count"] += info["count"]
            by_group[grp]["ev"] = round(by_group[grp]["ev"] + info["ev"], 2)
        games.append({
            "id": i,
            "date": g["date"],
            "total_mistakes": s.get("total_mistakes", 0),
            "total_ev_loss": s.get("total_ev_loss", 0),
            "total_turns": s.get("total_turns"),
            "ev_per_turn": s.get("ev_per_turn"),
            "by_severity": s.get("by_severity", {}),
            "by_group": by_group,
        })
    # Sort by date then id
    games.sort(key=lambda g: (g["date"], g["id"]))
    return jsonify(games)


@app.route("/api/games")
def api_games():
    data = load_games()
    # Return summary info for each game (not full mistake data)
    games = []
    for i, g in enumerate(data["games"]):
        annotated = sum(
            1 for rnd in g["rounds"] for m in rnd["mistakes"] if m.get("category")
        )
        total = g.get("summary", {}).get("total_mistakes", 0)
        games.append({
            "id": i,
            "date": g["date"],
            "log_url": g.get("log_url"),
            "summary": g.get("summary"),
            "annotated": annotated,
            "total": total,
        })
    return jsonify(games)


@app.route("/api/games/<int:game_id>")
def api_game(game_id):
    data = load_games()
    if game_id < 0 or game_id >= len(data["games"]):
        return jsonify({"error": "Game not found"}), 404
    return jsonify(data["games"][game_id])


@app.route("/api/games/<int:game_id>", methods=["DELETE"])
def api_delete_game(game_id):
    data = load_games()
    if game_id < 0 or game_id >= len(data["games"]):
        return jsonify({"error": "Game not found"}), 404
    data["games"].pop(game_id)
    save_games(data)
    return jsonify({"ok": True, "remaining": len(data["games"])})


@app.route("/api/games/<int:game_id>/annotate", methods=["POST"])
def api_annotate(game_id):
    data = load_games()
    if game_id < 0 or game_id >= len(data["games"]):
        return jsonify({"error": "Game not found"}), 404

    body = request.json
    round_name = body.get("round")
    turn = body.get("turn")
    index = body.get("index", 0)
    category = body.get("category")
    note = body.get("note")

    game = data["games"][game_id]
    target_round = None
    for rnd in game["rounds"]:
        if rnd["round"] == round_name:
            target_round = rnd
            break
    if target_round is None:
        return jsonify({"error": f"Round '{round_name}' not found"}), 404

    candidates = [m for m in target_round["mistakes"] if m["turn"] == turn]
    if not candidates:
        return jsonify({"error": f"Turn {turn} not found in {round_name}"}), 404
    if index >= len(candidates):
        return jsonify({"error": f"Index {index} out of range"}), 404

    mistake = candidates[index]
    if category is not None:
        mistake["category"] = category if category else None
    if note is not None:
        mistake["note"] = note if note else None

    compute_summary(game)
    save_games(data)

    return jsonify({"ok": True, "summary": game["summary"]})


@app.route("/api/games/<int:game_id>/categorize", methods=["POST"])
def api_categorize(game_id):
    from mj_categorize import categorize_game

    data = load_games()
    if game_id < 0 or game_id >= len(data["games"]):
        return jsonify({"error": "Game not found"}), 404

    body = request.json or {}
    force = body.get("force", False)

    game = data["games"][game_id]
    n, api_calls = categorize_game(game, game_id, force=force)

    if n > 0:
        compute_summary(game)
        save_games(data)

    return jsonify({"ok": True, "categorized": n, "api_calls": api_calls, "summary": game["summary"]})


@app.route("/api/games/add", methods=["POST"])
def api_add():
    import urllib.parse
    from datetime import date

    body = request.json
    url = body.get("url", "")
    game_date = body.get("date") or date.today().isoformat()

    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if "data" not in qs:
        return jsonify({"error": "URL must contain ?data= parameter"}), 400

    data_path = qs["data"][0]
    download_url = f"https://mjai.ekyu.moe{data_path}"
    filename = Path(data_path).name

    mortal_dir = DIR / "mortal_analysis"
    mortal_dir.mkdir(exist_ok=True)
    dest = mortal_dir / filename

    if not dest.exists():
        try:
            resp = http_requests.get(download_url, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
        except Exception as e:
            return jsonify({"error": f"Download failed: {e}"}), 500

    with open(dest) as f:
        mortal_data = json.load(f)

    game = parse_game(mortal_data, game_date=game_date)
    game["mortal_file"] = str(dest.relative_to(DIR))
    compute_summary(game)

    if GAMES_FILE.exists():
        data = load_games()
    else:
        data = {"games": []}
    data["games"].append(game)
    game_id = len(data["games"]) - 1
    save_games(data)

    # Auto-categorize
    from mj_categorize import categorize_game
    cat_n, api_calls = categorize_game(game, game_id)
    if cat_n > 0:
        compute_summary(game)
        save_games(data)

    return jsonify({"ok": True, "game_id": game_id, "summary": game["summary"],
                    "categorized": cat_n, "api_calls": api_calls})


@app.route("/api/practice")
def api_practice():
    import random
    data = load_games()

    # Filters
    sev_filter = request.args.get("severity")       # "??" or "???"
    group_filter = request.args.get("group")         # "Efficiency", "Strategy", etc.
    defense_filter = request.args.get("defense")     # "1" = only riichi situations

    candidates = []
    for i, g in enumerate(data["games"]):
        for rnd in g["rounds"]:
            for m in rnd["mistakes"]:
                if ((m.get("actual") or {}).get("type") != "dahai" or
                    (m.get("expected") or {}).get("type") != "dahai" or
                    m.get("severity") not in ("??", "???") or
                    not m.get("hand")):
                    continue
                if sev_filter and m["severity"] != sev_filter:
                    continue
                if group_filter:
                    cat = m.get("category", "")
                    cat_group = CATEGORY_INFO.get(cat, {}).get("group", "")
                    if cat_group != group_filter:
                        continue
                if defense_filter == "1" and not m.get("safety_ratings"):
                    continue
                candidates.append({
                    "game_id": i,
                    "game_date": g["date"],
                    "round": rnd["round"],
                    "mistake": m,
                })
    if not candidates:
        return jsonify({"error": "No matching practice problems"}), 404
    pick = random.choice(candidates)
    pick["pool_size"] = len(candidates)
    return jsonify(pick)


if __name__ == "__main__":
    import os
    # Only start nanikiru in the reloader child (or when not using reloader)
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        start_nanikiru()
        atexit.register(stop_nanikiru)
    app.run(debug=True, port=5000)
