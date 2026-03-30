const CATEGORIES = [
  "", "1A", "1B", "1C", "1D", "1E",
  "2A", "2B", "2C",
  "3A", "3B", "3C",
  "4A", "4B",
  "5A", "5B",
];

const CATEGORY_LABELS = {
  "1A": "Tile Efficiency", "1B": "Dora Handling", "1C": "Honor Ordering",
  "1D": "Honor vs Number", "1E": "Pair Management",
  "2A": "Bad Defend", "2B": "Missed Defend", "2C": "Inefficient Defense",
  "3A": "Bad Meld", "3B": "Missed Meld", "3C": "Bad Strategy after Meld",
  "4A": "Bad Riichi", "4B": "Missed Riichi",
  "5A": "Bad Kan", "5B": "Missed Kan",
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

function renderTile(t, extraClass = "") {
  const cls = ["tile", extraClass].filter(Boolean).join(" ");
  return `<img class="${cls}" src="${tileSrc(t)}" alt="${t}" title="${t}">`;
}

function renderHand(tiles, draw) {
  if (!tiles || !tiles.length) return "";
  return tiles.map((t, i) => {
    let extra = "";
    if (draw && i === tiles.length - 1 && t === draw) extra = "draw";
    return renderTile(t, extra);
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
      <h2>Game ${state.currentGame + 1} &mdash; ${game.date}</h2>
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
          <span class="tiles">${renderHand(m.hand, m.draw, m.actual, m.expected)}</span>
        </div>`;
      }

      // Top actions
      if (m.top_actions && m.top_actions.length) {
        html += `<div class="top-actions">`;
        for (const a of m.top_actions) {
          html += `<span class="top-action">${renderAction(a.action)} <b>${a.q_value.toFixed(2)}</b> <span class="prob">${(a.prob * 100).toFixed(0)}%</span></span>`;
        }
        html += `</div>`;
      }

      // Annotation
      const catOptions = CATEGORIES.map(c => {
        const sel = (m.category || "") === c ? "selected" : "";
        const label = c ? `${c}` : "---";
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

  // Category summary
  if (s.by_category && Object.keys(s.by_category).length) {
    html += `<div class="game-summary"><h3>Categories</h3><div class="category-grid">`;
    const sorted = Object.entries(s.by_category).sort((a, b) => a[0].localeCompare(b[0]));
    for (const [cat, data] of sorted) {
      const label = CATEGORY_LABELS[cat] || cat;
      html += `<span class="cat-chip">
        <span class="cat-name">${cat}</span>
        <span class="cat-stat">${data.count} (${data.ev.toFixed(2)})</span>
        <span style="font-size:10px;color:var(--text-dim)">${label}</span>
      </span>`;
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

// --- Init ---

document.addEventListener("DOMContentLoaded", () => {
  fetchGames();
});
