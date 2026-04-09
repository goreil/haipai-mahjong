# UX Feedback

**Source**: Direct user feedback + visual audit (2026-04-08)

Completed: UX-01 through UX-05, UX-07 through UX-14, UX-16 through UX-19.

---

## UX-06: Google OAuth login (HIGH)

See `AUTH.md` A-02. Confirms user priority for Google OAuth.

**Files**: `app.py`, `db.py`, `requirements.txt`

---

## UX-13: Kakan meld rendering fix (HIGH) ✅ DONE

The kakan (added kan) tile stacking is visually broken:
- The 4th tile doesn't stack cleanly on top of the rotated called tile
- Hovering disrupts the layout
- In `renderAction` for kakan decisions, the consumed array has 3 tiles + pai, but the rendering logic doesn't handle this correctly

The kakan should look like: two upright tiles + a rotated tile with another tile stacked directly on top of it (like `||=`).

**Files**: `static/app.js` (renderMeld kakan case), `static/style.css` (meld-kakan, meld-stacked-tile)

---

## UX-14: Visual cleanup — reduce clutter (MEDIUM) ✅ DONE

Observed from visual audit of the game review, trends, and practice pages:

**Game review view:**
- The top nav bar has too many buttons (Trends, Practice, Help, My Feedback, Send Feedback, Admin) — consider a hamburger menu or grouping
- The "Show ?? (medium) / Show ? (minor)" checkboxes are always visible even when not reviewing a game — should be contextual
- Each mistake card has a lot of vertical space: hand + board context (winds, dora, scores) + discards + EV table + annotation. The board context repeats nearly identical info between consecutive mistakes in the same round — could be shown once per round instead
- The annotation dropdown + note field on every mistake is noisy when you're just browsing — could collapse to show only on hover/click

**Sidebar:**
- Game list items are tall — date + stats + annotation bar takes 3 lines. Could be more compact
- No visual distinction between games from different sessions/days

**Practice view:**
- The tutorial box is good but takes up a lot of space after the first session — maybe auto-dismiss after 3 uses
- The draw tile (last tile with gap) is subtle — could use a stronger visual indicator

**Trends view:**
- The two chart cards (EV per Decision, Mistakes by Severity) are quite tall
- The skill area bar expansion inserts full mistake cards inline which pushes everything down — a modal/panel might work better

**Files**: `static/app.js`, `static/style.css`

---

## UX-16: Community pool EV should be 1st-vs-2nd, not 1st-vs-actual (MEDIUM) ✅ DONE

For community practice problems, the `actual` play is stripped (UX-09). The EV loss displayed should be the gap between Mortal's #1 and #2 choices (`details[0].q_value - details[1].q_value`), not between Mortal's pick and the original player's pick. This better reflects the difficulty of the decision rather than how bad the original player was.

Currently `ev_loss` is stored per-mistake as `details[0].q_value - details[actual_index].q_value`. For community display, compute it on the fly or store a second field.

**Files**: `db.py` (get_public_practice_problem), `lib/parse.py` (store top-2 gap), `static/app.js` (display)

---

## UX-17: Mistake breakdown scoped to current game + explanatory text (HIGH) ✅ DONE

The mistake breakdown in the game analysis section currently shows mistakes across all games. It should be scoped to the current game only.

Additionally, each mistake should have a short explanatory text on the right side describing what happened. Examples:
- "Mortal and calc both agree: best discard was 3m, but you chose 1m"
- "Mortal recommends riichi here, but you discarded 5p instead"
- "Calc says 2s is more efficient, but Mortal prefers the safer E — you chose 7p"
- "You called chi, but passing was better here"

The text should be generated from the mistake data (category, actual/expected actions, cpp agreement).

**Files**: `static/app.js` (mistake breakdown rendering, text generation), `static/style.css`

---

## UX-18: Rich categorization explanations per mistake (HIGH) ✅ DONE

The current explanatory text in the mistake breakdown is too brief (e.g. "best discard was 3m, but you chose 1m"). It should be a detailed, educational paragraph that:

1. **Explains the category** in context — not just "this is 1A (Efficiency)" but why this specific mistake falls into that category for this hand.
2. **Describes the AI reasoning** — what Mortal considered (hand shape, shanten, tiles remaining, safety, hand value) and what mahjong-cpp's tile efficiency analysis says.
3. **Teaches the player** — connects the mistake to a general mahjong principle. E.g. for a 2A (Value Tile) mistake: "Your hand is 1-shanten. Both 1m and E reduce to 0-shanten with similar acceptance counts, but Mortal values keeping E because it's a yakuhai (round wind) — dropping it loses potential hand value."
4. **Uses available data**: `cpp_stats` (shanten, necessary_count, exp_score per discard), `safety_ratings`, `top_actions` (Mortal q_values), `board_state` (dora, winds, scores), `category`, `cpp_best`, `labels` (dora/yakuhai/terminal tags).

Examples of the desired level of detail:

- **1A (Efficiency)**: "Both Mortal and calc agree: discard 3m for maximum tile acceptance (14 tiles vs 8 tiles for your 7p). At 2-shanten, pure efficiency matters most — you want to reduce shanten as fast as possible."
- **2A (Value Tiles)**: "Calc says 1m and E have similar efficiency (both reach 1-shanten with 12 vs 10 tiles). But Mortal prefers keeping E — it's the round wind (yakuhai), so completing the hand with E in it is worth significantly more points."
- **3A (Complex Decision)**: "Calc recommends 4s for best tile acceptance, but Mortal disagrees and prefers 8p. This is a strategic judgment call — possibly considering hand shape, potential yaku, or opponents' states. The AI sees something beyond pure efficiency here."
- **3B (Defense)**: "An opponent declared riichi. Mortal recommends discarding E (safety: 14) over your 5p (safety: 2). Calc doesn't account for defense — it still wants 5p for efficiency. Mortal is prioritizing survival: E is nearly 100% safe (genbutsu) while 5p is very dangerous."
- **4B (Missed Meld)**: "You passed on a pon of 7s. With your hand at 2-shanten, calling this pon immediately drops you to 1-shanten. The trade-off is losing a closed hand, but at this point the speed advantage outweighs the value loss."
- **5B (Missed Riichi)**: "Your hand is tenpai and ready to declare riichi. Riichi adds at least 1 han and ippatsu chance. Mortal says the expected value of declaring far exceeds the risk of being locked into your wait."

**Placement**: The explanation should appear inline on each mistake card in the main game review view (not in the category summary breakdown). It should sit below the hand/EV table area, as a readable paragraph that the player sees when reviewing each individual mistake.

**Implementation**: Expand `generateExplanation(m)` in `static/app.js` to use `m.cpp_stats`, `m.safety_ratings`, `m.top_actions`, `m.board_state`, `m.labels`, `m.shanten`, and `m.category` to build contextual paragraphs. Call it from the main mistake rendering in `renderGame()`, not just the breakdown panel. Consider a helper per category group.

**Files**: `static/app.js` (`generateExplanation` function, mistake rendering in `renderGame`), `static/style.css`

---

## UX-19: Mascot character (MEDIUM) ✅ DONE

Add a mascot character to Haipai that serves two purposes:

1. **Favicon**: A small mascot icon as `favicon.ico` for browser tabs/bookmarks.
2. **Trainer persona**: The mascot "says" the explanatory text on mistake cards (UX-18), giving it personality. Instead of plain italic text, show a small mascot avatar next to a speech bubble with the explanation. Could also appear in:
   - Practice mode ("Good job!" / "Think about defense here...")
   - Empty states ("No games yet — upload your first replay!")
   - Onboarding steps

**Design direction**: Should feel friendly and mahjong-themed. Ideas: a small tile character, a cartoon tanuki/cat in a mahjong robe, a chibi player, etc. Could be pixel art or simple vector. Needs to work at 16x16 (favicon), ~40px (inline avatar), and larger for the landing page/login. Replaces the current MPS tile logo (`.brand-mark` in sidebar, landing page hero, login page header) as the primary brand identity.

**Files**: `static/favicon.ico`, `static/mascot.svg` (or `.png`), `static/style.css`, `static/index.html` (favicon link), `static/landing.html` (hero), `static/app.js` (sidebar brand, mascot integration with explanations), `app.py` (login page template)

---

## UX-15: Mobile responsiveness (LOW)

The layout doesn't adapt well to narrow screens. The sidebar + content split doesn't work on mobile. The tile images are tiny. Consider a responsive layout with collapsible sidebar.

**Files**: `static/style.css`, `static/app.js`
