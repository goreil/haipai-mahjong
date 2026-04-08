#!/usr/bin/env python3
"""Tests for lib/categorize.py — categorization decision logic, labels, helpers."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.categorize import (
    RULES,
    categorize_by_action_type,
    classify_efficiency,
    _cpp_reasonably_agrees,
    _is_terminal_mjai,
    _is_number_tile_mjai,
    _is_value_tile_mjai,
    _next_tile_mjai,
    compute_labels,
    extract_cpp_stats,
    is_honor_mjai,
    is_red_five_mjai,
    tile_id_to_base,
)


# --- categorize_by_action_type tests ---

class TestCategorizeByActionType:
    def test_bad_meld_chi(self):
        assert categorize_by_action_type({"type": "chi"}, {"type": "none"}) == "4A"

    def test_bad_meld_pon(self):
        assert categorize_by_action_type({"type": "pon"}, {"type": "none"}) == "4A"

    def test_missed_meld_chi(self):
        assert categorize_by_action_type({"type": "none"}, {"type": "chi"}) == "4B"

    def test_missed_meld_pon(self):
        assert categorize_by_action_type({"type": "none"}, {"type": "pon"}) == "4B"

    def test_wrong_meld(self):
        assert categorize_by_action_type({"type": "chi"}, {"type": "pon"}) == "4C"

    def test_bad_riichi(self):
        assert categorize_by_action_type({"type": "reach"}, {"type": "dahai"}) == "5A"

    def test_missed_riichi(self):
        assert categorize_by_action_type({"type": "dahai"}, {"type": "reach"}) == "5B"

    def test_bad_kan(self):
        for kan_type in ("ankan", "kakan", "daiminkan"):
            for expected in ("dahai", "none"):
                assert categorize_by_action_type({"type": kan_type}, {"type": expected}) == "6A"

    def test_missed_kan(self):
        for actual in ("dahai", "none"):
            for kan_type in ("ankan", "kakan", "daiminkan"):
                assert categorize_by_action_type({"type": actual}, {"type": kan_type}) == "6B"

    def test_missed_win(self):
        assert categorize_by_action_type({"type": "none"}, {"type": "hora"}) == "3A"

    def test_dahai_vs_dahai_returns_none(self):
        assert categorize_by_action_type({"type": "dahai"}, {"type": "dahai"}) is None

    def test_other_combinations_default_3A(self):
        assert categorize_by_action_type({"type": "reach"}, {"type": "none"}) == "3A"


# --- classify_efficiency tests ---

class TestClassifyEfficiency:
    def _mistake(self, actual_pai, expected_pai):
        return {
            "actual": {"type": "dahai", "pai": actual_pai},
            "expected": {"type": "dahai", "pai": expected_pai},
        }

    def test_no_value_tile_returns_1A(self):
        """Two number tiles -> always 1A regardless of cpp scores."""
        m = self._mistake("3m", "5p")
        assert classify_efficiency(m, []) == "1A"

    def test_value_tile_close_scores_returns_2A(self):
        """Honor tile with close cpp scores -> 2A."""
        m = self._mistake("E", "3m")
        stats = [
            {"tile": "E", "shanten": 1, "necessary_count": 10, "exp_score": 100},
            {"tile": "3m", "shanten": 1, "necessary_count": 10, "exp_score": 140},
        ]
        assert classify_efficiency(m, stats) == "2A"

    def test_value_tile_distant_scores_returns_1A(self):
        """Honor tile but cpp scores far apart -> 1A."""
        m = self._mistake("E", "3m")
        stats = [
            {"tile": "E", "shanten": 1, "necessary_count": 10, "exp_score": 100},
            {"tile": "3m", "shanten": 1, "necessary_count": 10, "exp_score": 500},
        ]
        assert classify_efficiency(m, stats) == "1A"

    def test_terminal_is_value_tile(self):
        """Terminal (1m, 9s) counts as value tile."""
        m = self._mistake("1m", "5p")
        stats = [
            {"tile": "1m", "shanten": 1, "necessary_count": 10, "exp_score": 100},
            {"tile": "5p", "shanten": 1, "necessary_count": 10, "exp_score": 120},
        ]
        assert classify_efficiency(m, stats) == "2A"

    def test_value_tile_no_cpp_stats_returns_1A(self):
        """Value tile but no cpp_stats -> falls through to 1A."""
        m = self._mistake("E", "3m")
        assert classify_efficiency(m, None) == "1A"
        assert classify_efficiency(m, []) == "1A"

    def test_boundary_value_tile_diff(self):
        """Exactly at threshold -> 2A."""
        m = self._mistake("N", "2s")
        threshold = RULES["value_tile_diff"]
        stats = [
            {"tile": "N", "shanten": 1, "necessary_count": 10, "exp_score": 100},
            {"tile": "2s", "shanten": 1, "necessary_count": 10, "exp_score": 100 + threshold},
        ]
        assert classify_efficiency(m, stats) == "2A"

    def test_just_over_threshold_returns_1A(self):
        """One point over threshold -> 1A."""
        m = self._mistake("N", "2s")
        threshold = RULES["value_tile_diff"]
        stats = [
            {"tile": "N", "shanten": 1, "necessary_count": 10, "exp_score": 100},
            {"tile": "2s", "shanten": 1, "necessary_count": 10, "exp_score": 100 + threshold + 1},
        ]
        assert classify_efficiency(m, stats) == "1A"


# --- _cpp_reasonably_agrees tests ---

class TestCppReasonablyAgrees:
    def test_empty_stats(self):
        assert _cpp_reasonably_agrees(0, []) is False
        assert _cpp_reasonably_agrees(0, None) is False

    def test_same_shanten_close_score(self):
        stats = [
            {"tile": "1m", "shanten": 1, "necessary_count": 10, "exp_score": 200},
            {"tile": "2m", "shanten": 1, "necessary_count": 8, "exp_score": 180},
        ]
        # mortal picked 2m (tile_id=1), top is 1m. diff=20, threshold=60
        assert _cpp_reasonably_agrees(1, stats) is True

    def test_same_shanten_far_score(self):
        stats = [
            {"tile": "1m", "shanten": 1, "necessary_count": 10, "exp_score": 200},
            {"tile": "2m", "shanten": 1, "necessary_count": 8, "exp_score": 50},
        ]
        assert _cpp_reasonably_agrees(1, stats) is False

    def test_different_shanten(self):
        stats = [
            {"tile": "1m", "shanten": 0, "necessary_count": 10, "exp_score": 200},
            {"tile": "2m", "shanten": 1, "necessary_count": 8, "exp_score": 200},
        ]
        assert _cpp_reasonably_agrees(1, stats) is False

    def test_fallback_necessary_count(self):
        """When no exp_score, falls back to necessary_count ratio."""
        stats = [
            {"tile": "1m", "shanten": 1, "necessary_count": 10},
            {"tile": "2m", "shanten": 1, "necessary_count": 9},
        ]
        # 9/10 = 0.9 >= 0.8 threshold
        assert _cpp_reasonably_agrees(1, stats) is True

    def test_fallback_necessary_count_too_low(self):
        stats = [
            {"tile": "1m", "shanten": 1, "necessary_count": 10},
            {"tile": "2m", "shanten": 1, "necessary_count": 5},
        ]
        # 5/10 = 0.5 < 0.8 threshold
        assert _cpp_reasonably_agrees(1, stats) is False

    def test_red_five_matches_base(self):
        """Red five (tile_id 34 = 5mr) should match base 5m in stats."""
        stats = [
            {"tile": "5m", "shanten": 1, "necessary_count": 10, "exp_score": 200},
            {"tile": "3m", "shanten": 1, "necessary_count": 8, "exp_score": 190},
        ]
        # tile_id 34 = 5mr, base = 4 = 5m
        assert _cpp_reasonably_agrees(34, stats) is True

    def test_tile_not_in_stats(self):
        stats = [
            {"tile": "1m", "shanten": 1, "necessary_count": 10, "exp_score": 200},
        ]
        # tile_id 1 = 2m, not in stats
        assert _cpp_reasonably_agrees(1, stats) is False


# --- compute_labels tests ---

class TestComputeLabels:
    def _mistake(self, actual_pai, expected_pai):
        return {
            "actual": {"type": "dahai", "pai": actual_pai},
            "expected": {"type": "dahai", "pai": expected_pai},
        }

    def test_honor_label(self):
        labels = compute_labels(self._mistake("E", "3m"), [])
        assert "honor" in labels

    def test_terminal_label(self):
        labels = compute_labels(self._mistake("1m", "5p"), [])
        assert "terminal" in labels

    def test_dora_from_indicator(self):
        """Dora indicator 3m means 4m is dora."""
        labels = compute_labels(self._mistake("4m", "5p"), ["3m"])
        assert "dora" in labels

    def test_red_five_dora(self):
        labels = compute_labels(self._mistake("5mr", "3m"), [])
        assert "dora" in labels

    def test_yakuhai_dragon(self):
        labels = compute_labels(self._mistake("P", "3m"), [])
        assert "yakuhai" in labels

    def test_yakuhai_seat_wind(self):
        labels = compute_labels(self._mistake("S", "3m"), [], seat_wind="S")
        assert "yakuhai" in labels

    def test_yakuhai_round_wind(self):
        labels = compute_labels(self._mistake("E", "3m"), [], round_wind="E")
        assert "yakuhai" in labels

    def test_no_duplicate_labels(self):
        """Even if both tiles are honors, 'honor' should appear only once."""
        labels = compute_labels(self._mistake("E", "S"), [])
        assert labels.count("honor") == 1

    def test_no_labels_for_plain_tiles(self):
        labels = compute_labels(self._mistake("3m", "5p"), [])
        assert labels == []


# --- _next_tile_mjai tests ---

class TestNextTileMjai:
    def test_number_wraps(self):
        assert _next_tile_mjai("9m") == "1m"
        assert _next_tile_mjai("9p") == "1p"
        assert _next_tile_mjai("9s") == "1s"

    def test_number_increments(self):
        assert _next_tile_mjai("3m") == "4m"
        assert _next_tile_mjai("1p") == "2p"

    def test_wind_cycle(self):
        assert _next_tile_mjai("E") == "S"
        assert _next_tile_mjai("N") == "E"

    def test_dragon_cycle(self):
        assert _next_tile_mjai("P") == "F"
        assert _next_tile_mjai("C") == "P"

    def test_red_five_indicator(self):
        assert _next_tile_mjai("5mr") == "6m"


# --- Tile helper tests ---

class TestTileHelpers:
    def test_is_honor(self):
        for t in ("E", "S", "W", "N", "P", "F", "C"):
            assert is_honor_mjai(t) is True
        assert is_honor_mjai("1m") is False

    def test_is_terminal(self):
        assert _is_terminal_mjai("1m") is True
        assert _is_terminal_mjai("9s") is True
        assert _is_terminal_mjai("5m") is False
        assert _is_terminal_mjai("E") is False

    def test_is_number_tile(self):
        assert _is_number_tile_mjai("5m") is True
        assert _is_number_tile_mjai("1m") is False  # terminal, not "number"
        assert _is_number_tile_mjai("E") is False

    def test_is_value_tile(self):
        assert _is_value_tile_mjai("E") is True
        assert _is_value_tile_mjai("1m") is True
        assert _is_value_tile_mjai("5m") is False

    def test_is_red_five(self):
        assert is_red_five_mjai("5mr") is True
        assert is_red_five_mjai("5pr") is True
        assert is_red_five_mjai("5sr") is True
        assert is_red_five_mjai("5m") is False


# --- extract_cpp_stats tests ---

class TestExtractCppStats:
    def test_basic_extraction(self):
        response = {
            "stats": [
                {"tile": 0, "shanten": 1, "necessary_tiles": [{"tile": 1, "count": 3}]},
                {"tile": 1, "shanten": 1, "necessary_tiles": [{"tile": 2, "count": 4}]},
            ],
            "config": {"calc_stats": False},
        }
        result = extract_cpp_stats(response)
        assert len(result) == 2
        # Sorted by shanten asc, necessary_count desc -> tile 1 (count=4) first
        assert result[0]["tile"] == "2m"  # tile 1 -> 2m, count=4
        assert result[0]["necessary_count"] == 4

    def test_with_exp_score_sorting(self):
        response = {
            "stats": [
                {"tile": 1, "shanten": 1, "necessary_tiles": [{"tile": 2, "count": 3}],
                 "exp_score": [100.0], "win_prob": [0.5]},
                {"tile": 0, "shanten": 1, "necessary_tiles": [{"tile": 1, "count": 4}],
                 "exp_score": [200.0], "win_prob": [0.8]},
            ],
            "config": {"calc_stats": True},
        }
        result = extract_cpp_stats(response)
        # Sorted by shanten asc, exp_score desc
        assert result[0]["tile"] == "1m"  # tile 0, exp_score 200
        assert result[0]["exp_score"] == 200.0

    def test_empty_stats(self):
        assert extract_cpp_stats({"stats": [], "config": {}}) == []
