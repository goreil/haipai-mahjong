# Test Coverage Gaps

**Date**: 2026-04-04
**Current**: 26 tests in `tests/test_core.py`, CI via `.github/workflows/test.yml`
**Estimated coverage**: ~40% of functions

---

## Coverage by File

| File | Functions | Tested | Gap | Risk |
|------|-----------|--------|-----|------|
| mj_defense.py | 5 | 0 | 100% untested | CRITICAL |
| mj_categorize.py | 21 | 7 | categorize_mistake(), classify_*, action_type | CRITICAL |
| app.py | 21 | 8 | 14 API routes untested | HIGH |
| db.py | 14 | 9 | practice, trends, invite codes | MEDIUM |
| mj_parse.py | 6 | 3 | format_action(), error paths | LOW |

---

## Tier 1: Core Logic (highest risk, no coverage)

### T-01: mj_defense.py -- zero tests

All 5 functions completely untested:
- `evaluate_safety()` -- core safety rating (0-15 scale), 58 lines of branching logic
- `_is_suji()` -- suji protection check, boundary conditions at suit borders
- `extract_riichi_state()` -- riichi opponent tracking from mjai event stream
- `get_opponent_discards()` -- discard pool extraction with meld handling
- `get_tile_safety_for_mistake()` -- public API integrating all of the above

Key edge cases to test:
- Genbutsu (discarded tiles = 15 rating)
- Suji vs non-suji terminals and number tiles
- Multiple opponents in riichi (safety averaging)
- Red five handling in safety context
- Empty riichi state (no opponent in riichi -> return None)

### T-02: Categorization decision logic

Untested functions in `mj_categorize.py`:
- `categorize_mistake()` (line 649) -- 113 lines, main decision tree
- `categorize_by_action_type()` (line 390) -- maps action pairs to 4A-6B
- `classify_efficiency()` (line 456) -- 1A vs 2A distinction
- `_classify_strategic()` (line 568) -- 3A vs 3B (defense gap check)
- `_cpp_reasonably_agrees()` (line 604) -- agreement threshold logic

Key edge cases:
- Action type pairs: chi+pass, pass+chi, pon+dahai, reach+dahai, etc.
- Efficiency with value tiles at boundary (exactly 60 point diff)
- Defense with safety gap exactly at threshold (3)
- Mortal and cpp pick same tile vs different tile with same shanten

### T-03: Wall reconstruction

`decrement_wall()` (line 82) has the red five double-decrement bug (see BUGS.md B-02). Tests would catch this immediately but none exist for this function directly.

---

## Tier 2: API Routes & Integration

### T-04: 14 untested API routes

No Flask test client tests exist for:
- `POST /api/games/add` -- game upload (most critical user flow)
- `DELETE /api/games/<id>` -- game deletion
- `GET /api/games/<id>` -- individual game retrieval
- `POST /api/games/<id>/categorize` -- auto-categorization trigger
- `GET /api/trends` -- trend analytics
- `GET /api/practice` -- practice problem selection
- `POST /api/practice/result` -- practice result recording (has ownership check)
- `GET /api/practice/stats` -- practice statistics
- `POST /api/games/import` -- batch import
- `POST /api/games/backfill-board-state` -- board state backfill
- `POST /api/games/backfill-decisions` -- decision count backfill
- `GET /api/me` -- current user info
- `POST /register` -- registration flow
- `POST /logout` -- logout

### T-05: Auth & security edge cases

Not tested:
- Login with wrong password (timing-safe comparison exists but unverified)
- Registration with duplicate username
- Registration with invalid invite code
- Password length validation (8+ chars)
- Category validation in annotate endpoint (empty string = clear)
- Note length validation (1000 char limit)
- CSRF token enforcement

### T-06: Database integration

Untested in db.py:
- `get_practice_problem()` (line 393) -- 85-line function with weighted random selection
- `get_trends()` (line 481) -- aggregation with group-by-category
- `compute_summary_for_game()` (line 514) -- stats recomputation
- `validate_invite_code()` (line 611) -- invite code consumption
- `annotate_mistake()` (line 286) -- ownership validation path

---

## Tier 3: Edge Cases & Error Paths

### T-07: Parse error handling

- Malformed Mortal JSON (missing fields, wrong types)
- Mismatched kyoku/start_event counts (triggers sys.exit -- see BUGS.md B-01)
- actual_index out of bounds
- Empty rounds or empty mistakes

### T-08: format_action() coverage

`mj_parse.py:27` -- formats all action types (dahai, chi, pon, reach, hora, none, ankan) but zero tests exist.

### T-09: Dora/yakuhai label computation

`mj_categorize.py:481-514` -- `compute_labels()` detects dora, yakuhai (seat/round wind), dragons, terminals. Complex wind-matching logic untested.

---

## Infrastructure Gaps

### T-10: No test configuration

Missing:
- `conftest.py` -- shared fixtures should be extracted from test_core.py
- `pytest.ini` or `pyproject.toml [tool.pytest]` -- no pytest configuration
- Coverage reporting -- no `pytest-cov` integration
- CI doesn't report coverage or enforce thresholds

### T-11: No integration or E2E tests

The test suite only has unit tests. Missing:
- Full workflow test: upload JSON -> parse -> categorize -> retrieve -> practice
- Docker build verification in CI
- API contract tests (request/response shapes)

### T-12: No test fixtures for failure modes

Current fixtures only provide valid data. Missing:
- Malformed JSON fixture
- Network error simulation (nanikiru down)
- Edge case game states (zero mistakes, 100+ mistakes, all severities)
