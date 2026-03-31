#!/usr/bin/env python3
"""Flask web server for mahjong game review."""

from flask import Flask, g, jsonify, redirect, render_template_string, request, send_from_directory, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from pathlib import Path
import atexit
import json
import subprocess
import sys
import time

import requests as http_requests

import db
from mj_parse import parse_game
from mj_games import compute_summary, CATEGORY_INFO

DIR = Path(__file__).parent
NANIKIRU_BIN = DIR / "mahjong-cpp" / "build" / "install" / "bin" / "nanikiru"
NANIKIRU_PORT = 50000

app = Flask(__name__, static_folder="static")
app.secret_key = "dev-secret-change-in-production"

# --- Auth ---

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    conn = db.get_db()
    row = db.get_user_by_id(conn, int(user_id))
    if row:
        return User(row["id"], row["username"])
    return None


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify({"error": "Login required"}), 401
    return redirect(url_for("login"))


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


# --- Database connection per request ---

def get_conn():
    if "db_conn" not in g:
        g.db_conn = db.get_db()
    return g.db_conn


@app.teardown_appcontext
def close_conn(exception):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


LOGIN_PAGE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login - Mahjong Review</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#1a1a2e;color:#e0e0e0;min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#16213e;border:1px solid #2a3a5a;border-radius:12px;padding:32px;width:360px;max-width:90vw}
h2{color:#4fc3f7;margin-bottom:20px;font-size:20px}
label{display:block;font-size:13px;color:#8892a4;margin-bottom:4px}
input{width:100%;padding:10px 12px;border-radius:6px;border:1px solid #2a3a5a;background:#0f1a2e;color:#e0e0e0;font-size:14px;margin-bottom:14px}
button{width:100%;padding:10px;border-radius:6px;border:none;background:#2a7aa3;color:#fff;font-size:14px;cursor:pointer;font-weight:600}
button:hover{background:#4fc3f7;color:#000}
.error{color:#ef5350;font-size:13px;margin-bottom:12px}
.link{text-align:center;margin-top:16px;font-size:13px;color:#8892a4}
.link a{color:#4fc3f7;text-decoration:none}
</style></head><body>
<div class="card">
<h2>{{ title }}</h2>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="POST">
<label>Username</label><input name="username" required autofocus>
<label>Password</label><input name="password" type="password" required>
{% if register %}<label>Invite Code</label><input name="invite_code" required>{% endif %}
<button>{{ title }}</button>
</form>
{% if register %}
<div class="link">Already have an account? <a href="/login">Login</a></div>
{% else %}
<div class="link">Need an account? <a href="/register">Register</a></div>
{% endif %}
</div></body></html>"""


# --- Routes ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_conn()
        user_row = db.get_user_by_username(conn, username)
        if user_row and check_password_hash(user_row["password_hash"], password):
            login_user(User(user_row["id"], user_row["username"]))
            return redirect("/")
        error = "Invalid username or password"
    return render_template_string(LOGIN_PAGE, title="Login", error=error, register=False)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect("/")
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        invite_code = request.form.get("invite_code", "").strip()
        conn = get_conn()

        if not username or not password:
            error = "Username and password required"
        elif len(password) < 4:
            error = "Password must be at least 4 characters"
        elif not db.validate_invite_code(conn, invite_code):
            error = "Invalid or already used invite code"
        else:
            try:
                pw_hash = generate_password_hash(password)
                user_id = db.create_user(conn, username, pw_hash, invite_code)
                login_user(User(user_id, username))
                return redirect("/")
            except Exception:
                error = "Username already taken"
    return render_template_string(LOGIN_PAGE, title="Register", error=error, register=True)


@app.route("/logout")
def logout():
    logout_user()
    return redirect("/login")


@app.route("/")
@login_required
def index():
    return send_from_directory("static", "index.html")


@app.route("/tiles/<path:filename>")
def tiles(filename):
    return send_from_directory(DIR / "riichi-mahjong-tiles" / "Regular", filename)


@app.route("/api/me")
@login_required
def api_me():
    return jsonify({"username": current_user.username, "id": current_user.id})


@app.route("/api/categories")
def api_categories():
    return jsonify(CATEGORY_INFO)


@app.route("/api/trends")
@login_required
def api_trends():
    conn = get_conn()
    uid = current_user.id
    return jsonify(db.get_trends(conn, uid))


@app.route("/api/games")
@login_required
def api_games():
    conn = get_conn()
    uid = current_user.id
    return jsonify(db.list_games(conn, uid))


@app.route("/api/games/<int:game_id>")
@login_required
def api_game(game_id):
    conn = get_conn()
    uid = current_user.id
    game = db.get_game(conn, game_id, user_id=uid)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    return jsonify(game)


@app.route("/api/games/<int:game_id>", methods=["DELETE"])
@login_required
def api_delete_game(game_id):
    conn = get_conn()
    uid = current_user.id
    if not db.delete_game(conn, game_id, user_id=uid):
        return jsonify({"error": "Game not found"}), 404
    remaining = conn.execute(
        "SELECT COUNT(*) FROM games WHERE user_id = ?", (uid,)
    ).fetchone()[0]
    return jsonify({"ok": True, "remaining": remaining})


@app.route("/api/games/<int:game_id>/annotate", methods=["POST"])
@login_required
def api_annotate(game_id):
    conn = get_conn()
    uid = current_user.id

    body = request.json
    round_name = body.get("round")
    turn = body.get("turn")
    index = body.get("index", 0)
    category = body.get("category")
    note = body.get("note")

    result = db.annotate_mistake(conn, game_id, round_name, turn, index, category, note, user_id=uid)
    if not result:
        return jsonify({"error": "Mistake not found"}), 404

    stats = db.compute_summary_for_game(conn, game_id)
    return jsonify({"ok": True, "summary": stats})


@app.route("/api/games/<int:game_id>/categorize", methods=["POST"])
@login_required
def api_categorize(game_id):
    conn = get_conn()
    uid = current_user.id

    game = db.get_game(conn, game_id, user_id=uid)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    body = request.json or {}
    force = body.get("force", False)

    from mj_categorize import categorize_game_db
    n, api_calls = categorize_game_db(conn, game_id, force=force)

    stats = db.compute_summary_for_game(conn, game_id) if n > 0 else game.get("summary", {})
    return jsonify({"ok": True, "categorized": n, "api_calls": api_calls, "summary": stats})


@app.route("/api/games/add", methods=["POST"])
@login_required
def api_add():
    import urllib.parse
    from datetime import date

    conn = get_conn()
    uid = current_user.id

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

    game_dict = parse_game(mortal_data, game_date=game_date)
    game_dict["mortal_file"] = str(dest.relative_to(DIR))
    compute_summary(game_dict)

    game_id = db.add_game(conn, uid, game_dict)

    # Auto-categorize
    from mj_categorize import categorize_game_db
    cat_n, api_calls = categorize_game_db(conn, game_id)

    stats = db.compute_summary_for_game(conn, game_id) if cat_n > 0 else game_dict.get("summary", {})
    return jsonify({"ok": True, "game_id": game_id, "summary": stats,
                    "categorized": cat_n, "api_calls": api_calls})


@app.route("/api/practice")
@login_required
def api_practice():
    conn = get_conn()
    uid = current_user.id

    sev = request.args.get("severity")
    group = request.args.get("group")
    defense = request.args.get("defense") == "1"

    pick = db.get_practice_problem(conn, uid, severity=sev, group=group, defense_only=defense)
    if not pick:
        return jsonify({"error": "No matching practice problems"}), 404
    return jsonify(pick)


if __name__ == "__main__":
    import os

    # Initialize database
    conn = db.get_db()
    db.init_db(conn)
    conn.close()

    # Only start nanikiru in the reloader child (or when not using reloader)
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        start_nanikiru()
        atexit.register(stop_nanikiru)
    app.run(debug=True, port=5000)
