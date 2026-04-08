# Auth: OAuth Login

**Goal**: Reduce registration friction with OAuth. Invite codes already removed.

**Prerequisites** (manual, ~10-15 min):
- Discord: Register app at discord.com/developers (free), set callback URL, copy client ID/secret
- Google: Create project in Google Cloud Console (free), configure consent screen, set callback URL, copy client ID/secret
- Set env vars: `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

---

## A-01: Discord OAuth login (HIGH)

**Files**: `app.py`, `db.py`, `requirements.txt`

- Add `authlib` to requirements
- Routes: `GET /auth/discord`, `GET /auth/discord/callback`
- Auto-create user from Discord profile on first login
- Store `discord_id` on users table

## A-02: Google OAuth login (HIGH)

**Files**: `app.py`, `db.py`

Same pattern as A-01. Routes: `GET /auth/google`, `GET /auth/google/callback`. Store `google_id`.

## A-04: Update login/register UI (MEDIUM)

**Files**: `app.py` (LOGIN_PAGE template)

Add OAuth buttons prominently above the username/password form.

## A-05: Link existing accounts to OAuth (MEDIUM)

**Files**: `app.py`, `db.py`

Allow logged-in users to link their account to an OAuth provider from a settings page. No email matching (app doesn't collect emails).

## A-06: Session persistence (LOW)

**Files**: `app.py`

Add "Remember me" with 30-day sessions. OAuth users stay logged in by default.
