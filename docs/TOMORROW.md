# Session Notes (2026-04-05)

## What got done today

### Parallel instances (4 total)

**Nanikiru pipeline** — Created `cpp_cache.py`: SQLite-backed cache for nanikiru API responses (SHA-256 keyed). Not yet integrated into `mj_categorize.py` (2-line change pending at the callsite).

**UX polish** (6 items) — Practice filtered to efficiency only (5a), "Push/Fold" renamed to "Complex Decision" (2b), severity filter banner (7b), riichi badge enlarged (9d), import button hidden when games exist (6a), "Calc agrees" checkbox removed (5b).
- Limitation: practice filter sends `calc_agree=1` which only matches 1A. Server-side change needed to also include 2A.

**Bug fixes** (8 items) — sys.exit→ValueError (B-01), input validation (B-03), atomic add_game (B-05), CATEGORIES from keys (B-04), failure reporting (B-06), DB indexes (B-08), backfill endpoint (B-09), json_set for data_json (B-07).

**Infrastructure** (10 items) — Removed --reload (I-01), /health endpoint (I-02), .env.example (I-04), nginx gzip+cache+HSTS (I-06/I-10), pinned images (I-05), ruff+coverage in CI (I-08), post-deploy health check (I-09), chown fix (I-12), pinned requirements (I-13).

### Still needs doing

1. **Integrate cpp_cache.py** — 2-line change in mj_categorize.py at the call_mahjong_cpp callsite. Commit with cpp_cache.py + .gitignore entry for cpp_cache.db.
2. **Push to origin** — 13+ commits ahead. This triggers deploy pipeline + recategorization.
3. **Verify HTTPS** on haipai.ylue.de. If cert issues: see nginx.conf.template, run certbot.
4. **Check category distribution** on server after recat. Spot-check ??? mistakes from games 33-34 for 2A vs 3A. If too few 2A: bump RULES["value_tile_diff"] from 60 to 100.
5. **Post Discord message** — invite codes ready (8 codes), draft below.
6. **Fix practice filter for 2A** — server-side: update the `calc_agree` filter logic to include 2A (Value Tile Ordering) alongside 1A.

### Remaining backlog (not urgent)

**docs/backlogs/UX-AUDIT.md** (5 open):
- 2c (LOW) — 2A group visual weight (design decision)
- 3c (LOW) — Scores buried in details
- 4b (LOW) — Mortal Q values opaque
- 6b (LOW) — Game numbering meaningless
- 8a (MEDIUM) — Onboarding JSON extraction fragile

**docs/backlogs/BUGS.md** (3 open):
- B-02 — Intentional behavior, investigate -1 edge cases separately
- B-10 (MEDIUM) — Negative wall counts silently clamped
- B-11 (LOW) — Dora indicator possibly double-counted in wall

**docs/backlogs/INFRA.md** (4 open):
- I-03 (HIGH) — No backup automation
- I-07 (MEDIUM) — Certbot renewal alerting
- I-11 (LOW) — No resource limits in docker-compose
- I-14/I-15 (LOW) — Deployment approval gate, fresh repo race condition

---

## Discord Draft

**Haipai — Mahjong Mistake Trainer**

Hey everyone! I've been building a tool to help study riichi mahjong mistakes and it's ready for beta testing.

**What it does:**
- Upload your Tenhou/MJS replay analysis from Mortal AI
- Auto-categorizes your mistakes (tile efficiency, value tiles, defense, melding, riichi, etc.)
- Practice mode: quiz yourself on your own past mistakes
- Trend tracking: see how your play improves over time

**Known issue:** Auto-categorization is a bit slow on the first upload and some mistakes may show up without a category. I'm actively fixing this — categories will fill in over the next few days as I push updates.

**How to get started:**
1. Go to **https://haipai.ylue.de**
2. Register with one of these invite codes (one per person, first come first served):
```
CsiTuDIAMs0
BdWiSd84sRw
qMBKe-6-XiI
aDgTfxcwU5s
8bXj6kOUh0o
1aQD3o_6M9c
DxUUQeKJr3A
-S7iMdqcrf
```
3. Run your replay through https://mjai.ekyu.moe, grab the JSON, and upload it

Feedback welcome — there's a feedback button in the app. This is a personal project so expect rough edges!
