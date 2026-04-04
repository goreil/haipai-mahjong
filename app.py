#!/usr/bin/env python3
"""Flask web server for mahjong game review."""

from flask import Flask, Response, g, jsonify, redirect, render_template_string, request, send_from_directory, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash
from pathlib import Path
import json
import os
import sys

import requests as http_requests

import db
from mj_parse import parse_game
from mj_games import compute_summary, CATEGORY_INFO

DIR = Path(__file__).parent

app = Flask(__name__, static_folder="static")
_secret = os.environ.get("SECRET_KEY")
if not _secret:
    print("WARNING: SECRET_KEY not set, using random key (sessions won't persist across restarts)", file=sys.stderr)
    import secrets
    _secret = secrets.token_hex(32)
app.secret_key = _secret
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") != "development"

csrf = CSRFProtect(app)

limiter = Limiter(get_remote_address, app=app, default_limits=["200 per minute"],
                  storage_uri="memory://")

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


# --- Error handling ---

@app.errorhandler(Exception)
def handle_exception(e):
    """Return JSON error for API routes, generic 500 otherwise."""
    if request.path.startswith("/api/"):
        print(f"Unhandled error on {request.path}: {e}", file=sys.stderr)
        return jsonify({"error": "Internal server error"}), 500
    return "Internal server error", 500


# --- Database connection per request ---

def get_conn():
    if "db_conn" not in g:
        g.db_conn = db.get_db()
    return g.db_conn


@app.teardown_appcontext
def close_conn(_exception):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


LOGIN_PAGE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} - Haipai</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:'DM Sans',sans-serif;
  background:#0d0f1a;
  color:#c8ccd8;
  min-height:100vh;
  display:flex;
  align-items:center;
  justify-content:center;
  overflow:hidden;
}
body::before{
  content:'';position:fixed;inset:0;
  background:
    radial-gradient(ellipse 60% 50% at 20% 80%, rgba(79,195,247,0.06) 0%, transparent 70%),
    radial-gradient(ellipse 50% 40% at 80% 20%, rgba(67,160,71,0.05) 0%, transparent 70%);
  pointer-events:none;
}
.login-wrap{position:relative;z-index:1;width:380px;max-width:92vw}
.brand{text-align:center;margin-bottom:32px}
.brand-tiles{
  display:inline-flex;gap:4px;margin-bottom:16px;
}
.brand-tile{
  width:28px;height:36px;border-radius:4px;
  background:linear-gradient(135deg,#1e2a48 0%,#16213e 100%);
  border:1px solid #2a3a5a;
  display:flex;align-items:center;justify-content:center;
  font-size:14px;font-weight:700;
  animation:tileIn 0.5s ease backwards;
}
.brand-tile:nth-child(1){color:#e53935;animation-delay:0.1s}
.brand-tile:nth-child(2){color:#43a047;animation-delay:0.2s}
.brand-tile:nth-child(3){color:#4fc3f7;animation-delay:0.3s}
@keyframes tileIn{from{opacity:0;transform:translateY(-12px)}}
.brand h1{
  font-family:'Outfit',sans-serif;font-weight:700;font-size:28px;
  color:#e8eaf0;letter-spacing:-0.5px;
  animation:fadeIn 0.6s ease 0.3s backwards;
}
.brand p{
  font-size:13px;color:#5a6078;margin-top:4px;letter-spacing:0.5px;
  animation:fadeIn 0.6s ease 0.45s backwards;
}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}}
.card{
  background:linear-gradient(160deg,#141828 0%,#111524 100%);
  border:1px solid #1e2540;
  border-radius:14px;padding:28px 30px;
  box-shadow:0 8px 40px rgba(0,0,0,0.4),0 0 0 1px rgba(255,255,255,0.02) inset;
  animation:cardIn 0.5s ease 0.2s backwards;
}
@keyframes cardIn{from{opacity:0;transform:translateY(16px) scale(0.98)}}
.card h2{
  font-family:'Outfit',sans-serif;font-weight:500;font-size:18px;
  color:#e0e4ee;margin-bottom:22px;letter-spacing:-0.2px;
}
label{display:block;font-size:12px;color:#5a6078;margin-bottom:5px;text-transform:uppercase;letter-spacing:0.8px}
input{
  width:100%;padding:11px 14px;border-radius:8px;
  border:1px solid #1e2540;background:#0d0f1a;color:#e0e4ee;
  font-size:14px;font-family:'DM Sans',sans-serif;
  margin-bottom:16px;transition:border-color 0.2s,box-shadow 0.2s;
}
input:focus{outline:none;border-color:#4fc3f7;box-shadow:0 0 0 3px rgba(79,195,247,0.1)}
button{
  width:100%;padding:12px;border-radius:8px;border:none;
  background:linear-gradient(135deg,#2a7aa3 0%,#357a8f 100%);
  color:#fff;font-size:14px;font-weight:500;cursor:pointer;
  font-family:'DM Sans',sans-serif;letter-spacing:0.3px;
  transition:all 0.2s;margin-top:4px;
}
button:hover{background:linear-gradient(135deg,#3a9ac3 0%,#4fc3f7 100%);box-shadow:0 4px 16px rgba(79,195,247,0.2)}
.error{
  color:#ef5350;font-size:13px;margin-bottom:14px;
  padding:8px 12px;background:rgba(239,83,80,0.08);
  border-radius:6px;border:1px solid rgba(239,83,80,0.15);
}
.link{text-align:center;margin-top:18px;font-size:13px;color:#5a6078}
.link a{color:#4fc3f7;text-decoration:none;font-weight:500}
.link a:hover{text-decoration:underline}
</style></head><body>
<div class="login-wrap">
<div class="brand">
  <div class="brand-tiles">
    <div class="brand-tile">M</div>
    <div class="brand-tile">P</div>
    <div class="brand-tile">S</div>
  </div>
  <h1>Haipai</h1>
  <p>Mahjong Mistake Trainer</p>
</div>
<div class="card">
<h2>{{ title }}</h2>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="POST">
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
<label>Username</label><input name="username" required autofocus autocomplete="username">
<label>Password</label><input name="password" type="password" required autocomplete="{{ 'new-password' if register else 'current-password' }}">
{% if register %}<label>Invite Code</label><input name="invite_code" required placeholder="From a club member">{% endif %}
<button>{{ title }}</button>
</form>
{% if register %}
<div class="link">Already have an account? <a href="/login">Login</a></div>
{% else %}
<div class="link">Need an account? <a href="/register">Register</a></div>
{% endif %}
<div class="link"><a href="/practice">Try practice mode without an account</a></div>
</div>
</div></body></html>"""


# --- Routes ---

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect("/")
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_conn()
        user_row = db.get_user_by_username(conn, username)
        # Always hash to prevent timing-based username enumeration
        pw_hash = user_row["password_hash"] if user_row else "pbkdf2:sha256:dummy"
        valid = check_password_hash(pw_hash, password)
        if user_row and valid:
            login_user(User(user_row["id"], user_row["username"]))
            return redirect("/")
        error = "Invalid username or password"
    return render_template_string(LOGIN_PAGE, title="Login", error=error, register=False)


@app.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
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
        elif len(password) < 8:
            error = "Password must be at least 8 characters"
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


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/")
def index():
    if not current_user.is_authenticated:
        return send_from_directory("static", "landing.html")
    return send_from_directory("static", "index.html")


@app.route("/practice")
def practice_page():
    return send_from_directory("static", "index.html")


@app.route("/tiles/<filename>")
def tiles(filename):
    return send_from_directory(DIR / "riichi-mahjong-tiles" / "Regular", filename)


@app.route("/api/me")
@login_required
@csrf.exempt
def api_me():
    from flask_wtf.csrf import generate_csrf
    conn = get_conn()
    user_row = db.get_user_by_id(conn, current_user.id)
    return jsonify({
        "username": current_user.username,
        "id": current_user.id,
        "is_admin": db.is_admin(conn, current_user.id),
        "practice_opt_in": bool(user_row["practice_opt_in"]) if user_row else False,
        "csrf_token": generate_csrf(),
    })


@app.route("/api/me/practice-opt-in", methods=["POST"])
@login_required
def api_practice_opt_in():
    conn = get_conn()
    body = request.json or {}
    opt_in = bool(body.get("opt_in"))
    db.set_practice_opt_in(conn, current_user.id, opt_in)
    return jsonify({"ok": True, "practice_opt_in": opt_in})


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
    if not body:
        return jsonify({"error": "JSON body required"}), 400
    round_name = body.get("round")
    turn = body.get("turn")
    index = body.get("index", 0)
    category = body.get("category")
    note = body.get("note")

    if not isinstance(round_name, str) or not isinstance(turn, int):
        return jsonify({"error": "round (string) and turn (int) required"}), 400
    if category is not None and not isinstance(category, str):
        return jsonify({"error": "category must be a string"}), 400
    if note is not None and not isinstance(note, str):
        return jsonify({"error": "note must be a string"}), 400
    if note and len(note) > 1000:
        return jsonify({"error": "note too long (max 1000 chars)"}), 400

    VALID_CATEGORIES = {"", "1A", "2A", "3A", "3B", "3C", "4A", "4B", "4C", "5A", "5B", "6A", "6B"}
    if category and category not in VALID_CATEGORIES:
        return jsonify({"error": f"Invalid category: {category}"}), 400

    result = db.annotate_mistake(conn, game_id, round_name, turn, index, category, note, user_id=uid)
    if not result:
        return jsonify({"error": "Mistake not found"}), 404

    stats = db.compute_summary_for_game(conn, game_id)
    return jsonify({"ok": True, "summary": stats})


@app.route("/api/games/<int:game_id>/categorize", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def api_categorize(game_id):
    conn = get_conn()
    uid = current_user.id

    game = db.get_game(conn, game_id, user_id=uid)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    body = request.json or {}
    force = body.get("force", False)

    from mj_categorize import categorize_game_db
    n, api_calls, failures = categorize_game_db(conn, game_id, force=force)

    stats = db.compute_summary_for_game(conn, game_id) if n > 0 else game.get("summary", {})
    result = {"ok": True, "categorized": n, "api_calls": api_calls, "summary": stats}
    if failures:
        result["failures"] = failures
    return jsonify(result)


@app.route("/api/games/backfill-board-state", methods=["POST"])
@login_required
def api_backfill_board_state():
    """Populate board_state on all mistakes missing it (no API calls needed)."""
    conn = get_conn()
    uid = current_user.id

    game_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM games WHERE user_id = ?", (uid,)
    ).fetchall()]

    from mj_categorize import backfill_board_state_db
    total_updated = 0
    for gid in game_ids:
        total_updated += backfill_board_state_db(conn, gid)
    return jsonify({"ok": True, "games_processed": len(game_ids), "updated": total_updated})


@app.route("/api/games/backfill-decisions", methods=["POST"])
@login_required
def api_backfill_decisions():
    """Backfill decision_count from mortal files and recompute stats."""
    conn = get_conn()
    uid = current_user.id

    games = conn.execute(
        "SELECT id, mortal_file, rounds_json FROM games WHERE user_id = ?", (uid,)
    ).fetchall()

    updated = 0
    for g in games:
        rounds = json.loads(g["rounds_json"]) if g["rounds_json"] else []
        if not rounds or not g["mortal_file"]:
            continue
        # Skip if all rounds already have decision_count
        if all(r.get("decision_count") for r in rounds):
            db.compute_summary_for_game(conn, g["id"])
            continue

        mortal_path = (DIR / g["mortal_file"]).resolve()
        if not str(mortal_path).startswith(str(DIR.resolve())):
            continue
        if not mortal_path.exists():
            continue

        with open(mortal_path) as f:
            mortal_data = json.load(f)

        kyokus = mortal_data.get("review", {}).get("kyokus", [])
        for i, rnd in enumerate(rounds):
            if not rnd.get("decision_count") and i < len(kyokus):
                rnd["decision_count"] = len(kyokus[i].get("entries", []))

        conn.execute(
            "UPDATE games SET rounds_json = ? WHERE id = ?",
            (json.dumps(rounds), g["id"]),
        )
        db.compute_summary_for_game(conn, g["id"])
        updated += 1

    return jsonify({"ok": True, "updated": updated, "total": len(games)})


@app.route("/api/games/add", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def api_add():
    from datetime import date

    conn = get_conn()
    uid = current_user.id

    body = request.json
    mortal_data = body.get("mortal_data")
    game_date = body.get("date") or date.today().isoformat()

    if not mortal_data or not isinstance(mortal_data, dict):
        return jsonify({"error": "mortal_data is required (Mortal analysis JSON)"}), 400

    # Save Mortal JSON to disk (needed by categorizer for wall reconstruction)
    import hashlib
    mortal_dir = DIR / "mortal_analysis"
    mortal_dir.mkdir(exist_ok=True)
    mortal_bytes = json.dumps(mortal_data, ensure_ascii=False).encode()
    filename = hashlib.sha256(mortal_bytes).hexdigest()[:16] + ".json"
    dest = mortal_dir / filename
    if not dest.exists():
        dest.write_bytes(mortal_bytes)

    try:
        game_dict = parse_game(mortal_data, game_date=game_date)
    except (ValueError, KeyError, IndexError, TypeError) as e:
        return jsonify({"error": f"Failed to parse Mortal data: {e}"}), 400
    game_dict["mortal_file"] = str(dest.relative_to(DIR))
    compute_summary(game_dict)

    game_id = db.add_game(conn, uid, game_dict)

    def generate():
        from mj_categorize import categorize_game_db
        import threading
        import queue

        # Own connection — the request-scoped conn may be closed by teardown
        # before this generator finishes, and the background thread needs its own.
        gen_conn = db.get_db()

        yield f"data: {json.dumps({'step': 'parsing', 'message': 'Game added, categorizing mistakes...'})}\n\n"

        progress_q = queue.Queue()

        def progress_cb(done, total):
            progress_q.put((done, total))

        result_holder = {}

        def run_categorize():
            try:
                cat_n, api_calls_n, failures_n = categorize_game_db(gen_conn, game_id, on_progress=progress_cb)
                result_holder["cat_n"] = cat_n
                result_holder["api_calls"] = api_calls_n
                result_holder["failures"] = failures_n
            except Exception as e:
                result_holder["error"] = str(e)
            finally:
                progress_q.put(None)  # sentinel

        t = threading.Thread(target=run_categorize)
        t.start()

        while True:
            item = progress_q.get()
            if item is None:
                break
            done, total = item
            yield f"data: {json.dumps({'step': 'categorizing', 'done': done, 'total': total})}\n\n"

        t.join()

        if "error" in result_holder:
            yield f"data: {json.dumps({'step': 'error', 'message': result_holder['error']})}\n\n"
        else:
            cat_n = result_holder.get("cat_n", 0)
            stats = db.compute_summary_for_game(gen_conn, game_id) if cat_n > 0 else game_dict.get("summary", {})
            final = {"step": "done", "ok": True, "game_id": game_id, "summary": stats,
                      "categorized": cat_n, "api_calls": result_holder.get("api_calls", 0)}
            if result_holder.get("failures"):
                final["failures"] = result_holder["failures"]
            yield f"data: {json.dumps(final)}\n\n"

        gen_conn.close()

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/practice")
@login_required
def api_practice():
    conn = get_conn()
    uid = current_user.id

    sev = request.args.get("severity")
    group = request.args.get("group")
    defense = request.args.get("defense") == "1"
    calc_agree = request.args.get("calc_agree") == "1"

    pick = db.get_practice_problem(conn, uid, severity=sev, group=group,
                                   defense_only=defense, calc_agree=calc_agree)
    if not pick:
        return jsonify({"error": "No matching practice problems"}), 404
    return jsonify(pick)


@app.route("/api/practice/public")
def api_practice_public():
    conn = get_conn()
    sev = request.args.get("severity")
    group = request.args.get("group")
    defense = request.args.get("defense") == "1"
    calc_agree = request.args.get("calc_agree") == "1"

    pick = db.get_public_practice_problem(conn, severity=sev, group=group,
                                          defense_only=defense, calc_agree=calc_agree)
    if not pick:
        return jsonify({"error": "No matching practice problems"}), 404
    return jsonify(pick)


@app.route("/api/practice/result", methods=["POST"])
@login_required
def api_practice_result():
    conn = get_conn()
    uid = current_user.id
    body = request.json
    if not body:
        return jsonify({"error": "JSON body required"}), 400
    mistake_id = body.get("mistake_id")
    correct = body.get("correct", False)
    if not isinstance(mistake_id, int):
        return jsonify({"error": "mistake_id (int) required"}), 400
    if not db.record_practice_result(conn, uid, mistake_id, correct):
        return jsonify({"error": "Mistake not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/practice/stats")
@login_required
def api_practice_stats():
    conn = get_conn()
    uid = current_user.id
    return jsonify(db.get_practice_stats(conn, uid))


@app.route("/api/feedback", methods=["POST"])
@login_required
def api_feedback():
    conn = get_conn()
    uid = current_user.id
    body = request.json or {}
    fb_type = body.get("type", "general")
    if fb_type not in ("bug", "feature", "general"):
        return jsonify({"error": "type must be bug, feature, or general"}), 400
    message = (body.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    if len(message) > 2000:
        return jsonify({"error": "Message too long (max 2000 chars)"}), 400
    conn.execute(
        "INSERT INTO feedback (user_id, type, message) VALUES (?, ?, ?)",
        (uid, fb_type, message),
    )
    conn.commit()

    # Discord webhook notification
    discord_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if discord_url:
        try:
            http_requests.post(discord_url, json={
                "content": f"**New feedback** ({fb_type}) from {current_user.username}:\n>>> {message[:500]}"
            }, timeout=5)
        except Exception:
            pass  # Non-critical — don't fail the request

    return jsonify({"ok": True})


# --- Admin routes ---

def require_admin(f):
    """Decorator that checks current_user is an admin."""
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        conn = get_conn()
        if not db.is_admin(conn, current_user.id):
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


@app.route("/api/admin/stats")
@require_admin
def api_admin_stats():
    conn = get_conn()
    users = db.admin_user_stats(conn)
    return jsonify({"users": users, "total_users": len(users)})


@app.route("/api/admin/feedback")
@require_admin
def api_admin_feedback():
    conn = get_conn()
    status = request.args.get("status")
    fb_type = request.args.get("type")
    items = db.list_feedback(conn, status=status, fb_type=fb_type)
    return jsonify(items)


@app.route("/api/admin/feedback/<int:feedback_id>", methods=["POST"])
@require_admin
def api_admin_feedback_update(feedback_id):
    conn = get_conn()
    body = request.json or {}
    status = body.get("status")
    admin_note = body.get("admin_note")

    if status and status not in ("new", "in-progress", "resolved"):
        return jsonify({"error": "Invalid status"}), 400
    if admin_note is not None and len(admin_note) > 2000:
        return jsonify({"error": "Note too long"}), 400

    updates = {}
    if status:
        updates["status"] = status
    if admin_note is not None:
        updates["admin_note"] = admin_note

    if not updates:
        return jsonify({"error": "Nothing to update"}), 400

    item = db.get_feedback_item(conn, feedback_id)
    if not item:
        return jsonify({"error": "Feedback not found"}), 404

    db.update_feedback(conn, feedback_id, **updates)
    return jsonify({"ok": True})


@app.route("/api/admin/feedback/<int:feedback_id>/create-issue", methods=["POST"])
@require_admin
@limiter.limit("10 per minute")
def api_admin_create_issue(feedback_id):
    conn = get_conn()
    item = db.get_feedback_item(conn, feedback_id)
    if not item:
        return jsonify({"error": "Feedback not found"}), 404
    if item.get("github_issue_url"):
        return jsonify({"error": "Issue already created", "url": item["github_issue_url"]}), 409

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return jsonify({"error": "GITHUB_TOKEN not configured"}), 500

    repo = os.environ.get("GITHUB_REPO", "goreil/haipai-mahjong")

    label_map = {"bug": "bug", "feature": "enhancement", "general": "feedback"}
    labels = ["feedback"]
    type_label = label_map.get(item["type"])
    if type_label and type_label != "feedback":
        labels.append(type_label)

    title = f"[feedback] {item['type']}: {item['message'][:60]}"
    body = (
        f"**From**: {item['username']}\n"
        f"**Type**: {item['type']}\n"
        f"**Date**: {item['created_at']}\n\n"
        f"---\n\n{item['message']}\n\n"
        f"---\n*Feedback ID: {feedback_id}*"
    )

    try:
        resp = http_requests.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            },
            json={"title": title, "body": body, "labels": labels},
            timeout=10,
        )
        resp.raise_for_status()
        issue_url = resp.json().get("html_url", "")
    except http_requests.RequestException as e:
        return jsonify({"error": f"GitHub API error: {e}"}), 502

    db.update_feedback(conn, feedback_id, github_issue_url=issue_url, status="in-progress")
    return jsonify({"ok": True, "url": issue_url})


# --- User feedback status ---

@app.route("/api/feedback/mine")
@login_required
def api_feedback_mine():
    conn = get_conn()
    items = db.get_user_feedback(conn, current_user.id)
    return jsonify(items)


def init_app():
    """Initialize database. Called once on startup."""
    conn = db.get_db()
    db.init_db(conn)
    conn.close()


# Auto-init when imported by gunicorn (not in Flask reloader parent)
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
    init_app()


if __name__ == "__main__":
    # Dev server: init in reloader child only
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        pass  # already initialized above
    elif not app.debug:
        init_app()
    app.run(debug=os.environ.get("FLASK_ENV") == "development", port=5000)
