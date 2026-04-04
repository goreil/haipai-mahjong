# Anonymous Practice Tool

**Date**: 2026-04-04
**Source**: Club member feedback — some people just want the practice drills without creating an account.

## Goal

Let anyone use the practice tool without logging in. Pool all uploaded games' mistakes into an anonymized practice set. Login is only required to track personal progress.

Future: if demand grows, add a lightweight anonymous progress tracker (cookie/localStorage) before requiring full login.

---

## High

### AP-01: Anonymized practice problem pool in db.py

**Location**: `db.py` (new function)

Add `get_public_practice_problem(conn, severity=None, group=None, defense_only=False)` that:
- Queries mistakes across ALL users' games (not filtered by user_id)
- Strips any user-identifying info (username, game date, notes, annotations) from the returned data
- Returns the same shape as `get_practice_problem()` but without user-specific spaced repetition weighting (just uniform random or severity-weighted)
- Only includes dahai-vs-dahai mistakes with a hand (same filters as existing practice)
- Only includes mistakes from games with `severity IN ('??', '???')` (meaningful mistakes)

### AP-02: Public practice API route in app.py

**Location**: `app.py` (new route)

Add `GET /api/practice/public` — no `@login_required`. Accepts same query params as `/api/practice` (severity, group, defense). Calls `get_public_practice_problem()`. Returns the same JSON shape as the authenticated endpoint so the frontend can reuse rendering logic.

Do NOT add a public result-recording endpoint — anonymous users can't save progress.

### AP-03: Update CLAUDE.md API routes list

Add the new `/api/practice/public` route to the API routes section in CLAUDE.md.

---

## Medium

### AP-04: Frontend anonymous practice mode

**Location**: `static/app.js`, `static/style.css`

Modify the practice view to work without authentication:
- If user is not logged in, call `/api/practice/public` instead of `/api/practice`
- Hide the stats/progress section for anonymous users
- Hide the "Record result" button (or show it but prompt to log in)
- Show a subtle "Log in to track your progress" banner
- Practice filters (severity, group, defense) should still work

### AP-05: Landing page integration

**Location**: `static/landing.html`, `app.py`

Add a "Try Practice Mode" CTA button on the landing page that links directly to the anonymous practice view. This gives visitors immediate value before they decide to register.

---

## Low / Future

### AP-06: Anonymous progress tracking (cookie-based)

If there's demand, add localStorage-based progress tracking for anonymous users:
- Store attempted/correct counts per category in localStorage
- Show a simplified stats view
- On login, offer to merge anonymous progress into the user's account

Don't build this until we see anonymous practice actually getting used.
