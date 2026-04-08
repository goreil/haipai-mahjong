# UX Feedback

**Source**: Direct user feedback

Completed: UX-01 (tutorial), UX-02 (simplified UI), UX-03 (back button), UX-04 (practice on frontpage), UX-05 (remove invite codes), UX-08 (opt-in popup), UX-09 (hide original play).

---

## UX-06: Google OAuth login (HIGH)

See `AUTH.md` A-02. Confirms user priority for Google OAuth.

**Files**: `app.py`, `db.py`, `requirements.txt`

---

## ~~UX-07: Unregistered game upload — preview mode~~ DONE

## ~~UX-10: Correct meld display notation~~ DONE

Basic notation with rotated called tiles, position based on source player, Back.svg for closed kans. Labels show meld type + source wind.

---

## UX-11: Ghost tiles in discard pools for called tiles (MEDIUM)

When a tile is called (chi/pon/kan), show a "ghost" tile in the original player's discard pool at the correct position in turn order, with a visual indicator (semi-transparent, dotted border). Hovering/clicking the meld should highlight the ghost tile, and vice versa.

Currently the called tile is removed from the discard pool entirely (in `extract_board_state`). Instead, keep it visually but marked as called.

**Files**: `lib/categorize.py` (board state extraction), `static/app.js` (discard rendering), `static/style.css`

---

## UX-12: Skill area category expansion with top mistakes (MEDIUM)

In the game summary or trends view, clicking a skill area category (e.g., "Efficiency", "Defense") should expand to show the top 3 worst mistakes in that category from the last 10 games. This helps players quickly find their biggest leaks without scrolling through every game.

Useful for finding specific mistake types like kans when they're rare.

**Files**: `static/app.js`, `db.py` (query for top mistakes by category), `routes/games.py` or `app.py` (new API endpoint)
