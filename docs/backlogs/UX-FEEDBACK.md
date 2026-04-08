# UX Feedback

**Source**: Direct user feedback

Completed: UX-01 (tutorial), UX-02 (simplified UI), UX-03 (back button), UX-04 (practice on frontpage), UX-05 (remove invite codes), UX-08 (opt-in popup), UX-09 (hide original play).

---

## UX-06: Google OAuth login (HIGH)

See `AUTH.md` A-02. Confirms user priority for Google OAuth.

**Files**: `app.py`, `db.py`, `requirements.txt`

---

## UX-07: Unregistered game upload — preview mode (MEDIUM)

Allow unregistered users to upload a mortal.json and see the analysis for one game without storing in DB. Ephemeral/temporary view — "try before you sign up."

**Files**: `app.py`, `routes/games.py`, `static/app.js`, `static/landing.html`
