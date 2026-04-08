# Auth: OAuth Login

**Goal**: Reduce registration friction with OAuth. Invite codes already removed.

---

## A-01: Discord OAuth login (HIGH)

**Files**: `app.py`, `db.py`, `requirements.txt`

- Register app at discord.com/developers
- Add `authlib` to requirements
- Routes: `GET /auth/discord`, `GET /auth/discord/callback`
- Auto-create user from Discord profile on first login
- Store `discord_id` on users table
- Env: `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`

## A-02: Google OAuth login (HIGH)

**Files**: `app.py`, `db.py`

Same pattern as A-01. Routes: `GET /auth/google`, `GET /auth/google/callback`. Store `google_id`, match by email.

## A-04: Update login/register UI (MEDIUM)

**Files**: `app.py` (LOGIN_PAGE template)

Add OAuth buttons prominently above the username/password form.

## A-05: Link existing accounts to OAuth (MEDIUM)

**Files**: `app.py`, `db.py`

If OAuth email matches existing user, offer to link rather than creating a duplicate.

## A-06: Session persistence (LOW)

**Files**: `app.py`

Add "Remember me" with 30-day sessions. OAuth users stay logged in by default.
