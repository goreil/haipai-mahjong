# Known Bugs & Edge Cases

**Date**: 2026-04-04
**Method**: Static analysis of mj_parse.py, mj_categorize.py, db.py, app.py

---

## Critical

### B-01: parse_game() calls sys.exit() in web context

**Location**: `mj_parse.py:58-63`

When kyoku count doesn't match start_kyoku events, the parser calls `sys.exit(1)`. In the web context (`app.py:551` calls `parse_game()`), this kills the entire Flask/gunicorn worker process instead of returning an error to the user.

**Fix**: Replace `sys.exit(1)` with `raise ValueError(...)`. Add try/except in `api_add()`.

---

### B-02: Red five double-decrement in wall reconstruction

**Location**: `mj_categorize.py:82-88`

`decrement_wall()` decrements both the base tile count AND the red tile count when a red five is played:

```python
wall[base] -= 1    # decrements regular 5m count
if tid != base:
    wall[tid] -= 1  # ALSO decrements red 5m count
```

Playing 5mr should only decrement the red five slot (`wall[34]`), not also `wall[4]`. This causes mahjong-cpp to receive incorrect wall counts, producing wrong tile efficiency recommendations.

**Fix**: Only decrement `wall[tid]`, not both `wall[base]` and `wall[tid]`.

---

### B-03: No input validation in parse_game()

**Location**: `mj_parse.py:52-107`

The parser directly accesses nested fields (`data["review"]["kyokus"]`, `data["mjai_log"]`, `entry["details"][entry["actual_index"]]`) with no validation. Any missing field crashes with an unhelpful KeyError or IndexError. Users uploading malformed JSON get a 500 error.

**Fix**: Validate required top-level structure before parsing. Wrap field access in try/except with descriptive error messages.

---

## High

### B-04: mj_games.py CATEGORIES list doesn't match CATEGORY_INFO

**Location**: `mj_games.py:14-20` vs `mj_games.py:22-35`

`CATEGORIES` lists: 1A, 1B, 1C, 1D, 1E, 2A, 2B, 2C, 3A, 3B, 3C, 4A, 4B, 5A, 5B
`CATEGORY_INFO` defines: 1A, 2A, 3A, 3B, 3C, 4A, 4B, 4C, 5A, 5B, 6A, 6B

The CLI's `--category` flag validates against the stale `CATEGORIES` list, rejecting valid codes (4C, 6A, 6B) and accepting deleted ones (1B-1E, 2B, 2C).

**Fix**: Derive `CATEGORIES` from `CATEGORY_INFO.keys()`. Single source of truth.

---

### B-05: Non-atomic game import can leave orphaned data

**Location**: `db.py:216-259`

`add_game()` inserts the game row first, then inserts each mistake separately. If a mistake insert fails midway, the game exists but is incomplete. No transaction wrapping or rollback.

**Fix**: Wrap the entire add_game() in a single transaction.

---

### B-06: Silent failure when nanikiru is down during categorization

**Location**: `mj_categorize.py:714-721`

`call_mahjong_cpp()` catches all exceptions and returns `None`. The caller skips uncategorizable mistakes silently. The API response reports success (`"ok": true`) with a count, but the user can't tell which mistakes failed or why.

**Fix**: Track and report failures. Return error count alongside success count.

---

## Medium

### B-07: Read-modify-write race on data_json

**Location**: `db.py:342-351`

`update_mistake_data()` reads the full `data_json`, modifies it in Python, then writes it back. Two concurrent requests modifying the same mistake's data_json will cause one write to overwrite the other.

**Fix**: Use SQLite JSON functions (`json_set`) for atomic field updates, or add row-level locking.

---

### B-08: No database indexes

**Location**: `db.py:12-73` (SCHEMA)

No indexes defined on any table. `SELECT * FROM mistakes WHERE game_id = ?` and similar queries do full table scans. Not a problem at current scale (single user, <100 games) but will degrade with growth.

**Fix**: Add indexes on `mistakes(game_id)`, `practice_results(mistake_id)`, `games(user_id)`.

---

### B-09: api_backfill_board_state() is misleading

**Location**: `app.py:461-477`

The endpoint name says "backfill board state" but it calls `categorize_game_db()` which does categorization, not board state backfill. If no recategorization is needed, it returns success having done nothing.

**Fix**: Either rename the endpoint or implement actual board state backfill.

---

### B-10: Negative wall counts silently clamped

**Location**: `mj_categorize.py:688-690`

Negative tile counts in the wall are clamped to 0 instead of raising an error. This hides upstream bugs (like B-02) rather than surfacing them.

**Fix**: Log a warning or raise an error on negative wall counts during development. Clamp only in production.

---

## Low

### B-11: Dora indicator may be double-counted in wall

**Location**: `mj_categorize.py:124, 179-180`

The dora indicator is added to the visible tiles list and then decremented from the wall. But dora indicators are not tiles in any player's hand -- they're revealed from the dead wall. Depending on how mahjong-cpp expects the wall, this may or may not be correct. Needs verification.

---

### B-12: vision.txt says "15-category system"

**Location**: `vision.txt:28,40`

References "15-category system" but the system now has 12 categories. Internal doc, low impact.
