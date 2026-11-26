"use strict";
const $ = (selector) => document.querySelector(selector);
const main = $("#main");
const pages = ["setup", "agents", "checks"];
let page = "setup", project = "", projects = {}, details = null;
let currentRun = "", activeAgent = "", stream = null, runData = null, draftCategories = [];
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
function heading(title, subtitle) {
  main.append(node("h1", title), node("p", subtitle, "muted"));
}
function closeStream() {
  if (stream) stream.close();
  stream = null;
}
async function getProject() {
  return query("project", {project});
}
function chooseProject(key) {
  project = key;
  localStorage.setItem("contextops-project", key);
  currentRun = "";
  activeAgent = "";
  closeStream();
  render();
}
function renderProjects() {
  const list = $("#projects");
  list.replaceChildren();
  for (const [key, row] of Object.entries(projects)) {
    list.append(button(row.name, () => chooseProject(key), key === project ? "active" : ""));
  }
}
function selectPage(next) {
  if (next === page) return;
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
  heading("Connect a project", "Choose the application checkout and the knowledge repository.");
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
  heading(details.name, "Connect and configure a local knowledge project.");
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
function renderAgents() {
  heading(details.name, "Review the evidence, agent activity and written knowledge.");
  const setup = section("Start a sweep");
  const form = node("form");
  const grid = node("div", "", "form-grid");
  const commits = details.commits.map((line) => {
    const [sha, subject] = line.split("\t");
    return [sha, sha.slice(0, 7) + " " + (subject || "")];
  });
  selector(grid, "Base commit", "base", commits, commits[1]?.[0]);
  selector(grid, "Head commit", "head", commits, commits[0]?.[0]);
  selector(grid, "Strategy", "strategy", strategyChoices, details.strategy);
  providerFields(grid);
  const sessions = selector(grid, "Claude Code sessions", "sessions", details.sessions.map((entry) =>
    [entry.session_id, entry.session_id.slice(0, 8) + " " + (entry.opening || "")]));
  sessions.multiple = true;
  sessions.required = true;
  if (sessions.options.length === 1) sessions.options[0].selected = true;
  form.append(grid);
  setup.append(form);
  submit(form, async (data) => {
    const result = await api("run", {project, ...Object.fromEntries(data), sessions: data.getAll("sessions")});
    currentRun = result.run;
    activeAgent = "";
    await render();
  }, "Run sweep");
  if (details.dirty) setup.append(node("small", "Review and commit the knowledge setup before starting."));
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
  if (currentRun) selectRun(currentRun);
}
function selectRun(id) {
  if (currentRun !== id) activeAgent = "";
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
      if (!runData.events.some((previous) => previous.id === item.id)) runData.events.push(item);
      drawRun();
      if (item.kind === "run_finished") {
        closeStream();
        selectRun(id);
      }
    };
  });
}
function drawRun() {
  const view = $("#run-detail");
  if (!view || !runData) return;
  const previous = view.querySelector(".messages");
  const oldTop = previous?.scrollTop || 0;
  const follow = !previous || previous.scrollHeight - previous.scrollTop - previous.clientHeight < 28;
  const oldOpen = [...view.querySelectorAll("details[open]")].map((item) => item.dataset.key);
  view.replaceChildren();
  const block = node("section", "", "card");
  block.append(node("h2", "Run " + runData.id));
  const agents = new Map();
  for (const item of runData.events) {
    if (!item.agent) continue;
    if (!agents.has(item.agent)) agents.set(item.agent, {status: "", messages: []});
    const agent = agents.get(item.agent);
    if (item.kind === "agent_started") agent.status = "running";
    if (item.kind === "agent_message") agent.messages.push(item.text);
    if (item.kind === "agent_finished") agent.status = item.status;
  }
  if (!activeAgent && agents.size) activeAgent = agents.keys().next().value;
  const tabs = node("div", "", "tabs");
  const done = node("div", "", "done");
  done.append(node("h3", "Done"));
  const content = node("div");
  const messages = node("div", "", "messages");
  const explanation = node("p", "", "muted");
  for (const [name, agent] of agents) {
    const status = agent.status === "running" ? " ◌" : agent.status === "success" ? " ✓" : " −";
    const tab = button(name + status, () => { activeAgent = name; drawRun(); },
                       agent.status === "running" ? "tab-running" : "");
    tab.setAttribute("aria-selected", String(activeAgent === name));
    tabs.append(tab);
    if (agent.status && agent.status !== "running") done.append(button(name + " · " + agent.status, () => {
      activeAgent = name; drawRun();
    }));
  }
  for (const text of agents.get(activeAgent)?.messages || []) messages.append(node("p", text));
  if (!messages.childNodes.length) messages.append(node("p", "No messages from this agent yet.", "muted"));
  for (const state of ["accepted", "rejected", "deferred"]) {
    for (const record of runData.review[state] || []) {
      done.append(button(state + " · " + (record.fact_id || record.target), () => {
        explanation.replaceChildren(node("strong", record.text), node("p", record.rejected_because || record.policy_reason || record.reason || ""));
        for (const source of record.evidence || []) {
          const ref = node("details");
          ref.append(node("summary", source.path || [source.session, source.message].filter(Boolean).join(" · ")),
                     node("pre", source.quote || JSON.stringify(source, null, 2)));
          explanation.append(ref);
        }
        if (runData.patch) explanation.append(button("View file diff", () => {
          diff.open = true;
          chooseFile(record.target);
        }));
      }));
    }
  }
  const diff = node("details");
  diff.dataset.key = "diff";
  diff.open = oldOpen.includes("diff");
  const fileSelect = document.createElement("select");
  fileSelect.setAttribute("aria-label", "File diff");
  const chunks = new Map();
  for (const chunk of (runData.patch || "").split(/(?=^diff --git )/m)) {
    const name = chunk.match(/^diff --git a\/.* b\/(.*)$/m)?.[1];
    if (name) chunks.set(name, chunk);
  }
  const patch = node("pre", runData.patch || "No written patch.");
  function chooseFile(name) {
    fileSelect.value = chunks.has(name) ? name : "";
    patch.textContent = chunks.get(name) || runData.patch || "No written patch.";
  }
  const all = node("option", "All changed files");
  all.value = "";
  fileSelect.append(all);
  for (const name of chunks.keys()) fileSelect.append(node("option", name));
  fileSelect.onchange = () => chooseFile(fileSelect.value);
  diff.append(node("summary", "Knowledge diff"), fileSelect, patch);
  content.append(tabs, messages, explanation, diff);
  const split = node("div", "", "split");
  split.append(done, content);
  block.append(split);
  if (runData.check) block.append(button("Open in Checks", () => selectPage("checks")));
  view.append(block);
  messages.scrollTop = follow ? messages.scrollHeight : oldTop;
}
function renderChecks() {
  heading("Checks", "Review proposed lint rules and behavior tests.");
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
$("#add-project").onclick = () => { project = ""; selectPage("setup"); render(); };
guarded(async () => {
  projects = (await api("projects")).projects;
  const saved = localStorage.getItem("contextops-project");
  project = saved in projects ? saved : (Object.keys(projects)[0] || "");
  await render();
});
