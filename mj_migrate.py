#!/usr/bin/env python3
"""One-shot migration: Mahjong Mistakes.txt → games.json.

Parses the text format, backfills rich data from Mortal JSON where available,
and writes the canonical JSON data store.
"""

import json
import re
import sys
from pathlib import Path

from mj_parse import parse_game, severity

DIR = Path(__file__).parent
TXT_FILE = DIR / "Mahjong Mistakes.txt"
OUT_FILE = DIR / "games.json"

# Map game index (0-based) to Mortal JSON file for backfilling.
# Games 1 & 2 have no JSON. Game 3 matches 2c7268c4e0205cc0.json.
MORTAL_MAP = {
    2: "mortal_analysis/2c7268c4e0205cc0.json",
}

# Regex patterns
RE_SEPARATOR = re.compile(r"^={6,}$")
RE_DATE = re.compile(r"^Date:\s*(.*)$")
RE_LOG = re.compile(r"^Log:\s*(.*)$")
RE_ROUND = re.compile(r"^([ES]\d+(?:-\d+)?)(T\d+)?\s*(:[()|D])?$")
RE_MISTAKE_CAT = re.compile(r'^(\d+)\s+([!?]+)\s+(\d+[A-Z]+)\s+(\d+\.\d+)\s*(.*)$')
RE_MISTAKE_BARE = re.compile(r'^(\d+)\s+([!?]+)\s+(\d+\.\d+)\s*(.*)$')
RE_SUMMARY = re.compile(r"^(SUMMARY|TOTAL|TURNS):")


def parse_note(raw):
    """Extract note text from parenthetical or bare string."""
    raw = raw.strip()
    if not raw or raw == '"':
        return raw if raw == '"' else None
    # Strip surrounding parens
    if raw.startswith("(") and raw.endswith(")"):
        return raw[1:-1]
    return raw


def parse_text_games():
    """Parse Mahjong Mistakes.txt into a list of raw game dicts."""
    lines = TXT_FILE.read_text().splitlines()
    games = []
    current = None

    for line in lines:
        line = line.rstrip()

        if RE_SEPARATOR.match(line):
            if current and current.get("date"):
                games.append(current)
            current = None
            continue

        if current is None:
            m = RE_DATE.match(line)
            if m:
                current = {"date": m.group(1).strip(), "log_url": None, "rounds": []}
            continue

        m = RE_LOG.match(line)
        if m:
            url = m.group(1).strip()
            current["log_url"] = url if url else None
            continue

        if RE_SUMMARY.match(line):
            continue

        m = RE_ROUND.match(line)
        if m:
            outcome = m.group(3)  # e.g. ":D" or ":(" or None
            turn_str = m.group(2)  # e.g. "T13" or None
            turn_count = int(turn_str[1:]) if turn_str else None
            # Parse honba from round header
            round_name = m.group(1)
            honba_match = re.search(r'-(\d+)$', round_name)
            honba = int(honba_match.group(1)) if honba_match else 0
            current["rounds"].append({
                "round": round_name,
                "honba": honba,
                "turn_count": turn_count,
                "outcome": outcome,
                "mistakes": [],
            })
            continue

        # Try mistake with category first, then bare
        m = RE_MISTAKE_CAT.match(line)
        if m and current.get("rounds"):
            current["rounds"][-1]["mistakes"].append({
                "turn": int(m.group(1)),
                "severity": m.group(2),
                "category": m.group(3),
                "ev_loss": round(float(m.group(4)), 2),
                "note": parse_note(m.group(5)),
            })
            continue

        m = RE_MISTAKE_BARE.match(line)
        if m and current.get("rounds"):
            current["rounds"][-1]["mistakes"].append({
                "turn": int(m.group(1)),
                "severity": m.group(2),
                "category": None,
                "ev_loss": round(float(m.group(3)), 2),
                "note": parse_note(m.group(4)),
            })
            continue

    # Catch trailing game without final separator
    if current and current.get("date"):
        games.append(current)

    return games


def backfill_from_mortal(game, mortal_path):
    """Enrich text-parsed game with data from Mortal JSON.

    Matches mistakes by round + turn number, adds hand/discard/shanten/top_actions.
    """
    with open(DIR / mortal_path) as f:
        data = json.load(f)

    parsed = parse_game(data, game_date=game["date"])
    parsed_file = mortal_path

    # Build lookup: (round_header, turn) → mortal mistake data
    mortal_lookup = {}
    for rnd in parsed["rounds"]:
        for m in rnd["mistakes"]:
            key = (rnd["round"], m["turn"])
            mortal_lookup[key] = m

    for rnd in game["rounds"]:
        for mistake in rnd["mistakes"]:
            key = (rnd["round"], mistake["turn"])
            mortal = mortal_lookup.get(key)
            if mortal:
                mistake["hand"] = mortal["hand"]
                mistake["melds"] = mortal["melds"]
                mistake["shanten"] = mortal["shanten"]
                mistake["draw"] = mortal["draw"]
                mistake["actual"] = mortal["actual"]
                mistake["expected"] = mortal["expected"]
                mistake["top_actions"] = mortal["top_actions"]
            else:
                # No match — fill with nulls
                for field in ("hand", "melds", "shanten", "draw",
                              "actual", "expected", "top_actions"):
                    mistake.setdefault(field, None)

    game["mortal_file"] = mortal_path
    return game


def fill_nulls(game):
    """Ensure all mistake fields exist even without Mortal data."""
    for rnd in game["rounds"]:
        for m in rnd["mistakes"]:
            for field in ("hand", "melds", "shanten", "draw",
                          "actual", "expected", "top_actions"):
                m.setdefault(field, None)
    game.setdefault("mortal_file", None)


def compute_summary(game):
    """Compute summary stats for a game."""
    total = 0
    total_ev = 0.0
    total_turns = 0
    by_severity = {"???": 0, "??": 0, "?": 0, "!": 0}
    by_category = {}

    for rnd in game["rounds"]:
        if rnd["turn_count"]:
            total_turns += rnd["turn_count"]
        for m in rnd["mistakes"]:
            total += 1
            total_ev += m["ev_loss"]
            sev = m["severity"]
            if sev in by_severity:
                by_severity[sev] += 1
            cat = m.get("category")
            if cat:
                if cat not in by_category:
                    by_category[cat] = {"count": 0, "ev": 0.0}
                by_category[cat]["count"] += 1
                by_category[cat]["ev"] = round(by_category[cat]["ev"] + m["ev_loss"], 2)

    game["summary"] = {
        "total_mistakes": total,
        "total_ev_loss": round(total_ev, 2),
        "total_turns": total_turns if total_turns > 0 else None,
        "ev_per_turn": round(total_ev / total_turns, 4) if total_turns > 0 else None,
        "by_severity": by_severity,
        "by_category": by_category,
    }


def main():
    print(f"Parsing {TXT_FILE}...")
    games = parse_text_games()
    print(f"Found {len(games)} games.")

    for i, game in enumerate(games):
        mortal_path = MORTAL_MAP.get(i)
        if mortal_path:
            print(f"  Game {i+1}: backfilling from {mortal_path}")
            backfill_from_mortal(game, mortal_path)
        else:
            print(f"  Game {i+1}: text-only (no Mortal JSON)")
            fill_nulls(game)
        compute_summary(game)

        n = game["summary"]["total_mistakes"]
        ev = game["summary"]["total_ev_loss"]
        print(f"    {game['date']}: {n} mistakes, {ev:.2f} EV")

    result = {"games": games}
    with open(OUT_FILE, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nWrote {OUT_FILE}")


if __name__ == "__main__":
    main()
