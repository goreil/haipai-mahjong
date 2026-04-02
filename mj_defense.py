#!/usr/bin/env python3
"""Defense analysis: suji-based tile safety evaluation.

Ported from Riichi-Trainer/src/scripts/Evaluations.js.
Uses a 0-15 safety rating scale where higher = safer.
"""

# Tile index scheme (matching Riichi-Trainer):
#   1-9:   man (1m-9m)
#   11-19: pin (1p-9p)
#   21-29: sou (1s-9s)
#   31-37: honors (E S W N P F C)
# Index 0, 10, 20, 30 are unused/red-five slots.

MJAI_TO_RT = {
    "1m": 1, "2m": 2, "3m": 3, "4m": 4, "5m": 5, "6m": 6, "7m": 7, "8m": 8, "9m": 9,
    "5mr": 5,
    "1p": 11, "2p": 12, "3p": 13, "4p": 14, "5p": 15, "6p": 16, "7p": 17, "8p": 18, "9p": 19,
    "5pr": 15,
    "1s": 21, "2s": 22, "3s": 23, "4s": 24, "5s": 25, "6s": 26, "7s": 27, "8s": 28, "9s": 29,
    "5sr": 25,
    "E": 31, "S": 32, "W": 33, "N": 34, "P": 35, "F": 36, "C": 37,
}


def _is_suji(tile, opponent_discards, remaining, riichi_tile):
    """Check if tile is suji-safe against opponent's discards."""
    suji_a = tile - 3
    suji_b = tile + 3

    # Check suji_a side
    a_passed = False
    if suji_a % 10 == 0 or suji_a // 10 != tile // 10:
        a_passed = True
    else:
        if suji_a == riichi_tile:
            return False
        a_passed = (suji_a in opponent_discards
                    or remaining[suji_a + 1] == 0
                    or remaining[suji_a + 2] == 0)

    # Check suji_b side
    b_passed = False
    if suji_b % 10 == 0 or suji_b // 10 != tile // 10:
        b_passed = True
    else:
        if suji_b == riichi_tile:
            return False
        b_passed = (suji_b in opponent_discards
                    or remaining[suji_b - 1] == 0
                    or remaining[suji_b - 2] == 0)

    return a_passed and b_passed


def evaluate_safety(hand_indices, opponent_discards, remaining, riichi_discards, riichi_tile):
    """Calculate safety rating (0-15) for each tile in hand.

    Args:
        hand_indices: set of RT tile indices in player's hand
        opponent_discards: set of RT tile indices opponent discarded
        remaining: list[38] of remaining tile counts (not visible to player)
        riichi_discards: set of RT indices discarded after opponent's riichi
        riichi_tile: RT index of opponent's riichi declaration tile (or -1)

    Returns:
        dict mapping RT tile index -> safety rating (0-15)
    """
    safety = {}
    for i in hand_indices:
        # Genbutsu (100% safe)
        if i in opponent_discards or i in riichi_discards:
            safety[i] = 15
            continue

        # Terminal (suit tile ending in 1 or 9)
        if i < 30 and (i % 10 == 1 or i % 10 == 9):
            if _is_suji(i, opponent_discards, remaining, riichi_tile):
                safety[i] = 14 - remaining[i]
            else:
                safety[i] = 5
            continue

        # Honor tile
        if i > 30:
            r = remaining[i]
            if r == 0:
                safety[i] = 14
            elif r == 1:
                safety[i] = 13
            elif r == 2:
                safety[i] = 10
            else:
                safety[i] = 6
            continue

        # Number tile (2-8)
        digit = i % 10
        if _is_suji(i, opponent_discards, remaining, riichi_tile):
            if digit in (4, 5, 6):
                safety[i] = 9
            elif digit in (2, 8):
                safety[i] = 8
            else:
                safety[i] = 7
        else:
            if digit in (4, 5, 6):
                safety[i] = 1
            elif digit in (2, 8):
                safety[i] = 3
            else:
                safety[i] = 2

    return safety


def extract_riichi_state(mjai_log_events, start_pos, end_pos, player_id, target_tiles_left):
    """Extract opponent riichi state from mjai_log events up to a given point.

    Returns list of dicts, one per opponent in riichi:
        {"discards": set, "riichi_discards": set, "riichi_tile": int}
    """
    opponents = {}  # actor -> {"discards": [], "in_riichi": False, "riichi_tile": None, "riichi_discards": []}
    tiles_left = 70

    for pos in range(start_pos + 1, end_pos):
        e = mjai_log_events[pos]
        etype = e.get("type")
        actor = e.get("actor")

        if etype == "tsumo":
            tiles_left -= 1

        elif etype == "dahai" and actor != player_id:
            if actor not in opponents:
                opponents[actor] = {"discards": set(), "in_riichi": False,
                                    "riichi_tile": -1, "riichi_discards": set()}
            opp = opponents[actor]
            rt_idx = MJAI_TO_RT.get(e["pai"])
            if rt_idx is not None:
                opp["discards"].add(rt_idx)
                if opp["in_riichi"]:
                    opp["riichi_discards"].add(rt_idx)

        elif etype == "reach" and actor != player_id:
            if actor not in opponents:
                opponents[actor] = {"discards": set(), "in_riichi": False,
                                    "riichi_tile": -1, "riichi_discards": set()}
            opponents[actor]["in_riichi"] = True

        elif etype == "reach_accepted" and actor != player_id:
            # The tile used for riichi was the last dahai by this actor
            pass  # riichi_tile already captured if we track it

        if tiles_left <= target_tiles_left:
            break

    # For riichi_tile, find the last dahai before reach for each riichi'd opponent
    # Actually, re-scan to get the riichi tile properly
    for actor, opp in opponents.items():
        if not opp["in_riichi"]:
            continue
        # Find the dahai right before/at the reach event
        last_dahai_tile = -1
        for pos in range(start_pos + 1, end_pos):
            e = mjai_log_events[pos]
            if e.get("type") == "dahai" and e.get("actor") == actor:
                last_dahai_tile = MJAI_TO_RT.get(e["pai"], -1)
            if e.get("type") == "reach" and e.get("actor") == actor:
                opp["riichi_tile"] = last_dahai_tile
                break

    # Return only opponents that are in riichi
    return [opp for opp in opponents.values() if opp["in_riichi"]]


def get_opponent_discards(mjai_log_events, start_pos, end_pos, player_id, target_tiles_left):
    """Extract opponent discard pools (in mjai notation, ordered) up to a point.

    Returns list of dicts for opponents in riichi:
        {"seat": int, "discards": [mjai tiles], "riichi_idx": int (index in discards where riichi was declared)}
    Returns None if no opponents are in riichi.
    """
    opponents = {}  # actor -> {"discards": [], "in_riichi": False, "riichi_idx": None}
    tiles_left = 70

    for pos in range(start_pos + 1, end_pos):
        e = mjai_log_events[pos]
        etype = e.get("type")
        actor = e.get("actor")

        if etype == "tsumo":
            tiles_left -= 1

        elif etype == "dahai" and actor != player_id:
            if actor not in opponents:
                opponents[actor] = {"discards": [], "in_riichi": False, "riichi_idx": None}
            opponents[actor]["discards"].append(e["pai"])

        elif etype == "reach" and actor != player_id:
            if actor not in opponents:
                opponents[actor] = {"discards": [], "in_riichi": False, "riichi_idx": None}
            opp = opponents[actor]
            opp["in_riichi"] = True
            opp["riichi_idx"] = len(opp["discards"]) - 1  # last discard was the riichi tile

        if tiles_left <= target_tiles_left:
            break

    riichi_opps = []
    for actor, opp in opponents.items():
        if opp["in_riichi"]:
            riichi_opps.append({
                "seat": actor,
                "discards": opp["discards"],
                "riichi_idx": opp["riichi_idx"],
            })

    return riichi_opps if riichi_opps else None


def get_tile_safety_for_mistake(hand_mjai, mjai_log_events, start_pos, end_pos,
                                player_id, tiles_left, wall_remaining):
    """Get safety ratings for tiles in hand against all riichi'd opponents.

    Args:
        hand_mjai: list of mjai tile strings in player's hand
        mjai_log_events: flattened mjai_log events
        start_pos: position of start_kyoku event
        end_pos: position of next start_kyoku (or end of events)
        player_id: player's actor ID
        tiles_left: tiles remaining in wall at mistake time
        wall_remaining: list[37] of remaining tile counts (from reconstruct_context)

    Returns:
        dict mapping mjai tile -> average safety rating across riichi opponents,
        or None if no opponents are in riichi.
    """
    riichi_opps = extract_riichi_state(mjai_log_events, start_pos, end_pos,
                                       player_id, tiles_left)
    if not riichi_opps:
        return None

    # Convert hand to RT indices
    hand_rt = set()
    for t in hand_mjai:
        rt = MJAI_TO_RT.get(t)
        if rt is not None:
            hand_rt.add(rt)

    # Build remaining tiles array in RT format (38 elements)
    rt_remaining = [0] * 38
    # Map from our wall (37 elements: 0-33 base + 34-36 red) to RT format
    for mjai_tile, rt_idx in MJAI_TO_RT.items():
        if mjai_tile.endswith("r"):
            continue  # red fives share index with base
        from mj_categorize import MJAI_TO_ID
        base_id = MJAI_TO_ID.get(mjai_tile)
        if base_id is not None and base_id < len(wall_remaining):
            rt_remaining[rt_idx] = wall_remaining[base_id]

    # Average safety across all riichi opponents
    avg_safety = {}
    for rt_idx in hand_rt:
        total = 0
        for opp in riichi_opps:
            s = evaluate_safety(
                {rt_idx}, opp["discards"], rt_remaining,
                opp["riichi_discards"], opp["riichi_tile"]
            )
            total += s.get(rt_idx, 0)
        avg_safety[rt_idx] = total / len(riichi_opps)

    # Convert back to mjai notation
    result = {}
    rt_to_mjai = {}
    for t in hand_mjai:
        rt = MJAI_TO_RT.get(t)
        if rt is not None:
            rt_to_mjai[rt] = t
    for rt_idx, rating in avg_safety.items():
        mjai_tile = rt_to_mjai.get(rt_idx)
        if mjai_tile:
            result[mjai_tile] = rating

    return result
