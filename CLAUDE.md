# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Personal Riichi Mahjong game analysis workspace. Contains game review logs from Tenhou replays analyzed with the Mortal AI, learning notes, and a summary calculator script.

## Key Files

- `games.json` - Canonical game data store (JSON). Contains all game reviews with structured mistake data.
- `mj_games.py` - Main CLI tool: list, review, annotate, summary, add games.
- `mj_parse.py` - Parses Mortal AI JSON analysis into structured game data (JSON default) or legacy text format.
- `mj_migrate.py` - One-shot migration script from Mahjong Mistakes.txt to games.json.
- `Mahjong Mistakes.txt` - Legacy game review log (read-only archive, superseded by games.json).
- `Richii Mahjong Learning.txt` - Strategy notes: defense heuristics, tile efficiency rules, when to open/fold.
- `mj_calc.sh` - Legacy summary calculator for .txt format (superseded by mj_games.py summary).
- `mahjong-cpp/` - Git submodule ([goreil/mahjong-cpp](https://github.com/goreil/mahjong-cpp)), a C++ mahjong library.

## Commands

```bash
# Main workflow
python3 mj_games.py add '<mjai-viewer-url>'           # Fetch + parse + store game
python3 mj_games.py add '<url>' --date 2026-03-25     # Override date
python3 mj_games.py list                               # List all games with stats
python3 mj_games.py review --game 3                    # Pretty-print mistakes (with hand/discard data)
python3 mj_games.py annotate 3 E1 1 -c 1D -n "note"   # Set category/note on a mistake
python3 mj_games.py summary                            # Recompute and display all summaries

# Lower-level
python3 mj_parse.py analysis.json                      # Parse Mortal JSON → structured JSON to stdout
python3 mj_parse.py analysis.json --text               # Parse → legacy text format with auto discard notes
```

## Data Format

Games in `games.json` have rounds, each with mistakes containing:
- `turn`, `severity` (?/??/???), `ev_loss`, `category`, `note`
- Rich data (from Mortal JSON): `hand`, `melds`, `shanten`, `draw`, `actual`/`expected` actions, `top_actions`

Categories: 1A-1E (efficiency/dora/honors/pairs), 2A-2C (defense), 3A-3C (melding), 4A-4B (riichi), 5A-5B (kan).
