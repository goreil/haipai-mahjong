#!/usr/bin/env python3
"""Automatic error categorization by comparing Mortal AI vs mahjong-cpp tile efficiency."""

import json
import sys
from pathlib import Path

import requests

DIR = Path(__file__).parent

# Local mahjong-cpp server (nanikiru binary)
LOCAL_API_URL = "http://127.0.0.1:50000/"

# --- Tile notation conversion (mjai <-> tile IDs) ---

MJAI_TO_ID = {
    "1m": 0, "2m": 1, "3m": 2, "4m": 3, "5m": 4, "6m": 5, "7m": 6, "8m": 7, "9m": 8,
    "1p": 9, "2p": 10, "3p": 11, "4p": 12, "5p": 13, "6p": 14, "7p": 15, "8p": 16, "9p": 17,
    "1s": 18, "2s": 19, "3s": 20, "4s": 21, "5s": 22, "6s": 23, "7s": 24, "8s": 25, "9s": 26,
    "E": 27, "S": 28, "W": 29, "N": 30, "P": 31, "F": 32, "C": 33,
    "5mr": 34, "5pr": 35, "5sr": 36,
}

ID_TO_MJAI = {v: k for k, v in MJAI_TO_ID.items()}

# Red five -> base five mapping (for comparison: 5mr and 5m are "same tile")
RED_TO_BASE = {34: 4, 35: 13, 36: 22}


def mjai_to_tile_id(tile):
    return MJAI_TO_ID[tile]


def tile_id_to_base(tid):
    """Map red five IDs to their base ID (34->4, 35->13, 36->22), others unchanged."""
    return RED_TO_BASE.get(tid, tid)


def is_honor_mjai(tile):
    return tile in ("E", "S", "W", "N", "P", "F", "C")


def is_red_five_mjai(tile):
    return tile in ("5mr", "5pr", "5sr")


def is_wind_mjai(tile):
    return tile in ("E", "S", "W", "N")


def is_dragon_mjai(tile):
    return tile in ("P", "F", "C")


# --- Wall reconstruction ---

def flatten_mjai_log(mjai_log):
    """Flatten mjai_log (which can have nested lists for simultaneous events)."""
    events = []
    for item in mjai_log:
        if isinstance(item, dict):
            events.append(item)
        elif isinstance(item, list):
            for sub in item:
                if isinstance(sub, dict):
                    events.append(sub)
    return events


def decrement_wall(wall, mjai_tile):
    """Decrement wall count for a tile. Handles red fives."""
    tid = mjai_to_tile_id(mjai_tile)
    base = tile_id_to_base(tid)
    wall[base] -= 1
    if tid != base:
        wall[tid] -= 1


def reconstruct_context(mortal_data, kyoku_idx, tiles_left_target):
    """Replay mjai_log for a kyoku up to tiles_left_target.

    Returns (wall, round_wind_id, seat_wind_id, dora_indicator_ids, visible_tiles).
    wall is a 37-element array of remaining tile counts.
    """
    player_id = mortal_data["player_id"]
    events = flatten_mjai_log(mortal_data["mjai_log"])

    # Find start_kyoku events and their positions
    start_positions = []
    for i, e in enumerate(events):
        if e.get("type") == "start_kyoku":
            start_positions.append(i)

    start_pos = start_positions[kyoku_idx]
    start = events[start_pos]

    # Round/seat wind
    bakaze = start["bakaze"]  # "E" or "S"
    round_wind_id = mjai_to_tile_id(bakaze)
    oya = start["oya"]
    seat_idx = (player_id - oya) % 4
    seat_wind_id = 27 + seat_idx

    # Initialize wall: 4 of each regular tile, 1 of each red five
    wall = [4] * 34 + [1, 1, 1]

    # Track dora indicators
    dora_indicators = [start["dora_marker"]]

    # Visible tiles (everything we can see that's NOT in our hand)
    visible = []
    visible.append(start["dora_marker"])

    # Replay events from after start_kyoku
    tiles_left = 70  # standard live wall for 4-player
    pos = start_pos + 1

    # Find end of this kyoku
    next_start = start_positions[kyoku_idx + 1] if kyoku_idx + 1 < len(start_positions) else len(events)

    while pos < next_start:
        e = events[pos]
        etype = e.get("type")

        if etype == "tsumo":
            tiles_left -= 1
            # The drawn tile is NOT visible to others (it goes into the drawer's hand)
            # We only care about it if it's our draw (it'll be in our tehai)

        elif etype == "dahai":
            # Discarded tile is visible to everyone
            visible.append(e["pai"])

        elif etype in ("chi", "pon"):
            # consumed tiles (from caller's hand) become visible via the meld
            # pai was already counted as a dahai by the target player
            for t in e.get("consumed", []):
                visible.append(t)

        elif etype == "ankan":
            # All 4 tiles revealed (even though face-down, the tile type is known)
            for t in e.get("consumed", []):
                visible.append(t)

        elif etype == "kakan":
            # The added tile becomes visible
            visible.append(e["pai"])

        elif etype == "daiminkan":
            # consumed tiles (3 from caller's hand) visible; pai was already a dahai
            for t in e.get("consumed", []):
                visible.append(t)

        elif etype == "dora":
            # New dora indicator revealed (after kan)
            visible.append(e["dora_marker"])
            dora_indicators.append(e["dora_marker"])

        if tiles_left <= tiles_left_target:
            break

        pos += 1

    # Build wall: subtract hand will be done by caller (since hand varies per mistake)
    # Here we subtract all visible tiles
    for t in visible:
        decrement_wall(wall, t)

    dora_ids = [mjai_to_tile_id(d) for d in dora_indicators]

    return wall, round_wind_id, seat_wind_id, dora_ids


def subtract_hand_from_wall(wall, hand_tiles):
    """Subtract player's hand tiles from wall. Returns a copy."""
    w = wall[:]
    for t in hand_tiles:
        decrement_wall(w, t)
    return w


# --- mahjong-cpp API ---

def build_api_request(hand_mjai, melds_mjai, round_wind_id, seat_wind_id, dora_ids, wall):
    """Build the API request payload."""
    hand_ids = [mjai_to_tile_id(t) for t in hand_mjai]

    melds = []
    for m in melds_mjai:
        mtype = m["type"]
        tiles = [mjai_to_tile_id(t) for t in m.get("consumed", [])]
        if "pai" in m:
            tiles.append(mjai_to_tile_id(m["pai"]))
        type_map = {"chi": 1, "pon": 0, "ankan": 2, "daiminkan": 3, "kakan": 4}
        melds.append({"type": type_map.get(mtype, 0), "tiles": sorted(tiles)})

    return {
        "enable_reddora": True,
        "enable_uradora": True,
        "enable_shanten_down": True,
        "enable_tegawari": True,
        "enable_riichi": False,
        "round_wind": round_wind_id,
        "seat_wind": seat_wind_id,
        "dora_indicators": dora_ids,
        "hand": hand_ids,
        "melds": melds,
        "wall": wall,
        "version": "0.9.1",
    }


def call_mahjong_cpp(request_data):
    """Call the local mahjong-cpp tile efficiency calculator (nanikiru server)."""
    resp = requests.post(
        LOCAL_API_URL,
        json=request_data,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"API error: {data.get('err_msg', 'unknown')}")
    return data["response"]


def get_cpp_best_discard(response):
    """Find the best discard tile ID from mahjong-cpp response.

    Ranks by: lowest shanten, then highest sum of exp_score.
    Returns (tile_id, shanten) or (None, None) if no stats.
    """
    stats = response.get("stats", [])
    if not stats:
        return None, None

    # Find minimum shanten
    min_shanten = min(s["shanten"] for s in stats)
    best = [s for s in stats if s["shanten"] == min_shanten]

    # Among best shanten, rank by expected score sum (or necessary tiles count as fallback)
    calc_stats = response.get("config", {}).get("calc_stats", False)

    if calc_stats:
        # Use sum of exp_score as ranking
        best.sort(key=lambda s: sum(s.get("exp_score", [0])), reverse=True)
    else:
        # Fallback: use total necessary tile count (acceptance / ukeiire)
        best.sort(
            key=lambda s: sum(t["count"] for t in s.get("necessary_tiles", s.get("necessary", []))),
            reverse=True,
        )

    return best[0]["tile"], min_shanten


# --- Categorization logic ---

def categorize_by_action_type(actual, expected):
    """Categorize non-discard-vs-discard mistakes by action type.
    Returns category string or None if this is a dahai-vs-dahai case.
    """
    at = actual.get("type")
    et = expected.get("type")

    # Meld decisions (3A-3C)
    if at in ("chi", "pon") and et == "none":
        return "3A"  # Bad meld call
    if at == "none" and et in ("chi", "pon"):
        return "3B"  # Missed meld opportunity
    if at in ("chi", "pon") and et in ("chi", "pon"):
        return "3C"  # Wrong meld choice

    # Riichi decisions (4A-4B)
    if at == "reach" and et == "dahai":
        return "4A"  # Bad riichi
    if at == "dahai" and et == "reach":
        return "4B"  # Missed riichi

    # Kan decisions (5A-5B)
    if at in ("ankan", "kakan", "daiminkan") and et in ("dahai", "none"):
        return "5A"  # Bad kan
    if at in ("dahai", "none") and et in ("ankan", "kakan", "daiminkan"):
        return "5B"  # Missed kan

    # Missed win
    if et == "hora":
        return "2A"  # Defensive error (passed on win)

    # dahai vs dahai -> needs mahjong-cpp comparison
    if at == "dahai" and et == "dahai":
        return None

    # Other combinations (reach vs none, etc.) - categorize as strategic
    return "2A"


def sub_categorize_efficiency(mistake, dora_indicators):
    """Sub-categorize a tile efficiency error (mahjong-cpp agrees with Mortal).

    Returns one of 1A-1E.
    """
    actual_tile = mistake["actual"]["pai"]
    expected_tile = mistake["expected"]["pai"]
    hand = mistake["hand"]

    # Compute dora tiles from indicators
    dora_tiles = set()
    for d in dora_indicators:
        dora_tiles.add(_next_tile_mjai(d))

    # 1B: Dora handling - player discarded a dora or red five when shouldn't have
    actual_is_dora = actual_tile in dora_tiles or is_red_five_mjai(actual_tile)
    expected_is_dora = expected_tile in dora_tiles or is_red_five_mjai(expected_tile)
    if actual_is_dora != expected_is_dora:
        return "1B"

    # 1C: Honor tile ordering (both are honors but different ones)
    if is_honor_mjai(actual_tile) and is_honor_mjai(expected_tile):
        return "1C"

    # 1D: Honor vs number tile
    if is_honor_mjai(actual_tile) != is_honor_mjai(expected_tile):
        return "1D"

    # 1E: Pair management - involves a paired tile
    tile_counts = {}
    for t in hand:
        base = t.rstrip("r")  # normalize red fives: 5mr -> 5m
        if len(base) == 2 and base[1] in "mps":
            key = base
        else:
            key = t
        tile_counts[key] = tile_counts.get(key, 0) + 1

    def normalize(t):
        base = t.rstrip("r")
        return base if len(base) == 2 and base[1] in "mps" else t

    if tile_counts.get(normalize(actual_tile), 0) >= 2 or tile_counts.get(normalize(expected_tile), 0) >= 2:
        return "1E"

    # 1A: General tile efficiency
    return "1A"


def _next_tile_mjai(indicator):
    """Given a dora indicator tile (mjai notation), return the actual dora tile."""
    # Number tiles: indicator N -> dora is N+1 (wrapping 9->1)
    for suit in ("m", "p", "s"):
        if indicator.endswith(suit) and not indicator.endswith("r"):
            num = int(indicator[0])
            next_num = (num % 9) + 1
            return f"{next_num}{suit}"
        if indicator.endswith(f"{suit}r"):
            # Red five indicator -> dora is 6 of that suit
            return f"6{suit}"

    # Wind tiles: E->S->W->N->E
    winds = ["E", "S", "W", "N"]
    if indicator in winds:
        return winds[(winds.index(indicator) + 1) % 4]

    # Dragon tiles: P->F->C->P
    dragons = ["P", "F", "C"]
    if indicator in dragons:
        return dragons[(dragons.index(indicator) + 1) % 3]

    return indicator


def extract_cpp_stats(response):
    """Extract top candidates from mahjong-cpp response for storage."""
    stats = response.get("stats", [])
    calc_stats = response.get("config", {}).get("calc_stats", False)
    result = []
    for s in stats:
        entry = {
            "tile": ID_TO_MJAI.get(s["tile"], str(s["tile"])),
            "shanten": s["shanten"],
            "necessary_count": sum(
                t["count"] for t in s.get("necessary_tiles", s.get("necessary", []))
            ),
        }
        if calc_stats:
            entry["exp_score"] = round(sum(s.get("exp_score", [0])), 1)
            entry["win_prob_max"] = round(max(s.get("win_prob", [0])), 4)
        result.append(entry)

    # Sort by shanten asc, then exp_score desc (or necessary_count desc)
    if calc_stats:
        result.sort(key=lambda x: (x["shanten"], -x.get("exp_score", 0)))
    else:
        result.sort(key=lambda x: (x["shanten"], -x["necessary_count"]))
    return result


def _classify_strategic(mistake, defense_ctx, tiles_left, wall):
    """Distinguish 2A (push/fold) vs 2B (defense) for genuine cpp/mortal disagreements.

    If an opponent is in riichi and mortal chose a significantly safer tile,
    it's a defense play (2B). Otherwise it stays as 2A (push/fold).
    """
    from mj_defense import get_tile_safety_for_mistake

    safety = get_tile_safety_for_mistake(
        mistake["hand"],
        defense_ctx["mjai_events"],
        defense_ctx["start_pos"],
        defense_ctx["end_pos"],
        defense_ctx["player_id"],
        tiles_left,
        wall,
    )

    if safety is None:
        # No opponent in riichi — strategic disagreement without defense pressure
        return "2A"

    mortal_tile = mistake["expected"]["pai"]
    mortal_safety = safety.get(mortal_tile, safety.get(mortal_tile.rstrip("r"), 0))

    # Check if cpp's tile (or player's tile) is less safe
    cpp_tile = mistake.get("cpp_best")
    if cpp_tile:
        cpp_safety = safety.get(cpp_tile, safety.get(cpp_tile.rstrip("r"), 0))
        # Mortal chose a significantly safer tile (3+ points difference on 0-15 scale)
        if mortal_safety - cpp_safety >= 3:
            return "2B"

    return "2A"


def _cpp_reasonably_agrees(mortal_tile_id, cpp_stats):
    """Check if mortal's pick is competitive in cpp's rankings.

    Returns True if mortal's tile has the same shanten as cpp's best
    and an expected score within 90% of the top candidate.
    """
    if not cpp_stats:
        return False

    mortal_base = tile_id_to_base(mortal_tile_id)
    mortal_mjai = ID_TO_MJAI.get(mortal_base, ID_TO_MJAI.get(mortal_tile_id))

    # Find mortal's tile in cpp stats
    mortal_entry = None
    for s in cpp_stats:
        s_base = s["tile"].rstrip("r")
        m_base = mortal_mjai.rstrip("r") if mortal_mjai else None
        if s["tile"] == mortal_mjai or s_base == m_base:
            mortal_entry = s
            break

    if mortal_entry is None:
        return False

    top = cpp_stats[0]

    # Must have same shanten
    if mortal_entry["shanten"] != top["shanten"]:
        return False

    # Compare expected scores (if available)
    top_score = top.get("exp_score")
    mortal_score = mortal_entry.get("exp_score")
    if top_score and mortal_score:
        return mortal_score >= top_score * 0.90

    # Fallback: compare necessary tile counts
    top_nec = top.get("necessary_count", 0)
    mortal_nec = mortal_entry.get("necessary_count", 0)
    if top_nec > 0:
        return mortal_nec >= top_nec * 0.80

    return False


def categorize_mistake(mistake, mortal_data, kyoku_idx, entry, dora_indicators,
                       defense_ctx=None):
    """Categorize a single mistake.

    Args:
        mistake: The mistake dict from games.json
        mortal_data: Full Mortal analysis JSON
        kyoku_idx: Index into review.kyokus
        entry: The original review entry from Mortal JSON
        dora_indicators: List of dora indicator mjai strings for this round
        defense_ctx: Optional dict with keys (mjai_events, start_pos, end_pos, player_id)
                     for defense analysis

    Returns:
        (category, cpp_data, safety_data) where cpp_data is a dict with cpp results
        (or None if no API call was made).
    """
    actual = mistake["actual"]
    expected = mistake["expected"]

    # Try action-type categorization first
    cat = categorize_by_action_type(actual, expected)
    if cat is not None:
        return cat, None, None

    # dahai vs dahai -> call mahjong-cpp
    hand = mistake["hand"]
    melds = mistake["melds"]
    tiles_left = entry["tiles_left"]

    # Reconstruct wall (visible tiles, not including our hand)
    wall, round_wind, seat_wind, dora_ids = reconstruct_context(
        mortal_data, kyoku_idx, tiles_left
    )
    # Subtract our hand from wall
    wall = subtract_hand_from_wall(wall, hand)

    # Validate wall (no negative values)
    for i, count in enumerate(wall):
        if count < 0:
            print(f"  Warning: wall[{i}] = {count} (negative), clamping to 0", file=sys.stderr)
            wall[i] = 0

    # Compute safety ratings for defense visuals
    safety_data = None
    if defense_ctx:
        from mj_defense import get_tile_safety_for_mistake
        safety_data = get_tile_safety_for_mistake(
            hand, defense_ctx["mjai_events"], defense_ctx["start_pos"],
            defense_ctx["end_pos"], defense_ctx["player_id"],
            tiles_left, wall,
        )
        if safety_data:
            safety_data = {k: round(v, 1) for k, v in safety_data.items()}

    # Build and send API request
    req = build_api_request(hand, melds, round_wind, seat_wind, dora_ids, wall)

    try:
        response = call_mahjong_cpp(req)
    except Exception as e:
        print(f"  API error: {e}", file=sys.stderr)
        return None, None, safety_data

    cpp_best_id, cpp_shanten = get_cpp_best_discard(response)
    if cpp_best_id is None:
        return None, None, safety_data

    cpp_best_mjai = ID_TO_MJAI.get(cpp_best_id)
    cpp_stats = extract_cpp_stats(response)

    # Build cpp_data to store on the mistake
    cpp_data = {
        "best": cpp_best_mjai,
        "shanten": response.get("shanten", {}).get("all"),
        "stats": cpp_stats,
    }

    # Compare mahjong-cpp recommendation with Mortal's and player's actual
    mortal_best_id = mjai_to_tile_id(expected["pai"])
    actual_id = mjai_to_tile_id(actual["pai"])
    cpp_base = tile_id_to_base(cpp_best_id)
    mortal_base = tile_id_to_base(mortal_best_id)
    actual_base = tile_id_to_base(actual_id)

    cpp_agrees_mortal = (cpp_base == mortal_base)

    if cpp_agrees_mortal:
        # cpp and mortal agree: tile efficiency error
        cat = sub_categorize_efficiency(mistake, dora_indicators)
    elif _cpp_reasonably_agrees(mortal_best_id, cpp_stats):
        # cpp and mortal pick different tiles but mortal's pick is still
        # competitive by cpp's own metrics — this is efficiency, not strategy
        cat = sub_categorize_efficiency(mistake, dora_indicators)
    else:
        # Genuine disagreement: mortal sees something cpp doesn't
        # Check if mortal is choosing a safer tile (defense-motivated)
        cat = "2A"
        if defense_ctx:
            cat = _classify_strategic(mistake, defense_ctx, tiles_left, wall)

    return cat, cpp_data, safety_data


def categorize_game(game, game_idx, force=False, dry_run=False):
    """Categorize all mistakes in a game.

    Args:
        game: Game dict from games.json
        game_idx: 0-based game index (for display)
        force: Re-categorize even if already categorized
        dry_run: Don't save, just print what would happen

    Returns:
        Number of mistakes categorized, number of API calls made.
    """
    mortal_file = game.get("mortal_file")
    if not mortal_file:
        print(f"  Skipping game {game_idx+1}: no mortal_file", file=sys.stderr)
        return 0, 0

    mortal_path = DIR / mortal_file
    if not mortal_path.exists():
        print(f"  Skipping game {game_idx+1}: {mortal_file} not found", file=sys.stderr)
        return 0, 0

    with open(mortal_path) as f:
        mortal_data = json.load(f)

    kyokus = mortal_data["review"]["kyokus"]

    # Build start_kyoku events for dora tracking
    events = flatten_mjai_log(mortal_data["mjai_log"])
    start_events = [e for e in events if e.get("type") == "start_kyoku"]

    # Build start positions for defense context
    start_positions = [i for i, e in enumerate(events) if e.get("type") == "start_kyoku"]
    player_id = mortal_data["player_id"]

    categorized = 0
    api_calls = 0

    for kyoku_idx, (kyoku, start) in enumerate(zip(kyokus, start_events)):
        # Match kyoku to round in games.json
        from mj_parse import round_header
        rnd_header = round_header(start)

        game_round = None
        for rnd in game["rounds"]:
            if rnd["round"] == rnd_header:
                game_round = rnd
                break

        if game_round is None:
            continue

        # Collect dora indicators for this round
        dora_indicators = [start["dora_marker"]]

        # Build defense context for this kyoku
        start_pos = start_positions[kyoku_idx]
        end_pos = start_positions[kyoku_idx + 1] if kyoku_idx + 1 < len(start_positions) else len(events)
        defense_ctx = {
            "mjai_events": events,
            "start_pos": start_pos,
            "end_pos": end_pos,
            "player_id": player_id,
        }

        # Match mistakes to review entries
        mistake_idx = 0
        for entry in kyoku["entries"]:
            if entry["is_equal"]:
                continue

            # Find the corresponding mistake in games.json
            while mistake_idx < len(game_round["mistakes"]):
                m = game_round["mistakes"][mistake_idx]
                if m["turn"] == entry["junme"]:
                    break
                mistake_idx += 1
            else:
                continue

            if mistake_idx >= len(game_round["mistakes"]):
                continue

            m = game_round["mistakes"][mistake_idx]
            mistake_idx += 1

            # Skip if already categorized (unless force)
            if m.get("category") and not force:
                continue

            needs_api = (m["actual"].get("type") == "dahai" and
                         m["expected"].get("type") == "dahai")

            label = f"  {rnd_header} T{m['turn']}: "
            if needs_api:
                api_calls += 1

            cat, cpp_data, safety_data = categorize_mistake(
                m, mortal_data, kyoku_idx, entry, dora_indicators,
                defense_ctx=defense_ctx,
            )

            if cat:
                actual_str = m["actual"].get("pai", m["actual"]["type"])
                expected_str = m["expected"].get("pai", m["expected"]["type"])
                cpp_str = f" cpp={cpp_data['best']}" if cpp_data else ""
                print(f"{label}{actual_str} -> {expected_str}{cpp_str} => {cat}")

                if not dry_run:
                    m["category"] = cat
                    if cpp_data:
                        m["cpp_best"] = cpp_data["best"]
                        m["cpp_stats"] = cpp_data["stats"]
                    if safety_data:
                        m["safety_ratings"] = safety_data

                categorized += 1
            else:
                print(f"{label}skipped (API error or unknown)")

    return categorized, api_calls


def recheck_game(game, game_idx, dry_run=False):
    """Re-run categorization logic using stored cpp_stats (no API calls).

    Use this after updating the categorization rules to reclassify
    existing mistakes without re-querying mahjong-cpp.

    Returns number of mistakes whose category changed.
    """
    mortal_file = game.get("mortal_file")
    if not mortal_file:
        return 0

    mortal_path = DIR / mortal_file
    if not mortal_path.exists():
        return 0

    with open(mortal_path) as f:
        mortal_data = json.load(f)

    events = flatten_mjai_log(mortal_data["mjai_log"])
    start_positions = [i for i, e in enumerate(events) if e.get("type") == "start_kyoku"]
    start_events = [events[p] for p in start_positions]
    player_id = mortal_data["player_id"]
    kyokus = mortal_data["review"]["kyokus"]

    changed = 0
    from mj_parse import round_header

    for kyoku_idx, (kyoku, start) in enumerate(zip(kyokus, start_events)):
        rnd_header = round_header(start)

        game_round = None
        for rnd in game["rounds"]:
            if rnd["round"] == rnd_header:
                game_round = rnd
                break
        if game_round is None:
            continue

        dora_indicators = [start["dora_marker"]]

        # Defense context
        start_pos = start_positions[kyoku_idx]
        end_pos = start_positions[kyoku_idx + 1] if kyoku_idx + 1 < len(start_positions) else len(events)
        defense_ctx = {
            "mjai_events": events,
            "start_pos": start_pos,
            "end_pos": end_pos,
            "player_id": player_id,
        }

        # Match mistakes to review entries for tiles_left
        mistake_idx = 0
        for entry in kyoku["entries"]:
            if entry["is_equal"]:
                continue
            while mistake_idx < len(game_round["mistakes"]):
                if game_round["mistakes"][mistake_idx]["turn"] == entry["junme"]:
                    break
                mistake_idx += 1
            else:
                continue
            if mistake_idx >= len(game_round["mistakes"]):
                continue

            m = game_round["mistakes"][mistake_idx]
            mistake_idx += 1

            actual = m.get("actual", {})
            expected = m.get("expected", {})
            old_cat = m.get("category")

            # Non-dahai: use action-type categorization
            cat = categorize_by_action_type(actual, expected)
            if cat is not None:
                if cat != old_cat:
                    if not dry_run:
                        m["category"] = cat
                    print(f"  {rnd_header} T{m['turn']}: {old_cat} -> {cat}")
                    changed += 1
                continue

            # dahai vs dahai: re-run classification using stored cpp data
            if not m.get("cpp_stats") or not m.get("cpp_best"):
                continue

            # Reconstruct wall for safety computation and strategic classification
            tiles_left = entry["tiles_left"]
            wall, _, _, _ = reconstruct_context(mortal_data, kyoku_idx, tiles_left)
            wall = subtract_hand_from_wall(wall, m["hand"])
            for i in range(len(wall)):
                if wall[i] < 0:
                    wall[i] = 0

            # Compute safety ratings for defense visuals
            from mj_defense import get_tile_safety_for_mistake
            safety = get_tile_safety_for_mistake(
                m["hand"], events, start_pos, end_pos,
                player_id, tiles_left, wall,
            )
            if safety:
                safety = {k: round(v, 1) for k, v in safety.items()}
            if not dry_run and safety:
                m["safety_ratings"] = safety

            cpp_best_mjai = m["cpp_best"]
            cpp_best_id = mjai_to_tile_id(cpp_best_mjai)
            mortal_best_id = mjai_to_tile_id(expected["pai"])
            cpp_base = tile_id_to_base(cpp_best_id)
            mortal_base = tile_id_to_base(mortal_best_id)

            if cpp_base == mortal_base:
                cat = sub_categorize_efficiency(m, dora_indicators)
            elif _cpp_reasonably_agrees(mortal_best_id, m["cpp_stats"]):
                cat = sub_categorize_efficiency(m, dora_indicators)
            else:
                cat = _classify_strategic(m, defense_ctx, tiles_left, wall)

            if cat != old_cat:
                if not dry_run:
                    m["category"] = cat
                print(f"  {rnd_header} T{m['turn']}: {old_cat} -> {cat}")
                changed += 1

    return changed
