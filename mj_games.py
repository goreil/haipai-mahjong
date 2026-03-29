#!/usr/bin/env python3
"""CLI tool for managing mahjong game review data in games.json."""

import argparse
import json
import sys
import urllib.parse
from datetime import date
from pathlib import Path

DIR = Path(__file__).parent
GAMES_FILE = DIR / "games.json"

CATEGORIES = [
    "1A", "1B", "1C", "1D", "1E",
    "2A", "2B", "2C",
    "3A", "3B", "3C",
    "4A", "4B",
    "5A", "5B",
]


def load_games():
    with open(GAMES_FILE) as f:
        return json.load(f)


def save_games(data):
    with open(GAMES_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def format_hand(tiles):
    """Group mjai tiles into a compact sorted display: 234m 15p 7s EFC."""
    if not tiles:
        return ""
    suits = {"m": [], "p": [], "s": []}
    honors = []
    for t in tiles:
        if len(t) >= 2 and t[-1] in suits:
            # Handle red fives: 5mr → 0m display
            if t.endswith("r"):
                suits[t[-2]].append("0")
            else:
                suits[t[-1]].append(t[:-1])
        elif len(t) >= 3 and t[-1] == "r":
            # e.g. 5mr, 5pr, 5sr
            suits[t[-2]].append("0")
        else:
            honors.append(t)
    parts = []
    for suit in ("m", "p", "s"):
        if suits[suit]:
            parts.append("".join(sorted(suits[suit])) + suit)
    if honors:
        parts.append("".join(honors))
    return " ".join(parts)


def format_action_short(action):
    """Format action for display."""
    if action is None:
        return "?"
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


def compute_summary(game):
    """Compute summary stats for a game. Mutates game dict."""
    total = 0
    total_ev = 0.0
    total_turns = 0
    by_severity = {"???": 0, "??": 0, "?": 0, "!": 0}
    by_category = {}

    for rnd in game["rounds"]:
        if rnd.get("turn_count"):
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


def cmd_list(args):
    """List all games with basic stats."""
    data = load_games()
    for i, game in enumerate(data["games"]):
        s = game.get("summary", {})
        n = s.get("total_mistakes", 0)
        ev = s.get("total_ev_loss", 0)
        turns = s.get("total_turns")

        # Count annotated vs total
        annotated = sum(
            1 for rnd in game["rounds"]
            for m in rnd["mistakes"]
            if m.get("category")
        )

        line = f"  {i+1}. {game['date']}  {n} mistakes  {ev:.2f} EV"
        if turns:
            line += f"  {turns}T  {s.get('ev_per_turn', 0):.4f}/T"
        if annotated < n:
            line += f"  [{annotated}/{n} annotated]"
        print(line)


def cmd_review(args):
    """Pretty-print mistakes for one or all games."""
    data = load_games()
    games = data["games"]

    if args.game:
        idx = args.game - 1
        if idx < 0 or idx >= len(games):
            print(f"Error: game {args.game} not found (have {len(games)})", file=sys.stderr)
            sys.exit(1)
        games = [(idx, games[idx])]
    else:
        games = list(enumerate(games))

    hide = set()
    if args.hide_minor:
        hide.add("?")
    if args.hide_medium:
        hide.add("??")

    for idx, game in games:
        print(f"=== Game {idx+1}: {game['date']} ===")
        if game.get("log_url"):
            print(f"Log: {game['log_url']}")
        print()

        for rnd in game["rounds"]:
            header = rnd["round"]
            if rnd.get("turn_count"):
                header += f"T{rnd['turn_count']}"
            if rnd.get("outcome"):
                header += f" {rnd['outcome']}"

            visible = [m for m in rnd["mistakes"] if m["severity"] not in hide]
            if not visible:
                print(header)
                continue

            print(header)
            for m in visible:
                actual_str = format_action_short(m.get("actual"))
                expected_str = format_action_short(m.get("expected"))

                # Main line
                cat = m.get("category") or "   "
                line = f"  {m['turn']:2d} {m['severity']:3s} {cat:3s} {m['ev_loss']:.2f}"

                if m.get("shanten") is not None:
                    line += f"  [{m['shanten']}-shanten]"

                if actual_str != "?" and expected_str != "?":
                    line += f"  |{actual_str}| > |{expected_str}|"

                print(line)

                # Hand line (if data available)
                if m.get("hand"):
                    hand_str = format_hand(m["hand"])
                    draw = m.get("draw", "")
                    draw_str = f"  Drew: {draw}" if draw else ""
                    print(f"       Hand: {hand_str}{draw_str}")

                # Top actions (if data available)
                if m.get("top_actions"):
                    tops = []
                    for a in m["top_actions"]:
                        action_str = format_action_short(a["action"])
                        tops.append(f"{action_str}({a['q_value']:.2f}, {a['prob']:.0%})")
                    print(f"       Top: {' '.join(tops)}")

                # Note
                if m.get("note"):
                    print(f"       Note: {m['note']}")

        # Summary
        s = game.get("summary", {})
        if s:
            print()
            cats = " ".join(
                f"{k}:{v['count']}({v['ev']})"
                for k, v in sorted(s.get("by_category", {}).items())
            )
            if cats:
                print(f"SUMMARY: {cats}")
            sev = s.get("by_severity", {})
            print(f"TOTAL: {s['total_mistakes']} mistakes, {s['total_ev_loss']:.2f} EV"
                  f" | ???:{sev.get('???',0)} ??:{sev.get('??',0)} ?:{sev.get('?',0)} !:{sev.get('!',0)}")
            if s.get("total_turns"):
                print(f"TURNS: {s['total_turns']} | EV/Turn: {s['ev_per_turn']:.4f}")
        print()


def cmd_annotate(args):
    """Set category and/or note on a specific mistake."""
    data = load_games()
    idx = args.game - 1
    if idx < 0 or idx >= len(data["games"]):
        print(f"Error: game {args.game} not found", file=sys.stderr)
        sys.exit(1)
    game = data["games"][idx]

    # Find the round
    target_round = None
    for rnd in game["rounds"]:
        if rnd["round"] == args.round:
            target_round = rnd
            break
    if target_round is None:
        rounds = [r["round"] for r in game["rounds"]]
        print(f"Error: round '{args.round}' not found. Available: {rounds}", file=sys.stderr)
        sys.exit(1)

    # Find the mistake by turn
    target = None
    candidates = []
    for m in target_round["mistakes"]:
        if m["turn"] == args.turn:
            candidates.append(m)
    if len(candidates) == 0:
        turns = [m["turn"] for m in target_round["mistakes"]]
        print(f"Error: turn {args.turn} not found in {args.round}. Available: {turns}", file=sys.stderr)
        sys.exit(1)
    elif len(candidates) == 1:
        target = candidates[0]
    else:
        # Multiple mistakes on same turn — use --index to disambiguate
        i = args.index or 0
        if i >= len(candidates):
            print(f"Error: turn {args.turn} has {len(candidates)} mistakes, use --index 0-{len(candidates)-1}",
                  file=sys.stderr)
            sys.exit(1)
        target = candidates[i]

    if args.category is not None:
        if args.category and args.category not in CATEGORIES:
            print(f"Warning: '{args.category}' is not a standard category", file=sys.stderr)
        target["category"] = args.category if args.category else None
    if args.note is not None:
        target["note"] = args.note if args.note else None

    compute_summary(game)
    save_games(data)

    cat_str = target.get("category") or "none"
    note_str = target.get("note") or ""
    print(f"Updated game {args.game} {args.round} turn {args.turn}: category={cat_str} note={note_str}")


def cmd_summary(args):
    """Recompute and display summaries."""
    data = load_games()
    games = data["games"]

    if args.game:
        idx = args.game - 1
        if idx < 0 or idx >= len(games):
            print(f"Error: game {args.game} not found", file=sys.stderr)
            sys.exit(1)
        indices = [idx]
    else:
        indices = range(len(games))

    for idx in indices:
        game = games[idx]
        compute_summary(game)

    save_games(data)

    # Print all summaries
    all_mistakes = 0
    all_ev = 0.0
    all_turns = 0
    all_by_cat = {}
    all_by_sev = {"???": 0, "??": 0, "?": 0, "!": 0}

    for idx in indices:
        s = games[idx]["summary"]
        print(f"Game {idx+1} ({games[idx]['date']}):")
        cats = " ".join(
            f"{k}:{v['count']}({v['ev']})"
            for k, v in sorted(s.get("by_category", {}).items())
        )
        print(f"  {s['total_mistakes']} mistakes, {s['total_ev_loss']:.2f} EV", end="")
        if s.get("total_turns"):
            print(f"  | {s['total_turns']}T, {s['ev_per_turn']:.4f}/T", end="")
        print()
        if cats:
            print(f"  {cats}")
        print()

        all_mistakes += s["total_mistakes"]
        all_ev += s["total_ev_loss"]
        if s.get("total_turns"):
            all_turns += s["total_turns"]
        for k, v in s.get("by_severity", {}).items():
            all_by_sev[k] = all_by_sev.get(k, 0) + v
        for k, v in s.get("by_category", {}).items():
            if k not in all_by_cat:
                all_by_cat[k] = {"count": 0, "ev": 0.0}
            all_by_cat[k]["count"] += v["count"]
            all_by_cat[k]["ev"] = round(all_by_cat[k]["ev"] + v["ev"], 2)

    if len(indices) > 1:
        print("--- All Games ---")
        print(f"  {all_mistakes} mistakes, {all_ev:.2f} EV", end="")
        if all_turns:
            print(f"  | {all_turns}T, {all_ev/all_turns:.4f}/T", end="")
        print()
        cats = " ".join(
            f"{k}:{v['count']}({v['ev']})"
            for k, v in sorted(all_by_cat.items())
        )
        if cats:
            print(f"  {cats}")
        sev = all_by_sev
        print(f"  ???:{sev['???']} ??:{sev['??']} ?:{sev['?']} !:{sev['!']}")


def cmd_add(args):
    """Fetch Mortal JSON, parse it, and append game to games.json."""
    from mj_parse import parse_game

    url = args.url
    game_date = args.date or date.today().isoformat()

    # Extract data path from mjai viewer URL
    # e.g. https://mjai.ekyu.moe/killerducky/?data=/report/HASH.json
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if "data" not in qs:
        print(f"Error: URL must contain ?data= parameter", file=sys.stderr)
        sys.exit(1)
    data_path = qs["data"][0]
    download_url = f"https://mjai.ekyu.moe{data_path}"
    filename = Path(data_path).name

    # Download JSON
    mortal_dir = DIR / "mortal_analysis"
    mortal_dir.mkdir(exist_ok=True)
    dest = mortal_dir / filename

    if dest.exists():
        print(f"Using existing {dest}")
    else:
        import requests
        print(f"Downloading {download_url}...")
        resp = requests.get(download_url, timeout=30)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        print(f"Saved to {dest}")

    # Parse
    with open(dest) as f:
        mortal_data = json.load(f)

    game = parse_game(mortal_data, game_date=game_date)
    game["mortal_file"] = str(dest.relative_to(DIR))
    compute_summary(game)

    # Append to games.json
    if GAMES_FILE.exists():
        data = load_games()
    else:
        data = {"games": []}
    data["games"].append(game)
    save_games(data)

    s = game["summary"]
    n = len(data["games"])
    print(f"\nAdded game {n}: {game_date}")
    print(f"  {s['total_mistakes']} mistakes, {s['total_ev_loss']:.2f} EV", end="")
    if s.get("total_turns"):
        print(f"  | {s['total_turns']}T, {s['ev_per_turn']:.4f}/T", end="")
    print()
    sev = s["by_severity"]
    print(f"  ???:{sev['???']} ??:{sev['??']} ?:{sev['?']} !:{sev['!']}")


def main():
    parser = argparse.ArgumentParser(description="Mahjong game review manager")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List all games")

    p_review = sub.add_parser("review", help="Pretty-print game mistakes")
    p_review.add_argument("--game", "-g", type=int, help="Game number (1-based)")
    p_review.add_argument("--hide-minor", action="store_true", help="Hide ? (0-0.50 EV) mistakes")
    p_review.add_argument("--hide-medium", action="store_true", help="Hide ?? (0.50-1.00 EV) mistakes")

    p_ann = sub.add_parser("annotate", help="Set category/note on a mistake")
    p_ann.add_argument("game", type=int, help="Game number (1-based)")
    p_ann.add_argument("round", help="Round header (e.g. E1, S2-1)")
    p_ann.add_argument("turn", type=int, help="Turn number")
    p_ann.add_argument("--category", "-c", help="Category code (e.g. 1A, 2B)")
    p_ann.add_argument("--note", "-n", help="Note text (empty string to clear)")
    p_ann.add_argument("--index", "-i", type=int, help="Disambiguate duplicate turns (0-based)")

    p_sum = sub.add_parser("summary", help="Recompute and display summaries")
    p_sum.add_argument("--game", "-g", type=int, help="Game number (1-based)")

    p_add = sub.add_parser("add", help="Fetch Mortal JSON and add game")
    p_add.add_argument("url", help="mjai.ekyu.moe viewer URL")
    p_add.add_argument("--date", help="Game date (default: today)")

    args = parser.parse_args()
    if args.command == "list":
        cmd_list(args)
    elif args.command == "review":
        cmd_review(args)
    elif args.command == "annotate":
        cmd_annotate(args)
    elif args.command == "summary":
        cmd_summary(args)
    elif args.command == "add":
        cmd_add(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
