#!/usr/bin/env python3
"""Cache layer for mahjong-cpp (nanikiru) API responses.

Stores responses in a SQLite database keyed by a SHA-256 hash of the
request payload.  On cache hit the HTTP call is skipped entirely,
eliminating the nanikiru bottleneck for repeated categorization runs.

Usage — drop-in replacement for call_mahjong_cpp:

    # In mj_categorize.py, change:
    #   response = call_mahjong_cpp(req)
    # To:
    #   from cpp_cache import cached_call
    #   response = cached_call(req)

The original call_mahjong_cpp is imported and used on cache miss.
"""

import hashlib
import json
import os
import sqlite3
import sys
import threading
from pathlib import Path

DIR = Path(__file__).parent
# Default to same directory as games.db (DB_PATH) so permissions match
_default_cache = Path(os.environ.get("DB_PATH", DIR / "games.db")).parent / "cpp_cache.db"
_CACHE_DB = Path(os.environ.get("CPP_CACHE_PATH", _default_cache))
_local = threading.local()
_cache_broken = False


def _get_conn():
    """Get or create a thread-local cache DB connection."""
    global _cache_broken
    if _cache_broken:
        return None
    conn = getattr(_local, "conn", None)
    if conn is None:
        try:
            conn = sqlite3.connect(str(_CACHE_DB))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS cache "
                "(key TEXT PRIMARY KEY, response TEXT)"
            )
            conn.commit()
            _local.conn = conn
        except (sqlite3.OperationalError, OSError) as e:
            print(f"  cpp_cache: disabled ({e})", file=sys.stderr)
            _cache_broken = True
            return None
    return conn


def _make_key(request_data):
    """Deterministic SHA-256 of the request payload."""
    canonical = json.dumps(request_data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def get(request_data):
    """Look up a cached response.  Returns parsed dict or None."""
    conn = _get_conn()
    if conn is None:
        return None
    key = _make_key(request_data)
    row = conn.execute(
        "SELECT response FROM cache WHERE key = ?", (key,)
    ).fetchone()
    if row:
        return json.loads(row[0])
    return None


def put(request_data, response):
    """Store a response in the cache.  Silently skips on error."""
    conn = _get_conn()
    if conn is None:
        return
    key = _make_key(request_data)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, response) VALUES (?, ?)",
            (key, json.dumps(response, separators=(",", ":"))),
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass


def cached_call(request_data):
    """Call mahjong-cpp with caching.  Drop-in replacement for call_mahjong_cpp."""
    cached = get(request_data)
    if cached is not None:
        return cached

    # Import here to avoid circular dependency
    from mj_categorize import call_mahjong_cpp

    response = call_mahjong_cpp(request_data)
    put(request_data, response)
    return response


def stats():
    """Return cache stats: total entries and approximate DB size."""
    conn = _get_conn()
    if conn is None:
        return {"entries": 0, "size_mb": 0.0, "disabled": True}
    count = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
    size_bytes = os.path.getsize(_CACHE_DB) if _CACHE_DB.exists() else 0
    return {"entries": count, "size_mb": round(size_bytes / 1_048_576, 1)}


def clear():
    """Delete all cached entries."""
    conn = _get_conn()
    if conn is None:
        return
    conn.execute("DELETE FROM cache")
    conn.commit()
    conn.execute("VACUUM")
