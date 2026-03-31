# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Personal Riichi Mahjong game analysis workspace. Analyzes Tenhou replays via Mortal AI, stores structured mistake data in JSON, and provides CLI + web UI for review and annotation.

## Key Files

- `games.json` - Canonical data store (JSON). All game reviews with structured mistake data.
- `mj_games.py` - Main CLI tool: `list`, `review`, `annotate`, `summary`, `add`, `categorize` subcommands.
- `mj_categorize.py` - Auto-categorization engine. Compares Mortal AI vs local mahjong-cpp server. Includes "reasonable agreement" check, defense-aware 2A/2B split, and safety rating computation.
- `mj_defense.py` - Suji-based tile safety evaluator (ported from Riichi-Trainer). Rates tiles 0-15 against riichi opponents.
- `mj_parse.py` - Core parser. `parse_game(data, date)` returns structured game dict from Mortal JSON. Also has `--text` legacy mode.
- `app.py` - Flask web server (port 5000). Auto-starts nanikiru tile efficiency server. Serves API + static frontend.
- `static/` - Web frontend: `index.html`, `style.css`, `app.js` (vanilla JS SPA).
- `riichi-mahjong-tiles/` - Git submodule with SVG tile graphics. Served at `/tiles/<Name>.svg`.
- `mahjong-cpp/` - Git submodule ([goreil/mahjong-cpp](https://github.com/goreil/mahjong-cpp)), a C++ mahjong library.
- `Riichi-Trainer/` - Git submodule. React-based trainer with defense analysis (suji evaluator ported to `mj_defense.py`).
- `mj_migrate.py` - One-shot migration from Mahjong Mistakes.txt → games.json (already run).
- `mj_calc.sh` - Legacy summary calculator for .txt format (superseded).
- `Mahjong Mistakes.txt` - Legacy game review log (read-only archive).
- `Richii Mahjong Learning.txt` - Strategy notes: defense heuristics, tile efficiency rules.
- `vision.txt` - Project roadmap with done/todo sections.

## Commands

```bash
# Web UI (auto-starts nanikiru tile efficiency server)
python3 app.py                                         # Start web server at http://localhost:5000

# CLI workflow
python3 mj_games.py add '<mjai-viewer-url>'            # Fetch + parse + store game
python3 mj_games.py add '<url>' --date 2026-03-25      # Override date
python3 mj_games.py list                                # List all games with stats
python3 mj_games.py review --game 3                     # Pretty-print mistakes
python3 mj_games.py review --game 3 --hide-minor        # Hide ? severity
python3 mj_games.py review --game 3 --hide-medium       # Hide ?? severity
python3 mj_games.py annotate 3 E1 1 -c 1D -n "note"    # Set category/note on a mistake
python3 mj_games.py summary                             # Recompute and display all summaries
python3 mj_games.py categorize                          # Auto-categorize all uncategorized mistakes
python3 mj_games.py categorize --game 3                 # Categorize specific game
python3 mj_games.py categorize --recheck                # Re-run logic on stored data (no API, instant)
python3 mj_games.py categorize --force                  # Re-query API for all (slow)
python3 mj_games.py categorize --dry-run                # Preview without saving

# Lower-level
python3 mj_parse.py analysis.json                       # Parse Mortal JSON → structured JSON to stdout
python3 mj_parse.py analysis.json --text                # Parse → legacy text format with auto discard notes
```

## Web UI

Flask app (`app.py`) serving a vanilla JS SPA. Features:
- Game list sidebar sorted by date (newest first), star ratings for top games
- Review view with SVG tile graphics, severity-colored mistake cards
- Defense visuals: colored tile borders (safe/caution/danger), Safety column in EV table, "RIICHI" badge
- Inline annotation (category dropdown with tooltip descriptions + note input, auto-saves)
- Severity filter checkboxes (hide minor/medium)
- Practice mode: random discard quizzes from your mistakes, clickable tiles, filters by category/severity/defense, session scoring, keyboard shortcuts (Space/Enter for next)
- Trend analysis: EV/turn chart, severity breakdown, skill area progression
- Help page: category reference, defense scale explanation, attribution/licenses
- Add game modal (paste Mortal viewer URL)
- Clean round badges, positive game rating banners

API routes: `GET /api/games`, `GET /api/games/<id>`, `GET /api/trends`, `GET /api/practice`, `POST /api/games/<id>/annotate`, `POST /api/games/<id>/categorize`, `POST /api/games/add`, `DELETE /api/games/<id>`.
Tiles served at `/tiles/<Name>.svg` from `riichi-mahjong-tiles/Regular/`.

## Data Format

Games in `games.json` have rounds, each with mistakes containing:
- `turn`, `severity` (?/??/???), `ev_loss`, `category`, `note`
- Rich data (from Mortal JSON): `hand`, `melds`, `shanten`, `draw`, `actual`/`expected` actions, `top_actions`
- `safety_ratings` (optional): dict of mjai tile → safety rating (0-15), present when opponent in riichi
- `cpp_best`, `cpp_stats`: mahjong-cpp tile efficiency analysis

Categories: 1A-1E (efficiency/dora/honors/pairs), 2A-2C (strategy), 3A-3C (melding), 4A-4B (riichi), 5A-5B (kan).

Efficiency sub-categories: 1B (dora handling), 1C (honor ordering), 1D (honor vs number), 1E (pair management), 1A (general).

Defense analysis uses suji-based safety ratings (0-15 scale, ported from Riichi-Trainer): genbutsu=15, suji terminals=13-14, honors by remaining count, non-suji middle tiles=1-3.

## Auto-Categorization Logic

When adding a game (CLI or web), mistakes are automatically categorized:

1. **Non-discard actions** are categorized by type: 3A-3C (meld), 4A-4B (riichi), 5A-5B (kan).
2. **Discard vs discard**: queries mahjong-cpp API for pure tile efficiency analysis, then:
   - **cpp == mortal** (exact match): efficiency error → sub-categorize as 1A-1E
   - **cpp ~= mortal** ("reasonable agreement" — same shanten, mortal's tile within 90% of cpp's best expected score): still efficiency → 1A-1E
   - **cpp != mortal** (genuine disagreement): check defense context:
     - If opponent is in riichi and mortal chose a significantly safer tile (3+ safety rating difference) → **2B** (Defense)
     - Otherwise → **2A** (Push/Fold)

Efficiency sub-categories: 1B (dora handling), 1C (honor ordering), 1D (honor vs number), 1E (pair management), 1A (general).

Defense analysis uses suji-based safety ratings (0-15 scale, ported from Riichi-Trainer): genbutsu=15, suji terminals=13-14, honors by remaining count, non-suji middle tiles=1-3.

Use `--recheck` to re-run categorization logic on stored data without API calls (instant). Use `--force` to re-query the API (slow).

## Tile Notation

Mortal uses mjai notation: `1m`-`9m`, `1p`-`9p`, `1s`-`9s`, `5mr`/`5pr`/`5sr` (red fives), `E`/`S`/`W`/`N` (winds), `P`/`F`/`C` (dragons).
SVG files: `Man1.svg`-`Man9.svg`, `Pin1.svg`-`Pin9.svg`, `Sou1.svg`-`Sou9.svg`, `Man5-Dora.svg` (red five), `Ton.svg`/`Nan.svg`/`Shaa.svg`/`Pei.svg`, `Haku.svg`/`Hatsu.svg`/`Chun.svg`.

## Important Notes

- Downloads from mjai.ekyu.moe must use the `requests` library (not `urllib.request`) — Cloudflare blocks bare urllib User-Agent.
- `mahjong-cpp` uses MPSZ notation (`1z`-`7z` for honors, `0m`/`0p`/`0s` for red fives) — conversion needed for integration.
- Tile efficiency calculator runs locally via `mahjong-cpp/build/install/bin/nanikiru PORT [BIND_ADDR]` (default: 127.0.0.1:50000). Auto-started by `app.py`.
