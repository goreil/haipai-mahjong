# Anonymous Practice Tool

**Date**: 2026-04-04
**Source**: Club member feedback — some people just want the practice drills without creating an account.

## Goal

Let anyone use the practice tool without logging in. Users opt-in to share their games in a community practice pool. Community pool is the default; authenticated users can filter to their own mistakes. Login is only required to track personal progress.

Future: if demand grows, add a lightweight anonymous progress tracker (cookie/localStorage) before requiring full login.

---

## High — DONE

### ~~AP-01: Anonymized practice problem pool in db.py~~ DONE

Added `get_public_practice_problem()` in `db.py`. Queries mistakes from opted-in users only (`practice_opt_in=1`), strips notes/dates, uniform random selection.

### ~~AP-02: Public practice API route in app.py~~ DONE

Added `GET /api/practice/public` — no `@login_required`. Same query params and JSON shape as `/api/practice`.

### ~~AP-03: Update CLAUDE.md API routes list~~ DONE

Added `/api/practice/public` and `/api/me/practice-opt-in` to API routes in CLAUDE.md.

---

## Medium — DONE

### ~~AP-04: Frontend anonymous practice mode~~ DONE

- Anonymous users at `/practice` get community pool problems
- Sidebar hides authenticated-only UI (Add Game, Trends, Help, Feedback)
- Login/register banner shown
- No result recording for anonymous users

### ~~AP-05: Landing page integration~~ DONE

"Try Practice Mode" is the primary CTA on the landing page. Description updated to mention community pool.

### ~~AP-07: Practice opt-in system~~ DONE

- `practice_opt_in` column on users table (default 0, with migration)
- `POST /api/me/practice-opt-in` to toggle
- `/api/me` returns `practice_opt_in` status
- Checkbox in practice view: "Share my games in community pool"
- Public pool only includes games from opted-in users

### ~~AP-08: Own vs community toggle~~ DONE

- Community pool is the default for all users
- "My mistakes only" checkbox to filter to own games (authenticated only)
- Own-mistakes mode uses spaced-repetition endpoint and records results
- Community mode uses public endpoint, no result recording

### ~~AP-09: Remove import games.json~~ DONE

Removed deprecated import functionality: button from index.html, `/api/games/import` route from app.py, `importGamesJson()` from app.js.

### ~~AP-10: Categorization progress bar~~ DONE

- `/api/games/add` streams SSE events with categorization progress
- `categorize_game_db` accepts `on_progress(done, total)` callback
- Frontend shows animated progress bar: "Analyzing decisions... 3/12"
- Replaces the old static "Adding..." spinner in the add game modal

---

## Low / Future

### AP-06: Anonymous progress tracking (cookie-based)

If there's demand, add localStorage-based progress tracking for anonymous users:
- Store attempted/correct counts per category in localStorage
- Show a simplified stats view
- On login, offer to merge anonymous progress into the user's account

Don't build this until we see anonymous practice actually getting used.
