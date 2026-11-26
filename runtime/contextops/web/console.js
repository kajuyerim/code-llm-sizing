"use strict";
const $ = (selector) => document.querySelector(selector);
const main = $("#main");
const pages = ["setup", "agents", "review"];
let page = "setup", project = "", projects = {}, details = null;
let currentRun = "", stream = null, runData = null, draftCategories = [];
let graphFilter = "", selectedFinding = "", graphObserver;
let openEvidence = new Set(), evidenceCache = new Map(), reviewFile = "";
let requestEpoch = 0, noticeTimer, navigationTimer;

function node(tag, text = "", className = "") {
  const result = document.createElement(tag);
  result.textContent = text;
  result.className = className;
  return result;
}
function button(text, action, className = "") {
  const result = node("button", text, className);
  result.type = "button";
  result.addEventListener("click", action);
  return result;
}
function formButton(text) {
  const result = node("button", text, "primary");
  result.type = "submit";
  return result;
}
function field(form, label, name, value = "", type = "text") {
  const wrapper = node("label", label);
  const input = document.createElement("input");
  input.type = type;
  input.name = name;
  if (type === "checkbox") input.checked = Boolean(value);
  else input.value = value;
  wrapper.append(input);
  form.append(wrapper);
  return input;
}
function selector(form, label, name, values, selected = "") {
  const wrapper = node("label", label);
  const select = document.createElement("select");
  select.name = name;
  for (const [value, label] of values) {
    const option = node("option", label);
    option.value = value;
    option.selected = value === selected;
    select.append(option);
  }
  wrapper.append(select);
  form.append(wrapper);
  return select;
}
function section(title, parent = main) {
  const container = node("section", "", "card");
  container.append(node("h2", title));
  parent.append(container);
  return container;
}
function notify(text) {
  const notice = $("#notice");
  notice.textContent = text;
  notice.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => { notice.hidden = true; }, 5500);
}
async function api(endpoint, body) {
  const response = await fetch("/api/" + endpoint, body === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
  return result;
}
function query(endpoint, args) {
  return api(endpoint + "?" + new URLSearchParams(args));
}
async function guarded(operation) {
  try { await operation(); }
  catch (error) { notify(error.message); }
}
function submit(form, send, text) {
  const submit = formButton(text);
  form.append(submit);
  form.onsubmit = (event) => {
    event.preventDefault();
    if (submit.disabled) return;
    submit.disabled = true;
    guarded(async () => {
      try { await send(new FormData(form)); }
      finally { submit.disabled = false; }
    });
  };
}
function heading(title) {
  const row = node("div", "", "heading");
  row.append(node("h1", title));
  main.append(row);
  return row;
}
function closeStream() {
  if (stream) stream.close();
  stream = null;
}
async function getProject() {
  return query("project", {project});
}
function chooseProject(key) {
  $(".sweep-dialog")?.close();
  $(".knowledge-diff-dialog")?.close();
  project = key;
  localStorage.setItem("contextops-project", key);
  $("#project-menu").open = false;
  setCurrentRun("");
  closeStream();
  render();
}
let projectRevealTimers = [];

function revealProjects() {
  for (const timer of projectRevealTimers) clearTimeout(timer);
  projectRevealTimers = [];
  const menu = $("#project-menu");
  const rows = menu.querySelectorAll(".project-popover button");
  rows.forEach((row) => row.classList.remove("revealed"));
  if (!menu.open) return;
  rows.forEach((row, index) => {
    projectRevealTimers.push(setTimeout(() => {
      if (menu.open) row.classList.add("revealed");
    }, index * 110));
  });
}

function renderProjects() {
  const list = $("#projects");
  list.replaceChildren();
  const name = projects[project]?.name || "Projects";
  $("#project-name").textContent = name;
  $("#project-toggle").title = name;
  for (const [key, row] of Object.entries(projects)) {
    list.append(button(row.name, () => chooseProject(key), key === project ? "active" : ""));
  }
  if ($("#project-menu").open) revealProjects();
}
function selectPage(next) {
  if (next === page) return;
  $(".sweep-dialog")?.close();
  $(".knowledge-diff-dialog")?.close();
  const direction = pages.indexOf(next) > pages.indexOf(page) ? 1 : -1;
  page = next;
  setNav();
  clearTimeout(navigationTimer);
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) { render(); return; }
  const wipe = $("#wipe");
  wipe.replaceChildren();
  for (let i = 0; i < 12; i++) {
    const tile = node("i", "", "go");
    tile.style.setProperty("--direction", direction);
    tile.style.animationDelay = (i * 13 % 31) + "ms";
    wipe.append(tile);
  }
  navigationTimer = setTimeout(render, 115);
}
function setNav() {
  document.querySelectorAll("nav button").forEach((tab) => {
    if (tab.dataset.page === page) tab.setAttribute("aria-current", "page");
    else tab.removeAttribute("aria-current");
  });
}
async function render() {
  const epoch = ++requestEpoch;
  closeStream();
  graphObserver?.disconnect();
  setNav();
  renderProjects();
  main.replaceChildren();
  if (!project) { renderConnect(); return; }
  try { details = await getProject(); }
  catch (error) {
    if (epoch === requestEpoch) { renderConnect(project); notify(error.message); }
    return;
  }
  if (epoch !== requestEpoch) return;
  draftCategories = (details.categories || []).map((item) => ({...item}));
  if (page === "setup") renderSetup();
  if (page === "agents") renderAgents();
  if (page === "review") renderReview();
}
function renderConnect(reconnect = "") {
  heading("Connect a project");
  const container = section("Local checkouts");
  const form = node("form");
  field(form, "Project name", "name", projects[reconnect]?.name || "");
  for (const [name, label] of [["app", "Application checkout"], ["kb", "Knowledge checkout"]]) {
    const input = field(form, label, name, projects[reconnect]?.[name] || "");
    input.required = true;
    const row = node("div", "", "inline");
    input.replaceWith(row);
    row.append(input, button("Browse…", () => guarded(async () => {
      const data = await api("pick", {});
      if (data.path) input.value = data.path;
    })));
  }
  field(form, "Application ID (optional)", "app_name");
  selector(form, "Default strategy", "strategy", strategyChoices, "fresh-specialists");
  field(form, "Enable the pre-push hook", "automatic", false, "checkbox");
  container.append(form);
  submit(form, async (data) => {
    const result = await api("connect", {...Object.fromEntries(data), reconnect, automatic: data.has("automatic")});
    projects = (await api("projects")).projects;
    chooseProject(result.id);
  }, "Connect");
}
const strategyChoices = [["fresh-specialists", "B · Fresh specialists"], ["sweeper-first", "A · Sweeper first"]];
function providerFields(form, onChange = () => {}) {
  const backend = selector(form, "Backend", "backend", [
    ["claude", "Claude"], ["codex", "Codex (GPT)"],
  ], details.backend);
  if (details.auth !== "subscription") backend.querySelector('option[value="codex"]').disabled = true;
  const model = field(form, "Model override", "model");
  const update = () => { model.placeholder = details.defaults[backend.value]; onChange(backend.value); };
  backend.addEventListener("change", update);
  update();
  return {backend, model};
}
function renderSetup() {
  heading("Configure Project");
  renderCategories();

  const connection = section("Connected repositories");
  const locations = node("dl", "", "checkout-list");
  for (const [name, location] of [["Application", details.app], ["Knowledge", details.kb]]) {
    const path = node("dd", location, "checkout-path");
    path.title = location;
    locations.append(node("dt", name), path);
  }
  if (details.knowledge_branch) {
    locations.append(node("dt", "Knowledge branch"), node("dd", details.knowledge_branch));
  }
  connection.append(locations);

  const controls = node("div", "", "setup-controls");
  const branch = togglePanel("Create an empty knowledge branch", false);
  branch.content.append(node("p", "Start fresh in the connected knowledge repo. This creates a local branch with empty knowledge templates. Your current branch’s history is preserved.", "muted"));
  const initForm = node("form");
  const initGrid = node("div", "", "form-grid");
  field(initGrid, "Name for the new branch", "branch", "knowledge/" + details.app_name).required = true;
  selector(initGrid, "Knowledge scope", "scope", [["team", "Team"], ["repository", "Application"]], details.scope);
  initForm.append(initGrid);
  submit(initForm, async (data) => {
    await api("init", {project, ...Object.fromEntries(data)});
    notify("Empty branch created. Review and commit below.");
    await render();
  }, "Create empty branch");
  branch.content.append(initForm);
  controls.append(branch.wrapper);

  const advanced = togglePanel("Sweep defaults", false);
  const defaults = node("form");
  const defaultsGrid = node("div", "", "form-grid");
  selector(defaultsGrid, "Strategy", "strategy", strategyChoices, details.strategy);
  const {backend, model} = providerFields(defaultsGrid);
  backend.value = details.run_backend || details.backend;
  backend.dispatchEvent(new Event("change"));
  model.value = details.run_model || "";
  defaults.append(defaultsGrid);
  if (!details.codex_available) defaults.append(node("small", "Codex CLI is unavailable on PATH."));
  submit(defaults, async (data) => {
    await api("sweep-defaults", {project, ...Object.fromEntries(data)});
    notify("Sweep defaults saved");
  }, "Save sweep defaults");
  advanced.content.append(defaults);
  controls.append(advanced.wrapper);
  connection.append(controls);

  if (details.diff) {
    const preview = section("Review setup changes");
    preview.append(node("pre", details.diff));
    preview.append(button("Commit setup", () => guarded(async () => {
      await api("commit", {project, preview: details.diff});
      notify("Setup committed");
      await render();
    }), "primary"));
  }
}
function renderCategories() {
  const currentProject = project;
  const draftKey = "contextops-category-draft:" + currentProject;
  const originalProfile = JSON.stringify(details.categories);
  const savedDraft = JSON.parse(sessionStorage.getItem(draftKey) || "null");
  let renderedScanId;
  if (savedDraft?.profile === originalProfile && Array.isArray(savedDraft.categories)) {
    draftCategories = savedDraft.categories;
    renderedScanId = savedDraft.scanId;
  }
  function rememberDraft() {
    sessionStorage.setItem(draftKey, JSON.stringify({
      profile: originalProfile, categories: draftCategories, scanId: renderedScanId,
    }));
  }
  const categories = section("What should we track?");
  categories.classList.add("category-setup");
  const profileStatus = node("p", details.profile_scope === "team" ? "Using the team profile."
    : details.profile_scope === "application" ? "Using this application’s profile."
    : "No category profile saved. Sweeps use the repository’s default policy.", "muted");
  categories.append(profileStatus);
  const grid = node("div", "", "form-grid");
  const {backend, model} = providerFields(grid);
  backend.value = details.run_backend || details.backend;
  backend.dispatchEvent(new Event("change"));
  model.value = details.run_model || "";
  const scanSessions = selector(grid, "Optional scan evidence", "scan_sessions", details.sessions.map((entry) =>
    [entry.session_id, entry.session_id.slice(0, 8) + " " + (entry.opening || "")]));
  scanSessions.multiple = true;
  for (const option of scanSessions.options) option.selected = false;
  const list = node("div", "", "category-list");
  const counter = node("small", "", "category-count");
  const empty = node("p", "Scan the repository to suggest categories, or add one yourself.", "category-empty muted");
  const scanState = node("p", "", "state");
  scanState.setAttribute("role", "status");
  const customPanel = togglePanel("Add a category manually", false);
  const scanOptions = togglePanel("Scan options", false);
  scanOptions.content.append(grid);
  const custom = node("form", "", "form-grid");
  field(custom, "Category name", "name").required = true;
  field(custom, "What should it collect?", "description").required = true;
  customPanel.content.append(custom);
  submit(custom, (data) => {
    const name = String(data.get("name")).trim();
    const description = String(data.get("description")).trim();
    if (!name || !description) throw new Error("Enter a name and collection description");
    const id = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 70) || "custom";
    if (draftCategories.some((existing) => existing.id === id)) throw new Error("A category with that name already exists");
    draftCategories.push({id, name, description, enabled: true});
    rememberDraft();
    custom.reset();
    draw();
  }, "Add category");
  function updateCount() {
    const count = draftCategories.filter((item) => item.enabled).length;
    counter.textContent = count + " of " + draftCategories.length + " selected";
  }
  function openCategory(item, updateTile) {
    const dialog = node("dialog", "", "category-dialog");
    dialog.append(node("h2", item.name), node("h3", "What to collect"),
      node("p", item.description));
    if (item.reason || item.path) {
      dialog.append(node("h3", "Why this category?"));
      if (item.reason) dialog.append(node("p", item.reason));
      if (item.path) dialog.append(node("code", item.path));
    }
    const actions = node("div", "", "actions");
    const selection = button("", () => {
      item.enabled = !item.enabled;
      rememberDraft();
      updateTile();
      updateCount();
      updateSelection();
    });
    function updateSelection() {
      selection.textContent = item.enabled ? "Remove from profile" : "Keep category";
      selection.setAttribute("aria-pressed", String(item.enabled));
    }
    updateSelection();
    actions.append(selection, button("Close", () => dialog.close()));
    dialog.append(actions);
    dialog.addEventListener("close", () => dialog.remove(), {once:true});
    document.body.append(dialog);
    dialog.showModal();
  }
  function draw() {
    list.replaceChildren();
    updateCount();
    empty.hidden = draftCategories.length > 0;
    save.hidden = !draftCategories.length && !details.profile_scope;
    recommendations.hidden = !draftCategories.some((item) => item.recommended);
    for (const item of draftCategories) {
      const tile = node("div", "", "category-tile");
      const title = button(item.name, () => openCategory(item, updateTile), "category-title");
      title.setAttribute("aria-haspopup", "dialog");
      const keep = button("", () => {
        item.enabled = !item.enabled;
        rememberDraft();
        updateTile();
        updateCount();
      }, "category-keep");
      function updateTile() {
        tile.classList.toggle("selected", item.enabled);
        keep.textContent = item.enabled ? "Selected" : "Keep";
        keep.setAttribute("aria-pressed", String(item.enabled));
        keep.setAttribute("aria-label", "Keep " + item.name);
      }
      updateTile();
      tile.append(title, keep);
      list.append(tile);
    }
  }
  function showScan(result) {
    const fresh = renderedScanId !== result.scan_id;
    const saved = new Set(details.categories.map((item) => item.id));
    const previous = new Map(draftCategories.map((item) => [item.id, item]));
    const candidates = (result.categories || []).map((item) => {
      const existing = previous.get(item.id);
      if (!existing) return item;
      if (!saved.has(item.id)) {
        if (!("recommended" in existing)) return existing;
        if (fresh) return item;
      }
      return {...item, ...existing, reason:item.reason, path:item.path, recommended:item.recommended};
    });
    const discovered = new Set(candidates.map((item) => item.id));
    draftCategories = [...candidates, ...draftCategories.filter((item) => !discovered.has(item.id)
      && (saved.has(item.id) || !("recommended" in item)))];
    scanState.textContent = candidates.length ? "Scanned " + result.revision.slice(0, 8)
      : "No categories suggested. You can add one manually.";
    renderedScanId = result.scan_id;
    rememberDraft();
    draw();
  }
  async function waitForScan(result) {
    if (result.status === "running") {
      scan.disabled = true;
      scanState.textContent = "Scanning committed repository";
    }
    while (result.status === "running" && currentProject === project && categories.isConnected) {
      await new Promise((resolve) => setTimeout(resolve, 700));
      result = await query("scan", {project: currentProject});
    }
    if (currentProject !== project || !categories.isConnected) return;
    if (result.status === "failed") {
      scanState.textContent = "";
      throw new Error(result.error);
    }
    if (result.status === "complete") showScan(result);
  }
  const actions = node("div", "", "actions");
  const scan = button("Scan repository", () => guarded(async () => {
    scan.disabled = true;
    scanState.textContent = "Scanning committed repository";
    try {
      const result = await api("scan", {project: currentProject, backend: backend.value, model: model.value,
                         sessions: Array.from(scanSessions.selectedOptions, (option) => option.value)});
      await waitForScan(result);
    } finally { scan.disabled = false; }
  }), "primary");
  const recommendations = button("Use recommendations", () => {
    draftCategories.forEach((item) => { if ("recommended" in item) item.enabled = item.recommended; });
    rememberDraft();
    draw();
  });
  actions.append(scan, recommendations, counter);
  const save = node("form", "", "profile-save");
  field(save, "Save as the team default", "team", false, "checkbox");
  submit(save, async (data) => {
    await api("profile", {project: currentProject, categories: draftCategories, team: data.has("team")});
    sessionStorage.removeItem(draftKey);
    notify("Profile saved to setup diff. Review and commit it.");
    await render();
  }, "Save profile");
  categories.append(actions, scanState, empty, list, customPanel.wrapper, scanOptions.wrapper, save);
  draw();
  guarded(async () => {
    const result = await query("scan", {project: currentProject});
    if (result.status === "failed") return;
    try { await waitForScan(result); }
    finally { scan.disabled = false; }
  });
}
function openSweep() {
  if ($(".sweep-dialog")) return;
  const selected = project;
  const dialog = node("dialog", "", "sweep-dialog");
  dialog.append(node("h2", "New sweep"));
  const form = node("form");
  const branch = selector(form, "Branch", "branch",
    details.branches.map(({ref, label}) => [ref, label]), details.branch);
  const sessions = selector(form, "Development sessions", "sessions", details.sessions.map((entry) =>
    [entry.session_id, entry.session_id.slice(0, 8) + " " + (entry.opening || "")]));
  sessions.multiple = true;
  sessions.required = true;
  if (sessions.options.length === 1) sessions.options[0].selected = true;
  if (!sessions.options.length) form.append(node("small", "No local Claude Code sessions for this checkout."));
  const range = node("p", "", "state");
  form.append(range);
  let preview, version = 0;
  submit(form, async (data) => {
    if (!preview?.ready) return;
    const result = await api("run", {project: selected, branch: data.get("branch"),
      sessions: data.getAll("sessions"), preview: [preview.base, preview.head]});
    dialog.close();
    if (project === selected) {
      setCurrentRun(result.run);
      await render();
    }
  }, "Run sweep");
  const submitButton = form.querySelector('[type="submit"]');
  if (details.dirty) form.append(node("small", "Commit the knowledge setup before starting."));
  form.append(button("Cancel", () => dialog.close()));
  async function update() {
    const request = ++version;
    submitButton.disabled = true;
    preview = null;
    range.textContent = "Resolving range";
    try {
      const result = await query("sweep-range", {project: selected, branch: branch.value});
      if (request !== version || !dialog.isConnected) return;
      preview = result;
      range.textContent = !result.ready ? "No new commits to sweep."
        : (result.checkpoint ? "Since last confirmed sweep" : "Latest branch change")
          + " · " + result.base.slice(0, 7) + " → " + result.head.slice(0, 7);
      submitButton.disabled = details.dirty || !result.ready || !sessions.options.length;
    } catch (error) {
      if (request === version && dialog.isConnected) range.textContent = error.message;
    }
  }
  branch.addEventListener("change", update);
  dialog.addEventListener("close", () => dialog.remove(), {once: true});
  dialog.append(form);
  document.body.append(dialog);
  dialog.showModal();
  update();
}
function setCurrentRun(id) {
  if (currentRun === id) return;
  currentRun = id;
  runData = null;
  graphFilter = "";
  selectedFinding = "";
  openEvidence.clear();
  evidenceCache.clear();
  reviewFile = "";
}
function runSelector(onSelect) {
  const selected = details.runs.find((run) => run.id === currentRun) || details.runs[0];
  const controls = node("div", "", "run-controls");
  if (selected) {
    const input = selector(controls, "Sweep run", "run", details.runs.map((run) => [
      run.id, [run.id, run.backend, run.model].filter(Boolean).join(" · "),
    ]), selected.id);
    input.onchange = () => onSelect(input.value);
  } else {
    controls.append(node("p", "No sweeps for this project.", "muted"));
  }
  controls.append(button("Refresh", render));
  main.append(controls);
  return selected?.id;
}
function renderAgents() {
  heading("Acquire Knowledge").append(button("New sweep", openSweep, "primary"));
  const selected = runSelector(selectRun);
  if (!selected) return;
  const view = node("div");
  view.id = "run-detail";
  main.append(view);
  selectRun(selected);
}
function selectRun(id) {
  setCurrentRun(id);
  closeStream();
  graphObserver?.disconnect();
  const selected = project;
  const view = $("#run-detail");
  const loading = node("p", "Loading run…", "muted");
  view.replaceChildren(loading);
  const isActive = () => view.isConnected && project === selected && currentRun === id && page === "agents";
  guarded(async () => {
    const data = await query("run", {project: selected, run: id});
    if (!loading.isConnected || !isActive()) return;
    runData = data;
    drawRun();
    if (["failed", "complete"].includes(runData.status)) return;
    const events = new EventSource("/api/events?" + new URLSearchParams({project: selected, run: id}));
    stream = events;
    events.onmessage = (event) => {
      if (stream !== events || !isActive()) return;
      const item = JSON.parse(event.data);
      if (runData.events.some((previous) => previous.id === item.id)) return;
      runData.events.push(item);
      drawRun();
      if (item.kind === "review_finished") {
        guarded(async () => {
          const updated = await query("run", {project: selected, run: id});
          if (stream === events && isActive()) {
            runData.review = updated.review;
            runData.forks = updated.forks;
            runData.sweeper_findings = updated.sweeper_findings;
            drawRun();
          }
        });
      }
      if (item.kind === "run_finished") {
        closeStream();
        selectRun(id);
      }
    };
  });
}
const sourceNames = {conversation:"Conversation", diff:"Git diff", source:"Source code", memory:"Repo memory"};
const verdictNames = {accepted:"Accepted", rejected:"Rejected", deferred:"Needs review", no_change:"No change"};

function findingCopy(record) {
  const text = (record.text || "").trim();
  if (!text.startsWith("|") || !text.endsWith("|")) {
    return {title: text || record.reason || record.target || "No change", details: []};
  }
  const cells = text.slice(1, -1).trim().split(/\s+\|\s+/);
  if (cells.length < 5) return {title: text, details: []};
  const [id, title, ...rest] = cells;
  const details = rest.slice(0, -1).filter((cell) => !/^(company|app:\S+|tool:\S+)$/.test(cell));
  return {title: title || id, details};
}

function agentName(label) {
  return (label || "").replace(/:handoffs$/, "");
}

function patchFiles(text) {
  const files = new Map();
  let entry, inHunk = false;
  for (const line of (text || "").split("\n")) {
    if (line.startsWith("diff --git ")) {
      const path = line.match(/^diff --git a\/.* b\/(.*)$/)?.[1];
      entry = path ? [] : undefined;
      if (entry) files.set(path, entry);
      inHunk = false;
    } else if (line.startsWith("@@ ") && entry) {
      inHunk = true;
    } else if (inHunk && (line[0] === "+" || line[0] === "-")) {
      entry.push({kind: line[0] === "+" ? "addition" : "deletion", text: line.slice(1)});
    }
  }
  return files;
}

function togglePanel(label, expanded, onToggle) {
  const wrapper = node("div", "", "console-disclosure");
  const content = node("div", "", "disclosure-content");
  const trigger = button("", () => {
    setOpen(content.hidden);
    onToggle?.(!content.hidden);
  }, "disclosure-trigger");
  const action = node("span", "", "disclosure-action");
  trigger.append(node("span", label), action);
  function setOpen(open) {
    trigger.setAttribute("aria-expanded", String(open));
    action.textContent = open ? "Hide" : "Show";
    content.hidden = !open;
  }
  wrapper.append(trigger, content);
  setOpen(expanded);
  return {wrapper, content};
}

function mergedSpans(spans) {
  const merged = [];
  for (const [start, end] of spans.sort(([a], [b]) => a - b)) {
    const last = merged.at(-1);
    if (last && start <= last[1]) last[1] = Math.max(last[1], end);
    else merged.push([start, end]);
  }
  return merged;
}

function drawEdges(graph, canvas, positions, edges, active) {
  const outer = graph.getBoundingClientRect();
  if (!outer.width || !outer.height) return;
  const scale = window.devicePixelRatio || 1;
  canvas.width = outer.width * scale;
  canvas.height = outer.height * scale;
  const context = canvas.getContext("2d");
  if (!context) return;
  context.scale(scale, scale);
  const snap = (n) => Math.round(n * scale) / scale + .5 / scale;
  const groups = new Map();
  for (const [from, to] of edges) {
    const origin = positions.get(from);
    const target = positions.get(to);
    if (!origin || !target) continue;
    const upper = origin.closest(".graph-lane");
    const lower = target.closest(".graph-lane");
    if (upper === lower) continue;
    const groupKey = upper.dataset.lane + ":" + lower.dataset.lane;
    if (!groups.has(groupKey)) {
      const bottom = upper.getBoundingClientRect().bottom;
      const top = lower.getBoundingClientRect().top;
      if (top <= bottom) continue;
      groups.set(groupKey, {rail: snap((bottom + top) / 2 - outer.top), routes: []});
    }
    const a = origin.getBoundingClientRect();
    const b = target.getBoundingClientRect();
    groups.get(groupKey).routes.push({
      x1: snap(a.left + a.width / 2 - outer.left), y1: snap(a.bottom - outer.top),
      x2: snap(b.left + b.width / 2 - outer.left), y2: snap(b.top - outer.top - 3),
      active: active.has(from) && active.has(to),
    });
  }

  context.lineWidth = 1;
  for (const {rail, routes} of groups.values()) {
    for (const highlight of [false, true]) {
      const visible = highlight ? routes.filter((route) => route.active) : routes;
      context.strokeStyle = highlight ? "#e2e2d9" : "#686b66";
      context.setLineDash([]);
      context.beginPath();
      for (const [left, right] of mergedSpans(visible.map(({x1, x2}) => [Math.min(x1,x2), Math.max(x1,x2)]))) {
        context.moveTo(left, rail);
        context.lineTo(right, rail);
      }
      context.stroke();
      context.setLineDash(highlight ? [] : [3, 3]);
      const stems = new Map();
      function stem(x, from, to) {
        if (!stems.has(x)) stems.set(x, []);
        stems.get(x).push([Math.min(from, to), Math.max(from, to)]);
      }
      for (const {x1, y1, x2, y2} of visible) {
        stem(x1, y1, rail);
        stem(x2, rail, y2);
      }
      context.beginPath();
      for (const [x, spans] of stems) {
        for (const [top, bottom] of mergedSpans(spans)) {
          context.moveTo(x, top);
          context.lineTo(x, bottom);
        }
      }
      context.stroke();
      context.setLineDash([]);
      const arrows = new Map(visible.map(({x2,y2}) => [x2 + ":" + y2, [x2,y2]]));
      context.fillStyle = highlight ? "#e2e2d9" : "#888a82";
      for (const [x,y] of arrows.values()) {
        context.beginPath();
        context.moveTo(x - 3, y - 4);
        context.lineTo(x + 3, y - 4);
        context.lineTo(x, y);
        context.fill();
      }
    }
  }
}

function drawRun() {
  const view = $("#run-detail");
  if (!view || !runData) return;
  graphObserver?.disconnect();
  view.replaceChildren();
  const block = node("section", "", "card");
  block.append(node("h2", "Evidence flow"));
  const blocked = Object.values(runData.worker_notes || {}).some((note) =>
    /tool host (?:was|is) disabled|no evidence was inspected/i.test(note || ""));
  if (blocked) block.append(node("p", "Evidence inspection was blocked for at least one specialist. An empty result from that specialist does not mean there was nothing worth keeping.", "muted"));
  const findings = Object.entries(verdictNames).flatMap(([status]) =>
    (runData.review[status] || []).map((record, index) => ({
      status, index, record, id: status + ":" + index,
      sources: Array.from(new Set((record.evidence || []).map((ref) => ref.kind).filter(Boolean))),
    })));
  const agents = new Map();
  for (const event of runData.events) {
    if (!event.agent) continue;
    const name = agentName(event.agent);
    if (!agents.has(name)) agents.set(name, {status:"", messages:[]});
    const agent = agents.get(name);
    if (event.kind === "agent_started") agent.status = "running";
    if (event.kind === "agent_message") agent.messages.push(event.text);
    if (event.kind === "agent_finished") agent.status = event.status;
  }
  for (const {record} of findings) {
    const name = agentName(record.agent);
    if (name && !agents.has(name)) agents.set(name, {status:"", messages:[]});
  }
  const files = patchFiles(runData.patch);
  const applied = runData.writer?.applied || [];
  const matched = ({status, record}) => status === "accepted" && runData.writer?.committed && files.has(record.target)
    && applied.some((item) => item.target === record.target && item.op === record.op
                            && record.fact_id && record.fact_id === item.fact_id);
  const subset = findings.filter(({status, record, sources}) => !graphFilter
    || graphFilter === status || graphFilter === "agent:" + agentName(record.agent)
    || sources.includes(graphFilter) || (graphFilter === "writer" && status === "accepted")
    || (graphFilter === "files" && matched({status, record})));
  const focused = subset.find((item) => item.id === selectedFinding) || subset[0];
  const summary = node("div", "", "run-summary");
  const outcome = [runData.status];
  for (const status of Object.keys(verdictNames)) {
    const count = (runData.review[status] || []).length;
    if (count) outcome.push(count + " " + verdictNames[status].toLowerCase());
  }
  if (files.size) outcome.push(files.size + (files.size === 1 ? " file changed" : " files changed"));
  else if (runData.status === "complete") outcome.push("no knowledge changes");
  summary.append(node("p", outcome.join(" · "), "muted"));
  if (files.size) {
    const review = button("Review changes", () => {
      if (files.has(focused?.record.target)) reviewFile = focused.record.target;
      openKnowledgeDiff(files);
    }, "primary");
    review.setAttribute("aria-haspopup", "dialog");
    summary.append(review);
  } else if (runData.status === "complete" || runData.check) {
    summary.append(button("Open review", () => selectPage("review")));
  }
  const active = new Set(graphFilter ? [graphFilter] : []);
  if (focused) {
    for (const key of [...focused.sources, "agent:" + agentName(focused.record.agent), focused.status]) active.add(key);
    if (matched(focused)) { active.add("writer"); active.add("files"); }
  }
  const graph = node("div", "", "run-graph");
  const canvas = node("canvas");
  canvas.setAttribute("aria-hidden", "true");
  graph.append(canvas);
  const positions = new Map(), edges = [], edgeKeys = new Set();
  function edge(from,to) {
    const key = JSON.stringify([from,to]);
    if (!edgeKeys.has(key)) { edges.push([from,to]); edgeKeys.add(key); }
  }
  function lane(title, entries) {
    if (!entries.length) return;
    const row = node("div", "", "graph-lane");
    row.dataset.lane = title;
    const nodes = node("div", "", "graph-nodes");
    row.append(node("h3", title), nodes);
    for (const [key, title, meta, running] of entries) {
      const chip = button("", () => {
        graphFilter = graphFilter === key ? "" : key;
        selectedFinding = "";
        drawRun();
      }, "graph-node" + (running ? " tab-running" : ""));
      chip.setAttribute("aria-pressed", String(graphFilter === key));
      chip.append(node("span", title));
      if (meta) chip.append(node("small", meta));
      positions.set(key, chip);
      nodes.append(chip);
    }
    graph.append(row);
  }
  const sourceKeys = Array.from(new Set(findings.flatMap((finding) => finding.sources)));
  const inputNodes = sourceKeys.map((kind) => [
    kind, sourceNames[kind] || kind, findings.filter((item) => item.sources.includes(kind)).length + " findings",
  ]);
  const sweeper = agents.get("sweeper");
  if (sweeper) inputNodes.push(["agent:sweeper", "Sweeper", sweeper.status, sweeper.status === "running"]);
  lane("Inputs", inputNodes);
  lane("Specialists", [...agents].filter(([name]) => !["sweeper", "writer", "cartographer", "check-proposer"].includes(name))
    .map(([name, agent]) => {
      const count = findings.filter((item) => agentName(item.record.agent) === name && item.status !== "no_change").length;
      const short = name.replace(/-maintainer(?=:|$)/, "").replace(/^./, (letter) => letter.toUpperCase());
      return ["agent:" + name, short, agent.status === "running" ? "working" : agent.status && agent.status !== "success"
        ? agent.status : (count + (count === 1 ? " proposal" : " proposals")),
              agent.status === "running"];
    }));
  lane("Review", Object.entries(verdictNames).map(([status, title]) => [
    status, title, findings.filter((item) => item.status === status).length + " records",
  ]).filter(([status]) => findings.some((item) => item.status === status)));
  const writer = agents.get("writer");
  if (writer || runData.writer || files.size) {
    lane("Write", [["writer", "Writer", writer?.status === "running" ? "working" :
      runData.writer ? applied.length + " reported applied" : "result not recorded", writer?.status === "running"]]);
  }
  if (files.size) lane("Files", [["files", runData.writer?.committed ? "Knowledge commit" : "Written diff",
                                files.size + " changed files"]]);
  for (const finding of findings) {
    const agent = "agent:" + agentName(finding.record.agent);
    finding.sources.forEach((kind) => edge(kind, agent));
    edge(agent, finding.status);
  }
  for (const child of runData.forks || []) edge("agent:sweeper", "agent:" + child);
  if (writer || runData.writer) edge("accepted", "writer");
  if (files.size) edge("writer", "files");

  const panel = node("div", "", "findings");
  const list = node("div", "", "finding-list");
  const body = node("div", "", "finding-body");
  const selectedAgent = graphFilter.startsWith("agent:") ? agents.get(graphFilter.slice(6)) : null;
  if (graphFilter === "agent:sweeper") {
    for (const item of runData.sweeper_findings || []) {
      list.append(node("p", item.summary || item.text));
      if (item.suggested_home) list.append(node("small", item.suggested_home));
    }
  }
  for (const item of subset) {
    const {record, status, id} = item;
    const copy = findingCopy(record);
    const row = button("", () => { selectedFinding = id; drawRun(); });
    row.setAttribute("aria-pressed", String(focused?.id === id));
    row.append(node("small", verdictNames[status] + (record.fact_id ? " · " + record.fact_id : "")),
               node("div", copy.title));
    list.append(row);
  }
  if (focused) {
    const {record, status, index} = focused;
    const copy = findingCopy(record);
    body.append(node("span", verdictNames[status], "state"), node("h3", copy.title));
    for (const detail of copy.details) body.append(node("p", detail));
    const reason = record.rejected_because || record.policy_reason || record.reason;
    if (reason && reason !== copy.title) body.append(node("p", reason));
    (record.evidence || []).forEach((source, i) => {
      const citation = source.path ? source.path + (source.line ? ":" + source.line : "")
        : [source.session, source.message].filter(Boolean).join(" · ");
      const key = focused.id + ":" + i;
      const excerpt = node("pre", evidenceCache.get(key) || source.quote || "");
      const runId = runData.id, runProject = project;
      async function read() {
        if (evidenceCache.has(key)) return;
        const result = await query("evidence", {project: runProject, run: runId, status, index, evidence:i});
        if (project !== runProject || runData?.id !== runId) return;
        const content = result.heading + "\n\n" + result.text;
        evidenceCache.set(key, content);
        excerpt.textContent = content;
      }
      const display = togglePanel((sourceNames[source.kind] || "Evidence") + (citation ? " · " + citation : ""),
        openEvidence.has(key), (open) => {
          if (open) { openEvidence.add(key); guarded(read); }
          else openEvidence.delete(key);
        });
      display.content.append(excerpt);
      if (openEvidence.has(key)) guarded(read);
      body.append(display.wrapper);
    });
  } else {
    body.append(node("p", graphFilter === "agent:sweeper" && runData.sweeper_findings?.length
      ? "These are leads the sweeper passed to the specialists." :
        agents.size ? "No review findings for this selection yet." : "Waiting for the first agent event.", "muted"));
  }
  const coverage = graphFilter.startsWith("agent:") && runData.worker_notes?.[graphFilter.slice(6)];
  if (coverage) {
    body.append(node("h3", "Coverage"), node("p", coverage));
  }
  if (selectedAgent?.messages.length) {
    const messages = togglePanel("Agent messages", false);
    const text = node("div", "", "messages");
    selectedAgent.messages.forEach((line) => text.append(node("p", line)));
    messages.content.append(text);
    body.append(messages.wrapper);
  }
  panel.append(list, body);
  const graphScroll = node("div", "", "graph-scroll");
  graphScroll.append(graph);
  block.append(graphScroll, panel);
  view.append(summary, block);
  graphObserver = new ResizeObserver(() => drawEdges(graph, canvas, positions, edges, active));
  graphObserver.observe(graph);
}

function renderReview() {
  heading("Review Changes");
  const view = node("div");
  const runProject = project;
  function load(id) {
    setCurrentRun(id);
    const loading = node("p", "Loading review…", "muted");
    view.replaceChildren(loading);
    guarded(async () => {
      const run = await query("run", {project: runProject, run: id});
      if (!loading.isConnected || project !== runProject || page !== "review") return;
      view.replaceChildren();
      drawKnowledgeDiff(section("Knowledge diff", view), patchFiles(run.patch), run.status);
      drawCheck(section("Application check proposal", view), run, runProject);
    });
  }
  const selected = runSelector(load);
  if (!selected) return;
  main.append(view);
  load(selected);
}
function openKnowledgeDiff(files) {
  const dialog = node("dialog", "", "knowledge-diff-dialog");
  const title = node("h2", "Knowledge diff");
  title.id = "knowledge-diff-title";
  dialog.setAttribute("aria-labelledby", title.id);
  const close = button("Close", () => dialog.close());
  close.autofocus = true;
  const actions = node("div", "", "actions");
  actions.append(button("Open full review", () => selectPage("review")), close);
  const header = node("div", "", "knowledge-diff-header");
  header.append(title, actions);
  dialog.append(header);
  drawKnowledgeDiff(dialog, files);
  dialog.addEventListener("close", () => dialog.remove(), {once:true});
  document.body.append(dialog);
  dialog.showModal();
}
function drawKnowledgeDiff(card, files, status) {
  if (!files.size) {
    const message = status === "complete" ? "No knowledge changes for this run."
      : status === "failed" ? "No knowledge diff was recorded."
      : "Knowledge changes will appear here after the writer finishes. Refresh to check for updates.";
    card.append(node("p", message, "muted"));
    return;
  }
  const paths = [...files.keys()];
  const input = selector(card, "Changed file", "diff-file", paths.map((name) => [name, name]),
    files.has(reviewFile) ? reviewFile : paths[0]);
  const patch = node("div", "", "diff-lines");
  function showPatch() {
    const lines = files.get(input.value);
    if (!lines.length) {
      patch.replaceChildren(node("p", "No text additions or deletions in this file.", "muted"));
      return;
    }
    patch.replaceChildren(...lines.map(({kind, text}) => {
      const row = node("div", "", "diff-line " + kind);
      row.append(node("span", kind === "addition" ? "+" : "−"), node("code", text));
      return row;
    }));
  }
  input.onchange = () => { reviewFile = input.value; showPatch(); };
  showPatch();
  card.append(patch);
}
function drawCheck(card, run, runProject) {
  card.replaceChildren(card.firstElementChild);
  async function refresh() {
    const updated = await query("run", {project: runProject, run: run.id});
    if (card.isConnected && project === runProject && page === "review") drawCheck(card, updated, runProject);
  }
  const check = run.check;
  if (!check) {
    card.append(node("p", "No check proposal for this run."));
    if (run.status === "complete") {
      const propose = button("Propose a check", () => guarded(async () => {
        propose.disabled = true;
        try {
          await api("check-propose", {project: runProject, run: run.id});
          await refresh();
        } finally { propose.disabled = false; }
      }));
      card.append(propose);
    }
    return;
  }
  const status = run.applied ? "Staged" : run.verification?.exit_code === 0 ? "Verified" : check.status;
  card.append(node("p", status, "state"), node("p", check.reason || ""));
  if (!check.patch_sha256) return;
  if (check.record) card.append(node("p", check.record.text));
  card.append(node("code", check.patch_sha256), node("p", "Passing: " + check.passing),
              node("p", "Failing: " + check.failing), node("pre", run.check_patch));
  if (run.verification) card.append(node("p", "Verification exit code: " + run.verification.exit_code));
  const form = node("form");
  field(form, "Verification argv as JSON", "argv").placeholder = '["python", "check_timeout.py"]';
  if (check.suggested_verification) form.append(node("small", "Suggested: " + check.suggested_verification));
  submit(form, async (data) => {
    const result = await api("check-verify", {project: runProject, run: run.id, digest: check.patch_sha256,
                                             argv: JSON.parse(data.get("argv"))});
    notify("Verification exit code: " + result.exit_code);
    await refresh();
  }, "Verify in a temporary worktree");
  card.append(form, button("Stage reviewed patch", () => guarded(async () => {
    await api("check-apply", {project: runProject, run: run.id, digest: check.patch_sha256});
    notify("Patch staged in application checkout");
    await refresh();
  })));
}

document.querySelectorAll("nav button").forEach((tab) => tab.onclick = () => selectPage(tab.dataset.page));
$("#project-menu").addEventListener("toggle", revealProjects);
$("#add-project").onclick = () => { $("#project-menu").open = false; project = ""; selectPage("setup"); render(); };
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") $("#project-menu").open = false;
});
document.addEventListener("click", (event) => {
  if (!$("#project-menu").contains(event.target)) $("#project-menu").open = false;
});
guarded(async () => {
  projects = (await api("projects")).projects;
  const saved = localStorage.getItem("contextops-project");
  project = saved in projects ? saved : (Object.keys(projects)[0] || "");
  await render();
});
