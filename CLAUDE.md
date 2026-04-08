# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Riichi Mahjong game analysis web app ("Haipai"). Analyzes Tenhou/MJS replays via Mortal AI, auto-categorizes mistakes using mahjong-cpp, and provides a web UI for review, annotation, practice, and trend tracking. Multi-user with invite-code registration.

## Key Files

- `app.py` - Flask web server (port 5000). App setup, auth, static routes, blueprint registration.
- `db.py` - SQLite database layer. Games, mistakes, users, practice results, feedback.
- `routes/` - Flask blueprints:
  - `routes/games.py` - Game CRUD: list, get, delete, add, annotate, categorize, backfill, background categorization.
  - `routes/practice.py` - Practice mode: get problem, public problem, record result, stats.
  - `routes/admin.py` - Admin + feedback: admin stats, feedback CRUD, GitHub issue creation, user feedback.
- `lib/` - Core logic modules:
  - `lib/categorize.py` - Auto-categorization engine. Compares Mortal AI vs mahjong-cpp. Wall reconstruction, defense-aware 2A/2B split, safety rating computation.
  - `lib/defense.py` - Suji-based tile safety evaluator (ported from Riichi-Trainer). Rates tiles 0-15.
  - `lib/parse.py` - Core parser. `parse_game(data, date)` returns structured game dict from Mortal JSON.
  - `lib/games.py` - CLI tool for games.json (legacy format, still functional for local use).
  - `lib/mahjong_cpp.py` - HTTP client for nanikiru tile efficiency server.
- `scripts/` - Ops scripts: `backup.sh`, `check-cert.sh`, `entrypoint.sh`, `migrate_categories.sh`.
- `static/` - Web frontend: `index.html`, `landing.html`, `style.css`, `app.js` (vanilla JS SPA).
- `tests/test_core.py` - pytest suite (26 tests): parsing, tile conversion, board state, DB, API, wall reconstruction.
- `Dockerfile` - Multi-stage build (nanikiru + Python runtime). Non-root user.
- `docker-compose.yml` - App + nanikiru + nginx + certbot. Bind mounts for hot reload.
- `nginx.conf.template` - Nginx config template with security headers. Copy to nginx.conf on server.
- `docs/DEPLOY.md` - Full deployment guide with auto-deploy setup.
- `docs/PROMPTS.md` - Instance prompts for parallel Claude sessions.
- `docs/ROADMAP.md` - Product roadmap: beta, post-beta, monetization, growth.
- `docs/backlogs/` - Backlog docs for each parallel instance.
- `riichi-mahjong-tiles/` - Git submodule with SVG tile graphics.
- `mahjong-cpp/` - Git submodule, C++ mahjong library for tile efficiency.
- `Riichi-Trainer/` - Git submodule. Source of defense analysis logic.
- `notes/` - Personal scratch files (gitignored).

## Commands

```bash
# Web UI (dev server)
FLASK_ENV=development python3 app.py       # http://localhost:5000

# Tests
python3 -m pytest tests/ -v

# Docker (production)
docker-compose up -d --build               # Full build + start
docker-compose restart app                  # Restart after code changes
docker-compose logs -f app                  # View logs

# CLI (legacy, works with games.json)
python3 -m lib.games list
python3 -m lib.games review --game 3
python3 -m lib.games categorize --recheck --dry-run

# Lower-level
python3 -m lib.parse analysis.json          # Parse Mortal JSON to stdout
```

## Web UI

Flask app (`app.py`) serving a vanilla JS SPA. Features:
- Game list sidebar with star ratings, EV/Decision stats
- Review view: SVG tiles, severity colors, dora highlighting, tile hover highlight
- Board context: dora indicators, collapsible discard pools, opponent melds, scores
- Defense visuals: safety-colored tile borders, Safety column in EV table, "RIICHI" badge
- Inline annotation: category dropdown with tooltips, note input, auto-saves
- Practice mode: discard quizzes from own mistakes, spaced repetition, filters, dora highlighting
- Trend analysis: EV/decision chart, severity breakdown, skill area progression
- New user onboarding: step-by-step guide when no games exist
- Help page, feedback form, add game modal

API routes:
- `GET /api/games`, `GET /api/games/<id>`, `GET /api/trends`
- `GET /api/practice`, `GET /api/practice/public`, `POST /api/practice/result`, `GET /api/practice/stats`
- `POST /api/games/<id>/annotate`, `POST /api/games/<id>/categorize`
- `POST /api/games/add`, `DELETE /api/games/<id>`
- `POST /api/me/practice-opt-in`, `GET /api/categories`, `GET /api/me`
- `POST /api/feedback`, `GET /api/feedback/mine`
- `GET /api/admin/feedback`, `POST /api/admin/feedback/<id>`, `POST /api/admin/feedback/<id>/create-issue`
- `POST /api/games/backfill-board-state`, `POST /api/games/backfill-decisions`

## Data Format

SQLite database (`games.db`) with tables: users, games, mistakes, invite_codes, practice_results, feedback.

Mistakes have: `turn`, `severity` (?/??/???), `ev_loss`, `category`, `note`, plus `data_json` with:
- `hand`, `melds`, `shanten`, `draw`, `actual`/`expected` actions, `top_actions`
- `safety_ratings`: dict of mjai tile -> safety rating (0-15), when opponent in riichi
- `cpp_best`, `cpp_stats`: mahjong-cpp tile efficiency analysis
- `board_state`: dora indicators, winds, scores, all discard pools, opponent melds
- `opponent_discards`: opponent discard pools for defense context

Categories: 1A (efficiency), 2A (value tiles), 3A-3C (strategy), 4A-4C (meld), 5A-5B (riichi), 6A-6B (kan).

## Auto-Categorization Logic

When adding a game (CLI or web), mistakes are automatically categorized:

1. **Non-discard actions** categorized by type: 4A-4C (meld), 5A-5B (riichi), 6A-6B (kan).
2. **Discard vs discard**: queries mahjong-cpp API for tile efficiency, then:
   - **cpp == mortal** or **cpp ~= mortal** (within 90% score): efficiency -> **1A** or **2A** (value tile)
   - **cpp != mortal** + opponent in riichi + mortal chose safer tile (3+ gap): **3B** (Defense)
   - **cpp != mortal** otherwise: **3A** (Push/Fold)
   - **Hand already winning**: defaults to **3A**

Thresholds in `RULES` dict at top of `lib/categorize.py`. Iterate with `--recheck --dry-run`.

## Tile Notation

Mortal/mjai: `1m`-`9m`, `1p`-`9p`, `1s`-`9s`, `5mr`/`5pr`/`5sr` (red fives), `E`/`S`/`W`/`N`, `P`/`F`/`C`.
mahjong-cpp/MPSZ: `1z`-`7z` for honors, `0m`/`0p`/`0s` for red fives.
SVG files: `Man1.svg`-`Man9.svg`, `Pin1.svg`-`Pin9.svg`, `Sou1.svg`-`Sou9.svg`, `Man5-Dora.svg`, `Ton.svg`, etc.

## Important Notes

- Downloads from mjai.ekyu.moe must use the `requests` library — Cloudflare blocks bare urllib.
- `mahjong-cpp` uses MPSZ notation — conversion needed (see `MJAI_TO_ID` in `lib/categorize.py`).
- `mahjong-cpp` runs as a separate Docker service (`nanikiru`) on port 50000. `lib/mahjong_cpp.py` is the HTTP client with retry logic.
- `SECRET_KEY` must be set via `.env` file or environment variable (no insecure defaults).
- Debug mode requires `FLASK_ENV=development` (off by default).

## Local vs Production Differences

Local dev (WSL) and production (Docker on Hetzner) differ in important ways:

- **mahjong-cpp**: Runs as a separate Docker service (`nanikiru`) on port 50000. Python calls it via HTTP (`lib/mahjong_cpp.py`). For local dev without Docker, build the nanikiru binary: `cd mahjong-cpp && mkdir build && cd build && cmake .. -DBUILD_SERVER=ON && make nanikiru`, then run `./nanikiru 50000` and set `NANIKIRU_URL=http://localhost:50000/`.
- **File permissions**: Docker runs gunicorn as `appuser` (uid 1000). Files created by `docker compose exec` run as root. Any new file the app writes at runtime (caches, DBs) must go in a directory writable by `appuser` — use the `data/` volume, not `/app/`.
- **File paths**: Production copies `app.py`, `db.py`, `lib/`, `routes/` into `/app/`. Bind mounts in docker-compose.yml overlay these for hot reload. New Python files under `lib/` or `routes/` are picked up automatically.
- **gunicorn workers**: Production runs 2 workers. Module-level state is per-worker.

## Backlog Documents

Issues and improvements are tracked in dedicated backlog docs. When working on a task, check the relevant doc for known issues and mark items as done when fixed.

| Document | Scope | Primary files |
|----------|-------|---------------|
| `docs/backlogs/AUTH.md` | OAuth login (Discord, Google) | `app.py`, `db.py`, `requirements.txt` |
| `docs/backlogs/AKOCHAN.md` | In-house AI analysis (replace Mortal dependency) | `lib/parse.py`, `app.py`, `Dockerfile` |
| `docs/backlogs/TESTING.md` | Test coverage gaps | `tests/` |
| `docs/backlogs/UX-FEEDBACK.md` | Guest upload, Google OAuth | `routes/games.py`, `static/app.js`, `app.py` |

Completed backlogs (archived via git history): BUGS.md, INFRA.md, UX-AUDIT.md, ANON-PRACTICE.md, FEEDBACK-PIPELINE.md, LANDING-PAGE.md, PIPELINE.md, PENTEST.md.

## Roadmap

See `docs/ROADMAP.md` for the full product roadmap: beta launch, post-beta features, monetization plan, and growth strategy.
