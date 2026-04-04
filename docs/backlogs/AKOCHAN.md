# Akochan Integration: In-House Game Analysis

**Date**: 2026-04-05
**Source**: The Mortal dependency is the #1 adoption killer. Users must do a 5-step copy-paste dance through mjai.ekyu.moe (Cloudflare-protected) before they see any value.

## Goal

Replace the Mortal dependency with Akochan (open-source mahjong AI) running on our server. Users paste a game log URL and get analysis in under a minute. No external services, no Cloudflare, no JSON files.

**Dream pipeline**: Paste Tenhou URL -> server fetches log -> Akochan analyzes -> mahjong-cpp categorizes -> results displayed. One step instead of seven.

**Trade-off**: Akochan is weaker than Mortal (roughly Tokujou-level vs Mortal's Houou-level). For club-level play this is more than sufficient. Advanced users can still upload Mortal JSON manually for higher-quality analysis.

---

## Critical

### AK-01: Research Akochan feasibility

Before building anything, verify:
- Can akochan-reviewer run on the Hetzner CX22 (2 vCPU, 4GB RAM)?
- What's the analysis time per hanchan? (Mortal takes ~30s externally)
- What's the output format? Does it map to our mistake structure (EV loss, hand state, actions)?
- Are pretrained weights freely available and redistributable?
- Build dependencies? Does it compile in the Docker multi-stage build?
- License compatibility with our GPLv3 codebase?

**Resources**:
- akochan: https://github.com/critter-mj/akochan
- akochan-reviewer: https://github.com/Equim-chan/akochan-reviewer
- Pretrained weights (ai.zip) from akochan releases

**Output**: Decision doc — go/no-go, with fallback options if Akochan doesn't fit.

---

## High

### AK-02: Fetch Tenhou game logs by URL

**Location**: `app.py`, new `log_fetcher.py`

Add endpoint `POST /api/games/import-url` that accepts a Tenhou game URL (e.g., `https://tenhou.net/0/?log=...`).
- Parse the log ID from the URL
- Fetch the raw game log from Tenhou's log server
- Tenhou logs are publicly accessible (no Cloudflare) via `https://tenhou.net/0/log/?...`
- Store the raw log for replay

**Note**: MJS (Mahjong Soul) logs are harder — they use protobuf and require authentication. Start with Tenhou only.

### AK-03: Akochan analysis runner

**Location**: new `akochan_runner.py`, `Dockerfile`

Build Akochan in the Docker image and create a Python wrapper:
- Accept a Tenhou log + player seat as input
- Run akochan-reviewer as a subprocess (or integrate via shared library if feasible)
- Parse the output into our mistake format: turn, hand, melds, actual action, expected action, EV loss
- Handle timeouts and errors gracefully

### AK-04: Adapt mj_parse.py for Akochan output

**Location**: `mj_parse.py`

Currently `parse_game()` expects Mortal JSON. Add a parallel parser for Akochan output:
- Same output shape (game dict with rounds, mistakes, severity, etc.)
- Map Akochan's tile notation to our mjai format
- Compute severity from EV loss (same thresholds as Mortal)

Keep the Mortal parser — users can still upload Mortal JSON if they want.

### AK-05: Unified import endpoint

**Location**: `app.py`

Modify or add an endpoint that:
1. Accepts a Tenhou URL (triggers AK-02 -> AK-03 -> AK-04)
2. OR accepts a Mortal JSON file (existing flow)
3. Returns the same game structure either way
4. Show progress to the user (analysis may take 30-60s)

---

## Medium

### AK-06: Background analysis with status polling

**Location**: `app.py`, `db.py`, `static/app.js`

Akochan analysis takes time. Instead of blocking the HTTP request:
- Start analysis as a background task
- Return a job ID immediately
- Frontend polls `GET /api/jobs/<id>` for status
- When done, redirect to the game review view

### AK-07: MJS (Mahjong Soul) log support

**Location**: `log_fetcher.py`

MJS uses protobuf-encoded logs behind authentication. Options:
- User pastes the MJS game ID, we fetch via unofficial API (fragile)
- User installs a browser extension that captures the log (complex)
- User copy-pastes raw log data from browser devtools (still friction but less than Mortal)

Defer until Tenhou import is working and validated.

### AK-08: Update landing page and onboarding

**Location**: `static/landing.html`, `static/app.js`

Once URL import works:
- Landing page CTA: "Paste your Tenhou game link to get started"
- Onboarding: single text input for URL instead of file upload instructions
- Keep "Upload Mortal JSON" as an advanced option

---

## Low / Future

### AK-09: Hybrid analysis (Akochan + Mortal)

If a user has both: use Mortal for the primary analysis (better AI) and Akochan as instant fallback. Show which AI was used per game.

### AK-10: Batch import

Accept multiple game URLs at once. Analyze in background, notify when all are done. Useful for importing a player's recent game history.
