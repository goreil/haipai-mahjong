# UX Feedback

**Source**: Direct user feedback

Completed: UX-01 (tutorial), UX-02 (simplified UI), UX-03 (back button), UX-04 (practice on frontpage), UX-05 (remove invite codes), UX-08 (opt-in popup), UX-09 (hide original play).

---

## UX-06: Google OAuth login (HIGH)

See `AUTH.md` A-02. Confirms user priority for Google OAuth.

**Files**: `app.py`, `db.py`, `requirements.txt`

---

## UX-07: Unregistered game upload — preview mode (MEDIUM)

Allow unregistered users to upload a mortal.json and see the analysis for one game without storing in DB. Ephemeral/temporary view — "try before you sign up."

**Files**: `app.py`, `routes/games.py`, `static/app.js`, `static/landing.html`

---

## UX-10: Correct meld display notation (MEDIUM)

Melds (pon, chi, kan) should use standard riichi notation showing which player the tile came from:

**Chi/Pon:**
- `-||` tile from left player (kamicha)
- `|-|` tile from across (toimen)
- `||-` tile from right player (shimocha)

On hover, highlight the wind label (E/S/W/N) of the player it came from.

**Kan:**
- Closed kan (ankan): show middle two tiles face-down using `Back.svg` (exists in `riichi-mahjong-tiles/Regular/Back.svg`)
- Open kan (daiminkan): called tile position like pon (`-|||`, `|-||`, `|||-`)
- Added kan (kakan): same as pon display but with 4th tile added on top

The meld data in `data_json` includes `type` (chi/pon/ankan/daiminkan/kakan) and `consumed`/`pai` fields which identify the called tile and source.

**Files**: `static/app.js` (meld rendering), `static/style.css`
