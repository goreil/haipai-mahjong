#!/usr/bin/env python3
"""Comprehensive tests for lib/defense.py - suji-based tile safety evaluation."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.defense import (
    MJAI_TO_RT,
    _is_suji,
    evaluate_safety,
    extract_riichi_state,
    get_opponent_discards,
    get_tile_safety_for_mistake,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_remaining(overrides=None):
    """Return a remaining-tiles array (38 elements) with all counts at 4.

    overrides: dict of RT index -> count
    """
    rem = [4] * 38
    # Zero out unused indices
    for idx in (0, 10, 20, 30):
        rem[idx] = 0
    if overrides:
        for k, v in overrides.items():
            rem[k] = v
    return rem


# ---------------------------------------------------------------------------
# MJAI_TO_RT mapping
# ---------------------------------------------------------------------------

class TestMjaiToRT:
    def test_man_tiles(self):
        for i in range(1, 10):
            assert MJAI_TO_RT[f"{i}m"] == i

    def test_pin_tiles(self):
        for i in range(1, 10):
            assert MJAI_TO_RT[f"{i}p"] == i + 10

    def test_sou_tiles(self):
        for i in range(1, 10):
            assert MJAI_TO_RT[f"{i}s"] == i + 20

    def test_honor_tiles(self):
        assert MJAI_TO_RT["E"] == 31
        assert MJAI_TO_RT["S"] == 32
        assert MJAI_TO_RT["W"] == 33
        assert MJAI_TO_RT["N"] == 34
        assert MJAI_TO_RT["P"] == 35
        assert MJAI_TO_RT["F"] == 36
        assert MJAI_TO_RT["C"] == 37

    def test_red_fives_share_index(self):
        assert MJAI_TO_RT["5mr"] == MJAI_TO_RT["5m"]
        assert MJAI_TO_RT["5pr"] == MJAI_TO_RT["5p"]
        assert MJAI_TO_RT["5sr"] == MJAI_TO_RT["5s"]


# ---------------------------------------------------------------------------
# _is_suji
# ---------------------------------------------------------------------------

class TestIsSuji:
    """Test the suji safety check."""

    def test_terminal_1m_suji_when_4m_discarded(self):
        # 1m: suji_a = -2 (out of suit), suji_b = 4m
        # 4m discarded -> suji_b passes -> True
        remaining = _make_remaining()
        assert _is_suji(1, {4}, remaining, -1) is True

    def test_terminal_1m_not_suji_when_4m_not_discarded(self):
        remaining = _make_remaining()
        assert _is_suji(1, set(), remaining, -1) is False

    def test_terminal_9m_suji_when_6m_discarded(self):
        # 9m: suji_a = 6m, suji_b = 12 (out of suit)
        remaining = _make_remaining()
        assert _is_suji(9, {6}, remaining, -1) is True

    def test_terminal_9m_not_suji_without_6m(self):
        remaining = _make_remaining()
        assert _is_suji(9, set(), remaining, -1) is False

    def test_middle_tile_5m_suji_both_sides(self):
        # 5m: suji_a = 2m, suji_b = 8m; both need to pass
        remaining = _make_remaining()
        assert _is_suji(5, {2, 8}, remaining, -1) is True

    def test_middle_tile_5m_suji_one_side_only(self):
        remaining = _make_remaining()
        # Only 2m discarded, 8m not
        assert _is_suji(5, {2}, remaining, -1) is False

    def test_suji_passes_when_adjacent_remaining_zero(self):
        # 4m: suji_a = 1m. If remaining[2] (=1m+1=2m) == 0, a-side passes
        # suji_b = 7m; discarded -> b passes
        remaining = _make_remaining({2: 0})  # 2m remaining = 0
        assert _is_suji(4, {7}, remaining, -1) is True

    def test_suji_passes_when_suji_tile_plus2_remaining_zero(self):
        # 4m: suji_a = 1m. remaining[suji_a+2] = remaining[3] (3m)
        remaining = _make_remaining({3: 0})  # 3m remaining = 0
        assert _is_suji(4, {7}, remaining, -1) is True

    def test_suji_b_passes_when_adjacent_remaining_zero(self):
        # 4m: suji_b = 7m. remaining[suji_b-1]=remaining[6]=6m
        remaining = _make_remaining({6: 0})
        assert _is_suji(4, {1}, remaining, -1) is True

    def test_riichi_tile_blocks_suji_a(self):
        # 4m: suji_a = 1m. If riichi_tile == 1, suji blocked
        remaining = _make_remaining()
        assert _is_suji(4, {1, 7}, remaining, riichi_tile=1) is False

    def test_riichi_tile_blocks_suji_b(self):
        # 4m: suji_b = 7m. If riichi_tile == 7, suji blocked
        remaining = _make_remaining()
        assert _is_suji(4, {1, 7}, remaining, riichi_tile=7) is False

    def test_riichi_tile_no_effect_when_out_of_suit(self):
        # 1m: suji_a out of suit, riichi_tile on suji_a side irrelevant
        remaining = _make_remaining()
        assert _is_suji(1, {4}, remaining, riichi_tile=99) is True

    def test_pin_suit_suji(self):
        # 14 = 4p, suji_a = 11 = 1p, suji_b = 17 = 7p
        remaining = _make_remaining()
        assert _is_suji(14, {11, 17}, remaining, -1) is True

    def test_sou_suit_suji(self):
        # 25 = 5s, suji_a = 22 = 2s, suji_b = 28 = 8s
        remaining = _make_remaining()
        assert _is_suji(25, {22, 28}, remaining, -1) is True

    def test_cross_suit_boundary_rejected(self):
        # 2m (idx 2): suji_a = -1 which is out of suit -> a passes
        # suji_b = 5m; not discarded -> should fail
        remaining = _make_remaining()
        assert _is_suji(2, set(), remaining, -1) is False

    def test_tile_3_suji_a_is_0_out_of_suit(self):
        # 3m (idx 3): suji_a = 0 -> 0 % 10 == 0 -> out of suit
        # suji_b = 6m; discarded
        remaining = _make_remaining()
        assert _is_suji(3, {6}, remaining, -1) is True

    def test_tile_7_suji_b_is_10_out_of_suit(self):
        # 7m (idx 7): suji_b = 10 -> 10 % 10 == 0 -> out of suit
        # suji_a = 4m; discarded
        remaining = _make_remaining()
        assert _is_suji(7, {4}, remaining, -1) is True

    def test_tile_8_suji_b_crosses_suit(self):
        # 8m (idx 8): suji_b = 11 = 1p -> different suit (8//10=0 vs 11//10=1)
        # suji_a = 5m; discarded
        remaining = _make_remaining()
        assert _is_suji(8, {5}, remaining, -1) is True

    def test_tile_12_suji_a_crosses_suit(self):
        # 2p (idx 12): suji_a = 9 = 9m -> different suit (12//10=1 vs 9//10=0)
        # suji_b = 15 = 5p; discarded
        remaining = _make_remaining()
        assert _is_suji(12, {15}, remaining, -1) is True


# ---------------------------------------------------------------------------
# evaluate_safety
# ---------------------------------------------------------------------------

class TestEvaluateSafety:
    """Test the evaluate_safety function."""

    def test_genbutsu_in_opponent_discards(self):
        remaining = _make_remaining()
        result = evaluate_safety({1}, {1}, remaining, set(), -1)
        assert result[1] == 15

    def test_genbutsu_in_riichi_discards(self):
        remaining = _make_remaining()
        result = evaluate_safety({5}, set(), remaining, {5}, -1)
        assert result[5] == 15

    def test_terminal_with_suji(self):
        # 1m with 4m discarded -> suji terminal -> 14 - remaining[1]
        remaining = _make_remaining({1: 2})
        result = evaluate_safety({1}, {4}, remaining, set(), -1)
        assert result[1] == 14 - 2  # 12

    def test_terminal_without_suji(self):
        # 1m, no 4m discarded -> no suji -> 5
        remaining = _make_remaining()
        result = evaluate_safety({1}, set(), remaining, set(), -1)
        assert result[1] == 5

    def test_terminal_9p_with_suji(self):
        # 19 = 9p, suji_a = 16 = 6p
        remaining = _make_remaining({19: 1})
        result = evaluate_safety({19}, {16}, remaining, set(), -1)
        assert result[19] == 14 - 1  # 13

    def test_terminal_9s_without_suji(self):
        remaining = _make_remaining()
        result = evaluate_safety({29}, set(), remaining, set(), -1)
        assert result[29] == 5

    def test_honor_remaining_0(self):
        remaining = _make_remaining({31: 0})
        result = evaluate_safety({31}, set(), remaining, set(), -1)
        assert result[31] == 14

    def test_honor_remaining_1(self):
        remaining = _make_remaining({32: 1})
        result = evaluate_safety({32}, set(), remaining, set(), -1)
        assert result[32] == 13

    def test_honor_remaining_2(self):
        remaining = _make_remaining({35: 2})
        result = evaluate_safety({35}, set(), remaining, set(), -1)
        assert result[35] == 10

    def test_honor_remaining_3(self):
        remaining = _make_remaining({37: 3})
        result = evaluate_safety({37}, set(), remaining, set(), -1)
        assert result[37] == 6

    def test_honor_remaining_4(self):
        remaining = _make_remaining({36: 4})
        result = evaluate_safety({36}, set(), remaining, set(), -1)
        assert result[36] == 6

    def test_number_456_with_suji(self):
        # 5m (idx 5), suji: 2m and 8m discarded
        remaining = _make_remaining()
        result = evaluate_safety({5}, {2, 8}, remaining, set(), -1)
        assert result[5] == 9

    def test_number_456_without_suji(self):
        remaining = _make_remaining()
        result = evaluate_safety({5}, set(), remaining, set(), -1)
        assert result[5] == 1

    def test_number_28_with_suji(self):
        # 2m (idx 2), suji_a out of suit, suji_b = 5m discarded
        remaining = _make_remaining()
        result = evaluate_safety({2}, {5}, remaining, set(), -1)
        assert result[2] == 8

    def test_number_28_without_suji(self):
        remaining = _make_remaining()
        result = evaluate_safety({2}, set(), remaining, set(), -1)
        assert result[2] == 3

    def test_number_37_with_suji(self):
        # 3m (idx 3), suji_a out of suit (0), suji_b = 6m discarded
        remaining = _make_remaining()
        result = evaluate_safety({3}, {6}, remaining, set(), -1)
        assert result[3] == 7

    def test_number_37_without_suji(self):
        remaining = _make_remaining()
        result = evaluate_safety({3}, set(), remaining, set(), -1)
        assert result[3] == 2

    def test_number_4p_with_suji(self):
        # 14 = 4p, digit 4 -> 9 with suji
        remaining = _make_remaining()
        result = evaluate_safety({14}, {11, 17}, remaining, set(), -1)
        assert result[14] == 9

    def test_number_6s_without_suji(self):
        # 26 = 6s, digit 6 -> 1 without suji
        remaining = _make_remaining()
        result = evaluate_safety({26}, set(), remaining, set(), -1)
        assert result[26] == 1

    def test_number_8s_with_suji(self):
        # 28 = 8s, digit 8, suji_a = 25 = 5s discarded, suji_b = 31 (honor, out of suit)
        remaining = _make_remaining()
        result = evaluate_safety({28}, {25}, remaining, set(), -1)
        assert result[28] == 8

    def test_multiple_tiles_in_hand(self):
        remaining = _make_remaining({31: 0, 1: 3})
        result = evaluate_safety(
            {1, 5, 31},
            {4},  # 4m discarded -> 1m has suji
            remaining,
            set(),
            -1,
        )
        assert result[1] == 14 - 3  # terminal with suji, remaining 3
        assert result[5] == 1       # 5m no suji (only 2m or 8m needed)
        assert result[31] == 14     # honor remaining 0

    def test_genbutsu_takes_priority_over_other_logic(self):
        # Even though it's an honor with remaining 4, genbutsu = 15
        remaining = _make_remaining({33: 4})
        result = evaluate_safety({33}, {33}, remaining, set(), -1)
        assert result[33] == 15

    def test_empty_hand(self):
        remaining = _make_remaining()
        result = evaluate_safety(set(), set(), remaining, set(), -1)
        assert result == {}

    def test_riichi_tile_affects_suji(self):
        # 1m: suji_b = 4m. 4m discarded but also riichi_tile -> _is_suji returns False
        remaining = _make_remaining()
        result = evaluate_safety({1}, {4}, remaining, set(), riichi_tile=4)
        assert result[1] == 5  # terminal without suji


# ---------------------------------------------------------------------------
# extract_riichi_state
# ---------------------------------------------------------------------------

class TestExtractRiichiState:

    def _make_events(self, extra_events):
        """Wrap events with start_kyoku and end_kyoku markers."""
        events = [{"type": "start_kyoku"}] + extra_events + [{"type": "end_kyoku"}]
        return events

    def test_no_riichi_returns_empty(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "1m"},
        ])
        result = extract_riichi_state(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert result == []

    def test_single_opponent_riichi(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "3m"},
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "7p"},
            {"type": "reach", "actor": 1},
            {"type": "tsumo", "actor": 2},
            {"type": "dahai", "actor": 2, "pai": "9s"},
        ])
        result = extract_riichi_state(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert len(result) == 1
        opp = result[0]
        assert opp["in_riichi"] is True
        assert 3 in opp["discards"]   # 3m = RT 3
        assert 17 in opp["discards"]  # 7p = RT 17
        assert opp["riichi_tile"] == 17  # last dahai before reach

    def test_riichi_discards_tracked(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "5m"},
            {"type": "reach", "actor": 1},
            {"type": "reach_accepted", "actor": 1},
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "E"},
        ])
        result = extract_riichi_state(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert len(result) == 1
        opp = result[0]
        assert 31 in opp["riichi_discards"]  # E discarded after riichi
        assert 5 in opp["discards"]  # 5m in discards

    def test_own_riichi_ignored(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 0},
            {"type": "dahai", "actor": 0, "pai": "1m"},
            {"type": "reach", "actor": 0},
        ])
        result = extract_riichi_state(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert result == []

    def test_multiple_opponents_riichi(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "2m"},
            {"type": "reach", "actor": 1},
            {"type": "tsumo", "actor": 2},
            {"type": "dahai", "actor": 2, "pai": "9p"},
            {"type": "reach", "actor": 2},
        ])
        result = extract_riichi_state(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert len(result) == 2

    def test_tiles_left_cutoff(self):
        # 70 tiles initially, each tsumo decrements. With 10 tsumo events, tiles_left = 60.
        # If target_tiles_left = 65, should stop after 5 tsumos.
        events = self._make_events(
            [{"type": "tsumo", "actor": i % 4} for i in range(10)]
            + [{"type": "dahai", "actor": 1, "pai": "1m"},
               {"type": "reach", "actor": 1}]
        )
        # 10 tsumos -> tiles_left = 60 <= 65, so the loop breaks before reaching the reach
        result = extract_riichi_state(events, 0, len(events), player_id=0, target_tiles_left=65)
        assert result == []

    def test_red_five_in_discards(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "5mr"},
            {"type": "reach", "actor": 1},
        ])
        result = extract_riichi_state(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert len(result) == 1
        assert 5 in result[0]["discards"]  # 5mr maps to RT index 5 (same as 5m)
        assert result[0]["riichi_tile"] == 5


# ---------------------------------------------------------------------------
# get_opponent_discards
# ---------------------------------------------------------------------------

class TestGetOpponentDiscards:

    def _make_events(self, extra_events):
        events = [{"type": "start_kyoku"}] + extra_events + [{"type": "end_kyoku"}]
        return events

    def test_no_riichi_returns_none(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "1m"},
        ])
        result = get_opponent_discards(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert result is None

    def test_single_riichi_opponent(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "3s"},
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "7m"},
            {"type": "reach", "actor": 1},
        ])
        result = get_opponent_discards(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert result is not None
        assert len(result) == 1
        opp = result[0]
        assert opp["seat"] == 1
        assert opp["discards"] == ["3s", "7m"]
        assert opp["riichi_idx"] == 1  # riichi declared after 2nd discard (index 1)

    def test_own_riichi_ignored(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 0},
            {"type": "dahai", "actor": 0, "pai": "1s"},
            {"type": "reach", "actor": 0},
        ])
        result = get_opponent_discards(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert result is None

    def test_multiple_riichi_opponents(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "4m"},
            {"type": "reach", "actor": 1},
            {"type": "tsumo", "actor": 2},
            {"type": "dahai", "actor": 2, "pai": "E"},
            {"type": "reach", "actor": 2},
        ])
        result = get_opponent_discards(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert result is not None
        assert len(result) == 2
        seats = {r["seat"] for r in result}
        assert seats == {1, 2}

    def test_tiles_left_cutoff(self):
        events = self._make_events(
            [{"type": "tsumo", "actor": i % 4} for i in range(10)]
            + [{"type": "dahai", "actor": 1, "pai": "1m"},
               {"type": "reach", "actor": 1}]
        )
        result = get_opponent_discards(events, 0, len(events), player_id=0, target_tiles_left=65)
        assert result is None

    def test_discards_preserve_mjai_notation(self):
        """Discards should be in original mjai notation, not RT indices."""
        events = self._make_events([
            {"type": "tsumo", "actor": 3},
            {"type": "dahai", "actor": 3, "pai": "5mr"},
            {"type": "reach", "actor": 3},
        ])
        result = get_opponent_discards(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert result is not None
        assert result[0]["discards"] == ["5mr"]

    def test_riichi_idx_points_to_last_discard(self):
        """riichi_idx should be the index of the last discard (the riichi tile)."""
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "1m"},
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "2m"},
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "3m"},
            {"type": "reach", "actor": 1},
        ])
        result = get_opponent_discards(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert result[0]["riichi_idx"] == 2  # 0-indexed, 3rd discard


# ---------------------------------------------------------------------------
# get_tile_safety_for_mistake
# ---------------------------------------------------------------------------

class TestGetTileSafetyForMistake:

    def _make_events(self, extra_events):
        events = [{"type": "start_kyoku"}] + extra_events + [{"type": "end_kyoku"}]
        return events

    def _make_wall_remaining(self, overrides=None):
        """Return wall_remaining in MJAI_TO_ID format (37 elements)."""
        wall = [4] * 37
        if overrides:
            for k, v in overrides.items():
                wall[k] = v
        return wall

    def test_no_riichi_returns_none(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "1m"},
        ])
        wall = self._make_wall_remaining()
        result = get_tile_safety_for_mistake(
            ["2m", "3m"], events, 0, len(events),
            player_id=0, tiles_left=60, wall_remaining=wall,
        )
        assert result is None

    def test_basic_safety_with_riichi(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "4m"},
            {"type": "reach", "actor": 1},
        ])
        wall = self._make_wall_remaining()
        hand = ["1m", "5m", "E"]
        result = get_tile_safety_for_mistake(
            hand, events, 0, len(events),
            player_id=0, tiles_left=60, wall_remaining=wall,
        )
        assert result is not None
        # 1m: terminal, suji via 4m discarded -> 14 - remaining
        assert "1m" in result
        # E: honor, remaining 4 -> 6
        assert "E" in result
        assert result["E"] == 6

    def test_genbutsu_in_safety_result(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 2},
            {"type": "dahai", "actor": 2, "pai": "3s"},
            {"type": "reach", "actor": 2},
        ])
        wall = self._make_wall_remaining()
        hand = ["3s", "7m"]
        result = get_tile_safety_for_mistake(
            hand, events, 0, len(events),
            player_id=0, tiles_left=60, wall_remaining=wall,
        )
        assert result is not None
        assert result["3s"] == 15  # genbutsu

    def test_red_five_in_hand(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "2m"},
            {"type": "reach", "actor": 1},
        ])
        wall = self._make_wall_remaining()
        hand = ["5mr"]
        result = get_tile_safety_for_mistake(
            hand, events, 0, len(events),
            player_id=0, tiles_left=60, wall_remaining=wall,
        )
        assert result is not None
        # 5mr maps to RT 5 = 5m, a middle tile
        assert "5mr" in result

    def test_multiple_opponents_averaging(self):
        # Two opponents in riichi. Both discarded E -> genbutsu for both -> avg 15.
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "E"},
            {"type": "reach", "actor": 1},
            {"type": "tsumo", "actor": 2},
            {"type": "dahai", "actor": 2, "pai": "E"},
            {"type": "reach", "actor": 2},
        ])
        wall = self._make_wall_remaining()
        hand = ["E"]
        result = get_tile_safety_for_mistake(
            hand, events, 0, len(events),
            player_id=0, tiles_left=60, wall_remaining=wall,
        )
        assert result is not None
        assert result["E"] == 15.0

    def test_averaging_mixed_safety(self):
        # Opponent 1 discarded E (genbutsu=15), opponent 2 did not (honor remaining 4 -> 6)
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "E"},
            {"type": "reach", "actor": 1},
            {"type": "tsumo", "actor": 2},
            {"type": "dahai", "actor": 2, "pai": "1m"},
            {"type": "reach", "actor": 2},
        ])
        wall = self._make_wall_remaining()
        hand = ["E"]
        result = get_tile_safety_for_mistake(
            hand, events, 0, len(events),
            player_id=0, tiles_left=60, wall_remaining=wall,
        )
        assert result is not None
        # opp1: genbutsu -> 15, opp2: honor remaining 4 -> 6
        assert result["E"] == (15 + 6) / 2

    def test_empty_hand(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "1m"},
            {"type": "reach", "actor": 1},
        ])
        wall = self._make_wall_remaining()
        result = get_tile_safety_for_mistake(
            [], events, 0, len(events),
            player_id=0, tiles_left=60, wall_remaining=wall,
        )
        assert result is not None  # riichi exists, just no tiles
        assert result == {}


# ---------------------------------------------------------------------------
# Edge cases and integration
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_all_suit_boundaries(self):
        """Test that tiles at suit boundaries get correct ratings."""
        remaining = _make_remaining()
        # 9m=9, 1p=11, 9p=19, 1s=21, 9s=29 are all terminals
        for idx in [9, 11, 19, 21, 29]:
            result = evaluate_safety({idx}, set(), remaining, set(), -1)
            assert result[idx] == 5  # terminal without suji

    def test_all_456_tiles_suji_rating(self):
        """All 4/5/6 tiles across suits should get rating 9 with suji."""
        remaining = _make_remaining()
        # man 4=4, 5=5, 6=6; pin 14,15,16; sou 24,25,26
        for base in (0, 10, 20):
            for digit in (4, 5, 6):
                idx = base + digit
                # Build suji discards: need idx-3 and idx+3 (if in suit)
                discards = set()
                a, b = idx - 3, idx + 3
                if a // 10 == idx // 10 and a % 10 != 0:
                    discards.add(a)
                if b // 10 == idx // 10 and b % 10 != 0:
                    discards.add(b)
                result = evaluate_safety({idx}, discards, remaining, set(), -1)
                assert result[idx] == 9, f"Failed for RT index {idx}"

    def test_honor_not_genbutsu_boundary_at_31(self):
        """Index 30 is unused; honor tiles start at 31."""
        remaining = _make_remaining({31: 2})
        result = evaluate_safety({31}, set(), remaining, set(), -1)
        assert result[31] == 10  # honor remaining 2

    def test_terminal_with_suji_remaining_0(self):
        """Terminal with suji and remaining 0 -> 14."""
        remaining = _make_remaining({1: 0})
        result = evaluate_safety({1}, {4}, remaining, set(), -1)
        assert result[1] == 14

    def test_terminal_with_suji_remaining_4(self):
        """Terminal with suji and remaining 4 -> 10."""
        remaining = _make_remaining({1: 4})
        result = evaluate_safety({1}, {4}, remaining, set(), -1)
        assert result[1] == 10

    def test_riichi_tile_prevents_suji_for_middle_tile(self):
        """Middle tile where riichi_tile blocks suji should get non-suji rating."""
        remaining = _make_remaining()
        # 5m: suji needs 2m and 8m. Both discarded, but riichi_tile=2
        result = evaluate_safety({5}, {2, 8}, remaining, set(), riichi_tile=2)
        assert result[5] == 1  # non-suji 456

    def test_safety_dict_keys_match_hand(self):
        """Output dict should have exactly the tiles in hand."""
        remaining = _make_remaining()
        hand = {1, 5, 15, 31}
        result = evaluate_safety(hand, set(), remaining, set(), -1)
        assert set(result.keys()) == hand

    def test_1m_terminal_boundary(self):
        """1m is both a terminal and has suji only on one side (4m)."""
        remaining = _make_remaining({1: 0})
        # With 4m discarded -> suji -> 14 - 0 = 14
        result = evaluate_safety({1}, {4}, remaining, set(), -1)
        assert result[1] == 14

    def test_9s_terminal_boundary(self):
        """9s (idx 29) has suji only from 6s (idx 26)."""
        remaining = _make_remaining({29: 3})
        result = evaluate_safety({29}, {26}, remaining, set(), -1)
        assert result[29] == 14 - 3  # 11

    def test_both_genbutsu_sources(self):
        """Tile in both opponent_discards and riichi_discards is still 15."""
        remaining = _make_remaining()
        result = evaluate_safety({7}, {7}, remaining, {7}, -1)
        assert result[7] == 15

    def test_non_riichi_opponent_discards_dont_appear(self):
        """extract_riichi_state should only return opponents who declared riichi."""
        events = [{"type": "start_kyoku"},
                  {"type": "tsumo", "actor": 1},
                  {"type": "dahai", "actor": 1, "pai": "1m"},
                  {"type": "tsumo", "actor": 2},
                  {"type": "dahai", "actor": 2, "pai": "2m"},
                  {"type": "reach", "actor": 2},
                  {"type": "end_kyoku"}]
        result = extract_riichi_state(events, 0, len(events), player_id=0, target_tiles_left=60)
        assert len(result) == 1
        # Only actor 2 should be in the result
        assert result[0]["riichi_tile"] == 2  # 2m = RT 2
