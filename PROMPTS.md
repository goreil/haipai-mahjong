# Parallel Instance Prompts

Copy-paste these into separate Claude Code sessions. Each instance reads its own backlog doc, picks up open items, and works autonomously. The manager instance coordinates.

**Convention**: Commit messages use `[prefix]` tags. Run tests before committing.

---

## UX

You are the UX instance for the Haipai project. Your job is to fix open items in `UX-AUDIT.md`.

**Your files**: `static/app.js`, `static/style.css`, `static/index.html`. Do NOT edit Python files, Docker files, or CI workflows.

**Parallel instances are editing** (do NOT touch):
- `mj_parse.py`, `mj_categorize.py`, `db.py`, `app.py` (Bugs instance)
- `Dockerfile`, `docker-compose.yml`, `.github/`, `nginx.conf.template` (Infra instance)
- `cpp_cache.py`, mahjong-cpp integration (Pipeline instance)

**Workflow**:
1. Read `UX-AUDIT.md` and identify open (non-checkmarked) items
2. Work through them in priority order (HIGH > MEDIUM > LOW)
3. Read relevant source files before changing them
4. Run `python3 -m pytest tests/ -v` after changes
5. Commit with prefix: `[ux] Short description (issue numbers)`
6. Mark items as done in `UX-AUDIT.md` with ✅

---

## Bugs

You are the Bugs instance for the Haipai project. Your job is to fix open items in `BUGS.md`.

**Your files**: `mj_parse.py`, `mj_categorize.py`, `db.py`, `app.py`, `mj_games.py`. Do NOT edit frontend files (`static/`), Docker files, or CI workflows.

**Parallel instances are editing** (do NOT touch):
- `static/app.js`, `style.css`, `index.html` (UX instance)
- `Dockerfile`, `docker-compose.yml`, `.github/`, `nginx.conf.template` (Infra instance)
- `cpp_cache.py` (Pipeline instance)

**Important**: B-02 (red five double-decrement) is NOT a bug — it's intentional. Do not "fix" it.

**Workflow**:
1. Read `BUGS.md` and identify open (non-checkmarked) items
2. Work through them in priority order (CRITICAL > HIGH > MEDIUM > LOW)
3. Read relevant source files before changing them
4. Run `python3 -m pytest tests/ -v` after changes
5. Commit with prefix: `[bugs] Short description (B-XX)`
6. Mark items as done in `BUGS.md` with ✅

---

## Infra

You are the Infra instance for the Haipai project. Your job is to fix open items in `INFRA.md`.

**Your files**: `Dockerfile`, `docker-compose.yml`, `entrypoint.sh`, `nginx.conf.template`, `.github/workflows/`, `requirements.txt`, `ruff.toml`. Do NOT edit Python source files or frontend files.

**Exception**: If you need a minimal `/health` route in `app.py`, that's OK — but nothing else in app.py.

**Parallel instances are editing** (do NOT touch):
- `static/app.js`, `style.css`, `index.html` (UX instance)
- `mj_parse.py`, `mj_categorize.py`, `db.py`, `app.py` (Bugs instance)
- `cpp_cache.py` (Pipeline instance)

**Workflow**:
1. Read `INFRA.md` and identify open (non-checkmarked) items
2. Work through them in priority order (HIGH > MEDIUM > LOW)
3. Read relevant files before changing them
4. Run `python3 -m pytest tests/ -v` after changes
5. Commit with prefix: `[infra] Short description (I-XX)`
6. Mark items as done in `INFRA.md` with ✅

---

## Feedback

You are the Feedback instance for the Haipai project. Your job is to build the feedback pipeline from `FEEDBACK-PIPELINE.md`.

**Your files**: `app.py` (new admin routes only), `db.py` (feedback schema additions), `static/app.js` (admin view). Coordinate with UX instance if both editing frontend files — you own the admin view, they own everything else.

**Parallel instances may be editing** (do NOT touch):
- `mj_parse.py`, `mj_categorize.py` (Bugs/Pipeline instances)
- `Dockerfile`, `docker-compose.yml`, `.github/` (Infra instance)
- Review/practice/trend views in `app.js` (UX instance)

**Workflow**:
1. Read `FEEDBACK-PIPELINE.md` and identify open items
2. Work through them in priority order (HIGH > MEDIUM > LOW)
3. Read relevant source files before changing them
4. Run `python3 -m pytest tests/ -v` after changes
5. Commit with prefix: `[feedback] Short description (F-XX)`
6. Mark items as done in `FEEDBACK-PIPELINE.md` with ✅

---

## Landing

You are the Landing Page instance for the Haipai project. Your job is to build a public landing page from `LANDING-PAGE.md`.

**Your files**: `static/landing.html` (new file), `static/style.css` (landing-specific styles only — add at the bottom, don't reorganize existing styles), `app.py` (modify the `/` route to show landing for unauthenticated users).

**Parallel instances may be editing** (do NOT touch):
- `static/app.js` (UX/Feedback instances)
- `mj_parse.py`, `mj_categorize.py`, `db.py` (Bugs/Pipeline instances)
- `Dockerfile`, `docker-compose.yml`, `.github/` (Infra instance)

**Design notes**: The app uses vanilla JS, no framework. Keep the landing page simple HTML+CSS. Use tile SVGs from `riichi-mahjong-tiles/` for visual flair. Match the existing dark theme in `style.css`.

**Workflow**:
1. Read `LANDING-PAGE.md` and identify open items
2. Read `static/style.css` and `app.py` to understand the existing setup
3. Build the landing page
4. Run `python3 -m pytest tests/ -v` after changes
5. Commit with prefix: `[landing] Short description (L-XX)`
6. Mark items as done in `LANDING-PAGE.md` with ✅

---

## Anonymous Practice

You are the Anonymous Practice instance for the Haipai project. Your job is to build the anonymous practice feature from `ANON-PRACTICE.md`.

**Context**: Club members want to try the practice tool without creating an account. The goal is to pool all users' mistakes into an anonymized practice set, accessible without login. Progress tracking requires login.

**Your files**: `app.py` (new public practice route only), `db.py` (new anonymized practice query), `static/app.js` (practice view changes for anonymous mode), `static/landing.html` (CTA button).

**Parallel instances may be editing** (do NOT touch):
- `mj_parse.py`, `mj_categorize.py` (Bugs/Pipeline instances)
- `Dockerfile`, `docker-compose.yml`, `.github/` (Infra instance)
- Non-practice views in `app.js` (UX instance)

**Important**: Do NOT add a public result-recording endpoint. Anonymous users cannot save progress.

**Workflow**:
1. Read `ANON-PRACTICE.md` and work through items in priority order
2. Read `db.py:get_practice_problem()` to understand the existing pattern
3. Read `app.py` practice routes to understand the API shape
4. Run `python3 -m pytest tests/ -v` after changes
5. Commit with prefix: `[practice] Short description (AP-XX)`
6. Mark items as done in `ANON-PRACTICE.md` with ✅

---

## Pipeline

You are the Pipeline instance for the Haipai project. Your job is to **replace the nanikiru HTTP server** with direct in-process calls to mahjong-cpp. This is the #1 priority — the HTTP server crashes, silently fails, and makes game uploads slow and unreliable. Read `PIPELINE.md` for the full plan.

**Your files**: `mahjong-cpp/` (submodule — CMakeLists.txt, new bridge source), new `mahjong_cpp.py`, `cpp_cache.py`, `mj_categorize.py` (the `call_mahjong_cpp` function), `app.py` (nanikiru startup/shutdown removal), `Dockerfile` (build changes).

**Parallel instances may be editing** (do NOT touch):
- `static/app.js`, `style.css`, `index.html` (UX instance)
- `mj_parse.py`, `db.py` (Bugs instance)

**Workflow**:
1. Read `PIPELINE.md` and work through items in order (P-01 → P-02 → P-03 → P-04)
2. If the shared library approach (P-01/P-02) hits a wall, fall back to P-05 (batch API)
3. Run `python3 -m pytest tests/ -v` after changes
4. Commit with prefix: `[pipeline] Short description (P-XX)`
5. Mark items as done in `PIPELINE.md` with ✅
