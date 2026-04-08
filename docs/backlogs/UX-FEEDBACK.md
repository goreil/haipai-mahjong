# UX Feedback

**Source**: Direct user feedback + visual audit (2026-04-08)

Completed: UX-01 through UX-05, UX-07 through UX-12.

---

## UX-06: Google OAuth login (HIGH)

See `AUTH.md` A-02. Confirms user priority for Google OAuth.

**Files**: `app.py`, `db.py`, `requirements.txt`

---

## UX-13: Kakan meld rendering fix (HIGH)

The kakan (added kan) tile stacking is visually broken:
- The 4th tile doesn't stack cleanly on top of the rotated called tile
- Hovering disrupts the layout
- In `renderAction` for kakan decisions, the consumed array has 3 tiles + pai, but the rendering logic doesn't handle this correctly

The kakan should look like: two upright tiles + a rotated tile with another tile stacked directly on top of it (like `||=`).

**Files**: `static/app.js` (renderMeld kakan case), `static/style.css` (meld-kakan, meld-stacked-tile)

---

## UX-14: Visual cleanup — reduce clutter (MEDIUM)

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

## UX-15: Mobile responsiveness (LOW)

The layout doesn't adapt well to narrow screens. The sidebar + content split doesn't work on mobile. The tile images are tiny. Consider a responsive layout with collapsible sidebar.

**Files**: `static/style.css`, `static/app.js`
