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
- `DEPLOY.md` - Full deployment guide with auto-deploy setup.
- `riichi-mahjong-tiles/` - Git submodule with SVG tile graphics.
- `mahjong-cpp/` - Git submodule, C++ mahjong library for tile efficiency.
- `Riichi-Trainer/` - Git submodule. Source of defense analysis logic.
- `archive/` - Legacy/one-shot scripts (migration tools, deployment notes, brainstorming).
- `vision.txt` - Project roadmap with done/todo sections.

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
- `POST /api/feedback`
- `POST /api/games/backfill-board-state`, `POST /api/games/backfill-decisions`

## Data Format

SQLite database (`games.db`) with tables: users, games, mistakes, invite_codes, practice_results, feedback.

Mistakes have: `turn`, `severity` (?/??/???), `ev_loss`, `category`, `note`, plus `data_json` with:
- `hand`, `melds`, `shanten`, `draw`, `actual`/`expected` actions, `top_actions`
- `safety_ratings`: dict of mjai tile -> safety rating (0-15), when opponent in riichi
- `cpp_best`, `cpp_stats`: mahjong-cpp tile efficiency analysis
- `board_state`: dora indicators, winds, scores, all discard pools, opponent melds
- `opponent_discards`: opponent discard pools for defense context

Categories: 1A-1E (efficiency), 2A-2C (strategy), 3A-3C (melding), 4A-4B (riichi), 5A-5B (kan).

## Auto-Categorization Logic

When adding a game (CLI or web), mistakes are automatically categorized:

1. **Non-discard actions** categorized by type: 3A-3C (meld), 4A-4B (riichi), 5A-5B (kan).
2. **Discard vs discard**: queries mahjong-cpp API for tile efficiency, then:
   - **cpp == mortal** or **cpp ~= mortal** (within 90% score): efficiency -> 1A-1E
   - **cpp != mortal** + opponent in riichi + mortal chose safer tile (3+ gap): **2B** (Defense)
   - **cpp != mortal** otherwise: **2A** (Push/Fold)
   - **Hand already winning**: defaults to **2A**

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
