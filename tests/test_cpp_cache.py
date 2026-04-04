#!/usr/bin/env python3
"""Tests for the mahjong-cpp API response cache."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch, tmp_path):
    """Point cpp_cache at a temp DB for every test."""
    import cpp_cache

    db_path = tmp_path / "test_cache.db"
    monkeypatch.setattr(cpp_cache, "_CACHE_DB", db_path)
    # Reset the module-level connection so it reconnects to the temp DB
    monkeypatch.setattr(cpp_cache, "_cache_conn", None)
    yield db_path


SAMPLE_REQUEST = {
    "enable_reddora": True,
    "enable_uradora": True,
    "enable_shanten_down": True,
    "enable_tegawari": True,
    "enable_riichi": False,
    "round_wind": 27,
    "seat_wind": 27,
    "dora_indicators": [10],
    "hand": [0, 1, 2, 9, 10, 11, 18, 19, 20, 27, 27, 28, 28],
    "melds": [],
    "wall": [2] * 34 + [1, 1, 1],
    "version": "0.9.1",
}

SAMPLE_RESPONSE = {
    "shanten": {"all": 0, "regular": 0, "seven_pairs": 3, "thirteen_orphans": 10},
    "stats": [
        {"tile": 0, "shanten": 0, "necessary_tiles": [{"tile": 1, "count": 2}]},
        {"tile": 27, "shanten": 0, "necessary_tiles": [{"tile": 28, "count": 1}]},
    ],
}


class TestCacheKeyDeterminism:
    def test_same_input_same_key(self):
        import cpp_cache

        k1 = cpp_cache._make_key(SAMPLE_REQUEST)
        k2 = cpp_cache._make_key(SAMPLE_REQUEST)
        assert k1 == k2

    def test_key_order_independent(self):
        """Dict key insertion order must not affect the hash."""
        import cpp_cache

        reversed_req = dict(reversed(list(SAMPLE_REQUEST.items())))
        assert cpp_cache._make_key(SAMPLE_REQUEST) == cpp_cache._make_key(reversed_req)

    def test_different_input_different_key(self):
        import cpp_cache

        other = {**SAMPLE_REQUEST, "seat_wind": 28}
        assert cpp_cache._make_key(SAMPLE_REQUEST) != cpp_cache._make_key(other)


class TestGetPut:
    def test_miss_returns_none(self):
        import cpp_cache

        assert cpp_cache.get(SAMPLE_REQUEST) is None

    def test_hit_after_put(self):
        import cpp_cache

        cpp_cache.put(SAMPLE_REQUEST, SAMPLE_RESPONSE)
        result = cpp_cache.get(SAMPLE_REQUEST)
        assert result == SAMPLE_RESPONSE

    def test_overwrite(self):
        import cpp_cache

        cpp_cache.put(SAMPLE_REQUEST, {"old": True})
        cpp_cache.put(SAMPLE_REQUEST, SAMPLE_RESPONSE)
        assert cpp_cache.get(SAMPLE_REQUEST) == SAMPLE_RESPONSE


class TestCachedCall:
    def test_cache_miss_calls_api(self, monkeypatch):
        """On miss, cached_call should call through to call_mahjong_cpp."""
        import cpp_cache

        called = []

        def fake_call(req):
            called.append(req)
            return SAMPLE_RESPONSE

        monkeypatch.setattr("mj_categorize.call_mahjong_cpp", fake_call)

        result = cpp_cache.cached_call(SAMPLE_REQUEST)
        assert result == SAMPLE_RESPONSE
        assert len(called) == 1

    def test_cache_hit_skips_api(self, monkeypatch):
        """On hit, the HTTP call should be skipped entirely."""
        import cpp_cache

        cpp_cache.put(SAMPLE_REQUEST, SAMPLE_RESPONSE)

        def should_not_be_called(req):
            raise AssertionError("API should not be called on cache hit")

        monkeypatch.setattr("mj_categorize.call_mahjong_cpp", should_not_be_called)

        result = cpp_cache.cached_call(SAMPLE_REQUEST)
        assert result == SAMPLE_RESPONSE


class TestStats:
    def test_empty_stats(self):
        import cpp_cache

        s = cpp_cache.stats()
        assert s["entries"] == 0

    def test_stats_after_puts(self):
        import cpp_cache

        cpp_cache.put(SAMPLE_REQUEST, SAMPLE_RESPONSE)
        cpp_cache.put({**SAMPLE_REQUEST, "seat_wind": 28}, SAMPLE_RESPONSE)
        s = cpp_cache.stats()
        assert s["entries"] == 2


class TestClear:
    def test_clear_empties_cache(self):
        import cpp_cache

        cpp_cache.put(SAMPLE_REQUEST, SAMPLE_RESPONSE)
        assert cpp_cache.get(SAMPLE_REQUEST) is not None
        cpp_cache.clear()
        assert cpp_cache.get(SAMPLE_REQUEST) is None
        assert cpp_cache.stats()["entries"] == 0
