#!/usr/bin/env python3
"""Flask web server for mahjong game review — app setup, auth, static routes."""

from flask import Flask, g, jsonify, redirect, render_template_string, request, send_from_directory, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash
from pathlib import Path
import os
import sys

import db
from lib.games import CATEGORY_INFO

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
  padding:40px 0;
}
body::before{
  content:'';position:fixed;inset:0;
  background:
    radial-gradient(ellipse 60% 50% at 20% 80%, rgba(79,195,247,0.06) 0%, transparent 70%),
    radial-gradient(ellipse 50% 40% at 80% 20%, rgba(67,160,71,0.05) 0%, transparent 70%);
  pointer-events:none;
}
.login-wrap{position:relative;z-index:1;width:480px;max-width:92vw}
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
.preview{margin-top:24px;border-radius:10px;overflow:hidden;border:1px solid #1e2540;box-shadow:0 6px 24px rgba(0,0,0,0.3)}
.preview img{width:100%;display:block}
.preview-label{text-align:center;font-size:11px;color:#5a6078;padding:6px 0 2px}
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
{% if register %}{% endif %}
<button>{{ title }}</button>
</form>
{% if register %}
<div class="link">Already have an account? <a href="/login">Login</a></div>
{% else %}
<div class="link">Need an account? <a href="/register">Register</a></div>
{% endif %}
<div class="link"><a href="/practice">Try practice mode without an account</a></div>
<div class="link"><a href="/">What is Haipai?</a></div>
</div>
<div class="preview">
  <img src="/static/screenshot-review.png" alt="Game review with mistake analysis">
</div>
<div class="preview-label">Upload Mortal analysis &middot; See every mistake categorized &middot; Track improvement</div>
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
        conn = get_conn()

        if not username or not password:
            error = "Username and password required"
        elif len(password) < 8:
            error = "Password must be at least 8 characters"
        else:
            try:
                pw_hash = generate_password_hash(password)
                user_id = db.create_user(conn, username, pw_hash)
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


@app.route("/api/top-mistakes")
@login_required
def api_top_mistakes():
    conn = get_conn()
    uid = current_user.id
    group = request.args.get("group")
    limit = min(int(request.args.get("limit", 5)), 20)
    games_limit = min(int(request.args.get("games", 10)), 50)

    # Get recent game IDs
    game_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM games WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
        (uid, games_limit),
    ).fetchall()]
    if not game_ids:
        return jsonify([])

    placeholders = ",".join("?" * len(game_ids))
    where = f"m.game_id IN ({placeholders}) AND m.category IS NOT NULL"
    params = list(game_ids)

    if group:
        # Map group name to category prefixes
        GROUP_PREFIXES = {
            "Efficiency": ["1A"], "Value Tiles": ["2A"],
            "Strategy": ["3A", "3B", "3C"], "Meld": ["4A", "4B", "4C"],
            "Riichi": ["5A", "5B"], "Kan": ["6A", "6B"],
        }
        cats = GROUP_PREFIXES.get(group, [])
        if cats:
            cat_ph = ",".join("?" * len(cats))
            where += f" AND m.category IN ({cat_ph})"
            params.extend(cats)

    rows = conn.execute(
        f"""SELECT m.*, g.date FROM mistakes m
            JOIN games g ON m.game_id = g.id
            WHERE {where}
            ORDER BY m.ev_loss DESC LIMIT ?""",
        params + [limit],
    ).fetchall()

    results = []
    for r in rows:
        m = db.row_to_mistake(r)
        m["game_id"] = r["game_id"]
        m["game_date"] = r["date"]
        m["round_name"] = r["round_name"]
        results.append(m)
    return jsonify(results)


# --- Register blueprints ---

from routes.games import games_bp
from routes.practice import practice_bp
from routes.admin import admin_bp

app.register_blueprint(games_bp)
app.register_blueprint(practice_bp)
app.register_blueprint(admin_bp)

# CSRF exemptions for anonymous endpoints


# --- Init ---

def init_app():
    """Initialize database. Called once on startup."""
    conn = db.get_db()
    db.init_db(conn)
    # Reset any stuck 'pending' categorizations from previous crashes
    conn.execute("UPDATE games SET categorization_status = 'failed' WHERE categorization_status = 'pending'")
    conn.commit()
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
