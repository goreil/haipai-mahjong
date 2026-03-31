const CATEGORIES = [
  "", "1A", "1B", "1C", "1D", "1E",
  "2A", "2B", "2C",
  "3A", "3B", "3C",
  "4A", "4B",
  "5A", "5B",
];

// Loaded from /api/categories on init
let CATEGORY_INFO = {};

function catLabel(code) {
  const info = CATEGORY_INFO[code];
  return info ? `${info.group} / ${info.label}` : code;
}

function catGroup(code) {
  const info = CATEGORY_INFO[code];
  return info ? info.group : code;
}

const GROUP_COLORS = {
  "Efficiency": "#4a9eff",
  "Strategy": "#ff6b6b",
  "Meld": "#ffa94d",
  "Riichi": "#a855f7",
  "Kan": "#22c55e",
};

const OUTCOME_EMOJI = { ":D": "\u{1F60E}", ":)": "\u{1F642}", ":|": "\u{1F610}", ":(": "\u{1F61E}" };

let state = {
  games: [],
  currentGame: null,
  currentGameData: null,
  showMinor: false,
  showMedium: false,
};

// --- Tile rendering ---

// mjai notation -> SVG filename
const TILE_FILE = {
  "1m": "Man1", "2m": "Man2", "3m": "Man3", "4m": "Man4", "5m": "Man5",
  "6m": "Man6", "7m": "Man7", "8m": "Man8", "9m": "Man9", "5mr": "Man5-Dora",
  "1p": "Pin1", "2p": "Pin2", "3p": "Pin3", "4p": "Pin4", "5p": "Pin5",
  "6p": "Pin6", "7p": "Pin7", "8p": "Pin8", "9p": "Pin9", "5pr": "Pin5-Dora",
  "1s": "Sou1", "2s": "Sou2", "3s": "Sou3", "4s": "Sou4", "5s": "Sou5",
  "6s": "Sou6", "7s": "Sou7", "8s": "Sou8", "9s": "Sou9", "5sr": "Sou5-Dora",
  "E": "Ton", "S": "Nan", "W": "Shaa", "N": "Pei",
  "P": "Haku", "F": "Hatsu", "C": "Chun",
};

function tileSrc(t) {
  const name = TILE_FILE[t];
  return name ? `/tiles/${name}.svg` : `/tiles/Back.svg`;
}

function renderTile(t, extraClass = "", titleOverride = null) {
  const cls = ["tile", extraClass].filter(Boolean).join(" ");
  const title = titleOverride || t;
  return `<img class="${cls}" src="${tileSrc(t)}" alt="${t}" title="${title}">`;
}

function renderHand(tiles, draw, safetyRatings) {
  if (!tiles || !tiles.length) return "";
  return tiles.map((t, i) => {
    let extra = "";
    if (draw && i === tiles.length - 1 && t === draw) extra = "draw";
    const sr = getSafetyRating(safetyRatings, t);
    if (sr != null) extra += ` ${safetyClass(sr)}`;
    const title = sr != null ? `${t} (safety: ${sr})` : null;
    return renderTile(t, extra, title);
  }).join("");
}

// --- Action formatting ---

function formatAction(action) {
  if (!action) return "?";
  switch (action.type) {
    case "dahai": return action.pai;
    case "chi": return `chi ${(action.consumed || []).join("")}+${action.pai || "?"}`;
    case "pon": return `pon ${(action.consumed || []).join("")}+${action.pai || "?"}`;
    case "reach": return "riichi";
    case "hora": return "win";
    case "none": return "pass";
    case "ankan": return `ankan ${(action.consumed || ["?"])[0]}`;
    default: return action.type;
  }
}

function renderAction(action, cls = "") {
  if (!action) return `<span class="action-text ${cls}">?</span>`;
  switch (action.type) {
    case "dahai":
      return renderTile(action.pai, `action-tile ${cls}`);
    case "chi":
      return `<span class="action-meld ${cls}">chi ${(action.consumed || []).map(t => renderTile(t, "action-tile-sm")).join("")}+${renderTile(action.pai || "?", "action-tile-sm")}</span>`;
    case "pon":
      return `<span class="action-meld ${cls}">pon ${(action.consumed || []).map(t => renderTile(t, "action-tile-sm")).join("")}+${renderTile(action.pai || "?", "action-tile-sm")}</span>`;
    case "reach": return `<span class="action-text ${cls}">riichi</span>`;
    case "hora": return `<span class="action-text ${cls}">win</span>`;
    case "none": return `<span class="action-text ${cls}">pass</span>`;
    case "ankan":
      return `<span class="action-meld ${cls}">ankan ${renderTile((action.consumed || ["?"])[0], "action-tile-sm")}</span>`;
    default: return `<span class="action-text ${cls}">${action.type}</span>`;
  }
}

function sevClass(sev) {
  if (sev === "???") return "sev-major";
  if (sev === "??") return "sev-medium";
  if (sev === "?") return "sev-minor";
  if (sev === "!") return "sev-flag";
  return "";
}

// --- EV Comparison ---

function renderEvComparison(m) {
  const hasSafety = m.safety_ratings && Object.keys(m.safety_ratings).length > 0;

  // Build a unified list of tiles from mortal top_actions and cpp_stats
  const mortalMap = {};
  for (const a of m.top_actions) {
    const tile = a.action.pai || a.action.type;
    mortalMap[tile] = a;
  }

  const cppMap = {};
  for (const s of m.cpp_stats) {
    cppMap[s.tile] = s;
  }

  // Collect all tiles to show: mortal top 3 + cpp top 3 + actual + expected
  const shown = new Set();
  for (const a of m.top_actions.slice(0, 3)) {
    shown.add(a.action.pai || a.action.type);
  }
  for (const s of m.cpp_stats.slice(0, 3)) {
    shown.add(s.tile);
  }
  if (m.actual && m.actual.pai) shown.add(m.actual.pai);
  if (m.expected && m.expected.pai) shown.add(m.expected.pai);

  // Sort: mortal best first, then by mortal q_value desc, then cpp exp_score desc
  const tiles = [...shown].sort((a, b) => {
    const ma = mortalMap[a], mb = mortalMap[b];
    const ca = cppMap[a], cb = cppMap[b];
    const qa = ma ? ma.q_value : -999;
    const qb = mb ? mb.q_value : -999;
    return qb - qa;
  });

  // Find best values for highlighting
  const bestCppScore = Math.max(...m.cpp_stats.slice(0, 5).map(s => s.exp_score || 0));
  const bestMortalQ = Math.max(...m.top_actions.map(a => a.q_value));

  let html = `<div class="ev-comparison">`;
  html += `<table class="ev-table">`;
  html += `<thead><tr>
    <th>Tile</th>
    <th class="mortal-col">Mortal Q</th>
    <th class="mortal-col">Prob</th>
    <th class="cpp-col">Tile Calc</th>
    <th class="cpp-col">Win%</th>
    <th class="cpp-col">Shanten</th>
    ${hasSafety ? '<th class="safety-col">Safety</th>' : ''}
  </tr></thead><tbody>`;

  for (const tile of tiles) {
    const ma = mortalMap[tile];
    const ca = cppMap[tile] || cppMap[normalizeRed(tile)];
    const isActual = m.actual && m.actual.pai === tile;
    const isExpected = m.expected && m.expected.pai === tile;
    const isCppBest = m.cpp_best === tile;

    let rowClass = "";
    if (isActual) rowClass = "row-actual";
    else if (isExpected) rowClass = "row-expected";

    const markers = [];
    if (isActual) markers.push('<span class="marker played">You</span>');
    if (isExpected) markers.push('<span class="marker ai">AI</span>');
    if (isCppBest) markers.push('<span class="marker cpp">Calc</span>');

    html += `<tr class="${rowClass}">`;
    html += `<td class="tile-cell">${renderTile(tile, "ev-tile")} ${markers.join("")}</td>`;

    if (ma) {
      const qClass = ma.q_value === bestMortalQ ? "best-val" : "";
      html += `<td class="mortal-col ${qClass}">${ma.q_value.toFixed(3)}</td>`;
      html += `<td class="mortal-col">${(ma.prob * 100).toFixed(0)}%</td>`;
    } else {
      html += `<td class="mortal-col dim">-</td><td class="mortal-col dim">-</td>`;
    }

    if (ca) {
      const sClass = ca.exp_score === bestCppScore ? "best-val" : "";
      html += `<td class="cpp-col ${sClass}">${Math.round(ca.exp_score).toLocaleString()}</td>`;
      html += `<td class="cpp-col">${(ca.win_prob_max * 100).toFixed(1)}%</td>`;
      html += `<td class="cpp-col">${ca.shanten}</td>`;
    } else {
      html += `<td class="cpp-col dim">-</td><td class="cpp-col dim">-</td><td class="cpp-col dim">-</td>`;
    }

    if (hasSafety) {
      const sr = getSafetyRating(m.safety_ratings, tile);
      if (sr != null) {
        html += `<td class="safety-col ${safetyClass(sr)}">${sr}</td>`;
      } else {
        html += `<td class="safety-col dim">-</td>`;
      }
    }

    html += `</tr>`;
  }

  html += `</tbody></table></div>`;
  return html;
}

function normalizeRed(tile) {
  // 5mr -> 5m, 5pr -> 5p, 5sr -> 5s
  if (tile && tile.endsWith("r")) return tile.slice(0, -1);
  return tile;
}

function getSafetyRating(safetyRatings, tile) {
  if (!safetyRatings) return null;
  if (safetyRatings[tile] != null) return safetyRatings[tile];
  const normalized = normalizeRed(tile);
  if (normalized !== tile && safetyRatings[normalized] != null) return safetyRatings[normalized];
  if (tile.match(/^5[mps]$/)) {
    const red = tile + "r";
    if (safetyRatings[red] != null) return safetyRatings[red];
  }
  return null;
}

function safetyClass(rating) {
  if (rating == null) return "";
  if (rating >= 10) return "safety-safe";
  if (rating >= 6) return "safety-caution";
  return "safety-danger";
}

// --- API ---

async function fetchGames() {
  const res = await fetch("/api/games");
  state.games = await res.json();
  renderGameList();
}

async function fetchGame(id) {
  const res = await fetch(`/api/games/${id}`);
  state.currentGameData = await res.json();
  state.currentGame = id;
  renderGame();
}

async function saveAnnotation(gameId, round, turn, index, category, note) {
  const res = await fetch(`/api/games/${gameId}/annotate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ round, turn, index, category, note }),
  });
  const data = await res.json();
  if (data.ok) {
    state.currentGameData.summary = data.summary;
    // Update sidebar
    const gameInfo = state.games.find(g => g.id === gameId);
    if (gameInfo) {
      gameInfo.summary = data.summary;
      // Recount annotated
      let annotated = 0;
      for (const rnd of state.currentGameData.rounds) {
        for (const m of rnd.mistakes) {
          if (m.category) annotated++;
        }
      }
      gameInfo.annotated = annotated;
      renderGameList();
    }
  }
  return data;
}

async function addGame(url, date) {
  const res = await fetch("/api/games/add", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, date: date || undefined }),
  });
  return await res.json();
}

// --- Render: Game List ---

function renderGameList() {
  const list = document.getElementById("game-list");
  const sorted = [...state.games].sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id);
  list.innerHTML = sorted.map(g => {
    const s = g.summary || {};
    const active = g.id === state.currentGame ? "active" : "";
    const pct = g.total > 0 ? Math.round((g.annotated / g.total) * 100) : 100;
    return `
      <div class="game-item ${active}" onclick="fetchGame(${g.id})">
        <div class="date">Game ${g.id + 1} &mdash; ${g.date}</div>
        <div class="stats">
          ${s.total_mistakes || 0} mistakes &middot; ${(s.total_ev_loss || 0).toFixed(2)} EV
          ${s.total_turns ? ` &middot; ${s.ev_per_turn.toFixed(4)}/T` : ""}
        </div>
        <div class="annotation-bar"><div class="fill" style="width:${pct}%"></div></div>
      </div>
    `;
  }).join("");
}

// --- Render: Game Detail ---

function renderGame() {
  const game = state.currentGameData;
  if (!game) return;
  const content = document.getElementById("content");

  const s = game.summary || {};
  const sev = s.by_severity || {};

  let html = `
    <div class="game-header">
      <h2>Game ${state.currentGame + 1} &mdash; ${game.date}
        <button class="btn btn-delete" onclick="deleteGame(${state.currentGame})" title="Delete game">Delete</button>
      </h2>
      ${game.log_url ? `<div class="log-link"><a href="${game.log_url}" target="_blank">${game.log_url}</a></div>` : ""}
    </div>

    <div class="summary-bar">
      <div class="stat"><span class="value">${s.total_mistakes || 0}</span><span class="label">Mistakes</span></div>
      <div class="stat"><span class="value">${(s.total_ev_loss || 0).toFixed(2)}</span><span class="label">EV Loss</span></div>
      ${s.total_turns ? `<div class="stat"><span class="value">${s.total_turns}</span><span class="label">Turns</span></div>
      <div class="stat"><span class="value">${s.ev_per_turn.toFixed(4)}</span><span class="label">EV/Turn</span></div>` : ""}
      <div class="stat"><span class="value" style="color:var(--sev-major)">${sev["???"] || 0}</span><span class="label">???</span></div>
      <div class="stat"><span class="value" style="color:var(--sev-medium)">${sev["??"] || 0}</span><span class="label">??</span></div>
      <div class="stat"><span class="value" style="color:var(--sev-minor)">${sev["?"] || 0}</span><span class="label">?</span></div>
    </div>
  `;

  // Rounds
  for (const rnd of game.rounds) {
    const visible = rnd.mistakes.filter(m => {
      if (m.severity === "?" && !state.showMinor) return false;
      if (m.severity === "??" && !state.showMedium) return false;
      return true;
    });

    const outcomeStr = rnd.outcome ? (OUTCOME_EMOJI[rnd.outcome] || rnd.outcome) : "";
    const turnStr = rnd.turn_count ? `T${rnd.turn_count}` : "";

    html += `<div class="round">`;
    html += `<div class="round-header">
      <span>${rnd.round}${turnStr}</span>
      ${outcomeStr ? `<span class="outcome">${outcomeStr}</span>` : ""}
      ${visible.length === 0 && rnd.mistakes.length === 0 ? "" :
        visible.length !== rnd.mistakes.length ?
        `<span style="font-size:12px;color:var(--text-dim)">(${visible.length}/${rnd.mistakes.length})</span>` : ""}
    </div>`;

    // Track turn index for duplicate turn disambiguation
    const turnCounts = {};
    for (const m of rnd.mistakes) {
      const key = m.turn;
      turnCounts[key] = (turnCounts[key] || 0) + 1;
    }
    const turnSeen = {};

    for (const m of rnd.mistakes) {
      const turnKey = m.turn;
      const idx = turnSeen[turnKey] = (turnSeen[turnKey] || 0);
      turnSeen[turnKey]++;

      if (m.severity === "?" && !state.showMinor) continue;
      if (m.severity === "??" && !state.showMedium) continue;

      const sc = sevClass(m.severity);
      const dataAttrs = `data-game="${state.currentGame}" data-round="${rnd.round}" data-turn="${m.turn}" data-index="${idx}"`;

      html += `<div class="mistake ${sc}" ${dataAttrs}>`;
      html += `<div class="mistake-top">`;
      html += `<span class="turn-num">T${m.turn}</span>`;
      html += `<span class="severity ${sc}">${m.severity}</span>`;
      html += `<span class="ev-loss">${m.ev_loss.toFixed(2)} EV</span>`;
      if (m.category) {
        const grp = catGroup(m.category);
        const color = GROUP_COLORS[grp] || "#888";
        html += `<span class="cat-badge" style="background:${color}20;color:${color};border:1px solid ${color}40">${catLabel(m.category)}</span>`;
      }
      if (m.shanten != null) {
        html += `<span class="shanten">${m.shanten}-shanten</span>`;
      }
      if (m.actual && m.expected) {
        const actStr = formatAction(m.actual);
        const expStr = formatAction(m.expected);
        if (actStr !== expStr) {
          html += `<span class="discard-comparison">
            <span class="played">${renderAction(m.actual, "played")}</span>
            <span class="arrow">&rarr;</span>
            <span class="ai">${renderAction(m.expected, "ai")}</span>
          </span>`;
        }
      }
      html += `</div>`;

      // Hand
      if (m.hand && m.hand.length) {
        html += `<div class="hand-row">
          <span class="label">Hand</span>
          ${m.safety_ratings ? '<span class="defense-badge">Riichi</span>' : ''}
          <span class="tiles">${renderHand(m.hand, m.draw, m.safety_ratings)}</span>
        </div>`;
      }

      // EV Comparison table (Mortal vs mahjong-cpp)
      if (m.top_actions && m.top_actions.length && m.cpp_stats && m.cpp_stats.length) {
        html += renderEvComparison(m);
      } else if (m.top_actions && m.top_actions.length) {
        // Fallback: just show mortal top actions
        html += `<div class="top-actions">`;
        for (const a of m.top_actions) {
          html += `<span class="top-action">${renderAction(a.action)} <b>${a.q_value.toFixed(2)}</b> <span class="prob">${(a.prob * 100).toFixed(0)}%</span></span>`;
        }
        html += `</div>`;
      }

      // Annotation
      const catOptions = CATEGORIES.map(c => {
        const sel = (m.category || "") === c ? "selected" : "";
        const label = c ? catLabel(c) : "---";
        return `<option value="${c}" ${sel}>${label}</option>`;
      }).join("");

      html += `<div class="annotation-row">
        <select onchange="onAnnotate(this)" ${dataAttrs}>${catOptions}</select>
        <input type="text" placeholder="Note..." value="${(m.note || "").replace(/"/g, "&quot;")}"
               onchange="onAnnotate(this)" ${dataAttrs}>
        <span class="save-indicator">Saved</span>
      </div>`;

      html += `</div>`; // .mistake
    }

    html += `</div>`; // .round
  }

  // Category summary - grouped by skill area
  if (s.by_category && Object.keys(s.by_category).length) {
    html += `<div class="game-summary"><h3>Mistake Breakdown</h3>`;

    // Group by skill area
    const groups = {};
    for (const [cat, data] of Object.entries(s.by_category)) {
      const grp = catGroup(cat);
      if (!groups[grp]) groups[grp] = { count: 0, ev: 0, subs: {} };
      groups[grp].count += data.count;
      groups[grp].ev += data.ev;
      groups[grp].subs[cat] = data;
    }

    html += `<div class="category-groups">`;
    for (const [grp, data] of Object.entries(groups).sort((a, b) => b[1].ev - a[1].ev)) {
      const color = GROUP_COLORS[grp] || "#888";
      html += `<div class="cat-group" style="border-left: 3px solid ${color}">
        <div class="cat-group-header">
          <span class="cat-group-name" style="color:${color}">${grp}</span>
          <span class="cat-group-stat">${data.count} mistakes &middot; ${data.ev.toFixed(2)} EV</span>
        </div>`;
      // Subcategories
      const subs = Object.entries(data.subs).sort((a, b) => b[1].ev - a[1].ev);
      for (const [cat, sub] of subs) {
        const info = CATEGORY_INFO[cat];
        const label = info ? info.label : cat;
        const desc = info ? info.desc : "";
        html += `<div class="cat-sub" title="${desc}">
          <span class="cat-sub-label">${label}</span>
          <span class="cat-sub-stat">${sub.count} (${sub.ev.toFixed(2)} EV)</span>
        </div>`;
      }
      html += `</div>`;
    }
    html += `</div></div>`;
  }

  content.innerHTML = html;

  // Re-highlight active game in sidebar
  renderGameList();
}

// --- Annotation handler ---

let annotateTimers = {};

function onAnnotate(el) {
  const gameId = parseInt(el.dataset.game);
  const round = el.dataset.round;
  const turn = parseInt(el.dataset.turn);
  const index = parseInt(el.dataset.index);
  const key = `${gameId}-${round}-${turn}-${index}`;

  // Find sibling select and input
  const row = el.closest(".annotation-row");
  const select = row.querySelector("select");
  const input = row.querySelector("input");
  const indicator = row.querySelector(".save-indicator");

  // Debounce
  clearTimeout(annotateTimers[key]);
  annotateTimers[key] = setTimeout(async () => {
    const category = select.value;
    const note = input.value;

    // Also update local state
    const rnd = state.currentGameData.rounds.find(r => r.round === round);
    if (rnd) {
      const candidates = rnd.mistakes.filter(m => m.turn === turn);
      if (candidates[index]) {
        candidates[index].category = category || null;
        candidates[index].note = note || null;
      }
    }

    await saveAnnotation(gameId, round, turn, index, category, note);
    indicator.classList.add("show");
    setTimeout(() => indicator.classList.remove("show"), 1200);
  }, 400);
}

// --- Filter handlers ---

function onToggleMinor(cb) {
  state.showMinor = cb.checked;
  if (state.currentGameData) renderGame();
}

function onToggleMedium(cb) {
  state.showMedium = cb.checked;
  if (state.currentGameData) renderGame();
}

// --- Add game modal ---

function showAddModal() {
  document.getElementById("add-modal").classList.add("show");
  document.getElementById("add-url").value = "";
  document.getElementById("add-date").value = "";
  document.getElementById("add-error").textContent = "";
}

function hideAddModal() {
  document.getElementById("add-modal").classList.remove("show");
}

async function submitAddGame() {
  const url = document.getElementById("add-url").value.trim();
  const date = document.getElementById("add-date").value.trim();
  const errEl = document.getElementById("add-error");
  const btn = document.getElementById("add-submit-btn");

  if (!url) {
    errEl.textContent = "URL is required";
    return;
  }

  btn.disabled = true;
  btn.innerHTML = 'Adding...<span class="spinner"></span>';
  errEl.textContent = "";

  const result = await addGame(url, date);

  btn.disabled = false;
  btn.textContent = "Add Game";

  if (result.error) {
    errEl.textContent = result.error;
    return;
  }

  hideAddModal();
  await fetchGames();
  fetchGame(result.game_id);
}

// --- Delete game ---

async function deleteGame(id) {
  if (!confirm(`Delete game ${id + 1}? This cannot be undone.`)) return;
  const res = await fetch(`/api/games/${id}`, { method: "DELETE" });
  const data = await res.json();
  if (data.ok) {
    state.currentGame = null;
    state.currentGameData = null;
    document.getElementById("content").innerHTML = '<div class="empty-state">Game deleted</div>';
    await fetchGames();
  }
}

// --- Trends ---

async function fetchTrends() {
  const res = await fetch("/api/trends");
  return await res.json();
}

async function showTrends() {
  state.currentGame = null;
  state.currentGameData = null;
  renderGameList();
  const content = document.getElementById("content");
  content.innerHTML = '<div class="empty-state">Loading trends...</div>';

  const games = await fetchTrends();
  if (games.length < 2) {
    content.innerHTML = '<div class="empty-state">Need at least 2 games for trend analysis</div>';
    return;
  }
  renderTrends(games);
}

function renderTrends(games) {
  const content = document.getElementById("content");

  // Compute aggregates
  const totalGames = games.length;
  const totalMistakes = games.reduce((s, g) => s + g.total_mistakes, 0);
  const totalEv = games.reduce((s, g) => s + g.total_ev_loss, 0);
  const gamesWithTurns = games.filter(g => g.ev_per_turn != null);
  const avgEvPerTurn = gamesWithTurns.length > 0
    ? gamesWithTurns.reduce((s, g) => s + g.ev_per_turn, 0) / gamesWithTurns.length : null;

  // Trend direction (last 5 vs first 5 for ev_per_turn)
  let trendArrow = "";
  if (gamesWithTurns.length >= 4) {
    const half = Math.floor(gamesWithTurns.length / 2);
    const firstHalf = gamesWithTurns.slice(0, half);
    const secondHalf = gamesWithTurns.slice(-half);
    const avgFirst = firstHalf.reduce((s, g) => s + g.ev_per_turn, 0) / firstHalf.length;
    const avgSecond = secondHalf.reduce((s, g) => s + g.ev_per_turn, 0) / secondHalf.length;
    const pctChange = ((avgSecond - avgFirst) / avgFirst * 100).toFixed(0);
    if (avgSecond < avgFirst) {
      trendArrow = `<span class="trend-down">${pctChange}%</span>`;
    } else {
      trendArrow = `<span class="trend-up">+${pctChange}%</span>`;
    }
  }

  let html = `
    <div class="game-header"><h2>Trend Analysis</h2></div>
    <div class="summary-bar">
      <div class="stat"><span class="value">${totalGames}</span><span class="label">Games</span></div>
      <div class="stat"><span class="value">${totalMistakes}</span><span class="label">Total Mistakes</span></div>
      <div class="stat"><span class="value">${totalEv.toFixed(1)}</span><span class="label">Total EV Loss</span></div>
      ${avgEvPerTurn != null ? `<div class="stat"><span class="value">${avgEvPerTurn.toFixed(4)}</span><span class="label">Avg EV/Turn</span></div>` : ""}
      ${trendArrow ? `<div class="stat"><span class="value">${trendArrow}</span><span class="label">EV/Turn Trend</span></div>` : ""}
    </div>
  `;

  // Chart 1: EV per turn over time
  if (gamesWithTurns.length >= 2) {
    html += `<div class="trend-chart-card">
      <h3>EV Loss per Turn</h3>
      <div class="trend-chart">${renderLineChart(gamesWithTurns, "ev_per_turn", {
        color: "#4fc3f7",
        avgColor: "#4fc3f740",
        format: v => v.toFixed(3),
        yLabel: "EV/Turn",
      })}</div>
    </div>`;
  }

  // Chart 2: Severity breakdown over time
  html += `<div class="trend-chart-card">
    <h3>Mistakes by Severity</h3>
    <div class="trend-chart">${renderStackedBarChart(games)}</div>
  </div>`;

  // Chart 3: Category EV breakdown across all games
  html += renderCategoryTrend(games);

  content.innerHTML = html;
}

function renderLineChart(games, field, opts) {
  const W = 700, H = 200, PAD = { top: 20, right: 20, bottom: 40, left: 55 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const values = games.map(g => g[field]);
  const minV = Math.min(...values) * 0.85;
  const maxV = Math.max(...values) * 1.1;
  const range = maxV - minV || 1;

  // Compute 3-game moving average
  const avg = [];
  for (let i = 0; i < values.length; i++) {
    const window = values.slice(Math.max(0, i - 2), i + 1);
    avg.push(window.reduce((a, b) => a + b, 0) / window.length);
  }

  function x(i) { return PAD.left + (i / (games.length - 1)) * plotW; }
  function y(v) { return PAD.top + plotH - ((v - minV) / range) * plotH; }

  let svg = `<svg viewBox="0 0 ${W} ${H}" class="trend-svg">`;

  // Y grid lines
  const yTicks = 5;
  for (let i = 0; i <= yTicks; i++) {
    const val = minV + (range * i / yTicks);
    const yy = y(val);
    svg += `<line x1="${PAD.left}" y1="${yy}" x2="${W - PAD.right}" y2="${yy}" stroke="var(--border)" stroke-width="0.5"/>`;
    svg += `<text x="${PAD.left - 8}" y="${yy + 4}" text-anchor="end" fill="var(--text-dim)" font-size="10">${opts.format(val)}</text>`;
  }

  // Moving average area
  if (avg.length >= 2) {
    let areaPath = `M${x(0)},${y(avg[0])}`;
    for (let i = 1; i < avg.length; i++) areaPath += ` L${x(i)},${y(avg[i])}`;
    svg += `<polyline points="${avg.map((v, i) => `${x(i)},${y(v)}`).join(" ")}" fill="none" stroke="${opts.avgColor}" stroke-width="2" stroke-dasharray="4,3"/>`;
  }

  // Main line
  const points = values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
  svg += `<polyline points="${points}" fill="none" stroke="${opts.color}" stroke-width="2"/>`;

  // Dots + labels
  for (let i = 0; i < games.length; i++) {
    const cx = x(i), cy = y(values[i]);
    svg += `<circle cx="${cx}" cy="${cy}" r="4" fill="${opts.color}" stroke="var(--bg)" stroke-width="1.5"/>`;
    // X label (date)
    const dateLabel = games[i].date.slice(5); // MM-DD
    svg += `<text x="${cx}" y="${H - 5}" text-anchor="middle" fill="var(--text-dim)" font-size="9" transform="rotate(-30,${cx},${H - 5})">${dateLabel}</text>`;
  }

  // Y axis label
  svg += `<text x="12" y="${PAD.top + plotH / 2}" text-anchor="middle" fill="var(--text-dim)" font-size="10" transform="rotate(-90,12,${PAD.top + plotH / 2})">${opts.yLabel}</text>`;

  svg += `</svg>`;
  return svg;
}

function renderStackedBarChart(games) {
  const W = 700, H = 200, PAD = { top: 20, right: 20, bottom: 40, left: 55 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const sevKeys = ["???", "??", "?"];
  const sevColors = { "???": "var(--sev-major)", "??": "var(--sev-medium)", "?": "var(--sev-minor)" };

  const maxTotal = Math.max(...games.map(g => {
    const sev = g.by_severity || {};
    return (sev["???"] || 0) + (sev["??"] || 0) + (sev["?"] || 0);
  }));

  const barW = Math.min(30, (plotW / games.length) * 0.7);
  const gap = plotW / games.length;

  function y(v) { return PAD.top + plotH - (v / (maxTotal || 1)) * plotH; }

  let svg = `<svg viewBox="0 0 ${W} ${H}" class="trend-svg">`;

  // Y grid
  const yTicks = 4;
  for (let i = 0; i <= yTicks; i++) {
    const val = Math.round(maxTotal * i / yTicks);
    const yy = y(val);
    svg += `<line x1="${PAD.left}" y1="${yy}" x2="${W - PAD.right}" y2="${yy}" stroke="var(--border)" stroke-width="0.5"/>`;
    svg += `<text x="${PAD.left - 8}" y="${yy + 4}" text-anchor="end" fill="var(--text-dim)" font-size="10">${val}</text>`;
  }

  // Bars
  for (let i = 0; i < games.length; i++) {
    const sev = games[i].by_severity || {};
    const cx = PAD.left + gap * i + gap / 2;
    let bottom = PAD.top + plotH;

    for (const key of sevKeys) {
      const count = sev[key] || 0;
      if (count === 0) continue;
      const barH = (count / (maxTotal || 1)) * plotH;
      const top = bottom - barH;
      svg += `<rect x="${cx - barW / 2}" y="${top}" width="${barW}" height="${barH}" fill="${sevColors[key]}" rx="2" opacity="0.85"/>`;
      if (barH > 14) {
        svg += `<text x="${cx}" y="${top + barH / 2 + 4}" text-anchor="middle" fill="var(--bg)" font-size="9" font-weight="700">${count}</text>`;
      }
      bottom = top;
    }

    // X label
    const dateLabel = games[i].date.slice(5);
    svg += `<text x="${cx}" y="${H - 5}" text-anchor="middle" fill="var(--text-dim)" font-size="9" transform="rotate(-30,${cx},${H - 5})">${dateLabel}</text>`;
  }

  // Legend
  let lx = W - PAD.right - 150;
  for (const key of sevKeys) {
    svg += `<rect x="${lx}" y="5" width="10" height="10" fill="${sevColors[key]}" rx="2"/>`;
    svg += `<text x="${lx + 14}" y="14" fill="var(--text-dim)" font-size="10">${key}</text>`;
    lx += 45;
  }

  svg += `</svg>`;
  return svg;
}

function renderCategoryTrend(games) {
  // Aggregate category EV across all games
  const groupTotals = {};
  for (const g of games) {
    for (const [grp, data] of Object.entries(g.by_group || {})) {
      if (!groupTotals[grp]) groupTotals[grp] = { count: 0, ev: 0 };
      groupTotals[grp].count += data.count;
      groupTotals[grp].ev += data.ev;
    }
  }

  const sorted = Object.entries(groupTotals).sort((a, b) => b[1].ev - a[1].ev);
  if (sorted.length === 0) return "";

  const maxEv = sorted[0][1].ev;

  let html = `<div class="trend-chart-card"><h3>EV Loss by Skill Area (All Games)</h3><div class="trend-bars">`;
  for (const [grp, data] of sorted) {
    const color = GROUP_COLORS[grp] || "#888";
    const pct = (data.ev / maxEv * 100).toFixed(0);
    html += `<div class="trend-bar-row">
      <span class="trend-bar-label" style="color:${color}">${grp}</span>
      <div class="trend-bar-track">
        <div class="trend-bar-fill" style="width:${pct}%;background:${color}"></div>
      </div>
      <span class="trend-bar-value">${data.ev.toFixed(1)} EV <span class="trend-bar-count">(${data.count})</span></span>
    </div>`;
  }
  html += `</div></div>`;

  // Per-game category breakdown table (sparkline style)
  html += `<div class="trend-chart-card"><h3>Skill Area per Game</h3><div class="trend-chart">`;
  html += renderGroupStackedChart(games, sorted.map(s => s[0]));
  html += `</div></div>`;

  return html;
}

function renderGroupStackedChart(games, groups) {
  const W = 700, H = 200, PAD = { top: 20, right: 20, bottom: 40, left: 55 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const maxEv = Math.max(...games.map(g => g.total_ev_loss || 0));
  const barW = Math.min(30, (plotW / games.length) * 0.7);
  const gap = plotW / games.length;

  function y(v) { return PAD.top + plotH - (v / (maxEv || 1)) * plotH; }

  let svg = `<svg viewBox="0 0 ${W} ${H}" class="trend-svg">`;

  // Y grid
  const yTicks = 4;
  for (let i = 0; i <= yTicks; i++) {
    const val = (maxEv * i / yTicks).toFixed(0);
    const yy = y(parseFloat(val));
    svg += `<line x1="${PAD.left}" y1="${yy}" x2="${W - PAD.right}" y2="${yy}" stroke="var(--border)" stroke-width="0.5"/>`;
    svg += `<text x="${PAD.left - 8}" y="${yy + 4}" text-anchor="end" fill="var(--text-dim)" font-size="10">${val}</text>`;
  }

  // Stacked bars
  for (let i = 0; i < games.length; i++) {
    const cx = PAD.left + gap * i + gap / 2;
    let bottom = PAD.top + plotH;

    for (const grp of groups) {
      const data = (games[i].by_group || {})[grp];
      if (!data || data.ev <= 0) continue;
      const barH = (data.ev / (maxEv || 1)) * plotH;
      const top = bottom - barH;
      const color = GROUP_COLORS[grp] || "#888";
      svg += `<rect x="${cx - barW / 2}" y="${top}" width="${barW}" height="${barH}" fill="${color}" rx="1" opacity="0.8"/>`;
      bottom = top;
    }

    const dateLabel = games[i].date.slice(5);
    svg += `<text x="${cx}" y="${H - 5}" text-anchor="middle" fill="var(--text-dim)" font-size="9" transform="rotate(-30,${cx},${H - 5})">${dateLabel}</text>`;
  }

  // Legend
  let lx = PAD.left;
  for (const grp of groups) {
    const color = GROUP_COLORS[grp] || "#888";
    svg += `<rect x="${lx}" y="4" width="10" height="10" fill="${color}" rx="2"/>`;
    svg += `<text x="${lx + 13}" y="13" fill="var(--text-dim)" font-size="9">${grp}</text>`;
    lx += grp.length * 7 + 22;
  }

  svg += `</svg>`;
  return svg;
}

// --- Init ---

document.addEventListener("DOMContentLoaded", async () => {
  const catRes = await fetch("/api/categories");
  CATEGORY_INFO = await catRes.json();
  fetchGames();
});
