#!/usr/bin/env python3
"""Parse Mortal AI JSON analysis into structured game data or text format."""

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


def round_header(start):
    """Build round header string from a start_kyoku event."""
    header = f"{start['bakaze']}{start['kyoku']}"
    if start["honba"] > 0:
        header += f"-{start['honba']}"
    return header


def format_action(action):
    """Format an action dict for text display."""
    t = action.get("type", "?")
    if t == "dahai":
        return action["pai"]
    elif t in ("chi", "pon"):
        consumed = "".join(action.get("consumed", []))
        return f"{t} {consumed}+{action.get('pai', '?')}"
    elif t == "reach":
        return "riichi"
    elif t == "hora":
        return "win"
    elif t == "none":
        return "pass"
    elif t == "ankan":
        return f"ankan {action.get('consumed', ['?'])[0]}"
    return t


def parse_game(data, game_date=None):
    """Parse Mortal JSON into structured game dict.

    Returns a dict matching the games.json schema (without summary/annotations).
    """
    game_date = game_date or date.today().isoformat()

    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object, got " + type(data).__name__)
    if "review" not in data or not isinstance(data.get("review"), dict):
        raise ValueError("Missing or invalid 'review' field")
    if "kyokus" not in data["review"] or not isinstance(data["review"]["kyokus"], list):
        raise ValueError("Missing or invalid 'review.kyokus' field")
    if "mjai_log" not in data or not isinstance(data.get("mjai_log"), list):
        raise ValueError("Missing or invalid 'mjai_log' field")

    kyokus = data["review"]["kyokus"]
    start_events = [
        e for e in data["mjai_log"]
        if isinstance(e, dict) and e.get("type") == "start_kyoku"
    ]

    if len(kyokus) != len(start_events):
        raise ValueError(
            f"{len(kyokus)} review kyokus but {len(start_events)} start_kyoku events"
        )

    rounds = []
    for kyoku, start in zip(kyokus, start_events):
        entries = kyoku["entries"]
        turn_count = (max(e["junme"] for e in entries) + 1) if entries else 0
        decision_count = len(entries)

        mistakes = []
        for entry in entries:
            if not entry["is_equal"]:
                try:
                    expected_q = entry["details"][0]["q_value"]
                    actual_q = entry["details"][entry["actual_index"]]["q_value"]
                except (KeyError, IndexError, TypeError) as e:
                    raise ValueError(f"Malformed entry in kyoku: {e}") from e
                ev_loss = round(expected_q - actual_q, 2)

                top_actions = [
                    {
                        "action": d["action"],
                        "q_value": round(d["q_value"], 4),
                        "prob": round(d["prob"], 4),
                    }
                    for d in entry["details"][:3]
                ]
                # Include player's actual choice if not in top 3
                actual_idx = entry["actual_index"]
                if actual_idx >= 3:
                    d = entry["details"][actual_idx]
                    top_actions.append({
                        "action": d["action"],
                        "q_value": round(d["q_value"], 4),
                        "prob": round(d["prob"], 4),
                    })

                mistakes.append({
                    "turn": entry["junme"],
                    "severity": severity(ev_loss),
                    "ev_loss": ev_loss,
                    "category": None,
                    "note": None,
                    "hand": entry["state"]["tehai"],
                    "melds": entry["state"]["fuuros"],
                    "shanten": entry.get("shanten"),
                    "draw": entry.get("tile"),
                    "actual": entry["actual"],
                    "expected": entry["expected"],
                    "top_actions": top_actions,
                })

        rounds.append({
            "round": round_header(start),
            "honba": start["honba"],
            "turn_count": turn_count,
            "decision_count": decision_count,
            "outcome": None,
            "mistakes": mistakes,
        })

    return {
        "date": game_date,
        "log_url": None,
        "mortal_file": None,
        "rounds": rounds,
        "summary": None,
    }


def print_text(game):
    """Print game in legacy text format with auto-generated discard notes."""
    print(f"Date: {game['date']}")
    print(f"Log: {game['log_url'] or ''}")
    print()

    for rnd in game["rounds"]:
        header = rnd["round"]
        if rnd["turn_count"]:
            header += f"T{rnd['turn_count']}"
        print(header)

        for m in rnd["mistakes"]:
            actual_str = format_action(m["actual"])
            expected_str = format_action(m["expected"])
            if actual_str != expected_str:
                note = f"(|{actual_str}| > |{expected_str}|)"
            else:
                note = ""
            print(f"{m['turn']} {m['severity']} {m['ev_loss']:.2f} {note}".rstrip())

    print()
    print("SUMMARY:")
    print("TOTAL:")
    print("TURNS:")
    print()
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Extract mistakes from a Mortal AI JSON analysis."
    )
    parser.add_argument("json_file", help="Path to the Mortal JSON file")
    parser.add_argument("--date", default=None, help="Game date (default: today)")
    parser.add_argument(
        "--text", action="store_true",
        help="Output legacy text format instead of JSON",
    )
    args = parser.parse_args()

    with open(args.json_file) as f:
        data = json.load(f)

    game = parse_game(data, game_date=args.date)
    game["mortal_file"] = args.json_file

    if args.text:
        print_text(game)
    else:
        json.dump(game, sys.stdout, indent=2, ensure_ascii=False)
        print()


if __name__ == "__main__":
    main()
