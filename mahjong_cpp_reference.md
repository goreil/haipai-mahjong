# mahjong-cpp Submodule Reference

## Overview

C++ library for Riichi Mahjong analysis. Git submodule at `mahjong-cpp/`, origin `git@github.com:goreil/mahjong-cpp.git`.

## Core calculators (`src/mahjong/core/`)

- `ShantenCalculator::calc()` — distance from tenpai/win
- `NecessaryTileCalculator::select()` — tiles that improve the hand
- `UnnecessaryTileCalculator::select()` — tiles safe to discard
- `ScoreCalculator::calc()` — full scoring with yaku detection
- `ExpectedScoreCalculator::calc()` — win/tenpai probabilities and expected scores per discard

## Tile notation (MPSZ format)

`1m`–`9m` manzu, `1p`–`9p` pinzu, `1s`–`9s` souzu, `1z`–`7z` honors, `0m/0p/0s` red fives.
Parsing: `from_mpsz(string)` → Hand, `to_mpsz(hand)` → string.

## Types (`src/mahjong/types/`)

`Player` (hand, wind, melds), `Round` (wind, dora_indicators, rules), `Meld`, `Block`, result types.

## JSON server (`src/server/`)

HTTP server (Boost.Beast + RapidJSON) accepting JSON requests for expected score calculations. Schema at `data/config/request_schema.json`. Key request fields: `hand` (tile IDs), `melds`, `round_wind`, `seat_wind`, `dora_indicators`, `enable_reddora`, `enable_uradora`.

## Build

C++17, CMake. Dependencies: Boost, RapidJSON (fetched if missing), spdlog.
Options: `BUILD_SERVER` (ON), `BUILD_SAMPLES` (ON), `BUILD_TEST` (OFF), `LANG_EN` (OFF).
Pre-computed lookup tables in `data/config/` (suits_table.bin 17MB, honors_table.bin 1.8MB).

## What it does NOT do

No Tenhou log parsing. No Mortal AI integration. No mjai format handling. It's a pure calculation library.
