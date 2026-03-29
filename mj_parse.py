#!/usr/bin/env python3
"""Parse Mortal AI JSON analysis and output mistake entries for Mahjong Mistakes.txt."""

import argparse
import json
import sys
from datetime import date


def severity(ev_loss):
    if ev_loss > 1.00:
        return "???"
    elif ev_loss >= 0.50:
        return "??"
    else:
        return "?"


def main():
    parser = argparse.ArgumentParser(
        description="Extract mistakes from a Mortal AI JSON analysis."
    )
    parser.add_argument("json_file", help="Path to the Mortal JSON file")
    parser.add_argument("--date", default=None, help="Game date (default: today)")
    args = parser.parse_args()

    with open(args.json_file) as f:
        data = json.load(f)

    game_date = args.date or date.today().isoformat()

    kyokus = data["review"]["kyokus"]
    start_events = [
        e for e in data["mjai_log"] if isinstance(e, dict) and e.get("type") == "start_kyoku"
    ]

    if len(kyokus) != len(start_events):
        print(
            f"Error: {len(kyokus)} review kyokus but {len(start_events)} start_kyoku events",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Date: {game_date}")
    print("Log:")
    print()

    for kyoku, start in zip(kyokus, start_events):
        # Build round header
        header = f"{start['bakaze']}{start['kyoku']}"
        if start["honba"] > 0:
            header += f"-{start['honba']}"

        entries = kyoku["entries"]
        if entries:
            max_junme = max(e["junme"] for e in entries)
            header += f"T{max_junme + 1}"

        print(header)

        # Collect and print mistakes
        for entry in entries:
            if not entry["is_equal"]:
                expected_q = entry["details"][0]["q_value"]
                actual_q = entry["details"][entry["actual_index"]]["q_value"]
                ev_loss = expected_q - actual_q
                print(f"{entry['junme']} {severity(ev_loss)} {ev_loss:.2f}")

    print()
    print("SUMMARY:")
    print("TOTAL:")
    print("TURNS:")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
