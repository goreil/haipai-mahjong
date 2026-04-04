# Haipai Roadmap

## Competitive Landscape (researched 2026-03-31)

What English riichi players have today:
- **Mortal** (mjai.ekyu.moe): free per-turn AI review, but raw viewer only. No categorization, no practice mode, no trend tracking.
- **NAGA**: paid replay analysis, needs Nicovideo account + Japanese knowledge. Inaccessible to most English speakers.
- **Akochan Reviewer**: CLI tool, static HTML output, no web UI, no taxonomy.
- **Euophrys' Efficiency Trainer** (itch.io): generic random hands, not your own games.
- **Riichi Scoring/Waits Trainers**: specific skill drills, no game review.

**Our differentiation**: Mortal tells you WHAT you did wrong. Haipai tells you WHY, tracks it over time, and lets you drill your actual weak spots.

---

## Phase 1: Beta Launch (this week)

Goal: Get 8 club members using the app and giving useful feedback.

### Replace Nanikiru (BLOCKING — highest priority)
The nanikiru HTTP server is the single biggest reliability and UX problem. It crashes under load, silently fails in local dev (so bugs go unnoticed), adds seconds per mistake during categorization, and makes the first game upload painfully slow. The cache (`cpp_cache.py`) only helps reruns — every new game still hits this.

**The goal is to eliminate the HTTP server entirely.** We own the mahjong-cpp fork. Options in order of preference:

1. **Python C extension / ctypes / cffi** — Call the mahjong-cpp calculator directly from Python. No HTTP, no process management, no port conflicts, no crashes. This is the endgame.
   - Build a shared library (.so) from mahjong-cpp
   - Write a thin Python wrapper (ctypes or cffi) that calls the calculator function
   - Replace `call_mahjong_cpp()` in `mj_categorize.py`
   - Eliminates: nanikiru process, retry logic, port management, timeout handling

2. **Batch API** — If option 1 is too complex, add a batch endpoint to nanikiru that accepts N hands in one request. Reduces crashes (fewer connections) and overhead (one process startup). But still HTTP, still a separate process.

3. **subprocess per call** — Run nanikiru as a CLI tool (stdin→stdout) instead of HTTP server. No port conflicts, no crash recovery needed. Simpler than option 1 but slower.

**Why this is Phase 1**: A beta tester uploads their first game. It takes 30+ seconds and half the mistakes come back uncategorized. They don't come back. Everything else (feedback pipeline, landing page, social features) is irrelevant if the core experience is broken.

See `docs/backlogs/PIPELINE.md` for implementation details.

### Feedback Pipeline
The feedback form writes to SQLite but nobody can read it without SSH. Fix this before launch — if a beta tester submits a bug report and nothing happens, they stop reporting.

- **Admin dashboard**: `/admin` page to view/filter/resolve feedback. Only for admin users.
- **GitHub issue bridge**: Button on admin dashboard to push feedback to a GitHub issue (pre-filled with user message, type, timestamp). Uses `gh` CLI or GitHub API.
- **Auto-triage** (stretch): Scheduled Claude agent reads new feedback nightly, creates GitHub issues with labels (bug/feature/ux), and drafts a thank-you response.

See `docs/backlogs/FEEDBACK-PIPELINE.md` for implementation details.

### Landing Page
Right now unauthenticated visitors hit a login wall. They can't see what the app does. Before posting the Discord invite, there should be a public page that shows:
- What Haipai does (3 bullet points)
- Screenshot or demo of the review UI
- "Register with invite code" CTA

This is a single static HTML page or a public route in Flask. Not a marketing site — just enough to not confuse someone clicking the link.

See `docs/backlogs/LANDING-PAGE.md` for implementation details.

### Onboarding Polish
UX-AUDIT 8a flagged that the JSON extraction from mjai.ekyu.moe is fragile and confusing. For beta this is the #1 friction point — if a tester can't upload their first game, they bounce.

Options (easiest first):
1. Better instructions with screenshots/GIF in the onboarding flow
2. URL-based import: paste the mjai.ekyu.moe URL, server fetches the JSON (may need `requests` with browser headers to bypass Cloudflare)
3. Browser extension that auto-downloads the JSON (overkill for now)

---

## Phase 2: Post-Beta Iteration (weeks 2-4)

Goal: Act on beta feedback, add features that make users come back daily.

### Practice Mode V2
Current practice is tile efficiency only (after the 5a fix). Expand:
- **Defense drills**: Show hand + opponent discards + riichi declaration, ask "which tile is safest?" Uses the safety_ratings data already stored.
- **Spaced repetition tuning**: Currently basic — add difficulty scaling based on streak.
- **Daily challenge**: One random mistake from your history, push notification or email.

### Social Features
Mahjong is social. Club members want to compare and discuss.
- **Share game link**: Public URL for an annotated game (read-only, no login required).
- **Club view**: See aggregate stats for all club members (opt-in). Who improved most this week?
- **Discord bot**: Post weekly digest to a Discord channel — "Your club reviewed 12 games this week, top improver: @name".

### Auto-Import
Kill the mjai.ekyu.moe copy-paste workflow:
- **Tenhou log URL import**: Paste a Tenhou URL, server submits to Mortal, polls for result, imports automatically. One step instead of five.
- Cloudflare is the blocker. Options: headless browser on server, or client-side fetch via JS (browsers aren't blocked — vision.txt item 1).

---

## Phase 3: Monetization (month 2+)

Goal: Validate willingness to pay before building billing infrastructure.

### GPL Reality Check
mahjong-cpp and Riichi-Trainer are GPLv3. SaaS is fine — GPL only triggers on distribution. You never ship binaries to users. Source can stay public. No legal blocker to charging for hosted access.

If you want to go closed-source later, you'd need to:
- Replace mahjong-cpp with your own calculator (or get relicensing permission from nekobean)
- Replace the Riichi-Trainer defense logic (mj_defense.py is a port)
- Or just stay open-source and charge for hosting/convenience (GitLab model)

### Freemium Model
Free tier:
- 5 games stored
- Basic practice mode
- Trend charts

Premium ($5-10/mo):
- Unlimited games
- Auto-import from Tenhou URL
- Defense practice drills
- Priority feedback (auto-triaged, faster response)
- Club/social features
- Export data (CSV/JSON)

### Implementation
- Stripe Checkout (simplest: hosted payment page, webhook for subscription status)
- Add `tier` column to users table (`free` / `premium`)
- Gate features with a decorator: `@premium_required`
- Don't build billing UI from scratch — Stripe Customer Portal handles upgrades/cancellations

### Pricing Validation
Before building Stripe integration, validate demand:
- Add a "Premium (coming soon)" section in the app with feature list
- Track clicks on it (simple counter in DB)
- Ask beta testers directly: "Would you pay $X/mo for Y?"

---

## Phase 4: Growth (month 3+)

### Marketing Channels
- **Reddit**: r/Mahjong (42k), r/RiichiMahjong — post a "I built this" thread with screenshots
- **Mahjong Discord servers**: EMA, WRC, Mahjong Soul communities
- **SEO**: Landing page targeting "riichi mahjong trainer", "mahjong mistake analyzer", "mortal mahjong review tool"
- **YouTube**: Screen recording of reviewing a game in Haipai, 3-5 min. Mahjong content creators might feature it.
- **Mahjong Soul forums/communities**: Where MJS players hang out

### Retention Features
- Email/Discord weekly summary: "You made 15% fewer efficiency mistakes this week"
- Achievement badges (reviewed 10 games, practiced 50 drills, etc.)
- Study plans: "This week focus on: Value Tile Ordering (your weakest area)"

---

## What NOT to build yet

- Mobile app (responsive CSS is enough for now)
- Multi-language support (English-only until there's demand)
- AI coaching ("here's why Mortal chose this" — Mortal doesn't explain, and hallucinating explanations is worse than none)
- Real-time game analysis (during play) — completely different architecture
- Tournament features — too niche, too early
