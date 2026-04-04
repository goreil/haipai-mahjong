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
from pathlib import Path

DIR = Path(__file__).parent
_CACHE_DB = Path(os.environ.get("CPP_CACHE_PATH", DIR / "cpp_cache.db"))
_cache_conn = None


def _get_conn():
    """Get or create the module-level cache DB connection."""
    global _cache_conn
    if _cache_conn is None:
        _cache_conn = sqlite3.connect(str(_CACHE_DB))
        _cache_conn.execute("PRAGMA journal_mode=WAL")
        _cache_conn.execute(
            "CREATE TABLE IF NOT EXISTS cache "
            "(key TEXT PRIMARY KEY, response TEXT)"
        )
        _cache_conn.commit()
    return _cache_conn


def _make_key(request_data):
    """Deterministic SHA-256 of the request payload."""
    canonical = json.dumps(request_data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def get(request_data):
    """Look up a cached response.  Returns parsed dict or None."""
    key = _make_key(request_data)
    row = _get_conn().execute(
        "SELECT response FROM cache WHERE key = ?", (key,)
    ).fetchone()
    if row:
        return json.loads(row[0])
    return None


def put(request_data, response):
    """Store a response in the cache."""
    key = _make_key(request_data)
    _get_conn().execute(
        "INSERT OR REPLACE INTO cache (key, response) VALUES (?, ?)",
        (key, json.dumps(response, separators=(",", ":"))),
    )
    _get_conn().commit()


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
    count = _get_conn().execute("SELECT COUNT(*) FROM cache").fetchone()[0]
    size_bytes = os.path.getsize(_CACHE_DB) if _CACHE_DB.exists() else 0
    return {"entries": count, "size_mb": round(size_bytes / 1_048_576, 1)}


def clear():
    """Delete all cached entries."""
    _get_conn().execute("DELETE FROM cache")
    _get_conn().commit()
    _get_conn().execute("VACUUM")
