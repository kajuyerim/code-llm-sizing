"use strict";
const $ = (selector) => document.querySelector(selector);
const main = $("#main");
const pages = ["setup", "agents", "checks"];
let page = "setup", project = "", projects = {}, details = null;
let currentRun = "", stream = null, runData = null, draftCategories = [];
let graphFilter = "", selectedFinding = "", graphObserver;
let openEvidence = new Set(), evidenceCache = new Map(), openDiff = false, fileFocus = "";
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
function section(title) {
  const container = node("section", "", "card");
  container.append(node("h2", title));
  main.append(container);
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
  project = key;
  localStorage.setItem("contextops-project", key);
  $("#project-menu").open = false;
  currentRun = "";
  graphFilter = "";
  selectedFinding = "";
  closeStream();
  render();
}
function renderProjects() {
  const list = $("#projects");
  list.replaceChildren();
  $("#project-toggle").textContent = projects[project]?.name || "Projects";
  for (const [key, row] of Object.entries(projects)) {
    list.append(button(row.name, () => chooseProject(key), key === project ? "active" : ""));
  }
}
function selectPage(next) {
  if (next === page) return;
  $(".sweep-dialog")?.close();
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
  if (page === "checks") renderChecks();
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
  const connection = section("01 · Connected checkouts");
  connection.append(node("p", details.app, "meta"), node("p", details.kb, "meta"));
  if (!details.codex_available) connection.append(node("small", "Codex CLI is unavailable on PATH."));
  const form = node("form");
  const grid = node("div", "", "form-grid");
  field(grid, "New knowledge branch", "branch", "knowledge/" + details.app_name);
  selector(grid, "Knowledge scope", "scope", [["team", "Team"], ["repository", "Application"]], details.scope);
  form.append(grid);
  const init = section("02 · Initialize knowledge");
  init.append(form);
  submit(form, async (data) => {
    await api("init", {project, ...Object.fromEntries(data)});
    await render();
  }, "Initialize on a new branch");
  renderCategories();
  const advanced = node("details", "", "card");
  advanced.append(node("summary", "Sweep defaults"));
  const defaults = node("form", "", "form-grid");
  selector(defaults, "Strategy", "strategy", strategyChoices, details.strategy);
  const {backend, model} = providerFields(defaults);
  backend.value = details.run_backend || details.backend;
  backend.dispatchEvent(new Event("change"));
  model.value = details.run_model || "";
  submit(defaults, async (data) => {
    await api("sweep-defaults", {project, ...Object.fromEntries(data)});
    notify("Sweep defaults saved");
  }, "Save sweep defaults");
  advanced.append(defaults);
  main.append(advanced);
  if (details.diff) {
    const preview = section("04 · Review setup changes");
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
  const categories = section("03 · What should we track?");
  const grid = node("div", "", "form-grid");
  const {backend, model} = providerFields(grid);
  const scanSessions = selector(grid, "Optional scan evidence", "scan_sessions", details.sessions.map((entry) =>
    [entry.session_id, entry.session_id.slice(0, 8) + " " + (entry.opening || "")]));
  scanSessions.multiple = true;
  for (const option of scanSessions.options) option.selected = false;
  const list = node("div");
  const counter = node("small");
  const scanState = node("p", "", "state");
  const custom = node("form", "", "form-grid");
  field(custom, "Custom category", "name");
  field(custom, "What should it collect?", "description");
  submit(custom, (data) => {
    const name = String(data.get("name")).trim();
    const description = String(data.get("description")).trim();
    if (!name || !description) throw new Error("Enter a name and collection description");
    const id = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 70) || "custom";
    if (draftCategories.some((existing) => existing.id === id)) throw new Error("A category with that name already exists");
    draftCategories.push({id, name, description, enabled: true});
    custom.reset();
    draw();
  }, "Add category");
  function draw() {
    list.replaceChildren();
    counter.textContent = draftCategories.filter((item) => item.enabled).length + " selected";
    for (const item of draftCategories) {
      const section = node("div", "", "category");
      const label = node("label");
      const selected = document.createElement("input");
      selected.type = "checkbox";
      selected.checked = item.enabled;
      selected.onchange = () => {
        item.enabled = selected.checked;
        counter.textContent = draftCategories.filter((entry) => entry.enabled).length + " selected";
      };
      label.append(selected, document.createTextNode(" " + item.name + (item.recommended ? " · Recommended" : "")));
      section.append(label, node("p", item.description, "muted"));
      if (item.reason || item.path) {
        const evidence = node("details");
        evidence.append(node("summary", "Why this category?"), node("p", item.reason || ""), node("code", item.path || ""));
        section.append(evidence);
      }
      list.append(section);
    }
  }
  const actions = node("div", "", "actions");
  const scan = button("Scan repository", () => guarded(async () => {
    scan.disabled = true;
    scanState.textContent = "Scanning committed repository";
    try {
      await api("scan", {project, backend: backend.value, model: model.value,
                         sessions: Array.from(scanSessions.selectedOptions, (option) => option.value)});
      while (currentProject === project && categories.isConnected) {
        await new Promise((resolve) => setTimeout(resolve, 700));
        const result = await query("scan", {project: currentProject});
        if (result.status === "running") continue;
        if (result.status === "failed") throw new Error(result.error);
        const previous = new Map(draftCategories.map((item) => [item.id, item]));
        for (const item of result.categories || []) {
          const existing = previous.get(item.id);
          previous.set(item.id, existing ? {...item, enabled: existing.enabled} : item);
        }
        draftCategories = [...previous.values()];
        scanState.textContent = "Scanned " + result.revision.slice(0, 8);
        draw();
        break;
      }
    } finally { scan.disabled = false; }
  }));
  actions.append(scan, button("Use recommendations", () => {
    draftCategories.forEach((item) => { if ("recommended" in item) item.enabled = item.recommended; });
    draw();
  }), counter);
  const save = node("form");
  field(save, "Save as the team default", "team", false, "checkbox");
  submit(save, async (data) => {
    await api("profile", {project, categories: draftCategories, team: data.has("team")});
    notify("Profile saved to setup diff. Review and commit it.");
    await render();
  }, "Save profile");
  categories.append(grid, actions, scanState, list, custom, save);
  draw();
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
      currentRun = result.run;
      graphFilter = "";
      selectedFinding = "";
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
function renderAgents() {
  heading("Acquire Knowledge").append(button("New sweep", openSweep, "primary"));
  const history = section("Runs");
  history.append(button("Refresh", render));
  if (!details.runs.length) history.append(node("p", "No runs for this project.", "muted"));
  for (const run of details.runs) {
    const entry = button("", () => selectRun(run.id), "run-row");
    entry.dataset.run = run.id;
    entry.append(node("span", run.id + " · " + run.backend + (run.model ? " · " + run.model : ""), "meta"),
                 node("span", run.status, "state"));
    history.append(entry);
  }
  main.append(node("div", "", "run-detail"));
  $(".run-detail").id = "run-detail";
  const selected = currentRun || details.runs[0]?.id;
  if (selected) selectRun(selected);
}
function selectRun(id) {
  if (currentRun !== id) {
    graphFilter = "";
    selectedFinding = "";
    openEvidence = new Set();
    evidenceCache = new Map();
    openDiff = false;
    fileFocus = "";
  }
  currentRun = id;
  closeStream();
  const selected = project;
  guarded(async () => {
    const data = await query("run", {project: selected, run: id});
    if (project !== selected || currentRun !== id || page !== "agents") return;
    runData = data;
    const status = document.querySelector("[data-run=\"" + CSS.escape(id) + "\"] .state");
    if (status) status.textContent = data.status;
    drawRun();
    if (["failed", "complete"].includes(runData.status)) return;
    stream = new EventSource("/api/events?" + new URLSearchParams({project: selected, run: id}));
    stream.onmessage = (event) => {
      const item = JSON.parse(event.data);
      if (runData.events.some((previous) => previous.id === item.id)) return;
      runData.events.push(item);
      drawRun();
      if (item.kind === "review_finished") {
        guarded(async () => {
          const updated = await query("run", {project: selected, run: id});
          if (project === selected && currentRun === id && page === "agents") {
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
  for (const chunk of (text || "").split(/(?=^diff --git )/m)) {
    const path = chunk.match(/^diff --git a\/.* b\/(.*)$/m)?.[1];
    if (path) files.set(path, chunk);
  }
  return files;
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
  for (const [from, to] of edges) {
    const a = positions.get(from)?.getBoundingClientRect();
    const b = positions.get(to)?.getBoundingClientRect();
    if (!a || !b) continue;
    const x1 = a.left + a.width / 2 - outer.left;
    const y1 = a.bottom - outer.top;
    const x2 = b.left + b.width / 2 - outer.left;
    const y2 = b.top - outer.top - 2;
    const middle = (y1 + y2) / 2;
    context.strokeStyle = active.has(from) && active.has(to) ? "#deded9" : "#646664";
    context.lineWidth = active.has(from) && active.has(to) ? 1.4 : 1;
    context.beginPath();
    context.moveTo(x1, y1);
    context.bezierCurveTo(x1, middle, x2, middle, x2, y2);
    context.lineTo(x2 - 3, y2 - 5);
    context.moveTo(x2, y2);
    context.lineTo(x2 + 3, y2 - 5);
    context.stroke();
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
  lane("Cited evidence", sourceKeys.map((kind) => [
    kind, sourceNames[kind] || kind, findings.filter((item) => item.sources.includes(kind)).length + " findings",
  ]));
  const sweeper = agents.get("sweeper");
  if (sweeper) lane("Survey", [["agent:sweeper", "Sweeper", sweeper.status, sweeper.status === "running"]]);
  lane("Specialists", [...agents].filter(([name]) => !["sweeper", "writer", "cartographer", "check-proposer"].includes(name))
    .map(([name, agent]) => {
      const count = findings.filter((item) => agentName(item.record.agent) === name && item.status !== "no_change").length;
      return ["agent:" + name, name, agent.status === "running" ? "working" : agent.status && agent.status !== "success"
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
      const disclosure = node("details", "", "evidence-detail");
      const citation = source.path ? source.path + (source.line ? ":" + source.line : "")
        : [source.session, source.message].filter(Boolean).join(" · ");
      disclosure.append(node("summary", (sourceNames[source.kind] || "Evidence") + (citation ? " · " + citation : "")));
      const key = focused.id + ":" + i;
      const excerpt = node("pre", evidenceCache.get(key) || source.quote || "");
      disclosure.append(excerpt);
      disclosure.open = openEvidence.has(key);
      disclosure.addEventListener("toggle", () => {
        if (!disclosure.isConnected) return;
        if (!disclosure.open) { openEvidence.delete(key); return; }
        openEvidence.add(key);
        if (evidenceCache.has(key) || disclosure.dataset.loaded) return;
        disclosure.dataset.loaded = "true";
        const runId = runData.id;
        guarded(async () => {
          const result = await query("evidence", {project, run: runId, status, index, evidence:i});
          if (runData.id !== runId) return;
          const content = result.heading + "\n\n" + result.text;
          evidenceCache.set(key, content);
          excerpt.textContent = content;
        });
      });
      body.append(disclosure);
    });
    if (matched(focused)) body.append(button("View written file diff", () => {
      fileFocus = record.target;
      fileSelect.value = fileFocus;
      showPatch();
      diff.open = true;
      openDiff = true;
    }));
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
    const messages = node("details");
    messages.append(node("summary", "Agent messages"));
    const text = node("div", "", "messages");
    selectedAgent.messages.forEach((line) => text.append(node("p", line)));
    messages.append(text);
    body.append(messages);
  }

  const diff = node("details");
  const fileSelect = document.createElement("select");
  fileSelect.setAttribute("aria-label", "File diff");
  const patch = node("pre", runData.patch || "No written patch.");
  function showPatch() { patch.textContent = files.get(fileSelect.value) || runData.patch || "No written patch."; }
  const all = node("option", "All changed files");
  all.value = "";
  fileSelect.append(all);
  for (const name of files.keys()) fileSelect.append(node("option", name));
  fileSelect.value = files.has(fileFocus) ? fileFocus : "";
  showPatch();
  fileSelect.onchange = () => { fileFocus = fileSelect.value; showPatch(); };
  diff.append(node("summary", "Knowledge diff"), fileSelect, patch);
  diff.open = openDiff || graphFilter === "files";
  diff.addEventListener("toggle", () => { if (diff.isConnected) openDiff = diff.open; });
  if (files.size) body.append(diff);
  panel.append(list, body);
  block.append(graph, panel);
  if (runData.check) block.append(button("Open in Checks", () => selectPage("checks")));
  view.append(block);
  graphObserver = new ResizeObserver(() => drawEdges(graph, canvas, positions, edges, active));
  graphObserver.observe(graph);
}

function renderChecks() {
  heading("Review Checks");
  const list = section("Application checks");
  for (const run of details.runs) {
    list.append(button(run.id, () => guarded(async () => {
      const data = await query("run", {project, run: run.id});
      drawCheck(data);
    }), "run-row"));
  }
  if (currentRun) guarded(async () => drawCheck(await query("run", {project, run: currentRun})));
}
function drawCheck(run) {
  $("#check-detail")?.remove();
  const card = section(run.id);
  card.id = "check-detail";
  const check = run.check;
  if (!check) {
    card.append(node("p", "No check proposal for this run."));
    if (run.status === "complete") {
      const propose = button("Propose a check", () => guarded(async () => {
        propose.disabled = true;
        try {
          await api("check-propose", {project, run: run.id});
          drawCheck(await query("run", {project, run: run.id}));
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
    const result = await api("check-verify", {project, run: run.id, digest: check.patch_sha256,
                                             argv: JSON.parse(data.get("argv"))});
    notify("Verification exit code: " + result.exit_code);
    drawCheck(await query("run", {project, run: run.id}));
  }, "Verify in a temporary worktree");
  card.append(form, button("Stage reviewed patch", () => guarded(async () => {
    await api("check-apply", {project, run: run.id, digest: check.patch_sha256});
    notify("Patch staged in application checkout");
    drawCheck(await query("run", {project, run: run.id}));
  })));
}

document.querySelectorAll("nav button").forEach((tab) => tab.onclick = () => selectPage(tab.dataset.page));
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
