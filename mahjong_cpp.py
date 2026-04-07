#!/usr/bin/env python3
"""HTTP client for the nanikiru mahjong-cpp tile efficiency server.

Usage:
    from mahjong_cpp import calculate
    response = calculate(request_data)
"""

import json
import os
import socket
import sys
import time
import urllib.request
import urllib.error

NANIKIRU_URL = os.environ.get("NANIKIRU_URL", "http://localhost:50000/")

# Parse host/port from URL for health checks
_url_parts = NANIKIRU_URL.replace("http://", "").rstrip("/").split(":")
_NANIKIRU_HOST = _url_parts[0]
_NANIKIRU_PORT = int(_url_parts[1]) if len(_url_parts) > 1 else 50000


def _wait_for_server(timeout=20):
    """Wait for nanikiru to be ready to serve requests."""
    deadline = time.time() + timeout
    # First wait for TCP port
    while time.time() < deadline:
        try:
            s = socket.create_connection((_NANIKIRU_HOST, _NANIKIRU_PORT), timeout=2)
            s.close()
            break
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    else:
        return False

    # Then verify it can actually handle a request (tables loaded)
    test_req = json.dumps({
        "hand": [0,1,2,9,10,11,18,19,20,27,28,29,30],
        "melds": [], "round_wind": 27, "seat_wind": 27,
        "dora_indicators": [0],
        "enable_reddora": True, "enable_uradora": True,
        "enable_shanten_down": True, "enable_tegawari": True,
        "enable_riichi": False, "version": "0.9.1"
    }).encode("utf-8")
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                NANIKIRU_URL, data=test_req,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read())
                if result.get("success"):
                    return True
        except Exception:
            time.sleep(1)
    return False


def calculate(request_data):
    """Calculate tile efficiency for a mahjong hand via nanikiru HTTP server.

    The nanikiru server may crash on certain inputs. Docker auto-restarts it.
    This function retries with server health checks between attempts.

    Returns:
        dict: The "response" portion of the result (shanten, stats, time, config).

    Raises:
        RuntimeError: If the calculation fails or server is unreachable.
    """
    # Strip null values — nanikiru's JSON schema rejects null fields
    cleaned = {k: v for k, v in request_data.items() if v is not None}
    json_bytes = json.dumps(cleaned, separators=(",", ":")).encode("utf-8")

    for attempt in range(4):
        if attempt > 0:
            # Server may have crashed — wait for Docker to restart it
            if not _wait_for_server():
                raise RuntimeError("nanikiru server did not restart in time")
            # Extra pause after server comes up to let it fully initialize
            time.sleep(0.5)

        try:
            req = urllib.request.Request(
                NANIKIRU_URL,
                data=json_bytes,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            if not result.get("success"):
                raise RuntimeError(f"mahjong-cpp error: {result.get('err_msg', 'unknown')}")

            return result["response"]

        except RuntimeError:
            raise  # Don't retry application-level errors (bad input, winning hand)
        except Exception as e:
            if attempt == 3:
                raise RuntimeError(f"nanikiru unreachable after retries: {e}")

    raise RuntimeError("nanikiru unreachable after retries")
