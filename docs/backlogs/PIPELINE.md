# Pipeline: Replace Nanikiru ✅ DONE

The nanikiru HTTP server has been replaced with an in-process shared library (`libmahjongcpp.so`).

## Architecture (current)

```
Python (mj_categorize.py)
  → call_mahjong_cpp(request_data)
    → mahjong_cpp.py (ctypes wrapper)
      → libmahjongcpp.so (in-process)
        → mahjong-cpp calculator
      → JSON response
    → return result
```

No HTTP. No separate process. No port. No crashes. No retry logic.

## What was done

- **P-01** ✅ Built mahjong-cpp as shared library
  - Created `mahjong-cpp/src/python_bridge.cpp` with `extern "C" mahjong_calculate()` 
  - Added `BUILD_PYTHON` CMake option to build `libmahjongcpp.so`
  - Changed `boost::dll::program_location()` → `this_line_location()` in core code so data files are found relative to the .so, not the Python interpreter
  - Data files (.bin, .json) are copied alongside the .so via CMake post-build step

- **P-02** ✅ Created Python wrapper
  - New `mahjong_cpp.py`: loads the .so via ctypes, same input/output contract
  - `mj_categorize.py`: `call_mahjong_cpp()` now calls `mahjong_cpp.calculate()` instead of HTTP POST
  - Removed `requests` import and HTTP retry logic from `mj_categorize.py`

- **P-03** ✅ Updated Dockerfile
  - Build stage: `cmake -DBUILD_PYTHON=ON -DBUILD_SERVER=OFF` → `make mahjong-python`
  - Runtime stage: installs `libboost-filesystem`, copies .so + data files to `/opt/mahjong-cpp/`
  - `MAHJONG_CPP_LIB` env var replaces `NANIKIRU_BIN`

- **P-04** ✅ Removed nanikiru scaffolding
  - Removed `start_nanikiru()`, `stop_nanikiru()`, atexit handler from `app.py`
  - Removed `NANIKIRU_BIN`, `NANIKIRU_PORT`, `LOCAL_API_URL` constants
  - Updated `CLAUDE.md` docs and `.env.example`

- **P-05** (skipped — shared library worked, fallback not needed)

- **P-06** ✅ Cache still works as-is
  - `cpp_cache.py` imports `call_mahjong_cpp` from `mj_categorize` which now uses in-process calls
  - No changes needed

## Build instructions (local dev)

```bash
cd mahjong-cpp
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_PYTHON=ON -DBUILD_SERVER=OFF -DBUILD_SAMPLES=OFF -DBUILD_TEST=OFF
make -j$(nproc) mahjong-python
```

The .so and data files will be in `mahjong-cpp/build/`. The Python wrapper auto-discovers them.

## Remaining: deploy and verify on server

This needs to be deployed and tested on the Hetzner server to verify:
- Docker build succeeds with the new Dockerfile
- libboost-filesystem runtime dependency is satisfied
- Categorization works end-to-end in production
