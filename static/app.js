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
  hideMinor: false,
  hideMedium: false,
};

// --- Tile rendering ---

function tileInfo(t) {
  if (!t) return { num: "?", suit: "" };
  if (t.endsWith("r")) {
    // Red five: 5mr -> 0, suit m
    return { num: "0", suit: t.slice(-2, -1), red: true };
  }
  if (t.length >= 2 && "mps".includes(t[t.length - 1])) {
    return { num: t.slice(0, -1), suit: t[t.length - 1] };
  }
  // Honor
  return { num: t, suit: "z" };
}

function renderTile(t, extraClass = "") {
  const info = tileInfo(t);
  const cls = ["tile", info.suit, extraClass].filter(Boolean).join(" ");
  const label = info.red ? "0" : info.num;
  return `<span class="${cls}" title="${t}">${label}</span>`;
}

function renderHand(tiles, draw, actual, expected) {
  if (!tiles || !tiles.length) return "";

  const actualPai = actual?.type === "dahai" ? actual.pai : null;
  const expectedPai = expected?.type === "dahai" ? expected.pai : null;

  // Mark the last tile as draw if it matches
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
  list.innerHTML = state.games.map(g => {
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
      if (state.hideMinor && m.severity === "?") return false;
      if (state.hideMedium && m.severity === "??") return false;
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

      if (state.hideMinor && m.severity === "?") continue;
      if (state.hideMedium && m.severity === "??") continue;

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
            <span class="played">${actStr}</span> &rarr; <span class="ai">${expStr}</span>
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
          const aStr = formatAction(a.action);
          html += `<span class="top-action">${aStr} <b>${a.q_value.toFixed(2)}</b> <span class="prob">${(a.prob * 100).toFixed(0)}%</span></span>`;
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
  state.hideMinor = cb.checked;
  if (state.currentGameData) renderGame();
}

function onToggleMedium(cb) {
  state.hideMedium = cb.checked;
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
