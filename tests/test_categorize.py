#!/usr/bin/env python3
"""Tests for lib/categorize.py — categorization decision logic, labels, helpers."""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.categorize import (
    MJAI_TO_ID,
    ID_TO_MJAI,
    RED_TO_BASE,
    RULES,
    categorize_by_action_type,
    classify_efficiency,
    _classify_strategic,
    _cpp_reasonably_agrees,
    _is_terminal_mjai,
    _is_number_tile_mjai,
    _is_value_tile_mjai,
    _next_tile_mjai,
    compute_labels,
    extract_cpp_stats,
    is_honor_mjai,
    is_red_five_mjai,
    mjai_to_tile_id,
    tile_id_to_base,
)


# =========================================================================
# Helper functions: mjai_to_tile_id, tile_id_to_base
# =========================================================================

class TestMjaiToTileId:
    def test_man_tiles(self):
        for n in range(1, 10):
            assert mjai_to_tile_id(f"{n}m") == n - 1

    def test_pin_tiles(self):
        for n in range(1, 10):
            assert mjai_to_tile_id(f"{n}p") == 9 + n - 1

    def test_sou_tiles(self):
        for n in range(1, 10):
            assert mjai_to_tile_id(f"{n}s") == 18 + n - 1

    def test_honor_tiles(self):
        assert mjai_to_tile_id("E") == 27
        assert mjai_to_tile_id("S") == 28
        assert mjai_to_tile_id("W") == 29
        assert mjai_to_tile_id("N") == 30
        assert mjai_to_tile_id("P") == 31
        assert mjai_to_tile_id("F") == 32
        assert mjai_to_tile_id("C") == 33

    def test_red_fives(self):
        assert mjai_to_tile_id("5mr") == 34
        assert mjai_to_tile_id("5pr") == 35
        assert mjai_to_tile_id("5sr") == 36

    def test_unknown_tile_raises(self):
        with pytest.raises(KeyError):
            mjai_to_tile_id("XX")


class TestTileIdToBase:
    def test_red_fives_map_to_base(self):
        assert tile_id_to_base(34) == 4   # 5mr -> 5m
        assert tile_id_to_base(35) == 13  # 5pr -> 5p
        assert tile_id_to_base(36) == 22  # 5sr -> 5s

    def test_non_red_unchanged(self):
        assert tile_id_to_base(0) == 0
        assert tile_id_to_base(4) == 4
        assert tile_id_to_base(27) == 27
        assert tile_id_to_base(33) == 33


class TestTileNotationMaps:
    def test_round_trip(self):
        """Every tile in MJAI_TO_ID round-trips through ID_TO_MJAI."""
        for tile, tid in MJAI_TO_ID.items():
            assert ID_TO_MJAI[tid] == tile

    def test_all_ids_covered(self):
        """IDs 0-36 are all mapped."""
        for i in range(37):
            assert i in ID_TO_MJAI

    def test_red_to_base_consistency(self):
        assert RED_TO_BASE[MJAI_TO_ID["5mr"]] == MJAI_TO_ID["5m"]
        assert RED_TO_BASE[MJAI_TO_ID["5pr"]] == MJAI_TO_ID["5p"]
        assert RED_TO_BASE[MJAI_TO_ID["5sr"]] == MJAI_TO_ID["5s"]


# =========================================================================
# Tile type predicates
# =========================================================================

class TestTileHelpers:
    def test_is_honor(self):
        for t in ("E", "S", "W", "N", "P", "F", "C"):
            assert is_honor_mjai(t) is True
        assert is_honor_mjai("1m") is False
        assert is_honor_mjai("5mr") is False

    def test_is_terminal(self):
        for suit in "mps":
            assert _is_terminal_mjai(f"1{suit}") is True
            assert _is_terminal_mjai(f"9{suit}") is True
        assert _is_terminal_mjai("5m") is False
        assert _is_terminal_mjai("E") is False
        # Red fives and multi-char tiles
        assert _is_terminal_mjai("5mr") is False
        assert _is_terminal_mjai("5pr") is False

    def test_is_number_tile(self):
        for suit in "mps":
            for n in range(2, 9):
                assert _is_number_tile_mjai(f"{n}{suit}") is True
        # Terminals excluded
        assert _is_number_tile_mjai("1m") is False
        assert _is_number_tile_mjai("9s") is False
        # Honors excluded
        assert _is_number_tile_mjai("E") is False
        # Red fives excluded (3-char string)
        assert _is_number_tile_mjai("5mr") is False

    def test_is_value_tile(self):
        # Honors are value tiles
        assert _is_value_tile_mjai("E") is True
        assert _is_value_tile_mjai("C") is True
        # Terminals are value tiles
        assert _is_value_tile_mjai("1m") is True
        assert _is_value_tile_mjai("9s") is True
        # Number tiles are not
        assert _is_value_tile_mjai("5m") is False
        assert _is_value_tile_mjai("3p") is False

    def test_is_red_five(self):
        assert is_red_five_mjai("5mr") is True
        assert is_red_five_mjai("5pr") is True
        assert is_red_five_mjai("5sr") is True
        assert is_red_five_mjai("5m") is False
        assert is_red_five_mjai("E") is False


# =========================================================================
# categorize_by_action_type
# =========================================================================

class TestCategorizeByActionType:
    """Tests for categorize_by_action_type(actual, expected)."""

    # --- Meld decisions (4A-4C) ---

    def test_chi_none_returns_4A(self):
        assert categorize_by_action_type({"type": "chi"}, {"type": "none"}) == "4A"

    def test_pon_none_returns_4A(self):
        assert categorize_by_action_type({"type": "pon"}, {"type": "none"}) == "4A"

    def test_none_chi_returns_4B(self):
        assert categorize_by_action_type({"type": "none"}, {"type": "chi"}) == "4B"

    def test_none_pon_returns_4B(self):
        assert categorize_by_action_type({"type": "none"}, {"type": "pon"}) == "4B"

    def test_chi_chi_returns_4C(self):
        assert categorize_by_action_type({"type": "chi"}, {"type": "chi"}) == "4C"

    def test_pon_pon_returns_4C(self):
        assert categorize_by_action_type({"type": "pon"}, {"type": "pon"}) == "4C"

    def test_chi_pon_returns_4C(self):
        assert categorize_by_action_type({"type": "chi"}, {"type": "pon"}) == "4C"

    def test_pon_chi_returns_4C(self):
        assert categorize_by_action_type({"type": "pon"}, {"type": "chi"}) == "4C"

    # --- Riichi decisions (5A-5B) ---

    def test_reach_dahai_returns_5A(self):
        assert categorize_by_action_type({"type": "reach"}, {"type": "dahai"}) == "5A"

    def test_dahai_reach_returns_5B(self):
        assert categorize_by_action_type({"type": "dahai"}, {"type": "reach"}) == "5B"

    # --- Kan decisions (6A-6B) ---

    def test_bad_kan_all_types(self):
        for kan_type in ("ankan", "kakan", "daiminkan"):
            for expected in ("dahai", "none"):
                assert categorize_by_action_type({"type": kan_type}, {"type": expected}) == "6A"

    def test_missed_kan_all_types(self):
        for actual in ("dahai", "none"):
            for kan_type in ("ankan", "kakan", "daiminkan"):
                assert categorize_by_action_type({"type": actual}, {"type": kan_type}) == "6B"

    # --- Missed win ---

    def test_expected_hora_from_dahai_returns_3A(self):
        assert categorize_by_action_type({"type": "dahai"}, {"type": "hora"}) == "3A"

    def test_expected_hora_from_none_returns_3A(self):
        assert categorize_by_action_type({"type": "none"}, {"type": "hora"}) == "3A"

    def test_expected_hora_from_chi_returns_3A(self):
        """hora check happens after meld checks but before dahai-dahai."""
        # chi + hora doesn't match 4A (et != "none") or 4C (et not chi/pon),
        # so it falls through to hora check.
        assert categorize_by_action_type({"type": "chi"}, {"type": "hora"}) == "3A"

    # --- dahai vs dahai returns None ---

    def test_dahai_dahai_returns_none(self):
        assert categorize_by_action_type({"type": "dahai"}, {"type": "dahai"}) is None

    # --- Other combos default to 3A ---

    def test_reach_none_returns_3A(self):
        assert categorize_by_action_type({"type": "reach"}, {"type": "none"}) == "3A"

    def test_none_reach_returns_3A(self):
        assert categorize_by_action_type({"type": "none"}, {"type": "reach"}) == "3A"

    def test_reach_reach_returns_3A(self):
        assert categorize_by_action_type({"type": "reach"}, {"type": "reach"}) == "3A"


# =========================================================================
# classify_efficiency
# =========================================================================

class TestClassifyEfficiency:
    """Tests for classify_efficiency(mistake, cpp_stats)."""

    def _mistake(self, actual_pai, expected_pai):
        return {
            "actual": {"type": "dahai", "pai": actual_pai},
            "expected": {"type": "dahai", "pai": expected_pai},
        }

    def _make_cpp_stats(self, tile_scores):
        """Build minimal cpp_stats list from {tile: exp_score} dict."""
        return [
            {"tile": tile, "shanten": 0, "necessary_count": 10, "exp_score": score}
            for tile, score in tile_scores.items()
        ]

    def test_no_value_tile_returns_1A(self):
        """Two number tiles -> always 1A regardless of cpp scores."""
        m = self._mistake("3m", "5p")
        assert classify_efficiency(m, []) == "1A"

    def test_no_value_tile_close_scores_still_1A(self):
        m = self._mistake("3m", "5p")
        stats = self._make_cpp_stats({"3m": 1000, "5p": 1010})
        assert classify_efficiency(m, stats) == "1A"

    def test_honor_actual_close_scores_returns_2A(self):
        m = self._mistake("E", "3m")
        stats = self._make_cpp_stats({"E": 100, "3m": 140})
        assert classify_efficiency(m, stats) == "2A"

    def test_honor_expected_close_scores_returns_2A(self):
        m = self._mistake("3m", "N")
        stats = self._make_cpp_stats({"3m": 1000, "N": 1040})
        assert classify_efficiency(m, stats) == "2A"

    def test_terminal_actual_close_scores_returns_2A(self):
        m = self._mistake("1m", "5p")
        stats = self._make_cpp_stats({"1m": 100, "5p": 120})
        assert classify_efficiency(m, stats) == "2A"

    def test_terminal_expected_close_scores_returns_2A(self):
        m = self._mistake("5s", "9p")
        stats = self._make_cpp_stats({"5s": 1000, "9p": 1000})
        assert classify_efficiency(m, stats) == "2A"

    def test_value_tile_distant_scores_returns_1A(self):
        m = self._mistake("E", "3m")
        stats = self._make_cpp_stats({"E": 100, "3m": 500})
        assert classify_efficiency(m, stats) == "1A"

    def test_exact_threshold_returns_2A(self):
        threshold = RULES["value_tile_diff"]  # 60
        m = self._mistake("N", "2s")
        stats = self._make_cpp_stats({"N": 100, "2s": 100 + threshold})
        assert classify_efficiency(m, stats) == "2A"

    def test_one_over_threshold_returns_1A(self):
        threshold = RULES["value_tile_diff"]
        m = self._mistake("N", "2s")
        stats = self._make_cpp_stats({"N": 100, "2s": 100 + threshold + 1})
        assert classify_efficiency(m, stats) == "1A"

    def test_value_tile_no_cpp_stats_returns_1A(self):
        m = self._mistake("E", "3m")
        assert classify_efficiency(m, None) == "1A"
        assert classify_efficiency(m, []) == "1A"

    def test_value_tile_missing_from_cpp_stats_returns_1A(self):
        """If the value tile isn't found in cpp_stats, fall back to 1A."""
        m = self._mistake("E", "3m")
        stats = self._make_cpp_stats({"3m": 1000, "5p": 900})  # E not in stats
        assert classify_efficiency(m, stats) == "1A"

    def test_both_value_tiles_close_returns_2A(self):
        """Both tiles are value tiles (honor vs terminal), close scores."""
        m = self._mistake("P", "1s")
        stats = self._make_cpp_stats({"P": 800, "1s": 820})
        assert classify_efficiency(m, stats) == "2A"

    def test_red_five_tile_stripped_for_lookup(self):
        """Red five notation (5mr) should match 5m in cpp_stats via rstrip."""
        m = self._mistake("1m", "5mr")
        stats = self._make_cpp_stats({"1m": 1000, "5m": 1020})
        assert classify_efficiency(m, stats) == "2A"

    def test_all_dragons_are_value_tiles(self):
        for dragon in ("P", "F", "C"):
            m = self._mistake(dragon, "4s")
            stats = self._make_cpp_stats({dragon: 500, "4s": 530})
            assert classify_efficiency(m, stats) == "2A"

    def test_all_winds_are_value_tiles(self):
        for wind in ("E", "S", "W", "N"):
            m = self._mistake(wind, "4s")
            stats = self._make_cpp_stats({wind: 500, "4s": 530})
            assert classify_efficiency(m, stats) == "2A"


# =========================================================================
# _classify_strategic (mocked defense)
# =========================================================================

class TestClassifyStrategic:
    """Tests for _classify_strategic with mocked defense module."""

    def _make_mistake(self, expected_pai, actual_pai="3m", cpp_best=None):
        m = {
            "actual": {"type": "dahai", "pai": actual_pai},
            "expected": {"type": "dahai", "pai": expected_pai},
            "hand": ["1m", "2m", "3m"],
        }
        if cpp_best:
            m["cpp_best"] = cpp_best
        return m

    def _make_defense_ctx(self):
        return {
            "mjai_events": [],
            "start_pos": 0,
            "end_pos": 10,
            "player_id": 0,
        }

    @patch("lib.defense.get_tile_safety_for_mistake")
    def test_no_riichi_returns_3A(self, mock_safety):
        """When no opponent in riichi, safety is None -> 3A."""
        mock_safety.return_value = None
        mistake = self._make_mistake("E", cpp_best="3m")
        result = _classify_strategic(mistake, self._make_defense_ctx(), 50, [4] * 37)
        assert result == "3A"

    @patch("lib.defense.get_tile_safety_for_mistake")
    def test_defense_mortal_safer_returns_3B(self, mock_safety):
        """Mortal chose a significantly safer tile -> 3B."""
        gap = RULES["defense_safety_gap"]  # 3
        mock_safety.return_value = {"E": 10, "3m": 10 - gap}
        mistake = self._make_mistake("E", cpp_best="3m")
        result = _classify_strategic(mistake, self._make_defense_ctx(), 50, [4] * 37)
        assert result == "3B"

    @patch("lib.defense.get_tile_safety_for_mistake")
    def test_defense_not_enough_gap_returns_3A(self, mock_safety):
        """Safety gap below threshold -> 3A."""
        gap = RULES["defense_safety_gap"]
        mock_safety.return_value = {"E": 10, "3m": 10 - gap + 1}
        mistake = self._make_mistake("E", cpp_best="3m")
        result = _classify_strategic(mistake, self._make_defense_ctx(), 50, [4] * 37)
        assert result == "3A"

    @patch("lib.defense.get_tile_safety_for_mistake")
    def test_defense_exact_gap_returns_3B(self, mock_safety):
        """Safety gap exactly at threshold -> 3B (>=)."""
        gap = RULES["defense_safety_gap"]
        mock_safety.return_value = {"E": 8, "3m": 8 - gap}
        mistake = self._make_mistake("E", cpp_best="3m")
        result = _classify_strategic(mistake, self._make_defense_ctx(), 50, [4] * 37)
        assert result == "3B"

    @patch("lib.defense.get_tile_safety_for_mistake")
    def test_no_cpp_best_returns_3A(self, mock_safety):
        """No cpp_best in mistake -> stays 3A even with riichi."""
        mock_safety.return_value = {"E": 10, "3m": 2}
        mistake = self._make_mistake("E")  # no cpp_best
        result = _classify_strategic(mistake, self._make_defense_ctx(), 50, [4] * 37)
        assert result == "3A"

    @patch("lib.defense.get_tile_safety_for_mistake")
    def test_red_five_fallback_lookup(self, mock_safety):
        """Red five tile uses rstrip('r') fallback for safety lookup."""
        gap = RULES["defense_safety_gap"]
        mock_safety.return_value = {"5m": 12, "3m": 12 - gap}
        mistake = self._make_mistake("5mr", cpp_best="3m")
        result = _classify_strategic(mistake, self._make_defense_ctx(), 50, [4] * 37)
        assert result == "3B"

    @patch("lib.defense.get_tile_safety_for_mistake")
    def test_mortal_less_safe_returns_3A(self, mock_safety):
        """Mortal chose a LESS safe tile -> not defense -> 3A."""
        mock_safety.return_value = {"E": 3, "3m": 10}
        mistake = self._make_mistake("E", cpp_best="3m")
        result = _classify_strategic(mistake, self._make_defense_ctx(), 50, [4] * 37)
        assert result == "3A"

    @patch("lib.defense.get_tile_safety_for_mistake")
    def test_equal_safety_returns_3A(self, mock_safety):
        """Mortal and cpp have equal safety -> gap is 0, below threshold -> 3A."""
        mock_safety.return_value = {"E": 8, "3m": 8}
        mistake = self._make_mistake("E", cpp_best="3m")
        result = _classify_strategic(mistake, self._make_defense_ctx(), 50, [4] * 37)
        assert result == "3A"

    @patch("lib.defense.get_tile_safety_for_mistake")
    def test_large_gap_returns_3B(self, mock_safety):
        """Very large safety gap -> clearly 3B."""
        mock_safety.return_value = {"E": 15, "3m": 0}
        mistake = self._make_mistake("E", cpp_best="3m")
        result = _classify_strategic(mistake, self._make_defense_ctx(), 50, [4] * 37)
        assert result == "3B"

    @patch("lib.defense.get_tile_safety_for_mistake")
    def test_cpp_tile_missing_from_safety_defaults_to_zero(self, mock_safety):
        """If cpp_best tile isn't in safety dict, defaults to 0 via .get(tile, 0)."""
        mock_safety.return_value = {"E": 5}  # "3m" not in dict
        mistake = self._make_mistake("E", cpp_best="3m")
        result = _classify_strategic(mistake, self._make_defense_ctx(), 50, [4] * 37)
        # mortal_safety=5, cpp_safety=0, gap=5 >= 3
        assert result == "3B"


# =========================================================================
# _cpp_reasonably_agrees
# =========================================================================

class TestCppReasonablyAgrees:
    """Tests for _cpp_reasonably_agrees(mortal_tile_id, cpp_stats)."""

    def _make_stats(self, entries):
        """entries: list of (tile_mjai, shanten, exp_score_or_None, necessary_count)."""
        result = []
        for tile, shanten, exp_score, nec_count in entries:
            entry = {"tile": tile, "shanten": shanten, "necessary_count": nec_count}
            if exp_score is not None:
                entry["exp_score"] = exp_score
            result.append(entry)
        return result

    def test_empty_stats_returns_false(self):
        assert _cpp_reasonably_agrees(0, []) is False
        assert _cpp_reasonably_agrees(0, None) is False

    def test_tile_not_in_stats_returns_false(self):
        stats = self._make_stats([("1m", 1, 200, 10)])
        assert _cpp_reasonably_agrees(mjai_to_tile_id("2m"), stats) is False

    def test_same_shanten_close_score_returns_true(self):
        stats = self._make_stats([
            ("1m", 1, 200, 10),
            ("2m", 1, 180, 8),
        ])
        # diff=20, threshold=60
        assert _cpp_reasonably_agrees(mjai_to_tile_id("2m"), stats) is True

    def test_same_shanten_far_score_returns_false(self):
        stats = self._make_stats([
            ("1m", 1, 200, 10),
            ("2m", 1, 50, 8),
        ])
        # diff=150, threshold=60
        assert _cpp_reasonably_agrees(mjai_to_tile_id("2m"), stats) is False

    def test_different_shanten_returns_false(self):
        stats = self._make_stats([
            ("1m", 0, 200, 10),
            ("2m", 1, 200, 8),
        ])
        assert _cpp_reasonably_agrees(mjai_to_tile_id("2m"), stats) is False

    def test_exact_threshold_returns_true(self):
        threshold = RULES["agree_exp_score_diff"]  # 60
        stats = self._make_stats([
            ("1m", 1, 200, 10),
            ("2m", 1, 200 - threshold, 8),
        ])
        assert _cpp_reasonably_agrees(mjai_to_tile_id("2m"), stats) is True

    def test_one_over_threshold_returns_false(self):
        threshold = RULES["agree_exp_score_diff"]
        stats = self._make_stats([
            ("1m", 1, 200, 10),
            ("2m", 1, 200 - threshold - 1, 8),
        ])
        assert _cpp_reasonably_agrees(mjai_to_tile_id("2m"), stats) is False

    def test_fallback_necessary_count_above_ratio(self):
        """When no exp_score, falls back to necessary_count ratio."""
        ratio = RULES["agree_necessary_ratio"]  # 0.80
        top_nec = 10
        mortal_nec = int(top_nec * ratio)  # 8, exactly at threshold
        stats = self._make_stats([
            ("1m", 1, None, top_nec),
            ("2m", 1, None, mortal_nec),
        ])
        assert _cpp_reasonably_agrees(mjai_to_tile_id("2m"), stats) is True

    def test_fallback_necessary_count_below_ratio(self):
        ratio = RULES["agree_necessary_ratio"]
        top_nec = 10
        mortal_nec = int(top_nec * ratio) - 1  # 7
        stats = self._make_stats([
            ("1m", 1, None, top_nec),
            ("2m", 1, None, mortal_nec),
        ])
        assert _cpp_reasonably_agrees(mjai_to_tile_id("2m"), stats) is False

    def test_fallback_top_nec_zero_returns_false(self):
        stats = self._make_stats([
            ("1m", 1, None, 0),
            ("2m", 1, None, 0),
        ])
        assert _cpp_reasonably_agrees(mjai_to_tile_id("2m"), stats) is False

    def test_red_five_matches_base(self):
        """Red five (5mr, tile_id=34) should match base '5m' in stats."""
        stats = self._make_stats([
            ("5m", 1, 200, 10),
            ("3m", 1, 190, 8),
        ])
        assert _cpp_reasonably_agrees(mjai_to_tile_id("5mr"), stats) is True

    def test_mortal_is_top_tile_returns_true(self):
        """Mortal picked cpp's best tile -> 0 diff, always agrees."""
        stats = self._make_stats([
            ("3m", 1, 1000, 10),
            ("5p", 2, 500, 4),
        ])
        assert _cpp_reasonably_agrees(mjai_to_tile_id("3m"), stats) is True

    def test_mortal_scores_higher_than_top(self):
        """Mortal's tile scores higher (abs diff still within threshold)."""
        stats = self._make_stats([
            ("3m", 1, 1000, 10),
            ("5p", 1, 1050, 12),
        ])
        assert _cpp_reasonably_agrees(mjai_to_tile_id("5p"), stats) is True

    def test_honor_tile_agreement(self):
        stats = self._make_stats([
            ("E", 2, 500, 5),
            ("3m", 2, 480, 4),
        ])
        assert _cpp_reasonably_agrees(mjai_to_tile_id("3m"), stats) is True


# =========================================================================
# compute_labels
# =========================================================================

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
        labels = compute_labels(self._mistake("E", "S"), [])
        assert labels.count("honor") == 1

    def test_no_labels_for_plain_tiles(self):
        labels = compute_labels(self._mistake("3m", "5p"), [])
        assert labels == []


# =========================================================================
# _next_tile_mjai
# =========================================================================

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


# =========================================================================
# extract_cpp_stats
# =========================================================================

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
        assert result[0]["tile"] == "2m"
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
        assert result[0]["tile"] == "1m"
        assert result[0]["exp_score"] == 200.0

    def test_empty_stats(self):
        assert extract_cpp_stats({"stats": [], "config": {}}) == []
