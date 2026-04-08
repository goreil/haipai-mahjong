#!/usr/bin/env python3
"""Tests for lib/parse.py — format_action and parse_game error handling."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.parse import format_action, parse_game, severity, round_header


# --- format_action tests ---

class TestFormatAction:
    def test_dahai(self):
        assert format_action({"type": "dahai", "pai": "5m"}) == "5m"

    def test_chi(self):
        result = format_action({"type": "chi", "consumed": ["3m", "4m"], "pai": "5m"})
        assert result == "chi 3m4m+5m"

    def test_pon(self):
        result = format_action({"type": "pon", "consumed": ["E", "E"], "pai": "E"})
        assert result == "pon EE+E"

    def test_reach(self):
        assert format_action({"type": "reach"}) == "riichi"

    def test_hora(self):
        assert format_action({"type": "hora"}) == "win"

    def test_none(self):
        assert format_action({"type": "none"}) == "pass"

    def test_ankan(self):
        result = format_action({"type": "ankan", "consumed": ["N"]})
        assert result == "ankan N"

    def test_unknown_type(self):
        assert format_action({"type": "kakan"}) == "kakan"

    def test_missing_type(self):
        assert format_action({}) == "?"


# --- parse_game error handling tests ---

class TestParseGameErrors:
    def test_not_a_dict(self):
        with pytest.raises(ValueError, match="Expected a JSON object"):
            parse_game([], game_date="2026-01-01")

    def test_missing_review(self):
        with pytest.raises(ValueError, match="Missing or invalid 'review'"):
            parse_game({"mjai_log": []}, game_date="2026-01-01")

    def test_review_not_dict(self):
        with pytest.raises(ValueError, match="Missing or invalid 'review'"):
            parse_game({"review": "bad", "mjai_log": []}, game_date="2026-01-01")

    def test_missing_kyokus(self):
        with pytest.raises(ValueError, match="Missing or invalid 'review.kyokus'"):
            parse_game({"review": {}, "mjai_log": []}, game_date="2026-01-01")

    def test_missing_mjai_log(self):
        with pytest.raises(ValueError, match="Missing or invalid 'mjai_log'"):
            parse_game({"review": {"kyokus": []}}, game_date="2026-01-01")

    def test_mismatched_kyoku_count(self):
        data = {
            "review": {"kyokus": [{"entries": []}, {"entries": []}]},
            "mjai_log": [{"type": "start_kyoku", "bakaze": "E", "kyoku": 1, "honba": 0}],
        }
        with pytest.raises(ValueError, match="2 review kyokus but 1 start_kyoku"):
            parse_game(data, game_date="2026-01-01")

    def test_valid_empty_game(self):
        """A game with zero kyokus should parse successfully."""
        data = {
            "review": {"kyokus": []},
            "mjai_log": [],
        }
        game = parse_game(data, game_date="2026-01-01")
        assert game["rounds"] == []
        assert game["date"] == "2026-01-01"

    def test_malformed_entry(self):
        """Missing details field should raise ValueError."""
        data = {
            "review": {"kyokus": [{
                "entries": [{
                    "is_equal": False,
                    "junme": 1,
                    "tiles_left": 60,
                    "state": {"tehai": [], "fuuros": []},
                    "actual": {"type": "dahai", "pai": "1m"},
                    "expected": {"type": "dahai", "pai": "2m"},
                    "actual_index": 1,
                    # missing "details"
                }],
            }]},
            "mjai_log": [{"type": "start_kyoku", "bakaze": "E", "kyoku": 1, "honba": 0}],
        }
        with pytest.raises(ValueError, match="Malformed entry"):
            parse_game(data, game_date="2026-01-01")
