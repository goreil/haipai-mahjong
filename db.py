#!/usr/bin/env python3
"""SQLite database module for mahjong game review data."""

import json
import os
import sqlite3
from pathlib import Path

DIR = Path(__file__).parent
DB_FILE = Path(os.environ.get("DB_PATH", DIR / "games.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    practice_opt_in INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invite_codes (
    code TEXT PRIMARY KEY,
    used_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP,
    FOREIGN KEY (used_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    log_url TEXT,
    mortal_file TEXT,
    stats_json TEXT,
    rounds_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS practice_results (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    mistake_id INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (mistake_id) REFERENCES mistakes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    admin_note TEXT,
    github_issue_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY,
    game_id INTEGER NOT NULL,
    round_name TEXT NOT NULL,
    round_idx INTEGER NOT NULL,
    mistake_idx INTEGER NOT NULL,
    data_json TEXT NOT NULL,
    category TEXT,
    severity TEXT,
    ev_loss REAL,
    turn INTEGER,
    note TEXT,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_games_user_id ON games(user_id);
CREATE INDEX IF NOT EXISTS idx_mistakes_game_id ON mistakes(game_id);
CREATE INDEX IF NOT EXISTS idx_practice_results_mistake_id ON practice_results(mistake_id);
"""

# Fields stored as columns (not in data_json)
MISTAKE_COLUMNS = {"category", "severity", "ev_loss", "turn", "note"}


def get_db(db_path=None):
    """Get a database connection."""
    path = db_path or DB_FILE
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn):
    """Create tables if they don't exist, then run migrations for new columns."""
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)


def _migrate(conn):
    """Add columns that may be missing on older databases."""
    def _has_column(table, column):
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(c["name"] == column for c in cols)

    altered = False
    if not _has_column("users", "is_admin"):
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
        altered = True
    if not _has_column("users", "practice_opt_in"):
        conn.execute("ALTER TABLE users ADD COLUMN practice_opt_in INTEGER NOT NULL DEFAULT 0")
        altered = True
    for col, typedef in [("status", "TEXT NOT NULL DEFAULT 'new'"),
                         ("admin_note", "TEXT"),
                         ("github_issue_url", "TEXT")]:
        if not _has_column("feedback", col):
            conn.execute(f"ALTER TABLE feedback ADD COLUMN {col} {typedef}")
            altered = True
    if altered:
        conn.commit()


# --- Mistake serialization ---

def mistake_to_row(mistake, game_id, round_name, round_idx, mistake_idx):
    """Convert a mistake dict to DB row values."""
    # Separate column fields from the data blob
    data = {k: v for k, v in mistake.items() if k not in MISTAKE_COLUMNS}
    return {
        "game_id": game_id,
        "round_name": round_name,
        "round_idx": round_idx,
        "mistake_idx": mistake_idx,
        "data_json": json.dumps(data, ensure_ascii=False),
        "category": mistake.get("category"),
        "severity": mistake.get("severity"),
        "ev_loss": mistake.get("ev_loss"),
        "turn": mistake.get("turn"),
        "note": mistake.get("note"),
    }


def row_to_mistake(row):
    """Convert a DB row back to a mistake dict."""
    m = json.loads(row["data_json"])
    m["category"] = row["category"]
    m["severity"] = row["severity"]
    m["ev_loss"] = row["ev_loss"]
    m["turn"] = row["turn"]
    m["note"] = row["note"]
    return m


# --- Games ---

def list_games(conn, user_id):
    """List all games for a user (summary info for sidebar)."""
    rows = conn.execute(
        "SELECT id, date, log_url, stats_json FROM games WHERE user_id = ? ORDER BY date DESC, id DESC",
        (user_id,),
    ).fetchall()
    result = []
    for row in rows:
        stats = json.loads(row["stats_json"]) if row["stats_json"] else {}
        # Count annotated mistakes
        annotated = conn.execute(
            "SELECT COUNT(*) FROM mistakes WHERE game_id = ? AND category IS NOT NULL",
            (row["id"],),
        ).fetchone()[0]
        total = conn.execute(
            "SELECT COUNT(*) FROM mistakes WHERE game_id = ?",
            (row["id"],),
        ).fetchone()[0]
        result.append({
            "id": row["id"],
            "date": row["date"],
            "log_url": row["log_url"],
            "summary": stats,
            "annotated": annotated,
            "total": total,
        })
    return result


def get_game(conn, game_id, user_id=None):
    """Get full game data with rounds and mistakes (for detail view)."""
    where = "id = ?"
    params = [game_id]
    if user_id is not None:
        where += " AND user_id = ?"
        params.append(user_id)

    game_row = conn.execute(
        f"SELECT * FROM games WHERE {where}", params
    ).fetchone()
    if not game_row:
        return None

    stats = json.loads(game_row["stats_json"]) if game_row["stats_json"] else {}
    rounds_meta = json.loads(game_row["rounds_json"]) if game_row["rounds_json"] else []

    # Load mistakes grouped by round
    mistake_rows = conn.execute(
        "SELECT * FROM mistakes WHERE game_id = ? ORDER BY round_idx, mistake_idx",
        (game_id,),
    ).fetchall()

    # Build rounds structure
    rounds_map = {}
    for mr in mistake_rows:
        ri = mr["round_idx"]
        if ri not in rounds_map:
            rounds_map[ri] = {
                "round": mr["round_name"],
                "mistakes": [],
            }
        rounds_map[ri]["mistakes"].append(row_to_mistake(mr))

    # Merge with round metadata (outcome, turn_count)
    rounds = []
    for idx, meta in enumerate(rounds_meta):
        rnd = rounds_map.get(idx, {"round": meta["round_name"], "mistakes": []})
        rnd["round"] = meta["round_name"]
        rnd["outcome"] = meta.get("outcome")
        rnd["turn_count"] = meta.get("turn_count")
        rnd["decision_count"] = meta.get("decision_count")
        rounds.append(rnd)

    # Add any rounds that have mistakes but no metadata (shouldn't happen but be safe)
    for idx in sorted(rounds_map.keys()):
        if idx >= len(rounds):
            rounds.append(rounds_map[idx])

    return {
        "id": game_row["id"],
        "date": game_row["date"],
        "log_url": game_row["log_url"],
        "mortal_file": game_row["mortal_file"],
        "summary": stats,
        "rounds": rounds,
    }


def add_game(conn, user_id, game_dict):
    """Insert a full game dict (as produced by mj_parse.parse_game).

    All inserts are wrapped in a transaction — if any mistake insert fails,
    the entire game (including the games row) is rolled back.

    Returns the new game_id.
    """
    # Build rounds metadata
    rounds_meta = []
    for rnd in game_dict.get("rounds", []):
        rounds_meta.append({
            "round_name": rnd["round"],
            "outcome": rnd.get("outcome"),
            "turn_count": rnd.get("turn_count"),
            "decision_count": rnd.get("decision_count"),
        })

    try:
        cur = conn.execute(
            """INSERT INTO games (user_id, date, log_url, mortal_file, stats_json, rounds_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                game_dict.get("date"),
                game_dict.get("log_url"),
                game_dict.get("mortal_file"),
                json.dumps(game_dict.get("summary") or {}, ensure_ascii=False),
                json.dumps(rounds_meta, ensure_ascii=False),
            ),
        )
        game_id = cur.lastrowid

        # Insert mistakes
        for round_idx, rnd in enumerate(game_dict.get("rounds", [])):
            for mistake_idx, m in enumerate(rnd.get("mistakes", [])):
                row = mistake_to_row(m, game_id, rnd["round"], round_idx, mistake_idx)
                conn.execute(
                    """INSERT INTO mistakes
                       (game_id, round_name, round_idx, mistake_idx, data_json,
                        category, severity, ev_loss, turn, note)
                       VALUES (:game_id, :round_name, :round_idx, :mistake_idx, :data_json,
                               :category, :severity, :ev_loss, :turn, :note)""",
                    row,
                )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return game_id


def delete_game(conn, game_id, user_id=None):
    """Delete a game and its mistakes. Returns True if deleted."""
    where = "id = ?"
    params = [game_id]
    if user_id is not None:
        where += " AND user_id = ?"
        params.append(user_id)

    cur = conn.execute(f"DELETE FROM games WHERE {where}", params)
    conn.commit()
    return cur.rowcount > 0


def update_game_stats(conn, game_id, stats):
    """Update the stats_json for a game."""
    conn.execute(
        "UPDATE games SET stats_json = ? WHERE id = ?",
        (json.dumps(stats, ensure_ascii=False), game_id),
    )
    conn.commit()


# --- Mistakes ---

def annotate_mistake(conn, game_id, round_name, turn, index, category, note, user_id=None):
    """Update category/note on a specific mistake. Returns the updated mistake or None."""
    # Verify game ownership
    if user_id is not None:
        owner = conn.execute("SELECT user_id FROM games WHERE id = ?", (game_id,)).fetchone()
        if not owner or owner["user_id"] != user_id:
            return None

    # Find the mistake
    rows = conn.execute(
        "SELECT id, category, note FROM mistakes WHERE game_id = ? AND round_name = ? AND turn = ? ORDER BY mistake_idx",
        (game_id, round_name, turn),
    ).fetchall()

    if index >= len(rows):
        return None

    mistake_id = rows[index]["id"]
    updates = {}
    if category is not None:
        updates["category"] = category if category else None
    if note is not None:
        updates["note"] = note if note else None

    ALLOWED_COLS = {"category", "note"}
    updates = {k: v for k, v in updates.items() if k in ALLOWED_COLS}
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE mistakes SET {set_clause} WHERE id = ?",
            list(updates.values()) + [mistake_id],
        )
        conn.commit()

    return True


def update_mistake_data(conn, mistake_id, updates):
    """Update columns and/or data_json fields on a mistake.

    `updates` can contain column names (category, severity, etc.)
    and data fields (cpp_best, cpp_stats, safety_ratings, etc.).
    Uses SQLite json_set() for atomic data_json updates to avoid
    read-modify-write races.
    """
    col_updates = {}
    data_updates = {}
    for k, v in updates.items():
        if k in MISTAKE_COLUMNS:
            col_updates[k] = v
        else:
            data_updates[k] = v

    if data_updates:
        # Atomic merge using json_set — no read-modify-write needed
        json_expr = "data_json"
        params = []
        for key, val in data_updates.items():
            json_expr = f"json_set({json_expr}, '$.{key}', json(?))"
            params.append(json.dumps(val, ensure_ascii=False))
        col_updates["data_json"] = None  # placeholder, handled by raw SQL below

    set_parts = []
    params_final = []
    for k, v in col_updates.items():
        if k == "data_json" and data_updates:
            set_parts.append(f"data_json = {json_expr}")
            params_final.extend(params)
        else:
            set_parts.append(f"{k} = ?")
            params_final.append(v)

    if set_parts:
        sql = f"UPDATE mistakes SET {', '.join(set_parts)} WHERE id = ?"
        params_final.append(mistake_id)
        conn.execute(sql, params_final)
        conn.commit()


def record_practice_result(conn, user_id, mistake_id, correct):
    """Record a practice attempt. Validates mistake belongs to user."""
    owner = conn.execute(
        "SELECT g.user_id FROM mistakes m JOIN games g ON m.game_id = g.id WHERE m.id = ?",
        (mistake_id,),
    ).fetchone()
    if not owner or owner["user_id"] != user_id:
        return False
    conn.execute(
        "INSERT INTO practice_results (user_id, mistake_id, correct) VALUES (?, ?, ?)",
        (user_id, mistake_id, 1 if correct else 0),
    )
    conn.commit()
    return True


def get_practice_stats(conn, user_id):
    """Get practice accuracy stats by category group."""
    from mj_games import CATEGORY_INFO
    rows = conn.execute(
        """SELECT m.category, pr.correct, COUNT(*) as cnt
           FROM practice_results pr
           JOIN mistakes m ON pr.mistake_id = m.id
           WHERE pr.user_id = ?
           GROUP BY m.category, pr.correct""",
        (user_id,),
    ).fetchall()
    groups = {}
    for row in rows:
        cat = row["category"] or "Unknown"
        grp = CATEGORY_INFO.get(cat, {}).get("group", "Other")
        if grp not in groups:
            groups[grp] = {"correct": 0, "total": 0}
        groups[grp]["total"] += row["cnt"]
        if row["correct"]:
            groups[grp]["correct"] += row["cnt"]
    return groups


def get_practice_problem(conn, user_id, severity=None, group=None, defense_only=False,
                         calc_agree=False):
    """Get a weighted-random eligible practice problem.

    Weighting: unseen problems x3, previously wrong x3, right once x1, right 2+ times x0.5.
    """
    from mj_games import CATEGORY_INFO
    import random

    where = ["g.user_id = ?", "m.severity IN ('??', '???' )"]
    params = [user_id]

    if severity:
        where.append("m.severity = ?")
        params.append(severity)

    if calc_agree:
        where.append("m.category IN ('1A','1B','1C','1D','1E')")

    rows = conn.execute(
        f"""SELECT m.*, g.date as game_date, g.id as gid
            FROM mistakes m JOIN games g ON m.game_id = g.id
            WHERE {' AND '.join(where)}""",
        params,
    ).fetchall()

    # Get practice history for this user
    history = {}
    hist_rows = conn.execute(
        "SELECT mistake_id, correct FROM practice_results WHERE user_id = ? ORDER BY created_at",
        (user_id,),
    ).fetchall()
    for hr in hist_rows:
        mid = hr["mistake_id"]
        if mid not in history:
            history[mid] = {"attempts": 0, "correct": 0, "last_correct": None}
        history[mid]["attempts"] += 1
        if hr["correct"]:
            history[mid]["correct"] += 1
        history[mid]["last_correct"] = bool(hr["correct"])

    # Filter and weight candidates
    candidates = []
    weights = []
    for row in rows:
        data = json.loads(row["data_json"])
        actual = data.get("actual") or {}
        expected = data.get("expected") or {}
        if actual.get("type") != "dahai" or expected.get("type") != "dahai":
            continue
        if not data.get("hand"):
            continue
        if defense_only and not data.get("safety_ratings"):
            continue
        if group:
            cat = row["category"] or ""
            cat_group = CATEGORY_INFO.get(cat, {}).get("group", "")
            if cat_group != group:
                continue

        mid = row["id"]
        h = history.get(mid)
        if h is None:
            w = 3.0  # never seen
        elif h["last_correct"] is False:
            w = 3.0  # got wrong last time
        elif h["correct"] >= 2:
            w = 0.5  # mastered
        else:
            w = 1.0  # seen, got right once

        candidates.append({
            "game_id": row["gid"],
            "game_date": row["game_date"],
            "round": row["round_name"],
            "mistake": row_to_mistake(row),
            "mistake_id": mid,
        })
        weights.append(w)

    if not candidates:
        return None

    pick = random.choices(candidates, weights=weights, k=1)[0]
    pick["pool_size"] = len(candidates)
    return pick


def get_public_practice_problem(conn, severity=None, group=None, defense_only=False,
                                calc_agree=False):
    """Get a random practice problem from opted-in users' games, anonymized.

    No spaced repetition — uniform random selection.
    Only includes games from users with practice_opt_in=1.
    Strips user-identifying info (notes, game dates).
    """
    from mj_games import CATEGORY_INFO
    import random

    where = ["m.severity IN ('??', '???' )", "u.practice_opt_in = 1"]
    params = []

    if severity:
        where.append("m.severity = ?")
        params.append(severity)

    if calc_agree:
        where.append("m.category IN ('1A','1B','1C','1D','1E')")

    rows = conn.execute(
        f"""SELECT m.*, g.id as gid
            FROM mistakes m
            JOIN games g ON m.game_id = g.id
            JOIN users u ON g.user_id = u.id
            WHERE {' AND '.join(where)}""",
        params,
    ).fetchall()

    candidates = []
    for row in rows:
        data = json.loads(row["data_json"])
        actual = data.get("actual") or {}
        expected = data.get("expected") or {}
        if actual.get("type") != "dahai" or expected.get("type") != "dahai":
            continue
        if not data.get("hand"):
            continue
        if defense_only and not data.get("safety_ratings"):
            continue
        if group:
            cat = row["category"] or ""
            cat_group = CATEGORY_INFO.get(cat, {}).get("group", "")
            if cat_group != group:
                continue

        mistake = row_to_mistake(row)
        mistake["note"] = None  # strip user annotation

        candidates.append({
            "game_id": row["gid"],
            "round": row["round_name"],
            "mistake": mistake,
            "mistake_id": row["id"],
        })

    if not candidates:
        return None

    pick = random.choice(candidates)
    pick["pool_size"] = len(candidates)
    return pick


def get_trends(conn, user_id):
    """Get per-game trend data."""
    from mj_games import CATEGORY_INFO
    rows = conn.execute(
        "SELECT id, date, stats_json FROM games WHERE user_id = ? ORDER BY date, id",
        (user_id,),
    ).fetchall()
    games = []
    for row in rows:
        s = json.loads(row["stats_json"]) if row["stats_json"] else {}
        by_cat = s.get("by_category", {})
        by_group = {}
        for cat, info in by_cat.items():
            grp = CATEGORY_INFO.get(cat, {}).get("group", cat)
            if grp not in by_group:
                by_group[grp] = {"count": 0, "ev": 0.0}
            by_group[grp]["count"] += info["count"]
            by_group[grp]["ev"] = round(by_group[grp]["ev"] + info["ev"], 2)
        games.append({
            "id": row["id"],
            "date": row["date"],
            "total_mistakes": s.get("total_mistakes", 0),
            "total_ev_loss": s.get("total_ev_loss", 0),
            "total_decisions": s.get("total_decisions"),
            "ev_per_decision": s.get("ev_per_decision"),
            "by_severity": s.get("by_severity", {}),
            "by_group": by_group,
        })
    return games


# --- Summary computation ---

def compute_summary_for_game(conn, game_id):
    """Recompute stats from mistakes and update the game row. Returns the stats dict."""
    rows = conn.execute(
        "SELECT severity, ev_loss, category FROM mistakes WHERE game_id = ?",
        (game_id,),
    ).fetchall()

    total = len(rows)
    ev = sum(r["ev_loss"] for r in rows if r["ev_loss"])
    by_sev = {}
    by_cat = {}
    for r in rows:
        s = r["severity"] or "?"
        by_sev[s] = by_sev.get(s, 0) + 1
        cat = r["category"]
        if cat:
            if cat not in by_cat:
                by_cat[cat] = {"count": 0, "ev": 0.0}
            by_cat[cat]["count"] += 1
            by_cat[cat]["ev"] = round(by_cat[cat]["ev"] + (r["ev_loss"] or 0), 2)

    # Get total decisions from rounds_json (fall back to turn_count for old data)
    game_row = conn.execute("SELECT rounds_json FROM games WHERE id = ?", (game_id,)).fetchone()
    total_decisions = None
    if game_row and game_row["rounds_json"]:
        rounds = json.loads(game_row["rounds_json"])
        decisions = [r.get("decision_count") or r.get("turn_count") for r in rounds]
        decisions = [d for d in decisions if d]
        if decisions:
            total_decisions = sum(decisions)

    stats = {
        "total_mistakes": total,
        "total_ev_loss": round(ev, 2),
        "total_decisions": total_decisions,
        "ev_per_decision": round(ev / total_decisions, 4) if total_decisions else None,
        "by_severity": by_sev,
        "by_category": by_cat,
    }

    update_game_stats(conn, game_id, stats)
    return stats


# --- Users ---

def create_user(conn, username, password_hash, invite_code=None):
    """Create a new user. Returns user_id or raises on duplicate."""
    cur = conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, password_hash),
    )
    user_id = cur.lastrowid

    if invite_code:
        conn.execute(
            "UPDATE invite_codes SET used_by = ?, used_at = CURRENT_TIMESTAMP WHERE code = ?",
            (user_id, invite_code),
        )

    conn.commit()
    return user_id


def get_user_by_username(conn, username):
    """Get user row by username."""
    return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def get_user_by_id(conn, user_id):
    """Get user row by id."""
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def set_practice_opt_in(conn, user_id, opt_in):
    """Set whether a user's games are available in the public practice pool."""
    conn.execute("UPDATE users SET practice_opt_in = ? WHERE id = ?",
                 (1 if opt_in else 0, user_id))
    conn.commit()


# --- Invite codes ---

def create_invite_codes(conn, n):
    """Generate n invite codes. Returns list of code strings."""
    import secrets
    codes = []
    for _ in range(n):
        code = secrets.token_urlsafe(8)
        conn.execute("INSERT INTO invite_codes (code) VALUES (?)", (code,))
        codes.append(code)
    conn.commit()
    return codes


def list_invite_codes(conn):
    """List all invite codes with status."""
    return conn.execute(
        """SELECT ic.code, ic.created_at, ic.used_at, u.username as used_by_name
           FROM invite_codes ic LEFT JOIN users u ON ic.used_by = u.id
           ORDER BY ic.created_at""",
    ).fetchall()


def validate_invite_code(conn, code):
    """Check if an invite code is valid (exists and unused). Returns True/False."""
    row = conn.execute(
        "SELECT used_by FROM invite_codes WHERE code = ?", (code,)
    ).fetchone()
    return row is not None and row["used_by"] is None


# --- Admin / Feedback management ---

def is_admin(conn, user_id):
    """Check if a user has admin privileges."""
    row = conn.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    return bool(row and row["is_admin"])


def admin_user_stats(conn):
    """Get per-user game counts for the admin dashboard."""
    rows = conn.execute(
        """SELECT u.id, u.username, u.created_at,
                  COUNT(g.id) as game_count
           FROM users u LEFT JOIN games g ON u.id = g.user_id
           GROUP BY u.id ORDER BY u.created_at""",
    ).fetchall()
    return [dict(r) for r in rows]


def list_feedback(conn, status=None, fb_type=None):
    """List all feedback with optional filters. Returns list of dicts."""
    where = []
    params = []
    if status:
        where.append("f.status = ?")
        params.append(status)
    if fb_type:
        where.append("f.type = ?")
        params.append(fb_type)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(
        f"""SELECT f.*, u.username FROM feedback f
            JOIN users u ON f.user_id = u.id
            {where_sql}
            ORDER BY f.created_at DESC""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def get_feedback_item(conn, feedback_id):
    """Get a single feedback item with username."""
    row = conn.execute(
        """SELECT f.*, u.username FROM feedback f
           JOIN users u ON f.user_id = u.id
           WHERE f.id = ?""",
        (feedback_id,),
    ).fetchone()
    return dict(row) if row else None


def update_feedback(conn, feedback_id, **kwargs):
    """Update feedback fields (status, admin_note, github_issue_url)."""
    ALLOWED = {"status", "admin_note", "github_issue_url"}
    updates = {k: v for k, v in kwargs.items() if k in ALLOWED}
    if not updates:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE feedback SET {set_clause} WHERE id = ?",
        list(updates.values()) + [feedback_id],
    )
    conn.commit()
    return True


def get_user_feedback(conn, user_id):
    """Get feedback submitted by a specific user."""
    rows = conn.execute(
        """SELECT id, type, message, status, admin_note, created_at
           FROM feedback WHERE user_id = ? ORDER BY created_at DESC""",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]
