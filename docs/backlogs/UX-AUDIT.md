# Haipai UX Audit

Systematic review of the web UI for outdated documentation, confusing elements, and layout improvements.

---

## 1. Outdated / Incorrect Documentation

### 1a. ~~Help page references deleted categories~~ (HIGH) ✅ DONE

`static/app.js:1519` says:

> "Sub-categorized into dora handling (1B), honor priority (1C/1D), pair management (1E), or general acceptance (1A)."

Categories 1B, 1C, 1D, 1E were collapsed in commit `f65e39c`. They no longer exist. The help page still describes them as if they do.

Similarly, `app.js:1521` references "2B Defense" -- the category is now `3B` (Strategy / Defense).

**Fix:** Rewrite the "How Auto-Categorization Works" section to match the current 12-category system (1A, 2A, 3A-3C, 4A-4C, 5A-5B, 6A-6B).

### 1b. ~~mj_games.py CATEGORIES list is stale~~ (MEDIUM) ✅ FIXED (B-04)

`mj_games.py:14-20` still lists the old categories: `1A, 1B, 1C, 1D, 1E, 2A, 2B, 2C, 3A, 3B, 3C, 4A, 4B, 5A, 5B`. This list no longer matches `CATEGORY_INFO` (which is correct). The CLI `--category` flag accepts these old codes. Another instance is working on categories, but this is worth flagging.

**Fixed:** CATEGORIES now derived from CATEGORY_INFO.keys() (see B-04 in docs/backlogs/BUGS.md).

### 1c. ~~vision.txt says "15-category system"~~ (LOW) ✅ DONE

Already fixed — vision.txt no longer references a specific category count.

---

## 2. Category System UX Issues

### 2a. ~~Category codes are meaningless to users~~ (HIGH) ✅ DONE

The UI shows badges like "Strategy / Push/Fold" alongside codes like "3A". The codes (1A, 2A, 3A, etc.) are an internal artifact of the auto-categorization engine. They don't help the user understand their mistakes and add visual noise. A user seeing "3A" gets no signal -- they still need the label.

**Recommendation:** Drop the category codes from all user-facing UI. Show only the group + label (e.g. "Strategy / Push/Fold"). Keep codes internal for the API and database. The help page currently shows them prominently too (`help-cat-code`) -- remove.

### 2b. ~~"Push/Fold" (3A) doesn't map well to Riichi Book concepts~~ (MEDIUM) ✅ DONE

The study reference says "Riichi Book Ch 8.1" but Push/Fold is a catch-all for "Mortal and mahjong-cpp disagree, and it's not defense." This covers a huge range of strategic decisions that aren't specifically push/fold. The label is misleading -- many of these are hand value decisions, wait selection, or complex multi-factor tradeoffs that Mortal evaluates differently from pure tile efficiency.

The user can't study "Push/Fold" as a coherent skill area because it's really "everything strategic that isn't defense." The Riichi Book Ch 8.1 reference specifically covers betaori timing, not the broad grab-bag this category actually contains.

**Recommendation:** Consider renaming to "Strategic" or "Complex Decision" with a description like "Mortal's strategic evaluation differs from pure tile efficiency -- may involve hand value, position, or game state factors." Drop the specific chapter reference or broaden it.

### 2c. ~~"Value Tile Ordering" (2A) is a narrow niche elevated to a top-level group~~ (LOW) ✅ DONE

This has its own group ("Value Tiles") with its own color, but it's really a sub-type of tile efficiency where the choice involves an honor or terminal vs a number tile. It only triggers when cpp scores are within 60 points. Giving it equal visual weight to "Strategy" or "Efficiency" in the trend charts and practice filters may overstate its importance.

**Recommendation:** Consider either folding it back into the Efficiency group (as a sub-category) or keeping it but de-emphasizing it in trend views.

---

## 3. Board Context Layout Issues

### 3a. ~~Opponent melds hidden inside "Details" collapse~~ (HIGH) ✅ DONE

`app.js:189-215` -- opponent pons/chis are inside a `<details>` element labeled "Details" that is collapsed by default. This means the user has to click to see what opponents have called, which is critical context for understanding:
- Why Mortal recommends a defensive play
- What tiles are visible and out of play
- Whether an opponent is building toward a visible hand

**Recommendation:** Move opponent melds inline with the discard rows. Each player row should show: `[East] [discards...] | [pon 456m] [chi 123p]`. The melds are as important as discards for reading the board state.

### 3b. ~~Discards always open, even when irrelevant~~ (MEDIUM) ✅ DONE

`app.js:167` -- the discards `<details>` element has `open` by default. For pure tile efficiency mistakes (categories 1A, 2A), the discards add visual clutter without helping the user understand the mistake. Tile efficiency is about your hand shape, not about what others discarded.

Conversely, for melding mistakes (4A-4C), riichi decisions (5A-5B), kan (6A-6B), and defense (3B), the discards are essential context.

**Recommendation:** Default discards to collapsed. Auto-expand when:
- Category is in Strategy, Meld, Riichi, or Kan groups (3A-6B)
- The mistake has `safety_ratings` (opponent in riichi)
- No category is set yet (user needs full context to annotate)

### 3c. ~~Scores buried in "Details" alongside melds~~ (LOW) ✅ DONE

Scores are in the same "Details" collapse as opponent melds. If melds move inline, scores could either:
- Go into the wind/dora info bar (compact: `E 25000 | S 32000 | ...`)
- Stay in a minimal collapse, but separate from melds

---

## 4. EV Comparison Table Issues

### 4a. ~~"Tile Calc" column header is ambiguous~~ (MEDIUM) ✅ DONE

The EV table header says "Tile Calc" which could mean many things. The help page explains it's mahjong-cpp expected score, but in-context the user sees a number like "8,432" with no unit.

**Recommendation:** Rename to "Exp Score" or add a unit hint. The tooltip or a small subtitle like "(expected score)" would help first-time users.

### 4b. ~~"Mortal Q" values are opaque~~ (LOW) ✅ DONE

Q-values like `0.847` are meaningless to users who don't understand reinforcement learning. The help page explains it, but in practice users ignore this column and focus on the tile calc numbers.

This isn't easily fixable since it's inherent to Mortal's output, but consider adding a brief hover tooltip on the column header: "AI's strategic evaluation (higher = better)"

---

## 5. Practice Mode Issues

### 5a. ~~Practice includes non-efficiency categories~~ (HIGH -- noted in vision.txt) ✅ DONE

`vision.txt:76-79` already notes this: practice mode includes strategy/defense mistakes where the "correct" answer depends on reading opponents, game state, etc. The user is shown only their hand and asked to pick a discard, but for a 3A "Push/Fold" mistake, the right answer requires strategic judgment that can't be learned from a hand quiz.

**Recommendation:** (Already in vision.txt) Rename to "Tile Efficiency Practice" and filter to only 1A and 2A categories. Add a clear explanation: "Practice pure hand-building decisions where the correct tile can be determined from your hand alone."

### 5b. ~~Practice "Calc agrees" filter label is unclear~~ (LOW) ✅ DONE

The checkbox label "Calc agrees" doesn't explain what it means. A user who hasn't read the help page won't know this filters to mistakes where mahjong-cpp and Mortal recommend the same tile.

**Recommendation:** Rename to "Efficiency only" or add a tooltip: "Only show problems where both AI and tile calculator agree on the best discard."

---

## 6. Game List / Sidebar Issues

### 6a. ~~"Import games.json" button is permanent~~ (LOW) ✅ DONE

`index.html:23` -- the import button is always visible in the sidebar. This is a one-time migration tool for the legacy JSON format. After importing, it serves no purpose and takes up space.

**Recommendation:** Hide after first use, or move to a settings/admin area. At minimum, only show it when no games exist yet.

### 6b. ~~Game numbering is confusing~~ (LOW) ✅ DONE

Games are labeled "Game 1", "Game 2" etc. based on their database ID. These numbers have no meaning to the user. When a game is deleted, the numbering has gaps.

**Recommendation:** Show the date more prominently as the primary identifier. Instead of "Game 7 -- 2025-03-15", just show "Mar 15" with the game details below.

---

## 7. Severity System Issues

### 7a. ~~?, ??, ??? symbols are non-standard~~ (MEDIUM) ✅ DONE

The severity markers `?`, `??`, `???` are compact but non-obvious. New users won't know what they mean without checking the help page. The summary bar shows counts of `???`, `??`, `?` with colored numbers but no legend.

**Recommendation:** Add tooltips to severity markers (e.g. `???` -> "Major mistake (>0.10 EV)"). Or use words: "minor / medium / major" alongside the symbols.

### 7b. ~~Medium and minor mistakes hidden by default with no indication~~ (MEDIUM) ✅ DONE

`index.html:31-32` -- `??` and `?` mistakes are hidden by default via unchecked checkboxes. A user reviewing a game sees only `???` mistakes and might think the game had very few errors. The round headers show `(2/5)` when filtered, but this is subtle.

**Recommendation:** Show a more visible indicator when mistakes are filtered out, like a banner: "Showing 3 of 12 mistakes. Enable ?? and ? to see all."

---

## 8. Onboarding Issues

### 8a. ~~Onboarding instructions are fragile~~ (MEDIUM) ✅ DONE

`app.js:462-481` -- the onboarding walks users through extracting the JSON URL from mjai.ekyu.moe's address bar. This is brittle:
- The URL format could change
- Users unfamiliar with browser dev tools find this confusing
- The Ctrl+S step to save raw JSON isn't obvious

**Recommendation:** Consider adding a URL-based import (paste the mjai.ekyu.moe report URL directly and let the server fetch it). If Cloudflare blocks server-side fetches, at least simplify the instructions with screenshots or a more step-by-step flow.

---

## 9. Minor Polish Items

### 9a. ~~Help page title says "Category Reference" but covers much more~~ ✅ DONE

The help page (`app.js:1494`) is titled "Category Reference" but also explains defense, EV comparison, ratings, practice, and attribution. It's really a full user guide.

**Recommendation:** Rename to "Help" or "User Guide".

### 9b. ~~No way to navigate back from Help/Trends/Practice~~ ✅ DONE

After clicking Help, Trends, or Practice, the user can only return by clicking a game in the sidebar. There's no back button or breadcrumb.

**Recommendation:** Add a simple "Back to games" link or make the Haipai header clickable to return to the game list.

### 9c. ~~Annotation dropdown shows codes alongside labels~~ ✅ DONE

`app.js:705-709` -- the category dropdown shows entries like "Efficiency / Tile Efficiency". Since the code is part of the option label via `catLabel()`, the user sees the full `group / label` format. This is fine, but the empty option shows "---" which doesn't communicate "uncategorized."

**Recommendation:** Change "---" to "Uncategorized" or "Not categorized."

### 9d. ~~"RIICHI" badge in hand row is small and easy to miss~~ ✅ DONE

`app.js:654` shows a small "Riichi" text badge when `safety_ratings` exist. This is the primary indicator that an opponent declared riichi, which is the single most important piece of defensive context.

**Recommendation:** Make the riichi indicator more prominent -- larger font, background color, or position it before the hand tiles so it's the first thing the user sees.

---

## Summary of Priorities

| Priority | Issue | Section |
|----------|-------|---------|
| ~~HIGH~~ | ~~Help page references deleted categories (1B-1E, 2B)~~ ✅ | 1a |
| ~~HIGH~~ | ~~Opponent melds hidden in "Details" collapse~~ ✅ | 3a |
| ~~HIGH~~ | ~~Practice includes non-efficiency categories~~ ✅ | 5a |
| ~~HIGH~~ | ~~Category codes add noise without helping users~~ ✅ | 2a |
| ~~MEDIUM~~ | ~~Discards always open even when irrelevant~~ ✅ | 3b |
| ~~MEDIUM~~ | ~~"Push/Fold" is a misleading catch-all~~ ✅ | 2b |
| ~~MEDIUM~~ | ~~mj_games.py CATEGORIES list is stale~~ ✅ (B-04) | 1b |
| ~~MEDIUM~~ | ~~Severity symbols unexplained~~ ✅ | 7a |
| ~~MEDIUM~~ | ~~Hidden mistakes with subtle indicator~~ ✅ | 7b |
| ~~MEDIUM~~ | ~~Onboarding JSON extraction is fragile~~ ✅ | 8a |
| ~~MEDIUM~~ | ~~"Tile Calc" header ambiguous~~ ✅ | 4a |
| ~~LOW~~ | ~~vision.txt says "15-category"~~ ✅ | 1c |
| ~~LOW~~ | ~~2A elevated to top-level group~~ ✅ | 2c |
| ~~LOW~~ | ~~Scores buried in details~~ ✅ | 3c |
| ~~LOW~~ | ~~"Calc agrees" filter label unclear~~ ✅ | 5b |
| ~~LOW~~ | ~~Import button always visible~~ ✅ | 6a |
| ~~LOW~~ | ~~Game numbering meaningless~~ ✅ | 6b |
| ~~LOW~~ | ~~Help page titled "Category Reference"~~ ✅ | 9a |
| ~~LOW~~ | ~~No back navigation from Help/Trends/Practice~~ ✅ | 9b |
| ~~LOW~~ | ~~"---" for uncategorized~~ ✅ | 9c |
| ~~LOW~~ | ~~Riichi badge too subtle~~ ✅ | 9d |
| ~~LOW~~ | ~~Mortal Q values opaque~~ ✅ | 4b |
