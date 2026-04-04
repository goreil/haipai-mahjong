# Pipeline: Replace Nanikiru

The nanikiru HTTP server wrapping mahjong-cpp is the #1 reliability problem. It crashes under sustained load (both WSL and Hetzner), silently fails in local dev, and makes game uploads slow and unreliable. We own the mahjong-cpp fork — there's no reason to keep the HTTP layer.

## Current architecture

```
Python (mj_categorize.py)
  → HTTP POST to 127.0.0.1:50000
    → nanikiru (C++ HTTP server)
      → mahjong-cpp calculator
    → JSON response
  → parse response
```

Problems:
- nanikiru crashes under load, needs retry logic and restart wrappers
- 2 gunicorn workers each try to start nanikiru, only one gets the port
- Local dev (WSL) often has no running nanikiru — categorization silently fails
- Each mistake = 1 HTTP roundtrip with 10s timeout + 2 retries with 2s sleep = up to 16s on failure
- New Python modules (like cpp_cache.py) must be added to Dockerfile COPY list

## Target architecture

```
Python (mj_categorize.py)
  → call_mahjong_cpp(request_data)
    → C shared library (.so) via ctypes/cffi
    → mahjong-cpp calculator (in-process)
  → return result
```

No HTTP. No separate process. No port. No crashes. No retry logic.

---

## P-01: Build mahjong-cpp as shared library (HIGH)

**Current**: mahjong-cpp builds a static library + nanikiru CLI/server.

**Goal**: Also build a shared library (`libmahjongcpp.so`) that exposes the calculator function.

**Steps**:
- Identify the C++ function that nanikiru calls internally (the calculator entry point)
- Add a C-linkage wrapper: `extern "C" const char* calculate(const char* json_request)`
- Update CMakeLists.txt to build a shared library target alongside the existing targets
- Test: `python3 -c "import ctypes; lib = ctypes.CDLL('./libmahjongcpp.so'); print('loaded')"`

**Files**: `mahjong-cpp/CMakeLists.txt`, new file `mahjong-cpp/src/python_bridge.cpp`

---

## P-02: Python wrapper for shared library (HIGH)

**Goal**: Replace `call_mahjong_cpp()` HTTP calls with direct library calls.

**Steps**:
- Write `mahjong_cpp.py`: loads the .so, exposes `calculate(request_dict) -> response_dict`
- Handle JSON serialization (Python dict → JSON string → C → JSON string → Python dict)
- Drop-in replacement for the HTTP call — same input/output contract
- Replace `call_mahjong_cpp()` in `mj_categorize.py` to use the new module
- Remove or deprecate: nanikiru startup/shutdown in `app.py`, retry logic, port management

**Files**: New `mahjong_cpp.py`, `mj_categorize.py` (replace call_mahjong_cpp), `app.py` (remove nanikiru management)

---

## P-03: Update build and deploy (HIGH)

**Steps**:
- Dockerfile: build the .so in the build stage, copy it to the runtime stage
- Remove nanikiru binary from the Docker image (no longer needed)
- Add `mahjong_cpp.py` to the COPY list in Dockerfile
- Update `.env.example` to remove NANIKIRU_BIN
- Test locally and in Docker

**Files**: `Dockerfile`, `docker-compose.yml`, `.env.example`

---

## P-04: Remove nanikiru scaffolding (MEDIUM)

After P-01 through P-03 are verified working:
- Remove `start_nanikiru()`, `stop_nanikiru()`, atexit handler from `app.py`
- Remove `NANIKIRU_BIN`, `NANIKIRU_PORT`, `LOCAL_API_URL` from `app.py` and `mj_categorize.py`
- Remove retry logic from `call_mahjong_cpp()` (no longer needed — in-process calls don't have connection errors)
- Update CLAUDE.md "Local vs Production Differences" section
- Update tests if any mock the HTTP calls

**Files**: `app.py`, `mj_categorize.py`, `CLAUDE.md`

---

## P-05: Fallback — batch API (if shared library is too complex)

If building a shared library with C-linkage proves too difficult (complex C++ types, template-heavy API, etc.), the fallback is:

- Add a `/batch` endpoint to nanikiru: accepts array of requests, returns array of responses
- Modify `categorize_game_db()` to collect all requests first, send one batch call
- Reduces crash surface (1 connection instead of N) and latency (1 roundtrip instead of N)
- Still keeps the HTTP server, but makes it bearable

---

## P-06: Keep cache as safety net (LOW)

`cpp_cache.py` should stay even after the HTTP layer is removed. In-process calls are fast but the cache still helps:
- `--recheck` reruns don't recompute identical hands
- Development iteration (test categorization changes without recomputing everything)
- Update `cached_call()` to call the new in-process function instead of HTTP

---

## Notes

- The mahjong-cpp fork is at `mahjong-cpp/` (git submodule)
- Current API contract: POST JSON with `hand`, `melds`, `round_wind`, `seat_wind`, `dora`, `wall` → response with `result` array of discard options with scores
- The C++ codebase uses templates heavily — inspect the actual calculator API before deciding on ctypes vs cffi vs pybind11
- pybind11 is another option if ctypes/cffi can't handle the types cleanly
