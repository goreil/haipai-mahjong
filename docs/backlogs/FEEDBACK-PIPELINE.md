# Feedback Pipeline

Build an admin dashboard and GitHub integration so beta feedback is visible and actionable.

---

## F-01: Admin dashboard page (HIGH) ✅

**Current state**: Feedback goes to `feedback` table in SQLite (user_id, type, message, created_at). No way to view it without SSH + SQL query.

**Build**:
- New route: `GET /admin` — renders a feedback list page (server-side or SPA view)
- Gate with admin check (add `is_admin` column to users table, or hardcode your user ID for now)
- Show: timestamp, username, type badge (bug/feature/general), message, status (new/resolved)
- Add `status` column to feedback table (default: 'new')
- Filter by type, status. Sort by newest first.
- "Mark resolved" button per item.

**Files**: `app.py` (new route), `db.py` (schema migration, query), `static/app.js` (admin view).

---

## F-02: GitHub issue creation (HIGH) ✅

**Build**:
- "Create Issue" button on each feedback item in admin dashboard
- Calls `POST /api/admin/feedback/<id>/create-issue`
- Server-side: uses GitHub API (personal access token in .env) to create an issue
  - Title: `[feedback] {type}: {first 60 chars of message}`
  - Body: full message, username, timestamp, link back to feedback item
  - Labels: `feedback`, `bug`/`feature`/`ux` based on type
- Store the GitHub issue URL on the feedback row (new column: `github_issue_url`)
- Show issue link in admin dashboard once created

**Auth**: GitHub personal access token stored in `.env` as `GITHUB_TOKEN`. Add to `.env.example`.

**Files**: `app.py` (new API route), `db.py` (schema migration).

---

## F-03: Feedback status tracking (MEDIUM) ✅

**Build**:
- Add columns to feedback table: `status` (new/in-progress/resolved), `github_issue_url`, `admin_note`
- Admin can add an internal note to feedback items
- Status auto-updates to "in-progress" when GitHub issue is created
- Schema migration: add columns with ALTER TABLE, default status='new'

**Files**: `db.py` (schema).

---

## F-04: Feedback notification (MEDIUM) ✅

**Build**:
- When new feedback is submitted, notify the admin somehow:
  - Option A: Discord webhook (post to a private channel). Simplest — one HTTP POST.
  - Option B: Email via SMTP (more setup, less useful if you're already on Discord)
  - Option C: Just check the admin dashboard daily (no code needed, but easy to forget)
- Recommendation: Discord webhook. Store `DISCORD_WEBHOOK_URL` in `.env`.

**Files**: `app.py` (add to api_feedback route).

---

## F-05: Auto-triage with Claude (STRETCH)

This is the "premium feedback" vision. A scheduled Claude agent:
1. Reads new feedback from the DB (via API or direct DB query)
2. Classifies severity and affected area (UX, bug, feature request, unclear)
3. Creates a GitHub issue with labels and suggested priority
4. Optionally drafts a response to the user ("Thanks for reporting, we've logged this as...")

**Implementation**: Claude Code scheduled agent (see `/schedule` skill) running nightly. Needs:
- API endpoint: `GET /api/admin/feedback?status=new` (returns unprocessed feedback)
- Agent prompt that understands the app's architecture and can triage effectively
- Write access to GitHub API for issue creation

**Note**: This is the foundation for "premium users get auto-implementation." Start with auto-triage, then evolve to auto-PR for simple requests (typo fixes, label changes, etc.).

---

## F-06: User-facing feedback status (LOW) ✅

Let users see that their feedback was received and is being acted on:
- `GET /api/feedback/mine` — returns user's own feedback with status
- Show in a "My Feedback" section: submitted date, type, status badge
- If resolved, show admin's note (optional)

This closes the feedback loop — users see their report → in progress → resolved.
