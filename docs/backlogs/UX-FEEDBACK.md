# UX Feedback

**Source**: Direct user feedback + visual audit (2026-04-08)

Completed: UX-01 through UX-05, UX-07 through UX-14, UX-16, UX-17.

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

## UX-15: Mobile responsiveness (LOW)

The layout doesn't adapt well to narrow screens. The sidebar + content split doesn't work on mobile. The tile images are tiny. Consider a responsive layout with collapsible sidebar.

**Files**: `static/style.css`, `static/app.js`
