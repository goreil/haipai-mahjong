# Auth Overhaul: OAuth + Open Registration

**Date**: 2026-04-05
**Source**: Club members not signing up — invite codes are confusing, creating yet another password is friction.

## Goal

Make registration as frictionless as possible. Discord OAuth (club members are already on Discord) + optional open registration. Keep invite codes as an optional tracking mechanism, not a gate.

---

## High

### A-01: Add Discord OAuth login

**Location**: `app.py`, `db.py`, `requirements.txt`

Add "Log in with Discord" button. Use Discord OAuth2 flow:
- Register app at discord.com/developers
- Add `flask-dance` or `authlib` to requirements
- New routes: `GET /auth/discord`, `GET /auth/discord/callback`
- On first login: auto-create user from Discord profile (username, avatar)
- On subsequent logins: match by Discord ID
- Store `discord_id` on users table

**Environment**: `DISCORD_CLIENT_ID` and `DISCORD_CLIENT_SECRET` in `.env`

### A-02: Add Google OAuth login

**Location**: `app.py`, `db.py`

Same pattern as A-01 but with Google. Lower priority than Discord since club is on Discord, but Google is the most universal OAuth provider.

- Routes: `GET /auth/google`, `GET /auth/google/callback`
- Store `google_id` on users table
- Match by email on subsequent logins

### A-03: Make invite codes optional

**Location**: `app.py`, `db.py`

Currently registration requires an invite code. Change to:
- OAuth login: no invite code needed (auto-register)
- Username/password registration: invite code optional
- If invite code provided: track it (for analytics), but don't require it
- Add a config flag `REQUIRE_INVITE_CODE=false` in `.env` to toggle

---

## Medium

### A-04: Update login/register UI

**Location**: `static/landing.html`, `static/style.css`

- Add OAuth buttons ("Log in with Discord", "Log in with Google") prominently
- Move username/password form below OAuth buttons
- Remove invite code field from the main flow (or make it a collapsible "Have an invite code?" section)

### A-05: Link existing accounts to OAuth

**Location**: `app.py`, `db.py`

If a user registered with username/password and later logs in with Discord/Google using the same email: offer to link accounts rather than creating a duplicate.

---

## Low

### A-06: Session persistence

**Location**: `app.py`

Current Flask-Login sessions expire quickly. Add "Remember me" checkbox with longer session duration (30 days). OAuth users should stay logged in by default.
