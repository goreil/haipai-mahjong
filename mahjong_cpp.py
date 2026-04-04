#!/usr/bin/env python3
"""In-process wrapper for the mahjong-cpp tile efficiency calculator.

Loads libmahjongcpp.so via ctypes and calls the calculator directly,
replacing the old HTTP-based nanikiru server approach.

Usage (drop-in replacement for the old call_mahjong_cpp):

    from mahjong_cpp import calculate
    response = calculate(request_data)  # same dict format as before
"""

import ctypes
import json
import os
import sys
from pathlib import Path

DIR = Path(__file__).parent

# Search order for the shared library:
# 1. MAHJONG_CPP_LIB env var (explicit path)
# 2. Next to this Python file (production Docker layout)
# 3. Build directory (local dev)
_LIB_SEARCH = [
    os.environ.get("MAHJONG_CPP_LIB", ""),
    str(DIR / "libmahjongcpp.so"),
    str(DIR / "mahjong-cpp" / "build" / "libmahjongcpp.so"),
]

_lib = None


def _load_lib():
    """Load the shared library. Called once on first use."""
    global _lib
    for path in _LIB_SEARCH:
        if path and os.path.isfile(path):
            try:
                _lib = ctypes.CDLL(path)
                _lib.mahjong_calculate.restype = ctypes.c_char_p
                _lib.mahjong_calculate.argtypes = [ctypes.c_char_p]
                return
            except OSError as e:
                print(f"  mahjong_cpp: failed to load {path}: {e}", file=sys.stderr)
                continue
    raise RuntimeError(
        f"libmahjongcpp.so not found. Searched: {[p for p in _LIB_SEARCH if p]}"
    )


def calculate(request_data):
    """Calculate tile efficiency for a mahjong hand.

    Args:
        request_data: dict with the same format as the old nanikiru HTTP API
            (hand, melds, round_wind, seat_wind, dora_indicators, wall, etc.)

    Returns:
        dict: The "response" portion of the result (shanten, stats, time, config).

    Raises:
        RuntimeError: If the calculation fails (e.g. winning hand, invalid tiles).
    """
    if _lib is None:
        _load_lib()

    json_bytes = json.dumps(request_data, separators=(",", ":")).encode("utf-8")
    result_ptr = _lib.mahjong_calculate(json_bytes)
    result = json.loads(result_ptr.decode("utf-8"))

    if not result.get("success"):
        raise RuntimeError(f"mahjong-cpp error: {result.get('err_msg', 'unknown')}")

    return result["response"]
