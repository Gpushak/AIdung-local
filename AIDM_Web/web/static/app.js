const logEl = document.querySelector("#log");
const actionEl = document.querySelector("#action");
const sendEl = document.querySelector("#send");
const statusEl = document.querySelector("#status");
const barEl = document.querySelector("#bar");
const barLabel = document.querySelector("#bar-label");
const noticeEl = document.querySelector("#notice");
const panel = document.querySelector("#panel");
const panelBody = document.querySelector("#panel-body");
const panelTitle = document.querySelector("#panel-title");

let strings = {};
let state = null;
let drafting = false;
let revision = 0;
let settingsCache = null;
let loadingOlder = false;
let pollTimer = 0;
let pendingPlayer = "";
let awaitingSettle = false;
let settleOnce = false;
let draftClosed = true;

if ("scrollRestoration" in history) history.scrollRestoration = "manual";

function t(key) {
  return strings[key] || key;
}

function plainText(value) {
  return String(value ?? "")
    .replace(/\p{Extended_Pictographic}/gu, "")
    .replace(/[\uFE0F\u200D\u2300-\u23FF\u25A0-\u25FF\u2600-\u27BF]/g, "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/^ +/, "");
}

function asText(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(asText).filter(Boolean).join(", ");
  if (typeof value === "object") {
    return Object.entries(value).map(([key, item]) => {
      const text = asText(item);
      return text ? `${key}: ${text}` : "";
    }).filter(Boolean).join("\n");
  }
  return String(value);
}

function applyStrings() {
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    if (node.id === "send" && node.classList.contains("stop")) return;
    node.textContent = t(node.dataset.i18n);
  });
}

async function api(path, options) {
  const opts = { cache: "no-store", ...(options || {}) };
  const method = (opts.method || "GET").toUpperCase();
  const url = method === "GET" ? path + (path.includes("?") ? "&" : "?") + "_=" + Date.now() : path;
  const response = await fetch(url, opts);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(response.statusText);
    error.status = response.status;
    error.body = data;
    throw error;
  }
  return data;
}

function paintFill(fill) {
  const ratio = Math.max(0, Math.min(1, fill.ratio || 0));
  barEl.className = fill.color || "ok";
  barEl.querySelector("span").style.width = `${ratio * 100}%`;
  barLabel.textContent = fill.label || "";
}

function paintNotice(text) {
  noticeEl.textContent = text || "";
  noticeEl.hidden = !text;
}

function paintMeters(meters) {
  if (!meters) return;
  const summaryBtn = document.querySelector("#toggle-summary");
  const memoryBtn = document.querySelector("#toggle-memory");
  const summaryCount = document.querySelector("#summary-count");
  const memoryCount = document.querySelector("#memory-count");
  summaryBtn.textContent = meters.summary_toggle || "";
  memoryBtn.textContent = meters.memory_toggle || "";
  summaryBtn.classList.toggle("on", Boolean(meters.summary_enabled));
  memoryBtn.classList.toggle("on", Boolean(meters.memory_enabled));
  summaryCount.textContent = meters.summary_text || "";
  memoryCount.textContent = meters.memory_text || "";
  summaryCount.className = meters.summary_color || "";
  memoryCount.className = meters.memory_color || "";
}

function paintStatus(status) {
  statusEl.textContent = status.text || "";
  const stop = Boolean(status.busy);
  document.body.classList.toggle("busy", stop);
  if (stop) document.body.classList.remove("writing");
  sendEl.classList.toggle("stop", stop);
  sendEl.textContent = stop ? t("btn.stop") : t("btn.send");
  actionEl.disabled = status.text === t("status.generating");
  fitChrome();
  syncPolling();
}

let freshIndex = null;
let awaitFresh = false;
let freshAnchor = null;

function noteFreshReply() {
  awaitFresh = true;
  const rows = state && state.history ? state.history : [];
  freshAnchor = rows.length ? rows[rows.length - 1].index : -1;
}

function settleFresh(snap) {
  if (!awaitFresh || !snap || snap.streaming) return;
  const rows = snap.history || [];
  const last = rows[rows.length - 1];
  if (last && last.kind === "dm" && last.index !== freshAnchor) freshIndex = last.index;
  awaitFresh = false;
}

function freshMark() {
  const line = document.createElement("hr");
  line.className = "fresh-mark";
  return line;
}

function jumpToEnd() {
  tailReady = false;
  const go = () => window.scrollTo(0, document.documentElement.scrollHeight);
  go();
  requestAnimationFrame(() => {
    go();
    requestAnimationFrame(() => { tailReady = true; });
  });
}

function nearBottom() {
  return document.documentElement.scrollHeight - window.scrollY - window.innerHeight < 180;
}

function renderLog(mode = "end", draftOverride) {
  if (!state) return;
  const fromDom = document.querySelector("#draft")?.textContent || "";
  const fromState = state && typeof state.draft === "string" ? state.draft : "";
  const draftText = drafting
    ? (typeof draftOverride === "string" ? draftOverride : (fromState.length >= fromDom.length ? fromState : fromDom))
    : "";
  const stick = mode === "end" || (mode === "follow" && nearBottom());
  const anchorY = window.scrollY;
  const anchorHeight = document.documentElement.scrollHeight;
  logEl.replaceChildren();
  if (state.history_from > 0) {
    const earlier = document.createElement("button");
    earlier.type = "button";
    earlier.className = "earlier";
    earlier.textContent = state.language === "en" ? "Earlier" : "Раньше";
    earlier.addEventListener("click", () => loadOlder());
    logEl.appendChild(earlier);
  }
  const lineBeforeDraft = awaitFresh && drafting;
  for (const row of state.history) {
    if (!lineBeforeDraft && freshIndex != null && row.index === freshIndex) {
      logEl.appendChild(freshMark());
    }
    const p = document.createElement("p");
    p.className = row.kind;
    p.dataset.index = String(row.index);
    p.textContent = plainText(row.text);
    if (row.kind === "player" || row.kind === "dm") {
      p.title = "edit";
      p.addEventListener("dblclick", () => editRow(row));
    }
    logEl.appendChild(p);
  }
  if (drafting) {
    if (lineBeforeDraft) logEl.appendChild(freshMark());
    const p = document.createElement("p");
    p.className = "dm draft";
    p.id = "draft";
    p.textContent = draftText;
    logEl.appendChild(p);
  }
  if (mode === "keep") {
    const grown = document.documentElement.scrollHeight - anchorHeight;
    window.scrollTo(0, anchorY + grown);
  } else if (stick) {
    jumpToEnd();
  }
}

function ensureDraft() {
  if (draftClosed) return null;
  let draft = document.querySelector("#draft");
  if (draft) return draft;
  drafting = true;
  draft = document.createElement("p");
  draft.className = "dm draft";
  draft.id = "draft";
  logEl.appendChild(draft);
  return draft;
}

async function loadOlder() {
  if (loadingOlder || !state || !state.history_from) return;
  loadingOlder = true;
  try {
    const page = await api(`/api/history?before=${state.history_from}`);
    if (!page.history.length) return;
    const seen = new Set(state.history.map((row) => row.index));
    const older = page.history.filter((row) => !seen.has(row.index));
    if (!older.length) {
      state.history_from = page.history_from;
      return;
    }
    state.history = older.concat(state.history);
    state.history_from = page.history_from;
    state.history_total = page.history_total;
    renderLog("keep");
  } finally {
    loadingOlder = false;
  }
}

function paintModels() {
  const menu = document.querySelector("#models-menu");
  const current = document.querySelector("#models-current");
  const presets = (state && state.presets) || { active: "", items: [] };
  const active = (presets.items || []).find((item) => item.name === presets.active);
  current.textContent = active ? active.name : "";
  current.hidden = !active;
  menu.replaceChildren();
  if (!(presets.items || []).length) {
    const empty = document.createElement("p");
    empty.className = "pop-empty";
    empty.textContent = t("models.empty");
    menu.append(empty);
    return;
  }
  for (const item of presets.items) {
    const button = document.createElement("button");
    button.type = "button";
    button.setAttribute("role", "menuitemradio");
    button.setAttribute("aria-checked", item.name === presets.active ? "true" : "false");
    const name = document.createElement("span");
    name.textContent = item.name;
    button.append(name);
    if (item.model) {
      const model = document.createElement("small");
      model.textContent = item.model;
      button.append(model);
    }
    button.addEventListener("click", () => selectPreset(item.name));
    menu.append(button);
  }
}

async function selectPreset(name) {
  setModelsOpen(false);
  if (state && state.presets && state.presets.active === name) return;
  const presets = await api("/api/presets/activate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (state) state.presets = presets;
  paintModels();
  if (!settingsCache) return;
  const found = (settingsCache.api_presets || []).find((item) => item.name === presets.active);
  if (!found) return;
  settingsCache.active_api_preset = found.name;
  settingsCache.api_url = found.api_url || "";
  settingsCache.api_key = found.api_key || "";
  settingsCache.model = found.model || "";
  const preset = document.querySelector("#settings-preset");
  if (preset) preset.value = found.name;
  for (const key of ["api_url", "api_key", "model"]) {
    const input = document.querySelector(`[data-setting="${key}"]`);
    if (input) input.value = settingsCache[key];
  }
}

function setModelsOpen(open) {
  if (open) setWorldsOpen(false);
  const menu = document.querySelector("#models-menu");
  const toggle = document.querySelector("#models-toggle");
  menu.hidden = !open;
  toggle.setAttribute("aria-expanded", open ? "true" : "false");
  toggle.closest(".models").classList.toggle("open", open);
}

function paintWorlds() {
  const menu = document.querySelector("#world-menu");
  const current = document.querySelector("#world-current");
  const names = (state && state.worlds) || [];
  const active = state && names.includes(state.world) ? state.world : "";
  current.textContent = active || t("no_worlds");
  menu.replaceChildren();
  if (!names.length) {
    const empty = document.createElement("p");
    empty.className = "pop-empty";
    empty.textContent = t("no_worlds");
    menu.append(empty);
    return;
  }
  for (const name of names) {
    const button = document.createElement("button");
    button.type = "button";
    button.setAttribute("role", "menuitemradio");
    button.setAttribute("aria-checked", name === active ? "true" : "false");
    button.textContent = name;
    button.addEventListener("click", () => openWorld(name));
    menu.append(button);
  }
}

async function openWorld(name) {
  setWorldsOpen(false);
  if (state && state.world === name) return;
  applySnapshot(await api("/api/worlds/open", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  }), "end");
}

function setWorldsOpen(open) {
  if (open) setModelsOpen(false);
  const menu = document.querySelector("#world-menu");
  const toggle = document.querySelector("#world-toggle");
  menu.hidden = !open;
  toggle.setAttribute("aria-expanded", open ? "true" : "false");
  toggle.closest(".worlds-picker").classList.toggle("open", open);
  if (!open) return;
  const checked = menu.querySelector('[aria-checked="true"]');
  if (checked) menu.scrollTop = Math.max(0, checked.offsetTop - 8);
}

function applySnapshot(snap, mode = "end") {
  if (!snap) return;
  if (typeof snap.rev === "number" && snap.rev < revision) {
    if (awaitingSettle) scheduleSettle();
    return;
  }
  if (pendingPlayer && !snapshotHasPlayer(snap, pendingPlayer)) {
    if (awaitingSettle) scheduleSettle();
    return;
  }
  const domDraft = document.querySelector("#draft")?.textContent || "";
  const serverDraft = snap.draft || "";
  const draftDrift = Boolean(snap.streaming) && domDraft !== serverDraft;
  const unchanged = !draftDrift
    && state
    && snap.rev === revision
    && serverDraft === (state.draft || "")
    && Boolean(snap.streaming) === Boolean(state.streaming)
    && snap.history_total === state.history_total
    && snap.status?.text === state.status?.text
    && (snap.notices || []).at(-1) === (state.notices || []).at(-1);
  if (typeof snap.rev === "number") revision = snap.rev;
  state = snap;
  drafting = Boolean(snap.streaming);
  draftClosed = !snap.streaming;
  if (!snap.streaming) {
    awaitingSettle = false;
    pendingPlayer = "";
    settleOnce = false;
  }
  settleFresh(snap);
  paintWorlds();
  paintModels();
  paintFill(snap.fill);
  paintStatus(snap.status);
  paintNotice((snap.notices || []).at(-1) || "");
  paintMeters(snap.meters);
  if (mode === "end" || !unchanged) renderLog(mode);
}

function snapshotHasPlayer(snap, text) {
  return (snap.history || []).some((row) => row.kind === "player" && row.text === text);
}

function scheduleSettle() {
  if (settleOnce || !awaitingSettle) return;
  settleOnce = true;
  window.setTimeout(() => {
    if (awaitingSettle) refresh("end");
  }, 50);
}

function beginTurn() {
  awaitingSettle = true;
  settleOnce = false;
  syncPolling();
}

async function refresh(mode = "end") {
  const start = mode === "keep" && state && Number.isInteger(state.history_from) ? `?start=${state.history_from}` : "";
  applySnapshot(await api(`/api/state${start}`), mode);
}

function syncPolling() {
  const keep = document.body.classList.contains("busy") || awaitingSettle;
  if (keep) {
    if (!pollTimer) pollTimer = window.setInterval(() => refresh("follow"), 2000);
  } else if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = 0;
  }
}

function catchUp(mode = "end") {
  if (document.visibilityState === "hidden") return;
  refresh(mode).catch(() => {});
}

let source = null;
let leftPage = false;
let resumeTimers = [];

function connectEvents() {
  if (source) {
    source.onopen = null;
    source.onmessage = null;
    source.onerror = null;
    source.close();
  }
  source = new EventSource("/api/events?_=" + Date.now());
  source.onopen = () => catchUp("follow");
  source.onerror = () => {
    const now = Date.now();
    if (now - (connectEvents.lastError || 0) < 1500) return;
    connectEvents.lastError = now;
    catchUp("follow");
  };
  source.onmessage = (message) => {
    let event;
    try {
      event = JSON.parse(message.data);
    } catch (error) {
      return;
    }
    if (typeof event.rev === "number" && event.rev < revision) return;
    if (typeof event.rev === "number") revision = event.rev;
    if (event.kind === "dm_start") {
      drafting = true;
      draftClosed = false;
      awaitingSettle = true;
      settleOnce = false;
      noteFreshReply();
      if (state) state.streaming = true;
      syncPolling();
      renderLog("end");
    } else if (event.kind === "dm_delta") {
      if (draftClosed) return;
      const follow = nearBottom();
      const draft = ensureDraft();
      if (!draft) return;
      const next = typeof event.full === "string" ? event.full : `${draft.textContent}${event.text || ""}`;
      if (next.length >= draft.textContent.length) {
        draft.textContent = next;
        if (state) {
          state.streaming = true;
          state.draft = next;
        }
      }
      if (follow) jumpToEnd();
    } else if (event.kind === "fill") {
      paintFill(event);
    } else if (event.kind === "meters") {
      paintMeters(event);
    } else if (event.kind === "system") {
      paintNotice(event.text || "");
      if (state) state.notices = [event.text || ""];
    } else if (event.kind === "status") {
      paintStatus(event);
      if (state && state.status) {
        state.status = { ...state.status, ...event };
      }
    } else if (event.kind === "scene") {
      openPanel("scene", event);
    } else if (event.kind === "card_desc") {
      const box = document.querySelector("#card-desc");
      if (box) box.value = event.text;
    } else if (event.kind === "dm_done" || event.kind === "dm_abort") {
      drafting = false;
      draftClosed = true;
      if (state) {
        state.streaming = false;
        state.draft = "";
      }
      refresh("end");
    } else if (event.kind === "history") {
      refresh("end");
    }
  };
}

function onResume() {
  resumeTimers.forEach((id) => clearTimeout(id));
  connectEvents();
  resumeTimers = [0, 600, 1800, 4000].map((delay) => window.setTimeout(() => catchUp("end"), delay));
  syncPolling();
}

async function boot() {
  strings = await api("/api/strings");
  applyStrings();
  document.querySelector("#lang").textContent = "…";
  await refresh();
  document.querySelector("#lang").textContent = (state.language || "ru").toUpperCase();
  connectEvents();
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      leftPage = true;
      return;
    }
    if (leftPage) {
      leftPage = false;
      onResume();
    }
  });
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) onResume();
  });
  document.addEventListener("resume", () => onResume());
  window.addEventListener("online", () => onResume());
}

const nextDialog = document.querySelector("#next-dialog");
const nextText = document.querySelector("#next-text");
const nextError = document.querySelector("#next-error");

document.querySelector("#next").addEventListener("click", () => {
  nextError.textContent = "";
  nextText.value = "";
  if (!nextDialog.open) nextDialog.showModal();
  nextText.focus();
});
document.querySelector("#next-close").addEventListener("click", () => nextDialog.close());
document.querySelector("#next-cancel").addEventListener("click", () => nextDialog.close());
function showPlayerLine(text) {
  if (!text || !state) return;
  beginTurn();
  pendingPlayer = text;
  const last = state.history.at(-1);
  if (last && last.kind === "player" && last.text === text) return;
  const index = Number.isInteger(state.history_total) ? state.history_total : state.history.length;
  state.history.push({ index, kind: "player", text });
  if (Number.isInteger(state.history_total)) state.history_total += 1;
  renderLog("end");
}

function retractPlayerLine(text) {
  if (!text || !state) {
    releaseTurn();
    return;
  }
  const last = state.history.at(-1);
  const shown = last && last.kind === "player" && last.text === text;
  if (shown) {
    state.history.pop();
    if (Number.isInteger(state.history_total)) state.history_total -= 1;
    renderLog("end");
  }
  releaseTurn();
}

function releaseTurn() {
  pendingPlayer = "";
  awaitingSettle = false;
  syncPolling();
}

document.querySelector("#next-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const direction = nextText.value.trim();
  if (!direction) {
    nextError.textContent = t("dialog.empty_next");
    return;
  }
  nextError.textContent = "";
  showPlayerLine(direction);
  try {
    await api("/api/turn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction }),
    });
    nextDialog.close();
  } catch (error) {
    retractPlayerLine(direction);
    nextText.value = direction;
  }
});

document.querySelector("#composer").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (sendEl.classList.contains("stop")) {
    await api("/api/stop", { method: "POST" });
    return;
  }
  const text = actionEl.value.trim();
  actionEl.value = "";
  if (text) showPlayerLine(text);
  else beginTurn();
  try {
    await api("/api/turn", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
    document.body.classList.remove("writing");
    fitChrome();
  } catch (error) {
    retractPlayerLine(text);
    actionEl.value = text;
  }
});

document.querySelector("#menu-toggle").addEventListener("click", () => {
  const bar = document.querySelector(".topbar");
  const open = bar.classList.toggle("open");
  document.querySelector("#menu-toggle").setAttribute("aria-expanded", open ? "true" : "false");
});

document.querySelector("#models-toggle").addEventListener("click", (event) => {
  event.stopPropagation();
  const menu = document.querySelector("#models-menu");
  setModelsOpen(menu.hidden);
});
document.querySelector("#world-toggle").addEventListener("click", (event) => {
  event.stopPropagation();
  const menu = document.querySelector("#world-menu");
  setWorldsOpen(menu.hidden);
});
document.addEventListener("click", (event) => {
  if (!event.target.closest(".models")) setModelsOpen(false);
  if (!event.target.closest(".worlds-picker")) setWorldsOpen(false);
});
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (!document.querySelector("#models-menu").hidden) setModelsOpen(false);
  if (!document.querySelector("#world-menu").hidden) setWorldsOpen(false);
});

document.querySelector("#act").addEventListener("click", async () => {
  if (document.body.classList.contains("busy")) {
    await api("/api/stop", { method: "POST" });
    return;
  }
  const writing = document.body.classList.toggle("writing");
  fitChrome();
  if (writing) actionEl.focus();
});

actionEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    document.querySelector("#composer").requestSubmit();
  } else if (event.key === "Escape") {
    api("/api/stop", { method: "POST" });
  }
});

document.querySelector("#undo").addEventListener("click", async () => {
  state = await api("/api/undo", { method: "POST" });
  renderLog("end");
  paintFill(state.fill);
  paintStatus(state.status);
});

document.querySelector("#toggle-summary").addEventListener("click", async () => {
  paintMeters(await api("/api/toggles/summary", { method: "POST" }));
});
document.querySelector("#toggle-memory").addEventListener("click", async () => {
  paintMeters(await api("/api/toggles/memory", { method: "POST" }));
});

document.querySelector("#reroll").addEventListener("click", () => api("/api/regenerate", { method: "POST" }));
document.querySelector("#edit").addEventListener("click", () => {
  const rows = editableRows();
  if (rows.length) openEditor(rows[rows.length - 1].index);
});
document.querySelector("#summarize").addEventListener("click", () => api("/api/summary", { method: "POST" }));

document.querySelector("#lang").addEventListener("click", async () => {
  const next = (state.language === "en") ? "ru" : "en";
  const settings = await api("/api/settings");
  settings.language = next;
  await api("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  strings = await api("/api/strings");
  applyStrings();
  await refresh("keep");
  document.querySelector("#lang").textContent = next.toUpperCase();
});

document.querySelector("#panel-close").addEventListener("click", () => panel.close());

function editableRows() {
  return (state.history || []).filter((row) => row.kind === "player" || row.kind === "dm");
}

function openEditor(index) {
  const rows = editableRows();
  let pos = rows.findIndex((row) => row.index === index);
  if (pos < 0) pos = rows.length - 1;
  if (pos < 0) return;
  panelBody.innerHTML = "";
  const heading = document.createElement("p");
  heading.className = "section";
  const label = document.createElement("label");
  const labelText = document.createTextNode("");
  const area = document.createElement("textarea");
  area.rows = 14;
  label.append(labelText, area);
  const nav = document.createElement("div");
  nav.className = "row";
  const prev = document.createElement("button");
  prev.type = "button";
  prev.textContent = t("dialog.edit_prev");
  const next = document.createElement("button");
  next.type = "button";
  next.textContent = t("dialog.edit_next");
  const save = document.createElement("button");
  save.type = "button";
  save.className = "primary";
  save.textContent = t("btn.save_ok");
  function show() {
    const row = rows[pos];
    const title = row.kind === "dm" ? t("dialog.edit_dm") : t("dialog.edit_player");
    panelTitle.textContent = title;
    heading.textContent = `${title} (${pos + 1}/${rows.length})`;
    labelText.textContent = row.kind === "dm" ? t("dialog.edit_dm_label") : t("dialog.edit_player_label");
    area.value = plainText(row.text);
    prev.disabled = pos === 0;
    next.disabled = pos === rows.length - 1;
  }
  prev.addEventListener("click", () => { if (pos > 0) { pos -= 1; show(); } });
  next.addEventListener("click", () => { if (pos < rows.length - 1) { pos += 1; show(); } });
  save.addEventListener("click", async () => {
    const row = rows[pos];
    const text = area.value.trim();
    if (!text) return;
    const start = Math.min(state.history_from || 0, row.index);
    await api(`/api/history/${row.index}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    state = await api(`/api/state?start=${start}`);
    paintWorlds();
    paintFill(state.fill);
    paintStatus(state.status);
    paintNotice((state.notices || []).at(-1) || "");
    paintMeters(state.meters);
    renderLog("keep");
    panel.close();
  });
  nav.append(prev, next, save);
  panelBody.append(heading, label, nav);
  show();
  if (!panel.open) panel.showModal();
}

async function editRow(row) {
  openEditor(row.index);
}

function openPanel(name, extra) {
  panelTitle.textContent = t(`btn.${name === "settings" ? "ai_settings" : name === "files" ? "world_files" : name === "scene" ? "scene_prompt" : name}`);
  panelBody.innerHTML = "";
  const loaders = { worlds: renderWorlds, files: renderFiles, cards: renderCards, memory: renderMemory, settings: renderSettings, prompt: renderPrompt, scene: renderScene };
  loaders[name](extra);
  if (!panel.open) panel.showModal();
}

document.querySelectorAll("[data-panel]").forEach((button) => {
  button.addEventListener("click", () => openPanel(button.dataset.panel));
});

function applyOpenedWorld() {
  paintWorlds();
  paintFill(state.fill);
  paintStatus(state.status);
  paintNotice((state.notices || []).at(-1) || "");
  paintMeters(state.meters);
  renderLog("end");
}

function mountCardEditor(host, cardsData, options) {
  const saveEnabled = !options || options.save !== false;
  const cards = cardsData.cards || (cardsData.cards = []);
  let current = 0;
  let query = "";
  const layout = document.createElement("div");
  layout.className = "cards-layout";
  const left = document.createElement("div");
  const listLabel = document.createElement("p");
  listLabel.className = "section";
  listLabel.textContent = t("cards.list");
  const search = document.createElement("input");
  search.type = "search";
  search.placeholder = t("cards.search");
  const list = document.createElement("div");
  list.className = "card-list";
  const right = document.createElement("div");
  const title = document.createElement("input");
  title.type = "text";
  const desc = document.createElement("textarea");
  desc.id = "card-desc";
  desc.rows = 10;
  const triggers = document.createElement("input");
  triggers.type = "text";
  triggers.placeholder = t("cards.triggers_ph");
  const note = document.createElement("p");
  note.className = "error";

  function labeled(text, field, hint) {
    const wrap = document.createElement("div");
    const label = document.createElement("label");
    label.textContent = text;
    label.append(field);
    wrap.append(label);
    if (hint) {
      const help = document.createElement("p");
      help.className = "hint";
      help.textContent = hint;
      wrap.append(help);
    }
    return wrap;
  }

  function nextId() {
    let max = 0;
    for (const card of cards) {
      const match = String(card.id || "").match(/card_(\d+)/);
      if (match) max = Math.max(max, Number(match[1]));
    }
    return `card_${String(max + 1).padStart(3, "0")}`;
  }

  function read() {
    if (!cards[current]) return;
    cards[current].title = title.value.trim() || t("cards.untitled");
    cards[current].description = desc.value;
    cards[current].triggers = triggers.value.split(/[,;\n]+/).map((item) => item.trim()).filter(Boolean);
  }

  function write() {
    const card = cards[current] || { title: "", description: "", triggers: [] };
    title.value = card.title || "";
    desc.value = asText(card.description);
    triggers.value = (card.triggers || []).map(asText).join(", ");
  }

  function visible() {
    const needle = query.trim().toLowerCase();
    return cards.map((card, index) => ({ card, index })).filter(({ card }) => {
      if (!needle) return true;
      const blob = `${asText(card.title)} ${asText(card.description)} ${(card.triggers || []).map(asText).join(" ")}`.toLowerCase();
      return blob.includes(needle);
    });
  }

  function draw() {
    list.innerHTML = "";
    for (const item of visible()) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = item.card.title || t("cards.untitled");
      button.setAttribute("aria-pressed", item.index === current ? "true" : "false");
      button.addEventListener("click", () => {
        read();
        current = item.index;
        write();
        draw();
      });
      list.append(button);
    }
  }

  search.addEventListener("input", () => {
    read();
    query = search.value;
    draw();
  });
  const row = document.createElement("div");
  row.className = "row";
  const add = document.createElement("button");
  add.type = "button";
  add.textContent = t("btn.add");
  add.addEventListener("click", () => {
    read();
    cards.push({ id: nextId(), title: t("cards.new"), description: "", triggers: [] });
    current = cards.length - 1;
    write();
    draw();
  });
  const del = document.createElement("button");
  del.type = "button";
  del.className = "danger";
  del.textContent = t("btn.delete");
  del.addEventListener("click", () => {
    if (!cards[current]) return;
    if (!window.confirm(t("cards.delete_q"))) return;
    cards.splice(current, 1);
    current = Math.max(0, current - 1);
    write();
    draw();
  });
  const gen = document.createElement("button");
  gen.type = "button";
  gen.textContent = t("cards.generate_desc");
  gen.addEventListener("click", () => {
    note.textContent = "";
    if (!title.value.trim()) {
      note.textContent = t("cards.enter_title_first");
      return;
    }
    api("/api/cards/describe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: title.value, description: desc.value }),
    }).catch(() => {});
  });
  const save = document.createElement("button");
  save.type = "button";
  save.className = "primary";
  save.textContent = t("btn.save");
  save.addEventListener("click", async () => {
    read();
    await api("/api/cards", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cards }),
    });
    await refresh("keep");
    draw();
  });
  row.append(add, del, gen);
  if (saveEnabled) row.append(save);
  right.append(
    labeled(t("cards.title"), title),
    labeled(t("cards.desc"), desc),
    labeled(t("cards.triggers"), triggers, t("cards.empty_triggers")),
    note,
    row,
  );
  left.append(listLabel, search, list);
  layout.append(left, right);
  host.append(layout);
  write();
  draw();
  return { read };
}

async function renderWorlds() {
  panelTitle.textContent = t("btn.worlds");
  panelBody.innerHTML = "";
  const data = await api("/api/worlds");
  let selected = data.current || (data.worlds || [])[0] || "";
  const heading = document.createElement("p");
  heading.className = "section";
  heading.textContent = t("dialog.your_worlds");
  const list = document.createElement("div");
  list.className = "world-list";
  function draw() {
    list.innerHTML = "";
    for (const name of data.worlds || []) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = name;
      button.setAttribute("aria-pressed", name === selected ? "true" : "false");
      button.addEventListener("click", () => {
        selected = name;
        draw();
      });
      list.append(button);
    }
  }
  draw();
  const note = document.createElement("p");
  note.className = "error";
  const actions = document.createElement("div");
  actions.className = "row";
  const load = document.createElement("button");
  load.type = "button";
  load.className = "primary";
  load.textContent = t("btn.load");
  load.addEventListener("click", async () => {
    if (!selected) return;
    state = await api("/api/worlds/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: selected }),
    });
    applyOpenedWorld();
    panel.close();
  });
  const del = document.createElement("button");
  del.type = "button";
  del.className = "danger";
  del.textContent = t("btn.delete");
  del.addEventListener("click", async () => {
    if (!selected) return;
    const question = t("dialog.delete_world_q").replace("{name}", selected);
    if (!window.confirm(question)) return;
    state = await api(`/api/worlds/${encodeURIComponent(selected)}`, { method: "DELETE" });
    applyOpenedWorld();
    renderWorlds();
  });
  const create = document.createElement("button");
  create.type = "button";
  create.textContent = t("btn.create");
  create.addEventListener("click", () => renderCreateWorld());
  const exp = document.createElement("button");
  exp.type = "button";
  exp.textContent = t("btn.export");
  exp.addEventListener("click", () => {
    if (!selected) return;
    const link = document.createElement("a");
    link.href = `/api/worlds/${encodeURIComponent(selected)}/export`;
    link.download = `${selected}.zip`;
    document.body.append(link);
    link.click();
    link.remove();
  });
  const file = document.createElement("input");
  file.type = "file";
  file.accept = ".zip,application/zip";
  file.hidden = true;
  const imp = document.createElement("button");
  imp.type = "button";
  imp.textContent = t("btn.import");
  imp.addEventListener("click", () => {
    note.textContent = "";
    file.click();
  });
  file.addEventListener("change", async () => {
    const chosen = file.files && file.files[0];
    file.value = "";
    if (!chosen) return;
    const stem = chosen.name.replace(/\.zip$/i, "").trim();
    note.textContent = "";
    try {
      const imported = await api(`/api/worlds/import?name=${encodeURIComponent(stem)}`, {
        method: "POST",
        headers: { "Content-Type": "application/zip" },
        body: chosen,
      });
      state = imported.state;
      applyOpenedWorld();
      panel.close();
    } catch (err) {
      note.textContent = err.status === 409 ? t("dialog.bad_name_msg") : t("dialog.import_failed");
    }
  });
  actions.append(load, exp, imp, create, del);
  panelBody.append(heading, list, note, file, actions);
}

async function renderCreateWorld() {
  panelTitle.textContent = t("dialog.create_world");
  panelBody.innerHTML = "";
  const draft = await api("/api/worlds/template");
  const error = document.createElement("p");
  error.className = "error";
  const nameLabel = document.createElement("label");
  nameLabel.textContent = t("dialog.world_name");
  const name = document.createElement("input");
  name.type = "text";
  name.value = draft.name || "";
  nameLabel.append(name);
  const files = draft.files || {};
  const names = Object.keys(files);
  let currentFile = names[0] || "";
  const buttons = document.createElement("div");
  buttons.className = "file-buttons";
  const area = document.createElement("textarea");
  area.rows = 12;
  function show(file) {
    currentFile = file;
    area.value = files[file] || "";
    buttons.querySelectorAll("button").forEach((button) => {
      button.setAttribute("aria-pressed", button.dataset.file === file ? "true" : "false");
    });
  }
  for (const file of names) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.file = file;
    button.textContent = t(`world_file.${file}`);
    button.addEventListener("click", () => show(file));
    buttons.append(button);
  }
  area.addEventListener("input", () => { files[currentFile] = area.value; });
  if (currentFile) show(currentFile);
  const cardsTitle = document.createElement("p");
  cardsTitle.className = "section";
  cardsTitle.textContent = t("world_file.story_cards");
  const cardsHost = document.createElement("div");
  const editor = mountCardEditor(cardsHost, draft.cards || { cards: [] }, { save: false });
  const actions = document.createElement("div");
  actions.className = "row";
  const ok = document.createElement("button");
  ok.type = "button";
  ok.className = "primary";
  ok.textContent = t("btn.create_ok");
  ok.addEventListener("click", async () => {
    error.textContent = "";
    files[currentFile] = area.value;
    editor.read();
    try {
      const created = await api("/api/worlds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.value, files, cards: draft.cards }),
      });
      state = created.state;
      applyOpenedWorld();
      panel.close();
    } catch (err) {
      error.textContent = t("dialog.bad_name_msg");
    }
  });
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.textContent = t("btn.cancel");
  cancel.addEventListener("click", () => renderWorlds());
  actions.append(ok, cancel);
  panelBody.append(error, nameLabel, buttons, area, cardsTitle, cardsHost, actions);
}

async function renderFiles() {
  const files = await api("/api/files");
  const names = Object.keys(files);
  let current = names[0] || "";
  const buttons = document.createElement("div");
  buttons.className = "file-buttons";
  const area = document.createElement("textarea");
  area.rows = 16;
  function show(name) {
    current = name;
    area.value = files[name] || "";
    buttons.querySelectorAll("button").forEach((button) => {
      button.setAttribute("aria-pressed", button.dataset.file === name ? "true" : "false");
    });
  }
  for (const name of names) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.file = name;
    button.textContent = t(`world_file.${name}`);
    button.addEventListener("click", () => show(name));
    buttons.append(button);
  }
  area.addEventListener("input", () => { files[current] = area.value; });
  if (current) show(current);
  const save = document.createElement("button");
  save.type = "button";
  save.textContent = t("btn.save");
  save.addEventListener("click", async () => {
    files[current] = area.value;
    const result = await api(`/api/files/${encodeURIComponent(current)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: area.value }),
    });
    paintFill(result.fill);
    await refresh("keep");
  });
  panelBody.append(buttons, area, save);
}

async function renderCards() {
  const data = await api("/api/cards");
  mountCardEditor(panelBody, data);
}

async function renderMemory() {
  const memory = await api("/api/memory");
  const box = document.createElement("div");
  for (const entry of memory.entries || []) {
    const p = document.createElement("p");
    p.textContent = `${entry.id}: ${entry.summary || ""}`;
    box.append(p);
  }
  if (!memory.entries || !memory.entries.length) {
    const p = document.createElement("p");
    p.textContent = "—";
    box.append(p);
  }
  panelBody.append(box);
}

async function renderPrompt() {
  const data = await api("/api/prompt");
  const prompt = data.prompt;
  const area = document.createElement("textarea");
  area.rows = 18;
  area.readOnly = true;
  area.value = prompt ? `${prompt.system || ""}\n\n---\n\n${prompt.user || ""}` : "—";
  panelBody.append(area);
}

async function renderScene(extra) {
  let scene = extra && extra.prompt ? extra : (await api("/api/scene")).scene;
  const prompt = document.createElement("textarea");
  prompt.rows = 8;
  prompt.readOnly = true;
  prompt.value = scene ? scene.prompt || "" : "";
  const negative = document.createElement("textarea");
  negative.rows = 4;
  negative.readOnly = true;
  negative.value = scene ? scene.negative || "" : "";
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = t("btn.scene_prompt");
  button.addEventListener("click", () => api("/api/scene", { method: "POST" }));
  panelBody.append(prompt, negative, button);
}

async function renderSettings() {
  settingsCache = await api("/api/settings");
  const tabs = document.createElement("div");
  tabs.className = "tabs";
  const body = document.createElement("div");
  const names = [
    ["ai", "dialog.tab_ai"],
    ["game", "dialog.tab_game"],
    ["prompts", "dialog.tab_prompts"],
  ];
  function show(which) {
    body.innerHTML = "";
    tabs.querySelectorAll("button").forEach((button) => button.setAttribute("aria-pressed", button.dataset.tab === which ? "true" : "false"));
    if (which === "ai") body.append(aiFields());
    else if (which === "game") body.append(gameFields());
    else body.append(promptFields());
  }
  for (const [id, key] of names) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.tab = id;
    button.textContent = t(key);
    button.addEventListener("click", () => show(id));
    tabs.append(button);
  }
  const error = document.createElement("p");
  error.className = "error";
  const save = document.createElement("button");
  save.type = "button";
  save.textContent = t("btn.save");
  save.addEventListener("click", async () => {
    error.textContent = "";
    try {
      settingsCache = await api("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settingsCache),
      });
      await refresh("keep");
    } catch (err) {
      error.textContent = JSON.stringify(err.body || err.message);
    }
  });
  panelBody.append(lanBlock(), tabs, body, error, save);
  show("ai");

  function lanBlock() {
    const box = document.createElement("div");
    box.className = "lan-box";
    const hint = document.createElement("p");
    hint.className = "hint";
    hint.textContent = t("dialog.lan_hint");
    const urls = document.createElement("div");
    urls.className = "lan-urls";
    const restart = document.createElement("p");
    restart.className = "hint";
    let info = null;
    function address(label, value) {
      const wrap = document.createElement("label");
      wrap.textContent = label;
      const input = document.createElement("input");
      input.type = "text";
      input.readOnly = true;
      input.value = value;
      input.addEventListener("focus", () => input.select());
      wrap.append(input);
      return wrap;
    }
    function paint() {
      urls.replaceChildren();
      restart.textContent = "";
      if (!info) return;
      urls.append(address(t("dialog.lan_this_computer"), info.local_url));
      if (info.lan_urls && info.lan_urls.length) {
        for (const url of info.lan_urls) urls.append(address(t("dialog.lan_phone"), url));
      } else if (!(info.tailscale_urls && info.tailscale_urls.length)) {
        const empty = document.createElement("p");
        empty.className = "hint";
        empty.textContent = t("dialog.lan_none");
        urls.append(empty);
      }
      for (const url of info.tailscale_urls || []) urls.append(address(t("dialog.lan_tailscale"), url));
      const open = Boolean(settingsCache.lan_access);
      const listening = info.listening === "0.0.0.0";
      restart.textContent = open === listening ? "" : t("dialog.lan_restart");
    }
    const toggle = check(t("dialog.lan_access"), "lan_access");
    toggle.querySelector("input").addEventListener("change", paint);
    api("/api/network").then((payload) => {
      info = payload;
      paint();
    }).catch(() => {});
    box.append(heading(t("dialog.lan_title")), toggle, hint, urls, restart);
    return box;
  }

  function field(label, key, options) {
    const spec = options || {};
    const wrap = document.createElement("label");
    wrap.textContent = label;
    const input = document.createElement("input");
    input.type = spec.type || "text";
    if (spec.min != null) input.min = String(spec.min);
    if (spec.max != null) input.max = String(spec.max);
    if (spec.step != null) input.step = String(spec.step);
    input.value = settingsCache[key] ?? "";
    input.dataset.setting = key;
    input.addEventListener("input", () => {
      settingsCache[key] = spec.type === "number" ? Number(input.value) : input.value;
    });
    wrap.append(input);
    return wrap;
  }
  function check(label, key) {
    const wrap = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(settingsCache[key]);
    input.addEventListener("change", () => { settingsCache[key] = input.checked; });
    wrap.append(input, document.createTextNode(" " + label));
    return wrap;
  }
  function heading(text) {
    const node = document.createElement("p");
    node.className = "section";
    node.textContent = text;
    return node;
  }
  function choice(label, key, values) {
    const wrap = document.createElement("label");
    wrap.textContent = label;
    const select = document.createElement("select");
    const current = String(settingsCache[key] ?? "");
    const options = values.includes(current) ? values : [current, ...values];
    for (const value of options) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.append(option);
    }
    select.value = current;
    select.addEventListener("change", () => { settingsCache[key] = Number(select.value); });
    wrap.append(select);
    return wrap;
  }
  function aiFields() {
    const box = document.createElement("div");
    box.append(heading(t("dialog.api_config")));
    const preset = document.createElement("select");
    preset.id = "settings-preset";
    const manual = document.createElement("option");
    manual.value = "";
    manual.textContent = t("dialog.manual_preset");
    preset.append(manual);
    for (const item of settingsCache.api_presets || []) {
      const option = document.createElement("option");
      option.value = item.name;
      option.textContent = item.name;
      preset.append(option);
    }
    const known = [...preset.options].some((option) => option.value === (settingsCache.active_api_preset || ""));
    preset.value = known ? (settingsCache.active_api_preset || "") : "";
    const url = field(t("dialog.api_url"), "api_url");
    const key = field(t("dialog.api_key"), "api_key", { type: "password" });
    const model = field(t("dialog.model"), "model");
    const keyInput = key.querySelector("input");
    preset.addEventListener("change", () => {
      settingsCache.active_api_preset = preset.value;
      const found = (settingsCache.api_presets || []).find((item) => item.name === preset.value);
      if (!found) return;
      settingsCache.api_url = found.api_url || "";
      settingsCache.api_key = found.api_key || "";
      settingsCache.model = found.model || "";
      url.querySelector("input").value = settingsCache.api_url;
      keyInput.value = settingsCache.api_key;
      model.querySelector("input").value = settingsCache.model;
    });
    const showKey = check(t("dialog.show_key"), "show_api_key");
    showKey.querySelector("input").checked = false;
    showKey.querySelector("input").addEventListener("change", (event) => {
      keyInput.type = event.target.checked ? "text" : "password";
    });
    const actions = document.createElement("div");
    actions.className = "row";
    const saveAs = document.createElement("button");
    saveAs.type = "button";
    saveAs.textContent = t("btn.save_as");
    saveAs.addEventListener("click", () => {
      const name = window.prompt(t("dialog.preset_name"));
      if (!name || !name.trim()) return;
      const data = {
        name: name.trim(),
        api_url: settingsCache.api_url || "",
        api_key: settingsCache.api_key || "",
        model: settingsCache.model || "",
      };
      const list = settingsCache.api_presets || [];
      const index = list.findIndex((item) => item.name === data.name);
      if (index >= 0) list[index] = data;
      else list.push(data);
      settingsCache.api_presets = list;
      settingsCache.active_api_preset = data.name;
      show("ai");
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = t("btn.delete_icon");
    remove.addEventListener("click", () => {
      const name = settingsCache.active_api_preset;
      if (!name) {
        error.textContent = t("dialog.delete_preset_pick");
        return;
      }
      const question = t("dialog.delete_preset_q").replace("{name}", name);
      if (!window.confirm(question)) return;
      settingsCache.api_presets = (settingsCache.api_presets || []).filter((item) => item.name !== name);
      settingsCache.active_api_preset = "";
      error.textContent = "";
      show("ai");
    });
    actions.append(saveAs, remove);
    const presetWrap = document.createElement("label");
    presetWrap.append(preset);
    box.append(
      presetWrap,
      preset,
      actions,
      url,
      key,
      showKey,
      model,
      field(t("dialog.temperature"), "temperature", { type: "number", min: 0, max: 2, step: 0.1 }),
      field(t("dialog.context_size"), "context_size", { type: "number", min: 4096, max: 131072, step: 4096 }),
    );
    return box;
  }
  function gameFields() {
    const box = document.createElement("div");
    const styleLabel = document.createElement("label");
    styleLabel.textContent = t("dialog.image_style");
    const style = document.createElement("select");
    for (const name of settingsCache.image_styles || []) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = t(`image_style.${name}`);
      style.append(option);
    }
    style.value = settingsCache.image_prompt_style || "";
    style.addEventListener("change", () => { settingsCache.image_prompt_style = style.value; });
    styleLabel.append(style);
    box.append(
      heading(t("dialog.gen_params")),
      check(t("dialog.stream"), "stream_mode"),
      field(t("dialog.max_tokens"), "max_tokens", { type: "number", min: 1, step: 1 }),
      heading(t("dialog.section_summary")),
      check(t("dialog.auto_summary"), "summary_enabled"),
      field(t("dialog.summary_fill"), "summary_fill_percent", { type: "number", min: 50, max: 95, step: 1 }),
      heading(t("dialog.section_memory")),
      check(t("dialog.memory_bank"), "memory_enabled"),
      choice(t("dialog.memory_every"), "memory_interval", ["3", "5", "10", "15"]),
      choice(t("dialog.memory_top_k"), "memory_top_k", ["3", "5", "7", "10"]),
      styleLabel,
    );
    return box;
  }
  function promptFields() {
    const box = document.createElement("div");
    const list = document.createElement("div");
    list.className = "prompt-list";
    const area = document.createElement("textarea");
    area.rows = 12;
    const lang = settingsCache.language || "ru";
    settingsCache.prompt_overrides = settingsCache.prompt_overrides || { ru: {}, en: {} };
    let selected = null;
    function choose(prompt) {
      selected = prompt;
      area.value = prompt.text;
    }
    for (const group of settingsCache.prompts || []) {
      const title = document.createElement("p");
      title.textContent = group.title;
      list.append(title);
      for (const prompt of group.prompts) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = prompt.name || prompt.key;
        button.addEventListener("click", () => choose(prompt));
        list.append(button);
      }
    }
    area.addEventListener("input", () => {
      if (!selected) return;
      selected.text = area.value;
      settingsCache.prompt_overrides[lang] = settingsCache.prompt_overrides[lang] || {};
      settingsCache.prompt_overrides[lang][selected.key] = area.value;
    });
    const reset = document.createElement("button");
    reset.type = "button";
    reset.textContent = t("btn.reset_prompt");
    reset.addEventListener("click", () => {
      if (!selected) return;
      area.value = selected.builtin;
      selected.text = selected.builtin;
      settingsCache.prompt_overrides[lang][selected.key] = "";
    });
    box.append(list, area, reset);
    return box;
  }
}

window.addEventListener("scroll", () => {
  if (!tailReady || loadingOlder || !state || !state.history_from) return;
  if (window.scrollY > 80) return;
  if (document.documentElement.scrollHeight <= window.innerHeight + 80) return;
  loadOlder();
}, { passive: true });

function fitChrome() {
  const viewport = window.visualViewport;
  const keyboard = viewport
    ? Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop)
    : 0;
  document.documentElement.style.setProperty("--keyboard", `${Math.round(keyboard)}px`);
  const composer = document.querySelector("#composer");
  if (composer) {
    document.documentElement.style.setProperty("--composer-height", `${composer.offsetHeight}px`);
  }
}

fitChrome();
window.addEventListener("resize", fitChrome);
if (window.visualViewport) {
  window.visualViewport.addEventListener("resize", fitChrome);
  window.visualViewport.addEventListener("scroll", fitChrome);
}
actionEl.addEventListener("focus", () => {
  const follow = nearBottom();
  setTimeout(() => {
    fitChrome();
    if (follow) jumpToEnd();
  }, 280);
});

boot();
