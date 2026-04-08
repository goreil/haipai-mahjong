# UX Feedback

**Date**: 2026-04-07
**Source**: Direct user feedback from goreil

---

## ~~UX-01: Practice mode tutorial for beginners~~ DONE

Practice mode needs more explanation for newcomers. Add an introductory tutorial or guided first-use experience that explains what the practice mode is, how problems are sourced, what the severity/category filters mean, and how scoring works.

**Files**: `static/app.js`

---

## ~~UX-02: Simplify UI for beginners, expandable for advanced~~ DONE

The current UX is overwhelming. Design a simpler default view for beginners (fewer controls, less jargon, clear next actions) with an option for advanced players to expand into the full view (filters, stats, category breakdowns, etc.).

**Files**: `static/app.js`, `static/style.css`

---

## ~~UX-03: Back button from practice mode to start page~~ DONE

There's no way to navigate back from practice mode to the main landing/start page. Add a back/home button.

**Files**: `static/app.js`

---

## ~~UX-04: Show practice mode directly on frontpage~~ DONE

The frontpage should display the practice mode immediately so nobody has to click through. Reduce friction — community practice should be the first thing a visitor sees, not a CTA button.

**Files**: `static/landing.html`, `app.py`

See also: `LANDING-PAGE.md` L-03 (demo mode) — this overlaps but is more specific: embed practice directly.

---

## ~~UX-05: Remove invite code requirement~~ DONE

Drop the invite code gate for registration entirely. It's confusing and blocks signups.

See also: `AUTH.md` A-03 (make invite codes optional). This feedback says go further — remove them, not just make them optional.

**Files**: `app.py`, `db.py`

---

## UX-06: Google OAuth login (HIGH)

Add Google OAuth as a login option. Most universal OAuth provider.

See also: `AUTH.md` A-02 (Google OAuth). Already specced there — this confirms user priority.

**Files**: `app.py`, `db.py`, `requirements.txt`

---

## UX-07: Unregistered game upload (preview mode) (MEDIUM)

Allow unregistered users to upload a mortal.json and see the analysis result for one game, without storing it in the DB. A "try before you sign up" experience. The game is parsed and displayed in a temporary/ephemeral view.

See also: `LANDING-PAGE.md` L-03 (demo mode) — this is a more concrete version: let them upload their own file, not just see a canned demo.

**Files**: `app.py`, `routes_games.py`, `static/app.js`, `static/landing.html`

---

## ~~UX-08: Practice opt-in popup on first use~~ DONE

Instead of a buried checkbox, show a popup/modal the first time a user enters their private practice mode asking if they want to share their games in the community pool. Explain the benefit clearly.

**Files**: `static/app.js`, `db.py` (track whether user has been prompted)

---

## ~~UX-09: Hide original play for community practice problems~~ DONE

In practice mode, when showing a community pool problem (not the user's own game), don't reveal what the original player actually chose. Showing their play confuses the practicing player — they only need to see the hand and decide what to discard. The "original play" reveal should only appear for the user's own mistakes (where seeing what they did wrong is the point).

**Files**: `static/app.js`, possibly `db.py` or `routes_practice.py` (strip `actual` from public problems server-side)
