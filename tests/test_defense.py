#!/usr/bin/env python3
"""Tests for lib/defense.py — safety evaluation, suji checks, riichi state extraction."""

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


# --- Helpers ---

def _empty_remaining():
    """38-element list with 4 copies of each tile (simplified)."""
    return [4] * 38


def _rt(tile):
    """Shorthand for MJAI_TO_RT lookup."""
    return MJAI_TO_RT[tile]


# --- _is_suji tests ---

class TestIsSuji:
    def test_suji_with_discarded_pair(self):
        """5m is suji-safe if 2m and 8m are both discarded."""
        discards = {_rt("2m"), _rt("8m")}
        remaining = _empty_remaining()
        assert _is_suji(_rt("5m"), discards, remaining, -1) is True

    def test_not_suji_missing_one_side(self):
        """5m is NOT suji if only 2m is discarded (8m missing)."""
        discards = {_rt("2m")}
        remaining = _empty_remaining()
        assert _is_suji(_rt("5m"), discards, remaining, -1) is False

    def test_terminal_1_suji(self):
        """1m: suji_a is out of suit (auto-pass), needs 4m discarded for suji_b."""
        discards = {_rt("4m")}
        remaining = _empty_remaining()
        assert _is_suji(_rt("1m"), discards, remaining, -1) is True

    def test_terminal_9_suji(self):
        """9s: suji_b is out of suit (auto-pass), needs 6s discarded for suji_a."""
        discards = {_rt("6s")}
        remaining = _empty_remaining()
        assert _is_suji(_rt("9s"), discards, remaining, -1) is True

    def test_terminal_not_suji(self):
        """1p without 4p discarded is not suji."""
        discards = set()
        remaining = _empty_remaining()
        assert _is_suji(_rt("1p"), discards, remaining, -1) is False

    def test_suji_blocked_by_riichi_tile(self):
        """If suji tile is the riichi declaration tile, not suji-safe."""
        discards = {_rt("2m"), _rt("8m")}
        remaining = _empty_remaining()
        # riichi_tile = 8m blocks the suji_b check
        assert _is_suji(_rt("5m"), discards, remaining, _rt("8m")) is False

    def test_suji_when_tiles_exhausted(self):
        """Suji passes if all copies of the waiting tile are gone (remaining=0)."""
        discards = set()
        remaining = _empty_remaining()
        # 4m's neighbors exhausted -> suji_a for 7m passes
        remaining[_rt("4m") + 1] = 0  # 5m remaining = 0
        remaining[_rt("4m") + 2] = 0  # 6m remaining = 0... actually let me rethink
        # For 3m: suji_a = 0m (out of suit, auto-pass), suji_b = 6m
        # 6m passes if 6m in discards OR remaining[6m-1]=0 OR remaining[6m-2]=0
        remaining[_rt("6m") - 1] = 0  # 5m
        assert _is_suji(_rt("3m"), set(), remaining, -1) is True


# --- evaluate_safety tests ---

class TestEvaluateSafety:
    def test_genbutsu_max_safety(self):
        """Tiles discarded by opponent (genbutsu) should be rated 15."""
        hand = {_rt("1m"), _rt("5p")}
        discards = {_rt("1m")}
        remaining = _empty_remaining()
        safety = evaluate_safety(hand, discards, remaining, set(), -1)
        assert safety[_rt("1m")] == 15

    def test_genbutsu_via_riichi_discards(self):
        """Tiles discarded after riichi are also genbutsu (safe)."""
        hand = {_rt("3s")}
        discards = set()
        riichi_discards = {_rt("3s")}
        remaining = _empty_remaining()
        safety = evaluate_safety(hand, discards, remaining, riichi_discards, -1)
        assert safety[_rt("3s")] == 15

    def test_honor_safety_by_remaining(self):
        """Honor tiles rated by remaining count: 0->14, 1->13, 2->10, 3->6."""
        remaining = _empty_remaining()
        for count, expected_rating in [(0, 14), (1, 13), (2, 10), (3, 6)]:
            remaining[_rt("E")] = count
            safety = evaluate_safety({_rt("E")}, set(), remaining, set(), -1)
            assert safety[_rt("E")] == expected_rating, f"remaining={count}"

    def test_terminal_suji_safety(self):
        """Terminal with suji: 14 - remaining."""
        remaining = _empty_remaining()
        remaining[_rt("1m")] = 2
        discards = {_rt("4m")}  # makes 1m suji-safe
        safety = evaluate_safety({_rt("1m")}, discards, remaining, set(), -1)
        assert safety[_rt("1m")] == 12  # 14 - 2

    def test_terminal_no_suji_safety(self):
        """Terminal without suji: rating 5."""
        remaining = _empty_remaining()
        safety = evaluate_safety({_rt("1m")}, set(), remaining, set(), -1)
        assert safety[_rt("1m")] == 5

    def test_middle_tile_suji_safety(self):
        """Middle tiles (4-6) with suji: rating 9."""
        remaining = _empty_remaining()
        discards = {_rt("2m"), _rt("8m")}
        safety = evaluate_safety({_rt("5m")}, discards, remaining, set(), -1)
        assert safety[_rt("5m")] == 9

    def test_middle_tile_no_suji_safety(self):
        """Middle tiles (4-6) without suji: rating 1."""
        remaining = _empty_remaining()
        safety = evaluate_safety({_rt("5m")}, set(), remaining, set(), -1)
        assert safety[_rt("5m")] == 1

    def test_edge_tile_suji_safety(self):
        """Edge tiles (2,8) with suji: rating 8."""
        remaining = _empty_remaining()
        discards = {_rt("5p")}  # makes 2p suji (suji_a out of suit, suji_b=5p discarded)
        safety = evaluate_safety({_rt("2p")}, discards, remaining, set(), -1)
        assert safety[_rt("2p")] == 8

    def test_edge_tile_no_suji_safety(self):
        """Edge tiles (2,8) without suji: rating 3."""
        remaining = _empty_remaining()
        safety = evaluate_safety({_rt("2p")}, set(), remaining, set(), -1)
        assert safety[_rt("2p")] == 3

    def test_number_37_suji_safety(self):
        """Tiles 3 and 7 with suji: rating 7."""
        remaining = _empty_remaining()
        discards = {_rt("6s"), _rt("4s")}  # makes 7s suji (suji_a=4s, suji_b out of suit... no, 7+3=10, out of suit)
        # Actually for 7s: suji_a = 4s, suji_b = 10s (out of suit, auto-pass)
        discards = {_rt("4s")}
        safety = evaluate_safety({_rt("7s")}, discards, remaining, set(), -1)
        assert safety[_rt("7s")] == 7

    def test_number_37_no_suji_safety(self):
        """Tiles 3 and 7 without suji: rating 2."""
        remaining = _empty_remaining()
        safety = evaluate_safety({_rt("3m")}, set(), remaining, set(), -1)
        assert safety[_rt("3m")] == 2

    def test_multiple_tiles_in_hand(self):
        """Safety is computed for every tile in hand."""
        hand = {_rt("1m"), _rt("5p"), _rt("E")}
        remaining = _empty_remaining()
        safety = evaluate_safety(hand, set(), remaining, set(), -1)
        assert len(safety) == 3
        assert all(0 <= v <= 15 for v in safety.values())


# --- extract_riichi_state tests ---

class TestExtractRiichiState:
    def _make_events(self, events):
        """Wrap events with a start_kyoku sentinel."""
        return [{"type": "start_kyoku"}] + events

    def test_no_riichi_returns_empty(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "1m"},
        ])
        result = extract_riichi_state(events, 0, len(events), 0, 60)
        assert result == []

    def test_single_opponent_riichi(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "3m"},
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "5p"},
            {"type": "reach", "actor": 1},
            {"type": "tsumo", "actor": 0},
        ])
        # tiles_left starts at 70, each tsumo decrements
        # 3 tsumos -> tiles_left = 67
        result = extract_riichi_state(events, 0, len(events), 0, 60)
        assert len(result) == 1
        opp = result[0]
        assert opp["in_riichi"] is True
        assert _rt("3m") in opp["discards"]
        assert _rt("5p") in opp["discards"]
        assert opp["riichi_tile"] == _rt("5p")  # last dahai before reach

    def test_ignores_player_riichi(self):
        """Player's own riichi should not appear in results."""
        events = self._make_events([
            {"type": "tsumo", "actor": 0},
            {"type": "dahai", "actor": 0, "pai": "1m"},
            {"type": "reach", "actor": 0},
        ])
        result = extract_riichi_state(events, 0, len(events), 0, 60)
        assert result == []

    def test_stops_at_tiles_left(self):
        """Should stop processing when tiles_left reaches target."""
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "1m"},
        ] * 5 + [
            {"type": "reach", "actor": 1},
        ])
        # 5 tsumos -> tiles_left = 65. If target is 66, we stop before riichi.
        result = extract_riichi_state(events, 0, len(events), 0, 66)
        assert result == []


# --- get_opponent_discards tests ---

class TestGetOpponentDiscards:
    def _make_events(self, events):
        return [{"type": "start_kyoku"}] + events

    def test_no_riichi_returns_none(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "1m"},
        ])
        result = get_opponent_discards(events, 0, len(events), 0, 60)
        assert result is None

    def test_riichi_returns_discards(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 2},
            {"type": "dahai", "actor": 2, "pai": "1m"},
            {"type": "tsumo", "actor": 2},
            {"type": "dahai", "actor": 2, "pai": "9s"},
            {"type": "reach", "actor": 2},
            {"type": "tsumo", "actor": 0},
        ])
        result = get_opponent_discards(events, 0, len(events), 0, 60)
        assert result is not None
        assert len(result) == 1
        assert result[0]["seat"] == 2
        assert result[0]["discards"] == ["1m", "9s"]
        assert result[0]["riichi_idx"] == 1  # riichi declared after 2nd discard


# --- get_tile_safety_for_mistake tests ---

class TestGetTileSafetyForMistake:
    def _make_events(self, events):
        return [{"type": "start_kyoku"}] + events

    def test_no_riichi_returns_none(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "1m"},
        ])
        wall = [4] * 37
        result = get_tile_safety_for_mistake(
            ["2m", "3m"], events, 0, len(events), 0, 60, wall
        )
        assert result is None

    def test_with_riichi_returns_ratings(self):
        events = self._make_events([
            {"type": "tsumo", "actor": 1},
            {"type": "dahai", "actor": 1, "pai": "1m"},
            {"type": "reach", "actor": 1},
            {"type": "tsumo", "actor": 0},
        ])
        wall = [4] * 37
        result = get_tile_safety_for_mistake(
            ["5m", "E"], events, 0, len(events), 0, 60, wall
        )
        assert result is not None
        assert "5m" in result or "E" in result
        assert all(0 <= v <= 15 for v in result.values())
