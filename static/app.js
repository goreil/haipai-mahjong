const CATEGORIES = [
  "", "1A",
  "2A",
  "3A", "3B", "3C",
  "4A", "4B", "4C",
  "5A", "5B",
  "6A", "6B",
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

function catDesc(code) {
  const info = CATEGORY_INFO[code];
  if (!info) return code;
  let desc = info.desc || "";
  if (info.study) desc += ` (${info.study})`;
  return desc;
}

const GROUP_COLORS = {
  "Efficiency": "#4a9eff",
  "Value Tiles": "#6db3e8",
  "Strategy": "#ff6b6b",
  "Meld": "#ffa94d",
  "Riichi": "#a855f7",
  "Kan": "#22c55e",
};

const OUTCOME_EMOJI = { ":D": "\u{1F60E}", ":)": "\u{1F642}", ":|": "\u{1F610}", ":(": "\u{1F61E}" };

let csrfToken = "";
let isAnonymous = false;
let practiceOptIn = false;
let practiceSource = "all"; // "mine" or "all"

let state = {
  games: [],
  currentGame: null,
  currentGameData: null,
  showMinor: false,
  showMedium: false,
};

let practice = {
  problem: null,
  answered: false,
  userPick: null,
  correct: 0,
  total: 0,
  poolSize: 0,
  filterSeverity: "",
  filterGroup: "",
  filterDefense: false,
  filterCalcAgree: false,
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

// Dora indicator -> actual dora tile mapping
const NEXT_TILE = {
  "1m":"2m","2m":"3m","3m":"4m","4m":"5m","5m":"6m","6m":"7m","7m":"8m","8m":"9m","9m":"1m",
  "1p":"2p","2p":"3p","3p":"4p","4p":"5p","5p":"6p","6p":"7p","7p":"8p","8p":"9p","9p":"1p",
  "1s":"2s","2s":"3s","3s":"4s","4s":"5s","5s":"6s","6s":"7s","7s":"8s","8s":"9s","9s":"1s",
  "E":"S","S":"W","W":"N","N":"E", "P":"F","F":"C","C":"P",
  "5mr":"6m","5pr":"6p","5sr":"6s",
};

function getDoraTiles(indicators) {
  if (!indicators) return new Set();
  const doras = new Set();
  for (const ind of indicators) {
    const d = NEXT_TILE[ind];
    if (d) doras.add(d);
    // Red fives are always dora
  }
  return doras;
}

// Normalize tile for comparison (red five -> base tile)
function tileBase(t) {
  if (t === "5mr") return "5m";
  if (t === "5pr") return "5p";
  if (t === "5sr") return "5s";
  return t;
}

function renderTile(t, extraClass = "", titleOverride = null) {
  const cls = ["tile", extraClass].filter(Boolean).join(" ");
  const title = titleOverride || t;
  return `<img class="${cls}" src="${tileSrc(t)}" alt="${t}" title="${title}" data-tile="${tileBase(t)}">`;
}

function renderHand(tiles, draw, safetyRatings, doraTiles) {
  if (!tiles || !tiles.length) return "";
  return tiles.map((t, i) => {
    let extra = "";
    if (draw && i === tiles.length - 1 && t === draw) extra = "draw";
    const sr = getSafetyRating(safetyRatings, t);
    if (sr != null) extra += ` ${safetyClass(sr)}`;
    // Red fives are always dora; also check if tile matches indicator dora
    if (t === "5mr" || t === "5pr" || t === "5sr" || (doraTiles && doraTiles.has(tileBase(t)))) {
      extra += " dora-highlight";
    }
    const title = sr != null ? `${t} — ${safetyLabel(sr)} (${sr}/15)` : null;
    return renderTile(t, extra, title);
  }).join("");
}

// --- Board context rendering ---

const WIND_DISPLAY = { "E": "East", "S": "South", "W": "West", "N": "North" };
const SEAT_NAMES = ["East", "South", "West", "North"];

function renderBoardContext(m) {
  const b = m.board_state;
  if (!b) return "";

  let html = `<div class="board-context">`;

  // Wind + Dora bar
  html += `<div class="board-info-bar">`;
  if (b.round_wind) {
    html += `<span class="wind-badge round-wind" title="Round wind">${renderTile(b.round_wind, "tile-sm wind-tile")}<span class="wind-label">Round</span></span>`;
  }
  if (b.seat_wind) {
    html += `<span class="wind-badge seat-wind" title="Seat wind">${renderTile(b.seat_wind, "tile-sm wind-tile")}<span class="wind-label">Seat</span></span>`;
  }
  if (b.dora_indicators && b.dora_indicators.length) {
    html += `<span class="dora-section"><span class="dora-label">Dora</span>`;
    for (const d of b.dora_indicators) {
      html += renderTile(d, "tile-sm dora-indicator");
    }
    html += `</span>`;
  }
  html += `</div>`;

  // Build seat -> melds lookup for inline rendering
  const meldsBySeat = {};
  if (b.opponent_melds) {
    for (const om of b.opponent_melds) {
      meldsBySeat[om.seat] = om.melds;
    }
  }

  // All player discards + inline melds (collapsible)
  // Auto-expand for strategy/defense/meld/riichi/kan, when opponent in riichi, or uncategorized
  if (b.all_discards && b.all_discards.length) {
    const hasDiscards = b.all_discards.some(d => d.discards.length > 0 || meldsBySeat[d.seat]);
    if (hasDiscards) {
      const doraTiles = getDoraTiles(b.dora_indicators);
      const cat = m.category || "";
      const expandDiscards = !cat || m.safety_ratings || /^[3-6]/.test(cat);
      html += `<details class="all-discards"${expandDiscards ? " open" : ""}>`;

      html += `<summary>Discards</summary>`;
      for (const d of b.all_discards) {
        const seatMelds = meldsBySeat[d.seat];
        if (!d.discards.length && !seatMelds) continue;
        const seatName = SEAT_NAMES[d.seat] || `P${d.seat}`;
        html += `<div class="discard-row">`;
        html += `<span class="discard-label">${seatName}</span>`;
        html += `<span class="tiles">`;
        for (let di = 0; di < d.discards.length; di++) {
          const isRiichi = di === d.riichi_idx;
          const isDora = d.discards[di] === "5mr" || d.discards[di] === "5pr" || d.discards[di] === "5sr"
            || doraTiles.has(tileBase(d.discards[di]));
          const cls = `action-tile-sm${isRiichi ? " riichi-tile" : ""}${isDora ? " dora-highlight" : ""}`;
          html += renderTile(d.discards[di], cls);
        }
        html += `</span>`;
        if (seatMelds) {
          html += `<span class="inline-melds">`;
          for (const meld of seatMelds) {
            const tiles = [...(meld.consumed || [])];
            if (meld.pai) tiles.push(meld.pai);
            html += `<span class="meld-group">${meld.type} ${tiles.map(t => renderTile(t, "action-tile-sm")).join("")}</span> `;
          }
          html += `</span>`;
        }
        html += `</div>`;
      }
      html += `</details>`;
    }
  }

  // Scores inline in info bar
  if (b.scores && b.scores.length) {
    html += `<div class="scores-bar">`;
    for (let i = 0; i < b.scores.length; i++) {
      const name = SEAT_NAMES[i] || `P${i}`;
      html += `<span class="score-item"><span class="score-seat">${name}</span> ${b.scores[i].toLocaleString()}</span>`;
    }
    html += `</div>`;
  }

  html += `</div>`;
  return html;
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

function sevTooltip(sev) {
  if (sev === "???") return "Major mistake (>0.10 EV loss)";
  if (sev === "??") return "Medium mistake (0.05–0.10 EV)";
  if (sev === "?") return "Minor mistake (<0.05 EV)";
  return "";
}

// --- Game rating ---

function computeRatingThresholds() {
  // Compute percentile thresholds from all games with ev_per_decision
  const evpts = state.games
    .map(g => (g.summary || {}).ev_per_decision)
    .filter(v => v != null)
    .sort((a, b) => a - b);
  if (evpts.length < 3) return { p25: 0.14, p50: 0.19 };
  const p25 = evpts[Math.floor(evpts.length * 0.25)];
  const p50 = evpts[Math.floor(evpts.length * 0.50)];
  return { p25, p50 };
}

function gameRating(summary) {
  if (!summary || !summary.total_decisions) return { icon: "", label: "", cls: "" };
  const evpt = summary.ev_per_decision;
  if (evpt == null) return { icon: "", label: "", cls: "" };

  const th = computeRatingThresholds();
  // Top 25%: excellent
  if (evpt <= th.p25) return { icon: "\u2605", label: "Great game", cls: "rating-excellent" };
  // Top 50%: good
  if (evpt <= th.p50) return { icon: "\u2606", label: "Solid game", cls: "rating-great" };
  return { icon: "", label: "", cls: "" };
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
    <th class="mortal-col" title="AI's strategic evaluation (higher = better)">Mortal Q</th>
    <th class="mortal-col" title="AI's confidence in this discard">Prob</th>
    <th class="cpp-col" title="Expected score from pure tile efficiency">Exp Score</th>
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
        html += `<td class="safety-col ${safetyClass(sr)}" title="${sr}/15">${safetyLabel(sr)}</td>`;
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

function safetyLabel(rating) {
  if (rating == null) return "";
  if (rating >= 15) return "Genbutsu";
  if (rating >= 14) return "Suji terminal / dead honor";
  if (rating >= 13) return "Honor (1 left) / suji terminal";
  if (rating >= 11) return "Suji terminal";
  if (rating >= 10) return "Honor (2 left)";
  if (rating >= 9) return "Suji 4-5-6";
  if (rating >= 8) return "Suji 2/8";
  if (rating >= 7) return "Suji 3/7";
  if (rating >= 6) return "Honor (3 left)";
  if (rating >= 5) return "Non-suji terminal";
  if (rating >= 3) return "Non-suji 2/8";
  if (rating >= 2) return "Non-suji 3/7";
  return "Non-suji 4-5-6";
}

// --- API ---

function apiPost(url, body) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
    body: JSON.stringify(body),
  });
}

function apiDelete(url) {
  return fetch(url, { method: "DELETE", headers: { "X-CSRFToken": csrfToken } });
}

async function fetchGames() {
  const res = await fetch("/api/games");
  state.games = await res.json();
  renderGameList();
  if (state.games.length === 0 && !state.currentGame) {
    showOnboarding();
  }
}

function showOnboarding() {
  document.getElementById("content").innerHTML = `
    <div class="onboarding">
      <h2>Welcome to Haipai</h2>
      <p>Haipai analyzes your Riichi Mahjong games using Mortal AI to help you study your mistakes, track improvement over time, and practice your weak spots.</p>
      <h3>How to add your first game</h3>
      <ol>
        <li>Play a game on <a href="https://tenhou.net" target="_blank">Tenhou</a> or <a href="https://mahjongsoul.game.yo-star.com" target="_blank">Mahjong Soul</a></li>
        <li>Go to <a href="https://mjai.ekyu.moe" target="_blank">mjai.ekyu.moe</a> and paste your replay link</li>
        <li>Wait for Mortal AI to finish analysis</li>
        <li>Download the analysis JSON:
          <ul class="onboarding-sub">
            <li>In the address bar, find the part that says <code>/report/...json</code></li>
            <li>Open that path directly: <code>https://mjai.ekyu.moe/report/abc123.json</code></li>
            <li>You'll see a page of raw data &mdash; press <b>Ctrl+S</b> (Cmd+S on Mac) to save it</li>
          </ul>
        </li>
        <li>Click <strong>+ Add Game</strong> below and upload the saved file</li>
      </ol>
      <button class="btn btn-primary" onclick="showAddModal()">+ Add Game</button>
    </div>
  `;
}

async function fetchGame(id) {
  const res = await fetch(`/api/games/${id}`);
  state.currentGameData = await res.json();
  state.currentGame = id;
  renderGame();
}

async function saveAnnotation(gameId, round, turn, index, category, note) {
  const res = await apiPost(`/api/games/${gameId}/annotate`, { round, turn, index, category, note });
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

async function addGameWithProgress(mortalData, date, onProgress) {
  if (onProgress) onProgress({ step: "categorizing", message: "Adding game and categorizing..." });
  const res = await apiPost("/api/games/add", { mortal_data: mortalData, date: date || undefined });
  if (!res.ok) {
    const text = await res.text();
    try { return JSON.parse(text); } catch { return { error: `Server error ${res.status}: ${text.slice(0, 200)}` }; }
  }
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
    const noMajor = !(s.by_severity || {})["???"];
    const rating = gameRating(s);
    const dateObj = new Date(g.date + "T00:00:00");
    const shortDate = dateObj.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    return `
      <div class="game-item ${active}" onclick="fetchGame(${g.id})">
        <div class="date">${shortDate}${rating.icon ? ` <span class="game-rating-icon" title="${rating.label}">${rating.icon}</span>` : ""}</div>
        <div class="stats">
          ${s.total_mistakes || 0} mistakes &middot; ${(s.total_ev_loss || 0).toFixed(2)} EV
          ${s.total_decisions ? ` &middot; ${s.ev_per_decision.toFixed(4)}/D` : ""}
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

  const dateObj = new Date(game.date + "T00:00:00");
  const displayDate = dateObj.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  let html = `
    <div class="game-header">
      <h2>${displayDate}
        <button class="btn btn-delete" onclick="deleteGame(${state.currentGame})" title="Delete game">Delete</button>
      </h2>
      ${game.log_url ? `<div class="log-link"><a href="${game.log_url}" target="_blank">${game.log_url}</a></div>` : ""}
    </div>

    <div class="summary-bar">
      <div class="stat"><span class="value">${s.total_mistakes || 0}</span><span class="label">Mistakes</span></div>
      <div class="stat"><span class="value">${(s.total_ev_loss || 0).toFixed(2)}</span><span class="label">EV Loss</span></div>
      ${s.total_decisions ? `<div class="stat"><span class="value">${s.total_decisions}</span><span class="label">Decisions</span></div>
      <div class="stat"><span class="value">${s.ev_per_decision.toFixed(4)}</span><span class="label">EV/Decision</span></div>` : ""}
      <div class="stat"><span class="value" style="color:var(--sev-major)">${sev["???"] || 0}</span><span class="label">???</span></div>
      <div class="stat"><span class="value" style="color:var(--sev-medium)">${sev["??"] || 0}</span><span class="label">??</span></div>
      <div class="stat"><span class="value" style="color:var(--sev-minor)">${sev["?"] || 0}</span><span class="label">?</span></div>
    </div>
  `;

  // Positive feedback banner
  const rating = gameRating(s);
  if (rating.icon) {
    const cleanRounds = game.rounds.filter(r => r.mistakes.length === 0).length;
    html += `<div class="game-rating ${rating.cls}">
      <span class="game-rating-star">${rating.icon}</span>
      <span>${rating.label}</span>
      ${cleanRounds > 0 ? `<span class="game-rating-detail">${cleanRounds}/${game.rounds.length} clean rounds</span>` : ""}
    </div>`;
  }

  // Filter banner (7b): show when severity filters hide some mistakes
  const totalMistakes = game.rounds.reduce((sum, r) => sum + r.mistakes.length, 0);
  const visibleMistakes = game.rounds.reduce((sum, r) => sum + r.mistakes.filter(m => {
    if (m.severity === "?" && !state.showMinor) return false;
    if (m.severity === "??" && !state.showMedium) return false;
    return true;
  }).length, 0);
  if (totalMistakes > 0 && visibleMistakes < totalMistakes) {
    const hidden = totalMistakes - visibleMistakes;
    html += `<div class="filter-banner">Showing ${visibleMistakes} of ${totalMistakes} mistakes. ${hidden} hidden by severity filter.</div>`;
  }

  // Rounds
  for (const rnd of game.rounds) {
    const visible = rnd.mistakes.filter(m => {
      if (m.severity === "?" && !state.showMinor) return false;
      if (m.severity === "??" && !state.showMedium) return false;
      return true;
    });

    const outcomeStr = rnd.outcome ? (OUTCOME_EMOJI[rnd.outcome] || rnd.outcome) : "";
    const turnStr = rnd.turn_count ? `T${rnd.turn_count}` : "";

    const isClean = rnd.mistakes.length === 0;
    html += `<div class="round${isClean ? " round-clean" : ""}">`;
    html += `<div class="round-header">
      <span>${rnd.round}${turnStr}</span>
      ${outcomeStr ? `<span class="outcome">${outcomeStr}</span>` : ""}
      ${isClean ? '<span class="clean-badge">Clean</span>' : ""}
      ${!isClean && visible.length !== rnd.mistakes.length ?
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
      html += `<span class="severity ${sc}" title="${sevTooltip(m.severity)}">${m.severity}</span>`;
      html += `<span class="ev-loss">${m.ev_loss.toFixed(2)} EV</span>`;
      if (m.category) {
        const grp = catGroup(m.category);
        const color = GROUP_COLORS[grp] || "#888";
        const desc = catDesc(m.category);
        html += `<span class="cat-badge" style="background:${color}20;color:${color};border:1px solid ${color}40" title="${desc}">${catLabel(m.category)}</span>`;
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
        const doraTiles = m.board_state ? getDoraTiles(m.board_state.dora_indicators) : new Set();
        html += `<div class="hand-row">
          <span class="label">Hand</span>
          ${m.safety_ratings ? '<span class="defense-badge">Riichi</span>' : ''}
          <span class="tiles">${renderHand(m.hand, m.draw, m.safety_ratings, doraTiles)}</span>
        </div>`;
      }

      // Melds
      if (m.melds && m.melds.length) {
        html += `<div class="hand-row">
          <span class="label">Melds</span>
          <span class="tiles">`;
        for (const meld of m.melds) {
          const meldTiles = [...(meld.consumed || [])];
          if (meld.pai) meldTiles.push(meld.pai);
          html += `<span class="meld-group">${meld.type} ${meldTiles.map(t => renderTile(t, "action-tile-sm")).join("")}</span> `;
        }
        html += `</span></div>`;
      }

      // Board context (dora, winds, all discards, scores, opponent melds)
      html += renderBoardContext(m);

      // Fallback: old opponent_discards (for mistakes without board_state)
      if (!m.board_state && m.opponent_discards && m.opponent_discards.length) {
        html += `<div class="opp-discards">`;
        for (const opp of m.opponent_discards) {
          const seatName = SEAT_NAMES[opp.seat] || `P${opp.seat}`;
          html += `<div class="opp-discard-row">`;
          html += `<span class="opp-label">${seatName}</span>`;
          html += `<span class="tiles">`;
          for (let di = 0; di < opp.discards.length; di++) {
            const isRiichi = di === opp.riichi_idx;
            html += renderTile(opp.discards[di], `action-tile-sm${isRiichi ? " riichi-tile" : ""}`);
          }
          html += `</span></div>`;
        }
        html += `</div>`;
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
        const label = c ? catLabel(c) : "Uncategorized";
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

// --- Sidebar toggle ---

function toggleSidebar() {
  document.querySelector(".sidebar").classList.toggle("collapsed");
}

// --- Add game modal ---

function showAddModal() {
  document.getElementById("add-modal").classList.add("show");
  document.getElementById("add-file").value = "";
  document.getElementById("add-date").value = "";
  document.getElementById("add-error").textContent = "";
}

function hideAddModal() {
  document.getElementById("add-modal").classList.remove("show");
}

async function submitAddGame() {
  const fileInput = document.getElementById("add-file");
  const date = document.getElementById("add-date").value.trim();
  const errEl = document.getElementById("add-error");
  const btn = document.getElementById("add-submit-btn");

  if (!fileInput.files.length) {
    errEl.textContent = "Select a Mortal analysis JSON file";
    return;
  }

  btn.disabled = true;
  errEl.textContent = "";

  // Show progress bar
  let progressEl = document.getElementById("add-progress");
  if (!progressEl) {
    progressEl = document.createElement("div");
    progressEl.id = "add-progress";
    progressEl.className = "add-progress";
    btn.parentElement.insertBefore(progressEl, btn);
  }
  progressEl.innerHTML = '<div class="add-progress-text">Parsing game...</div><div class="add-progress-bar"><div class="add-progress-fill"></div></div>';
  progressEl.style.display = "";

  try {
    const text = await fileInput.files[0].text();
    const mortalData = JSON.parse(text);

    const result = await addGameWithProgress(mortalData, date, (progress) => {
      const fill = progressEl.querySelector(".add-progress-fill");
      const label = progressEl.querySelector(".add-progress-text");
      if (progress.step === "parsing") {
        label.textContent = progress.message;
      } else if (progress.step === "categorizing") {
        const pct = progress.total > 0 ? Math.round((progress.done / progress.total) * 100) : 0;
        fill.style.width = pct + "%";
        label.textContent = `Analyzing decisions... ${progress.done}/${progress.total}`;
      }
    });

    btn.disabled = false;
    progressEl.style.display = "none";

    if (result.error) {
      errEl.textContent = result.error || result.message;
      return;
    }

    hideAddModal();
    await fetchGames();
    fetchGame(result.game_id);
  } catch (e) {
    btn.disabled = false;
    progressEl.style.display = "none";
    errEl.textContent = e.message;
  }
}

// --- Delete game ---

async function deleteGame(id) {
  if (!confirm(`Delete this game? This cannot be undone.`)) return;
  const res = await apiDelete(`/api/games/${id}`);
  const data = await res.json();
  if (data.ok) {
    state.currentGame = null;
    state.currentGameData = null;
    document.getElementById("content").innerHTML = '<div class="empty-state">Game deleted</div>';
    await fetchGames();
  }
}

// --- Import from games.json ---

// --- Trends ---

async function fetchTrends() {
  const res = await fetch("/api/trends");
  return await res.json();
}

function navigateHome() {
  state.currentGame = null;
  state.currentGameData = null;
  renderGameList();
  document.getElementById("content").innerHTML = '<div class="empty-state">Select a game to review</div>';
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
  const gamesWithDecisions = games.filter(g => g.ev_per_decision != null);
  const avgEvPerDecision = gamesWithDecisions.length > 0
    ? gamesWithDecisions.reduce((s, g) => s + g.ev_per_decision, 0) / gamesWithDecisions.length : null;

  // Trend direction (last 5 vs first 5 for ev_per_decision)
  let trendArrow = "";
  if (gamesWithDecisions.length >= 4) {
    const half = Math.floor(gamesWithDecisions.length / 2);
    const firstHalf = gamesWithDecisions.slice(0, half);
    const secondHalf = gamesWithDecisions.slice(-half);
    const avgFirst = firstHalf.reduce((s, g) => s + g.ev_per_decision, 0) / firstHalf.length;
    const avgSecond = secondHalf.reduce((s, g) => s + g.ev_per_decision, 0) / secondHalf.length;
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
      ${avgEvPerDecision != null ? `<div class="stat"><span class="value">${avgEvPerDecision.toFixed(4)}</span><span class="label">Avg EV/Decision</span></div>` : ""}
      ${trendArrow ? `<div class="stat"><span class="value">${trendArrow}</span><span class="label">EV/Decision Trend</span></div>` : ""}
    </div>
  `;

  // Personal best / recent performance
  if (gamesWithDecisions.length >= 3) {
    const sorted = [...gamesWithDecisions].sort((a, b) => a.ev_per_decision - b.ev_per_decision);
    const best = sorted[0];
    const recent = gamesWithDecisions.slice(-3);
    const recentAvg = recent.reduce((s, g) => s + g.ev_per_decision, 0) / recent.length;
    html += `<div class="summary-bar" style="margin-top:0">
      <div class="stat"><span class="value">${best.ev_per_decision.toFixed(4)}</span><span class="label">Best EV/D (${best.date.slice(5)})</span></div>
      <div class="stat"><span class="value">${recentAvg.toFixed(4)}</span><span class="label">Last 3 Avg</span></div>
      <div class="stat"><span class="value">${games.reduce((s, g) => s + ((g.by_severity || {})["???"] || 0), 0)}</span><span class="label">Total ??? Mistakes</span></div>
    </div>`;
  }

  // Chart 1: EV per decision over time
  if (gamesWithDecisions.length >= 2) {
    html += `<div class="trend-chart-card">
      <h3>EV Loss per Decision</h3>
      <div class="trend-chart">${renderLineChart(gamesWithDecisions, "ev_per_decision", {
        color: "#4fc3f7",
        avgColor: "#4fc3f740",
        format: v => v.toFixed(3),
        yLabel: "EV/Decision",
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

// --- Practice mode ---

async function fetchPractice() {
  const params = new URLSearchParams();
  if (practice.filterSeverity) params.set("severity", practice.filterSeverity);
  if (practice.filterDefense) params.set("defense", "1");
  // Always restrict to efficiency categories (1A) for practice
  params.set("calc_agree", "1");
  const qs = params.toString();
  const usePublic = isAnonymous || practiceSource === "all";
  const endpoint = usePublic ? "/api/practice/public" : "/api/practice";
  const res = await fetch(`${endpoint}${qs ? "?" + qs : ""}`);
  if (!res.ok) return null;
  return await res.json();
}

async function showPractice() {
  state.currentGame = null;
  state.currentGameData = null;
  renderGameList();
  const content = document.getElementById("content");
  content.innerHTML = '<div class="empty-state">Loading practice problem...</div>';

  const data = await fetchPractice();
  if (!data || data.error) {
    practice.problem = null;
    practice.poolSize = 0;
  } else {
    practice.problem = data;
    practice.poolSize = data.pool_size;
  }
  practice.answered = false;
  practice.userPick = null;
  renderPractice();
}

function renderPracticeHand(tiles, draw, doraTiles) {
  if (!tiles || !tiles.length) return "";
  return tiles.map((t, i) => {
    const isDraw = draw && i === tiles.length - 1 && t === draw;
    let extra = isDraw ? "draw" : "";
    if (t === "5mr" || t === "5pr" || t === "5sr" || (doraTiles && doraTiles.has(tileBase(t)))) {
      extra += " dora-highlight";
    }
    // Escape single quotes in tile names for onclick
    const safe = t.replace(/'/g, "\\'");
    return `<span class="practice-tile" onclick="submitPracticeAnswer('${safe}')">${renderTile(t, extra)}</span>`;
  }).join("");
}

function submitPracticeAnswer(tile) {
  if (practice.answered) return;
  practice.answered = true;
  practice.userPick = tile;
  practice.total++;

  const m = practice.problem.mistake;
  const expected = m.expected.pai;
  // Correct if matches expected (normalize red fives)
  const isCorrect = tile === expected || normalizeRed(tile) === normalizeRed(expected);
  if (isCorrect) practice.correct++;

  // Record result for spaced repetition (own mistakes only)
  if (!isAnonymous && practiceSource === "mine" && practice.problem.mistake_id) {
    apiPost("/api/practice/result", { mistake_id: practice.problem.mistake_id, correct: isCorrect });
  }

  renderPractice();
}

function renderPractice() {
  const content = document.getElementById("content");
  const p = practice.problem;

  let html = `
    <div class="practice-header">
      <h2>Tile Efficiency Practice</h2>
      <div class="practice-score">
        <span class="practice-score-num">${practice.correct}</span>/<span>${practice.total}</span> correct
        <span class="practice-pool">${practice.poolSize} problems</span>
      </div>
    </div>
    <p class="practice-explanation">Practice hand-building decisions where the correct tile can be determined from your hand alone.</p>
    ${isAnonymous ? '<div class="practice-login-banner">Problems drawn from community pool. <a href="/register">Register</a> or <a href="/login">log in</a> to practice your own mistakes and track progress.</div>' : ''}
    <div class="practice-filters">
      ${!isAnonymous ? `<label class="practice-filter-check"><input type="checkbox" ${practiceSource === "mine" ? "checked" : ""} onchange="setPracticeSource(this.checked ? 'mine' : 'all')"> My mistakes only</label>` : ''}
      <select onchange="setPracticeFilter('severity', this.value)">
        <option value="" ${!practice.filterSeverity ? "selected" : ""}>All severity</option>
        <option value="???" ${practice.filterSeverity === "???" ? "selected" : ""}>??? only</option>
        <option value="??" ${practice.filterSeverity === "??" ? "selected" : ""}>?? only</option>
      </select>
      <label class="practice-filter-check"><input type="checkbox" ${practice.filterDefense ? "checked" : ""} onchange="setPracticeFilter('defense', this.checked)"> Riichi only</label>
      ${!isAnonymous ? `<label class="practice-filter-check practice-opt-in"><input type="checkbox" ${practiceOptIn ? "checked" : ""} onchange="togglePracticeOptIn(this.checked)"> Share my games in community pool</label>` : ''}
    </div>`;

  if (!p) {
    const hint = practiceSource === "mine"
      ? "No eligible problems in your games. Uncheck \"My mistakes only\" to try the community pool."
      : "No problems available yet. Users need to opt in to share their games.";
    html += `<div class="empty-state">${hint}</div>`;
    content.innerHTML = html;
    return;
  }

  const m = p.mistake;
  const answered = practice.answered;

  const sc = sevClass(m.severity);
  const shantenStr = m.shanten != null ? `${m.shanten}-shanten` : "";

  html += `

    <div class="practice-context">
      ${p.game_date ? `<span>${p.game_date}</span>` : ''}
      <span>${p.round}</span>
      <span class="severity ${sc}" title="${sevTooltip(m.severity)}">${m.severity}</span>
      ${shantenStr ? `<span class="shanten">${shantenStr}</span>` : ""}
      <span class="ev-loss">${m.ev_loss.toFixed(2)} EV</span>
    </div>
  `;

  // Melds
  if (m.melds && m.melds.length) {
    html += `<div class="practice-melds">`;
    for (const meld of m.melds) {
      const tiles = [...(meld.consumed || [])];
      if (meld.pai) tiles.push(meld.pai);
      html += `<span class="practice-meld">${meld.type} ${tiles.map(t => renderTile(t, "action-tile-sm")).join("")}</span>`;
    }
    html += `</div>`;
  }

  // Hand
  const doraTiles = m.board_state ? getDoraTiles(m.board_state.dora_indicators) : new Set();

  if (answered) {
    // Show hand with answer indicators
    html += `<div class="practice-hand-area">`;
    html += `<div class="hand-row"><span class="label">Hand</span>`;
    if (m.safety_ratings) html += `<span class="defense-badge">Riichi</span>`;
    html += `<span class="tiles">`;
    const expected = m.expected.pai;
    const actual = m.actual.pai;
    html += m.hand.map((t, i) => {
      const isDraw = m.draw && i === m.hand.length - 1 && t === m.draw;
      let cls = isDraw ? "draw" : "";
      // Safety colors
      const sr = getSafetyRating(m.safety_ratings, t);
      if (sr != null) cls += ` ${safetyClass(sr)}`;
      // Dora highlighting
      if (t === "5mr" || t === "5pr" || t === "5sr" || doraTiles.has(tileBase(t))) cls += " dora-highlight";
      const title = sr != null ? `${t} — ${safetyLabel(sr)} (${sr}/15)` : t;

      // Answer highlight
      const isUserPick = t === practice.userPick || normalizeRed(t) === normalizeRed(practice.userPick);
      const isExpected = t === expected || normalizeRed(t) === normalizeRed(expected);
      let marker = "";
      if (isExpected) marker = "practice-correct";
      if (isUserPick && !isExpected) marker = "practice-wrong";

      return `<span class="practice-tile-result ${marker}">${renderTile(t, cls, title)}</span>`;
    }).join("");
    html += `</span></div>`;

    // Board context
    html += renderBoardContext(m);

    html += `</div>`; // .practice-hand-area
  } else {
    // Clickable hand
    html += `<div class="practice-hand-area">`;
    html += `<div class="practice-prompt">Pick a tile to discard</div>`;
    html += `<div class="hand-row"><span class="label">Hand</span>`;
    html += `<span class="tiles">${renderPracticeHand(m.hand, m.draw, doraTiles)}</span>`;
    html += `</div>`;
    // Board context (dora, discards, etc.)
    html += renderBoardContext(m);
    html += `</div>`;
  }

  // Answer section
  if (answered) {
    const isCorrect = normalizeRed(practice.userPick) === normalizeRed(m.expected.pai);
    html += `<div class="practice-result ${isCorrect ? "practice-result-correct" : "practice-result-wrong"}">`;
    if (isCorrect) {
      html += `<div class="practice-result-label">Correct!</div>`;
    } else {
      html += `<div class="practice-result-label">Mortal recommends: ${renderTile(m.expected.pai, "action-tile")}</div>`;
    }
    html += `<div class="practice-result-detail">`;
    html += `<span>You picked: </span><span class="played">${renderTile(practice.userPick, "action-tile")}</span>`;
    html += `<span class="arrow"> &rarr; </span>`;
    html += `<span>Original play: </span><span class="played">${renderTile(m.actual.pai, "action-tile")}</span>`;
    if (m.category) {
      const grp = catGroup(m.category);
      const color = GROUP_COLORS[grp] || "#888";
      html += ` <span class="cat-badge" style="background:${color}20;color:${color};border:1px solid ${color}40">${catLabel(m.category)}</span>`;
    }
    html += `</div>`;

    // EV comparison table
    if (m.top_actions && m.top_actions.length && m.cpp_stats && m.cpp_stats.length) {
      html += renderEvComparison(m);
    } else if (m.top_actions && m.top_actions.length) {
      html += `<div class="top-actions">`;
      for (const a of m.top_actions) {
        html += `<span class="top-action">${renderAction(a.action)} <b>${a.q_value.toFixed(2)}</b> <span class="prob">${(a.prob * 100).toFixed(0)}%</span></span>`;
      }
      html += `</div>`;
    }

    // Note if present
    if (m.note) {
      html += `<div class="practice-note">${m.note}</div>`;
    }

    html += `</div>`; // .practice-result

    html += `<div class="practice-actions">`;
    html += `<button class="btn btn-primary" onclick="showPractice()">Next Problem <span class="shortcut-hint">Space</span></button>`;
    html += `<button class="btn" onclick="resetPracticeScore()">Reset Score</button>`;
    html += `</div>`;
  }

  content.innerHTML = html;
}

function resetPracticeScore() {
  practice.correct = 0;
  practice.total = 0;
  renderPractice();
}

function setPracticeFilter(key, value) {
  if (key === "group") practice.filterGroup = value;
  else if (key === "severity") practice.filterSeverity = value;
  else if (key === "defense") practice.filterDefense = value;
  else if (key === "calc_agree") practice.filterCalcAgree = value;
  // Reset score and fetch new problem with new filters
  practice.correct = 0;
  practice.total = 0;
  showPractice();
}

function setPracticeSource(value) {
  practiceSource = value;
  practice.correct = 0;
  practice.total = 0;
  showPractice();
}

async function togglePracticeOptIn(checked) {
  practiceOptIn = checked;
  await apiPost("/api/me/practice-opt-in", { opt_in: checked });
}

// --- Help ---

function showHelp() {
  state.currentGame = null;
  state.currentGameData = null;
  renderGameList();
  const content = document.getElementById("content");

  // Group categories
  const groups = {};
  for (const [code, info] of Object.entries(CATEGORY_INFO)) {
    const grp = info.group;
    if (!groups[grp]) groups[grp] = [];
    groups[grp].push({ code, ...info });
  }

  let html = `<div class="game-header"><h2>Help</h2></div>`;

  for (const [grp, cats] of Object.entries(groups)) {
    const color = GROUP_COLORS[grp] || "#888";
    html += `<div class="help-group">`;
    html += `<div class="help-group-header" style="color:${color}">${grp}</div>`;
    for (const cat of cats) {
      html += `<div class="help-cat">
        <span class="help-cat-label">${cat.label}</span>
        <span class="help-cat-desc">${cat.desc || ""}</span>
        ${cat.study ? `<span class="help-cat-study">${cat.study}</span>` : ""}
      </div>`;
    }
    html += `</div>`;
  }

  // How categorization works
  html += `
    <div class="help-section">
      <h3>How Auto-Categorization Works</h3>
      <p>Every discard mistake is categorized by comparing two independent analyses:</p>
      <p><span style="color:#81c784"><b>Mortal AI</b></span> &mdash; A neural-network mahjong AI that considers the full game state: tile efficiency, defense, hand value, riichi timing, opponent behavior, and more. Its "Q-value" is a strategic evaluation of each discard.</p>
      <p><span style="color:#64b5f6"><b>Tile Calculator</b></span> (mahjong-cpp) &mdash; A pure tile efficiency engine. It calculates expected score, win probability, and shanten for each discard, considering only your hand and visible tiles. It ignores defense and strategy entirely.</p>
      <p style="margin-top:8px"><b>The comparison tells us WHY you made a mistake:</b></p>
      <p>&bull; <b>Both agree on the best tile</b> (or nearly agree) &rarr; This is a <span style="color:#4a9eff">Tile Efficiency</span> error. If the choice involves an honor or terminal vs. a number tile, it's categorized as <span style="color:#38bdf8">Value Tile Ordering</span>; otherwise it's a general efficiency mistake.</p>
      <p>&bull; <b>They disagree</b> &rarr; Mortal sees something the calculator doesn't. This is a <span style="color:#ff6b6b">strategic</span> decision. We then check defense context:</p>
      <p style="padding-left:16px">&bull; If an opponent is in riichi and Mortal chose a significantly safer tile &rarr; <b>Defense</b> (you should have played safe)</p>
      <p style="padding-left:16px">&bull; Otherwise &rarr; <b>Complex Decision</b> (general strategic disagreement)</p>
      <p>&bull; <b>Non-discard actions</b> (chi, pon, riichi, kan) are categorized by type: Meld, Riichi, or Kan.</p>
      <p style="margin-top:8px"><i>"Reasonable agreement"</i>: If Mortal's pick has the same shanten and at least 90% of the calculator's best expected score, we still call it efficiency &mdash; the two engines agree in substance even if they pick different tiles.</p>
    </div>

    <div class="help-section">
      <h3>Defense &amp; Safety Ratings</h3>
      <p>When an opponent declares riichi, each tile in your hand is rated for safety using <b>suji analysis</b> &mdash; a technique based on which tiles the opponent has discarded and what that implies about their waiting tiles.</p>
      <div class="help-safety-scale">
        <div class="help-safety-item">
          <span class="help-safety-bar" style="background:var(--sev-minor)"></span>
          <span><b>15 &mdash; Genbutsu:</b> Tile the opponent already discarded (or discarded after riichi). Cannot deal in. 100% safe.</span>
        </div>
        <div class="help-safety-item">
          <span class="help-safety-bar" style="background:var(--sev-minor)"></span>
          <span><b>14-11 &mdash; Suji terminal / dead honor:</b> Terminal (1/9) with suji protection (rating decreases as more copies remain in wall). Honor tiles: 14 (0 left), 13 (1 left).</span>
        </div>
        <div class="help-safety-item">
          <span class="help-safety-bar" style="background:var(--sev-medium)"></span>
          <span><b>10-7 &mdash; Suji number / honor (2 left):</b> Number tiles (2-8) with suji protection. Suji 4-5-6 = 9, suji 2/8 = 8, suji 3/7 = 7. Honor with 2 remaining = 10.</span>
        </div>
        <div class="help-safety-item">
          <span class="help-safety-bar" style="background:var(--sev-medium)"></span>
          <span><b>6-5 &mdash; Honor (3 left) / non-suji terminal:</b> Unpaired honors or terminals without suji protection.</span>
        </div>
        <div class="help-safety-item">
          <span class="help-safety-bar" style="background:var(--sev-major)"></span>
          <span><b>3-1 &mdash; Non-suji number tiles:</b> No suji protection. 2/8 = 3, 3/7 = 2, 4-5-6 = 1. Middle tiles without suji are the most dangerous discards.</span>
        </div>
      </div>
      <p>When an opponent is in riichi, their discard pool is shown below your hand. The sideways tile marks their riichi declaration. Tiles they discarded are genbutsu (safe) &mdash; study their discards to understand the safety ratings.</p>
    </div>

    <div class="help-section">
      <h3>EV Comparison Table</h3>
      <p><span style="color:#81c784">Mortal Q</span> &mdash; Mortal AI's evaluation. Higher = better strategic play considering defense, hand value, game state. The <b>AI</b> marker shows Mortal's top pick.</p>
      <p><span style="color:#64b5f6">Exp Score</span> &mdash; Pure expected score from tile efficiency. Higher = better hand-building potential. The <b>Calc</b> marker shows the calculator's top pick.</p>
      <p><span style="color:var(--sev-major)">You</span> &mdash; The tile you actually played. Compare your choice against both analyses.</p>
      <p>When Mortal Q and Exp Score agree, the correct play is clear. When they disagree, Mortal is weighing factors like defense or hand value that pure efficiency misses.</p>
    </div>

    <div class="help-section">
      <h3>Game Ratings</h3>
      <p>\u2605 <b>Great game</b> &mdash; EV/decision in the top 25% of your games</p>
      <p>\u2606 <b>Solid game</b> &mdash; EV/decision in the top 50% of your games</p>
      <p>Ratings are relative to your own history, so they reflect personal improvement. Rounds with zero mistakes get a <span class="clean-badge" style="display:inline">Clean</span> badge.</p>
    </div>

    <div class="help-section">
      <h3>Tile Efficiency Practice</h3>
      <p>Practice replays your tile efficiency mistakes as quizzes. You see the hand + draw and pick a discard. After answering, the full analysis is revealed.</p>
      <p>Only tile efficiency mistakes are included &mdash; decisions where the correct tile can be determined from your hand alone. Strategic decisions (defense, push/fold) are excluded because they depend on game context that a hand quiz can't capture.</p>
      <p><b>Spaced repetition:</b> Problems you get wrong (or haven't seen) appear 3x more often. Problems you've answered correctly multiple times appear less. This focuses practice on your weakest areas.</p>
      <p><b>Filters:</b> Focus on severity levels or riichi-only situations.</p>
    </div>

    <div class="help-section">
      <h3>Attribution & Licenses</h3>
      <div class="help-cat"><span class="help-cat-label">Mortal AI</span><span class="help-cat-desc">Mahjong AI engine for game analysis &mdash; <a href="https://mjai.ekyu.moe" target="_blank" style="color:var(--accent-dim)">mjai.ekyu.moe</a></span></div>
      <div class="help-cat"><span class="help-cat-label">mahjong-cpp</span><span class="help-cat-desc">Tile efficiency calculator by nekobean &mdash; GPLv3 &mdash; <a href="https://github.com/nekobean/mahjong-cpp" target="_blank" style="color:var(--accent-dim)">GitHub</a></span></div>
      <div class="help-cat"><span class="help-cat-label">Riichi Trainer</span><span class="help-cat-desc">Defense analysis ported from Euophrys &mdash; GPLv3 &mdash; <a href="https://github.com/Euophrys/Riichi-Trainer" target="_blank" style="color:var(--accent-dim)">GitHub</a></span></div>
      <div class="help-cat"><span class="help-cat-label">Tile Graphics</span><span class="help-cat-desc">SVG tiles by FluffyStuff &mdash; CC0 (Public Domain) &mdash; <a href="https://github.com/FluffyStuff/riichi-mahjong-tiles" target="_blank" style="color:var(--accent-dim)">GitHub</a></span></div>
    </div>
  `;

  content.innerHTML = html;
}

// --- Admin Dashboard ---

let adminState = { items: [], users: [], filterStatus: "", filterType: "" };

async function showAdmin() {
  state.currentGame = null;
  state.currentGameData = null;
  renderGameList();
  const content = document.getElementById("content");
  content.innerHTML = '<div class="empty-state">Loading...</div>';

  const params = new URLSearchParams();
  if (adminState.filterStatus) params.set("status", adminState.filterStatus);
  if (adminState.filterType) params.set("type", adminState.filterType);

  const [fbRes, statsRes] = await Promise.all([
    fetch(`/api/admin/feedback?${params}`),
    fetch("/api/admin/stats"),
  ]);
  if (fbRes.status === 403) {
    content.innerHTML = '<div class="empty-state">Admin access required</div>';
    return;
  }
  adminState.items = await fbRes.json();
  const stats = await statsRes.json();
  adminState.users = stats.users || [];
  renderAdmin();
}

function renderAdmin() {
  const content = document.getElementById("content");
  const items = adminState.items;

  const statusColors = { "new": "#4fc3f7", "in-progress": "#ffa94d", "resolved": "#66bb6a" };
  const typeColors = { "bug": "#ef5350", "feature": "#a855f7", "general": "#888" };

  const users = adminState.users;
  const totalGames = users.reduce((s, u) => s + u.game_count, 0);

  let html = `<div class="game-header"><h2>Admin Dashboard</h2></div>`;

  // User stats
  html += `<div class="admin-card" style="margin-bottom:16px">
    <div class="admin-card-header"><b>${users.length} users</b> <span class="admin-meta">&middot; ${totalGames} games total</span></div>
    <table class="admin-users-table">
      <tr><th>User</th><th>Games</th><th>Joined</th></tr>
      ${users.map(u => {
        const joined = new Date(u.created_at + "Z").toLocaleDateString();
        return `<tr><td>${escapeHtml(u.username)}</td><td>${u.game_count}</td><td>${joined}</td></tr>`;
      }).join("")}
    </table>
  </div>`;

  html += `<div class="game-header" style="margin-top:8px"><h2>Feedback (${items.length})</h2></div>`;

  html += `<div class="admin-filters">
    <select onchange="adminState.filterStatus=this.value;showAdmin()">
      <option value="">All statuses</option>
      <option value="new" ${adminState.filterStatus==="new"?"selected":""}>New</option>
      <option value="in-progress" ${adminState.filterStatus==="in-progress"?"selected":""}>In Progress</option>
      <option value="resolved" ${adminState.filterStatus==="resolved"?"selected":""}>Resolved</option>
    </select>
    <select onchange="adminState.filterType=this.value;showAdmin()">
      <option value="">All types</option>
      <option value="bug" ${adminState.filterType==="bug"?"selected":""}>Bug</option>
      <option value="feature" ${adminState.filterType==="feature"?"selected":""}>Feature</option>
      <option value="general" ${adminState.filterType==="general"?"selected":""}>General</option>
    </select>
  </div>`;

  if (!items.length) {
    html += '<div class="empty-state">No feedback items</div>';
    content.innerHTML = html;
    return;
  }

  for (const item of items) {
    const sc = statusColors[item.status] || "#888";
    const tc = typeColors[item.type] || "#888";
    const date = new Date(item.created_at + "Z").toLocaleString();

    html += `<div class="admin-card" id="fb-${item.id}">
      <div class="admin-card-header">
        <span class="admin-badge" style="background:${tc}20;color:${tc}">${item.type}</span>
        <span class="admin-badge" style="background:${sc}20;color:${sc}">${item.status}</span>
        <span class="admin-meta">${item.username} &middot; ${date}</span>
        ${item.github_issue_url ? `<a href="${escapeHtml(item.github_issue_url)}" target="_blank" class="admin-gh-link">GitHub</a>` : ""}
      </div>
      <div class="admin-card-body">${escapeHtml(item.message)}</div>
      ${item.admin_note ? `<div class="admin-note-display"><b>Note:</b> ${escapeHtml(item.admin_note)}</div>` : ""}
      <div class="admin-card-actions">
        ${item.status !== "resolved" ? `<button class="btn btn-sm" onclick="adminResolve(${item.id})">Resolve</button>` : ""}
        ${item.status === "resolved" ? `<button class="btn btn-sm" onclick="adminReopen(${item.id})">Reopen</button>` : ""}
        <button class="btn btn-sm" onclick="adminToggleNote(${item.id})">Note</button>
        ${!item.github_issue_url ? `<button class="btn btn-sm" onclick="adminCreateIssue(${item.id})">Create Issue</button>` : ""}
      </div>
      <div class="admin-note-form" id="fb-note-${item.id}" style="display:none">
        <textarea rows="2" placeholder="Admin note..." id="fb-note-text-${item.id}">${escapeHtml(item.admin_note || "")}</textarea>
        <button class="btn btn-sm btn-primary" onclick="adminSaveNote(${item.id})">Save Note</button>
      </div>
    </div>`;
  }

  content.innerHTML = html;
}

function escapeHtml(s) {
  if (!s) return "";
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

async function adminResolve(id) {
  await apiPost(`/api/admin/feedback/${id}`, { status: "resolved" });
  showAdmin();
}

async function adminReopen(id) {
  await apiPost(`/api/admin/feedback/${id}`, { status: "new" });
  showAdmin();
}

function adminToggleNote(id) {
  const el = document.getElementById(`fb-note-${id}`);
  el.style.display = el.style.display === "none" ? "block" : "none";
}

async function adminSaveNote(id) {
  const note = document.getElementById(`fb-note-text-${id}`).value.trim();
  await apiPost(`/api/admin/feedback/${id}`, { admin_note: note });
  showAdmin();
}

async function adminCreateIssue(id) {
  const btn = event.target;
  btn.disabled = true;
  btn.textContent = "Creating...";
  const res = await apiPost(`/api/admin/feedback/${id}/create-issue`, {});
  const data = await res.json();
  if (data.ok) {
    showAdmin();
  } else {
    btn.disabled = false;
    btn.textContent = "Create Issue";
    alert(data.error || "Failed to create issue");
  }
}

// --- My Feedback ---

async function showMyFeedback() {
  state.currentGame = null;
  state.currentGameData = null;
  renderGameList();
  const content = document.getElementById("content");
  content.innerHTML = '<div class="empty-state">Loading...</div>';

  const res = await fetch("/api/feedback/mine");
  const items = await res.json();

  const statusColors = { "new": "#4fc3f7", "in-progress": "#ffa94d", "resolved": "#66bb6a" };

  let html = `<div class="game-header"><h2>My Feedback</h2></div>`;

  if (!items.length) {
    html += '<div class="empty-state">No feedback submitted yet</div>';
    content.innerHTML = html;
    return;
  }

  for (const item of items) {
    const sc = statusColors[item.status] || "#888";
    const date = new Date(item.created_at + "Z").toLocaleString();

    html += `<div class="admin-card">
      <div class="admin-card-header">
        <span class="admin-badge" style="background:${sc}20;color:${sc}">${item.status}</span>
        <span class="admin-meta">${item.type} &middot; ${date}</span>
      </div>
      <div class="admin-card-body">${escapeHtml(item.message)}</div>
      ${item.status === "resolved" && item.admin_note ? `<div class="admin-note-display"><b>Response:</b> ${escapeHtml(item.admin_note)}</div>` : ""}
    </div>`;
  }

  content.innerHTML = html;
}

// --- Feedback ---

function showFeedbackModal() {
  document.getElementById("feedback-modal").style.display = "flex";
  document.getElementById("feedback-message").value = "";
  document.getElementById("feedback-error").textContent = "";
}

function hideFeedbackModal() {
  document.getElementById("feedback-modal").style.display = "none";
}

async function submitFeedback() {
  const type = document.getElementById("feedback-type").value;
  const message = document.getElementById("feedback-message").value.trim();
  const errEl = document.getElementById("feedback-error");
  const btn = document.getElementById("feedback-submit-btn");

  if (!message) {
    errEl.textContent = "Please enter a message.";
    return;
  }

  btn.disabled = true;
  btn.textContent = "Sending...";
  errEl.textContent = "";

  const res = await apiPost("/api/feedback", { type, message });
  const data = await res.json();

  btn.disabled = false;
  btn.textContent = "Send";

  if (data.ok) {
    hideFeedbackModal();
  } else {
    errEl.textContent = data.error || "Failed to send feedback.";
  }
}

// --- Keyboard shortcuts ---

document.addEventListener("keydown", (e) => {
  // Practice mode: Space/Enter for next problem after answering
  if (practice.problem && practice.answered) {
    if (e.code === "Space" || e.code === "Enter") {
      e.preventDefault();
      showPractice();
    }
  }
});

// --- Tile hover highlighting ---
// Hovering a tile highlights all copies of that tile type on the board

document.addEventListener("mouseover", (e) => {
  const tile = e.target.closest("[data-tile]");
  if (!tile) return;
  const tileType = tile.dataset.tile;
  document.querySelectorAll(`[data-tile="${tileType}"]`).forEach(el => el.classList.add("tile-hover"));
});

document.addEventListener("mouseout", (e) => {
  const tile = e.target.closest("[data-tile]");
  if (!tile) return;
  const tileType = tile.dataset.tile;
  document.querySelectorAll(`[data-tile="${tileType}"]`).forEach(el => el.classList.remove("tile-hover"));
});

// --- Init ---

document.addEventListener("DOMContentLoaded", async () => {
  const onPracticePage = window.location.pathname === "/practice";

  // Load user info
  const meRes = await fetch("/api/me");
  if (meRes.status === 401) {
    if (onPracticePage) {
      // Anonymous practice mode
      isAnonymous = true;
      document.getElementById("user-info").innerHTML =
        `<a href="/login">Log in</a> | <a href="/register">Register</a>`;
      // Hide authenticated-only UI
      document.querySelector('.sidebar-header button[onclick="showAddModal()"]').style.display = "none";
      for (const id of ["trends-btn", "help-btn"]) {
        const btn = document.getElementById(id);
        if (btn) btn.style.display = "none";
      }
      document.querySelector('button[onclick="showMyFeedback()"]').style.display = "none";
      document.querySelector('button[onclick="showFeedbackModal()"]').style.display = "none";
    } else {
      window.location.href = "/login";
      return;
    }
  } else {
    const me = await meRes.json();
    csrfToken = me.csrf_token || "";
    practiceOptIn = !!me.practice_opt_in;
    document.getElementById("user-info").innerHTML =
      `${me.username} <a href="/logout">logout</a>`;

    // Show admin button only for admins
    const adminBtn = document.getElementById("admin-btn");
    if (adminBtn && me.is_admin) adminBtn.style.display = "";
  }

  const catRes = await fetch("/api/categories");
  CATEGORY_INFO = await catRes.json();
  // 2b: Override "Push/Fold" — it's a catch-all for strategic disagreements, not specifically push/fold
  if (CATEGORY_INFO["3A"]) {
    CATEGORY_INFO["3A"].label = "Complex Decision";
    CATEGORY_INFO["3A"].desc = "Mortal's strategic evaluation differs from pure tile efficiency — may involve hand value, position, or game state factors";
    delete CATEGORY_INFO["3A"].study;
  }

  if (isAnonymous) {
    showPractice();
  } else {
    fetchGames();
  }
});
