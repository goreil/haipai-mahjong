#!/usr/bin/env python3
"""Flask web server for mahjong game review."""

from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path
import json

from mj_parse import parse_game
from mj_games import compute_summary

DIR = Path(__file__).parent
GAMES_FILE = DIR / "games.json"

app = Flask(__name__, static_folder="static")


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


@app.route("/api/games/add", methods=["POST"])
def api_add():
    import urllib.parse
    from datetime import date
    import requests as http_requests

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
    save_games(data)

    return jsonify({"ok": True, "game_id": len(data["games"]) - 1, "summary": game["summary"]})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
