# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Riichi Mahjong game analysis web app ("Haipai"). Analyzes Tenhou/MJS replays via Mortal AI, auto-categorizes mistakes using mahjong-cpp, and provides a web UI for review, annotation, practice, and trend tracking. Multi-user with invite-code registration.

## Key Files

- `app.py` - Flask web server (port 5000). Multi-user auth, API routes, auto-starts nanikiru.
- `db.py` - SQLite database layer. Games, mistakes, users, practice results, feedback.
- `mj_categorize.py` - Auto-categorization engine. Compares Mortal AI vs mahjong-cpp. Wall reconstruction, defense-aware 2A/2B split, safety rating computation.
- `mj_defense.py` - Suji-based tile safety evaluator (ported from Riichi-Trainer). Rates tiles 0-15.
- `mj_parse.py` - Core parser. `parse_game(data, date)` returns structured game dict from Mortal JSON.
- `mj_games.py` - CLI tool for games.json (legacy format, still functional for local use).
- `static/` - Web frontend: `index.html`, `style.css`, `app.js` (vanilla JS SPA).
- `tests/test_core.py` - pytest suite (26 tests): parsing, tile conversion, board state, DB, API, wall reconstruction.
- `Dockerfile` - Multi-stage build (nanikiru binary + Python runtime). Non-root user.
- `docker-compose.yml` - App + nginx + certbot. Bind mounts for hot reload.
- `nginx.conf.template` - Nginx config template with security headers. Copy to nginx.conf on server.
- `docs/DEPLOY.md` - Full deployment guide with auto-deploy setup.
- `docs/PROMPTS.md` - Instance prompts for parallel Claude sessions.
- `docs/ROADMAP.md` - Product roadmap: beta, post-beta, monetization, growth.
- `docs/backlogs/` - Backlog docs for each parallel instance (BUGS.md, UX-AUDIT.md, etc.).
- `riichi-mahjong-tiles/` - Git submodule with SVG tile graphics.
- `mahjong-cpp/` - Git submodule, C++ mahjong library for tile efficiency.
- `Riichi-Trainer/` - Git submodule. Source of defense analysis logic.
- `archive/` - Legacy/one-shot scripts (migration tools, deployment notes, brainstorming).
- `notes/` - Personal scratch files (gitignored).

## Commands

```bash
# Web UI (dev server, auto-starts nanikiru)
FLASK_ENV=development python3 app.py       # http://localhost:5000

# Tests
python3 -m pytest tests/ -v

# Docker (production)
docker-compose up -d --build               # Full build + start
docker-compose restart app                  # Restart after code changes
docker-compose logs -f app                  # View logs

# CLI (legacy, works with games.json)
python3 mj_games.py list
python3 mj_games.py review --game 3
python3 mj_games.py categorize --recheck --dry-run

# Lower-level
python3 mj_parse.py analysis.json          # Parse Mortal JSON to stdout
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
- `GET /api/practice`, `POST /api/practice/result`, `GET /api/practice/stats`
- `POST /api/games/<id>/annotate`, `POST /api/games/<id>/categorize`
- `POST /api/games/add`, `DELETE /api/games/<id>`
- `POST /api/games/import`, `GET /api/categories`, `GET /api/me`
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

Thresholds in `RULES` dict at top of `mj_categorize.py`. Iterate with `--recheck --dry-run`.

## Tile Notation

Mortal/mjai: `1m`-`9m`, `1p`-`9p`, `1s`-`9s`, `5mr`/`5pr`/`5sr` (red fives), `E`/`S`/`W`/`N`, `P`/`F`/`C`.
mahjong-cpp/MPSZ: `1z`-`7z` for honors, `0m`/`0p`/`0s` for red fives.
SVG files: `Man1.svg`-`Man9.svg`, `Pin1.svg`-`Pin9.svg`, `Sou1.svg`-`Sou9.svg`, `Man5-Dora.svg`, `Ton.svg`, etc.

## Important Notes

- Downloads from mjai.ekyu.moe must use the `requests` library — Cloudflare blocks bare urllib.
- `mahjong-cpp` uses MPSZ notation — conversion needed (see `MJAI_TO_ID` in mj_categorize.py).
- Nanikiru runs locally at 127.0.0.1:50000, auto-started by `app.py`.
- `SECRET_KEY` must be set via `.env` file or environment variable (no insecure defaults).
- Debug mode requires `FLASK_ENV=development` (off by default).

## Local vs Production Differences

Local dev (WSL) and production (Docker on Hetzner) differ in important ways:

- **Nanikiru**: Auto-started by `app.py` but often not running locally (no build, crashes in WSL). All categorization silently fails — API errors are caught and return `None` category. Code that touches categorization **must be tested on the server** or with a running nanikiru.
- **File permissions**: Docker runs gunicorn as `appuser` (uid 1000). Files created by `docker compose exec` run as root. Any new file the app writes at runtime (caches, DBs) must go in a directory writable by `appuser` — use the `data/` volume, not `/app/`.
- **File paths**: Production copies specific `.py` files into `/app/` (see `COPY` line in Dockerfile). New Python modules must be added to the Dockerfile `COPY` list or they won't exist in the container.
- **gunicorn workers**: Production runs 2 workers. Each starts its own nanikiru instance (only one wins the port). Module-level state is per-worker.

## Backlog Documents

Issues and improvements are tracked in dedicated backlog docs. When working on a task, check the relevant doc for known issues and mark items as done when fixed.

| Document | Scope | Primary files |
|----------|-------|---------------|
| `docs/backlogs/TESTING.md` | Test coverage gaps, missing test cases | `tests/` |
| `docs/backlogs/PENTEST.md` | Security findings and remediation | `app.py`, `nginx.conf` |
| `docs/backlogs/PIPELINE.md` | Replace nanikiru HTTP server with in-process calls | `mahjong-cpp/`, `mj_categorize.py`, `app.py`, `Dockerfile` |
| `docs/backlogs/ANON-PRACTICE.md` | Anonymous practice tool (no login required) | `app.py`, `db.py`, `static/app.js`, `static/landing.html` |
| `docs/backlogs/FEEDBACK-PIPELINE.md` | Feedback admin (1 stretch item remaining) | `app.py`, `db.py`, `static/app.js` |
| `docs/backlogs/LANDING-PAGE.md` | Landing page (1 stretch item remaining) | `static/landing.html`, `app.py`, `style.css` |

Completed backlogs (archived via git history): BUGS.md, INFRA.md, UX-AUDIT.md.

When running multiple Claude instances in parallel, avoid editing the same files concurrently. The table above shows which files each backlog primarily touches. See `docs/PROMPTS.md` for ready-to-use instance prompts.

## Roadmap

See `docs/ROADMAP.md` for the full product roadmap: beta launch, post-beta features, monetization plan, and growth strategy.
