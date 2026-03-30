# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Personal Riichi Mahjong game analysis workspace. Analyzes Tenhou replays via Mortal AI, stores structured mistake data in JSON, and provides CLI + web UI for review and annotation.

## Key Files

- `games.json` - Canonical data store (JSON). All game reviews with structured mistake data.
- `mj_games.py` - Main CLI tool: `list`, `review`, `annotate`, `summary`, `add`, `categorize` subcommands.
- `mj_categorize.py` - Auto-categorization engine. Compares Mortal AI vs mahjong-cpp tile efficiency via pystyle.info API.
- `mj_parse.py` - Core parser. `parse_game(data, date)` returns structured game dict from Mortal JSON. Also has `--text` legacy mode.
- `app.py` - Flask web server (port 5000). Serves API + static frontend.
- `static/` - Web frontend: `index.html`, `style.css`, `app.js` (vanilla JS SPA).
- `riichi-mahjong-tiles/` - Git submodule with SVG tile graphics. Served at `/tiles/<Name>.svg`.
- `mahjong-cpp/` - Git submodule ([goreil/mahjong-cpp](https://github.com/goreil/mahjong-cpp)), a C++ mahjong library.
- `mj_migrate.py` - One-shot migration from Mahjong Mistakes.txt → games.json (already run).
- `mj_calc.sh` - Legacy summary calculator for .txt format (superseded).
- `Mahjong Mistakes.txt` - Legacy game review log (read-only archive).
- `Richii Mahjong Learning.txt` - Strategy notes: defense heuristics, tile efficiency rules.
- `vision.txt` - Project roadmap with done/todo sections.

## Commands

```bash
# Web UI
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
python3 mj_games.py categorize --dry-run                # Preview without saving

# Lower-level
python3 mj_parse.py analysis.json                       # Parse Mortal JSON → structured JSON to stdout
python3 mj_parse.py analysis.json --text                # Parse → legacy text format with auto discard notes
```

## Web UI

Flask app (`app.py`) serving a vanilla JS SPA. Features:
- Game list sidebar sorted by date (newest first)
- Review view with SVG tile graphics, severity-colored mistake cards
- Inline annotation (category dropdown + note input, auto-saves)
- Severity filter checkboxes (hide minor/medium)
- Add game modal (paste Mortal viewer URL)

API routes: `GET /api/games`, `GET /api/games/<id>`, `POST /api/games/<id>/annotate`, `POST /api/games/<id>/categorize`, `POST /api/games/add`.
Tiles served at `/tiles/<Name>.svg` from `riichi-mahjong-tiles/Regular/`.

## Data Format

Games in `games.json` have rounds, each with mistakes containing:
- `turn`, `severity` (?/??/???), `ev_loss`, `category`, `note`
- Rich data (from Mortal JSON): `hand`, `melds`, `shanten`, `draw`, `actual`/`expected` actions, `top_actions`

Categories: 1A-1E (efficiency/dora/honors/pairs), 2A-2C (defense), 3A-3C (melding), 4A-4B (riichi), 5A-5B (kan).

## Tile Notation

Mortal uses mjai notation: `1m`-`9m`, `1p`-`9p`, `1s`-`9s`, `5mr`/`5pr`/`5sr` (red fives), `E`/`S`/`W`/`N` (winds), `P`/`F`/`C` (dragons).
SVG files: `Man1.svg`-`Man9.svg`, `Pin1.svg`-`Pin9.svg`, `Sou1.svg`-`Sou9.svg`, `Man5-Dora.svg` (red five), `Ton.svg`/`Nan.svg`/`Shaa.svg`/`Pei.svg`, `Haku.svg`/`Hatsu.svg`/`Chun.svg`.

## Important Notes

- Downloads from mjai.ekyu.moe must use the `requests` library (not `urllib.request`) — Cloudflare blocks bare urllib User-Agent.
- `mahjong-cpp` uses MPSZ notation (`1z`-`7z` for honors, `0m`/`0p`/`0s` for red fives) — conversion needed for integration.
- `mahjong_curl` file has a working curl example hitting the pystyle.info hosted mahjong-cpp web API.
