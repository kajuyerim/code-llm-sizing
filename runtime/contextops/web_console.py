"""Authenticated loopback console around the local Context Ops runtime."""

from __future__ import annotations

import asyncio
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import asdict
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from contextops import checks, frontmatter, gitutil, profiles, transcripts
from contextops.attach import attach
from contextops.config import load_config
from contextops.onboarding import initialize_knowledge
from contextops.run import create_run, load_run

WEB = Path(__file__).with_name("web")
ASSETS = {"/": ("index.html", "text/html"), "/console.css": ("console.css", "text/css"),
          "/console.js": ("console.js", "text/javascript")}
MAX_BODY = 256 * 1024


def _json(path: Path, fallback=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else fallback


def _text(path: Path) -> str:
    if not path.is_file():
        return ""
    with path.open("rb") as stream:
        return stream.read(1_000_000).decode("utf-8", errors="replace")


class Console:
    def __init__(self, home: Path):
        self.home = home
        self.registry = home / "projects.json"
        self.lock = threading.RLock()
        self.processes = {}
        self.scans = {}

    def projects(self) -> dict:
        return _json(self.registry, {})

    def connect(self, data: dict) -> dict:
        app = gitutil.repo_root(Path(data["app"]).expanduser()).resolve()
        kb = gitutil.repo_root(Path(data["kb"]).expanduser()).resolve()
        if app == kb or app.is_relative_to(kb) or kb.is_relative_to(app):
            raise ValueError("Choose two separate Git checkouts")
        config = load_config(kb)
        name = data.get("name", app.name).strip() or app.name
        slug = data.get("app_name") or gitutil.config_get(app, "contextops.app") or app.name.lower()
        strategy = data.get("strategy") or "fresh-specialists"
        if strategy not in ("fresh-specialists", "sweeper-first"):
            raise ValueError("Choose a supported sweep strategy")
        if config.scope == "repository" and config.application and slug != config.application:
            raise ValueError("This knowledge checkout is configured for another application")
        if data.get("automatic") and config.output.open_pr:
            raise ValueError("Disable remote knowledge publication before attaching the local console hook")
        attach(app, kb, strategy, name=slug, hook=bool(data.get("automatic")), refresh=False)
        with self.lock:
            projects = self.projects()
            reconnect = data.get("reconnect")
            key = reconnect if reconnect in projects else next(
                (key for key, row in projects.items() if row["app"] == str(app)), secrets.token_hex(8))
            projects[key] = {"name": name[:120], "app": str(app), "strategy": strategy}
            self.home.mkdir(parents=True, mode=0o700, exist_ok=True)
            stage = self.registry.with_suffix(".tmp")
            stage.write_text(json.dumps(projects, indent=2) + "\n", encoding="utf-8")
            stage.replace(self.registry)
        return {"id": key}

    def roots(self, key: str):
        row = self.projects().get(key)
        if row is None:
            raise ValueError("Choose a saved project")
        app = Path(row["app"])
        if not app.is_dir():
            raise ValueError("Application checkout moved. Reconnect the project.")
        selected = gitutil.config_get(app, "contextops.kb")
        if not selected or not Path(selected).is_dir():
            raise ValueError("Knowledge checkout moved. Reconnect the project.")
        return row, app, Path(selected).resolve()

    @staticmethod
    def branches(app: Path) -> tuple[list[dict], str]:
        current = gitutil.git(app, "symbolic-ref", "--quiet", "HEAD", check=False)
        rows = gitutil.git(app, "for-each-ref", "--format=%(refname)%09%(refname:short)%09%(symref)",
                           "refs/heads", "refs/remotes").splitlines()
        branches = []
        for row in rows:
            ref, label, *target = row.split("\t")
            if not any(target):
                branches.append({"ref": ref, "label": label})
        if not current:
            current = "HEAD"
            branches.insert(0, {"ref": "HEAD", "label": "HEAD (detached)"})
        return branches, current

    @staticmethod
    def commit_range(app: Path, branch: str) -> list[str]:
        branches, _ = Console.branches(app)
        if not any(item["ref"] == branch for item in branches):
            raise ValueError("Choose a local or remote-tracking branch from this checkout")
        tip = gitutil.rev_parse(app, branch)
        return gitutil.git(app, "log", "--first-parent", "-30", "--format=%H%x09%s", tip, "--").splitlines()

    def project_commits(self, key: str, branch: str) -> dict:
        _, app, _ = self.roots(key)
        return {"commits": self.commit_range(app, branch)}

    def load_project(self, key: str) -> dict:
        row, app, kb = self.roots(key)
        config = load_config(kb)
        slug = gitutil.config_get(app, "contextops.app") or app.name.lower()
        settings, _ = frontmatter.read(kb / "init.md")
        branches, current_branch = self.branches(app)
        return {
            **row, "kb": str(kb), "app_name": slug, "backend": config.backend,
            "defaults": {"claude": settings.get("model", "sonnet"),
                         "codex": settings.get("codex_model", "gpt-6.1-terra")},
            "codex_available": bool(shutil.which("codex")), "auth": config.auth, "scope": config.scope,
            "categories": config.profiles.get(slug, config.profiles.get("*", {})).get("categories", []),
            "branches": branches, "branch": current_branch, "commits": self.commit_range(app, current_branch),
            "sessions": [asdict(item) for item in transcripts.list_sessions(app)[:40]],
            "dirty": bool(gitutil.status(kb)), "diff": gitutil.git(kb, "diff", "HEAD")[:200_000],
            "runs": list(self.runs(key).values()),
        }

    def runs(self, key: str) -> dict:
        _, app, kb = self.roots(key)
        parent = load_config(kb).output.runs_dir
        paths = list(parent.glob("*/*/run.json")) + list(parent.glob("codex/*/*/run.json"))
        runs = {}
        for path in sorted(paths, key=lambda file: file.parent.name, reverse=True):
            try:
                ctx = load_run(path.parent)
            except (OSError, ValueError, TypeError):
                continue
            if (ctx.app_root, ctx.kb_root) != (app, kb) or ctx.run_dir.resolve() != path.parent.resolve():
                continue
            events = self.read_events(ctx.run_dir)
            terminal = next((event["status"] for event in reversed(events)
                             if event["kind"] == "run_finished"), None)
            process = self.processes.get(ctx.run_id)
            status = terminal or ("complete" if (ctx.run_dir / "completion.txt").exists() else
                                  "failed" if process and process.poll() is not None else
                                  "running" if (ctx.run_dir / "started").exists() else "queued")
            runs[ctx.run_id] = {"id": ctx.run_id, "dir": str(ctx.run_dir), "status": status,
                                "strategy": ctx.strategy, "backend": ctx.backend, "model": ctx.model or ctx.model_default,
                                "base": ctx.base_sha, "head": ctx.head_sha, "trigger": ctx.ref}
        return runs

    @staticmethod
    def read_events(run_dir: Path) -> list[dict]:
        path = run_dir / "events.jsonl"
        if not path.is_file():
            return []
        # Ignore a final incomplete write while another process appends an event.
        return [json.loads(line) for line in path.read_bytes().splitlines(keepends=True)
                if line.endswith(b"\n")]

    def run_path(self, key: str, run_id: str) -> tuple[Path, dict]:
        row = self.runs(key).get(run_id)
        if row is None:
            raise ValueError("Run does not belong to this project")
        return Path(row["dir"]), row

    def run_detail(self, key: str, run_id: str) -> dict:
        path, row = self.run_path(key, run_id)
        return {**row, "events": self.read_events(path), "review": _json(path / "review.json", {}),
                "patch": _text(path / "knowledge.patch"), "report": _text(path / "report.md"),
                "check": _json(path / checks.OUTPUT / "proposal.json"),
                "check_patch": _text(path / checks.OUTPUT / "check.patch"),
                "verification": _json(path / checks.OUTPUT / "verification.json"),
                "applied": _json(path / checks.OUTPUT / "applied.json")}

    def launch(self, ctx):
        with (ctx.run_dir / "run.log").open("ab") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "contextops", "run", str(ctx.run_dir)],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
        self.processes[ctx.run_id] = process

    def action(self, action: str, data: dict):
        if action == "connect":
            return self.connect(data)
        if action == "pick":
            if sys.platform != "darwin":
                raise ValueError("Enter the local checkout path in the field")
            p = subprocess.run(["osascript", "-e", "POSIX path of (choose folder)"],
                               capture_output=True, text=True, timeout=120)
            return {"path": p.stdout.strip() if p.returncode == 0 else ""}
        key = data["project"]
        row, app, kb = self.roots(key)
        slug = gitutil.config_get(app, "contextops.app") or app.name.lower()
        if action == "init":
            changed = initialize_knowledge(kb, data["branch"], data["scope"],
                                           slug if data["scope"] == "repository" else None)
            return {"changed": changed}
        if action == "commit":
            if not gitutil.status(kb):
                raise ValueError("There are no setup changes to commit")
            expected = data["preview"]
            if gitutil.git(kb, "diff", "HEAD")[:200_000] != expected:
                raise ValueError("The setup diff changed. Refresh and review it again.")
            if any(code == "??" or not (name in ("init.md", "index.md", "log.md")
                                        or name.startswith(("core/", "tools/")))
                   for code, name in gitutil.status(kb)):
                raise ValueError("The checkout contains changes outside the setup files")
            gitutil.git(kb, "-c", "core.hooksPath=/dev/null", "commit", "-am", "Configure Context Ops knowledge")
            return {"revision": gitutil.rev_parse(kb, "HEAD")}
        if action == "profile":
            if (kb / "init.md").is_symlink():
                raise ValueError("The configuration must be a regular file")
            profiles.save(kb, "*" if data.get("team") else slug, data["categories"])
            return {"saved": True}
        backend = data.get("backend") or load_config(kb).backend
        model = data.get("model") or None
        load_config(kb, backend)
        if model and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,119}", model):
            raise ValueError("Enter a valid provider model identifier")
        if action == "scan":
            with self.lock:
                if self.scans.get(key, {}).get("status") == "running":
                    raise ValueError("A category scan is already running")
                self.scans[key] = {"status": "running"}
            threading.Thread(target=self._scan, args=(key, app, kb, backend, model, data.get("sessions", [])),
                             daemon=True).start()
            return {"status": "running"}
        if action == "run":
            with self.lock:
                if any(run["status"] in ("queued", "running") for run in self.runs(key).values()):
                    raise ValueError("This project already has an active run")
                branch = data.get("branch")
                if branch is not None:
                    commits = [row.split("\t", 1)[0] for row in self.commit_range(app, branch)]
                    head, base = data["head"], data["base"]
                    if head not in commits or base not in commits or commits.index(base) <= commits.index(head):
                        raise ValueError("Choose an earlier base and a later head from the selected branch")
                ctx = create_run(app, kb, "origin", "manual", data["head"], data["base"],
                                 backend=backend, strategy=data["strategy"], sessions=data["sessions"],
                                 model=model, local_only=True)
                if ctx is None:
                    raise ValueError("Choose different base and head commits")
                self.launch(ctx)
                return {"run": ctx.run_id}
        if action == "check-propose":
            path, _ = self.run_path(key, data["run"])
            result = asyncio.run(checks.propose_manually(path))
            return {"status": _json(result)["status"]}
        if action == "check-apply":
            path, _ = self.run_path(key, data["run"])
            checks.apply(path, data["digest"])
            return {"staged": True}
        if action == "check-verify":
            path, _ = self.run_path(key, data["run"])
            # Explicit argv from the reviewing user, never the model's suggested command.
            argv = data["argv"]
            if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
                raise ValueError("Enter a command as a program and argument list")
            return {"exit_code": checks.verify(path, data["digest"], argv)}
        raise ValueError("Unknown console action")

    def _scan(self, key, app, kb, backend, model, sessions):
        try:
            result = asyncio.run(profiles.discover(app, kb, backend, model, sessions))
            self.scans[key] = {"status": "complete", **result}
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            self.scans[key] = {"status": "failed", "error": "Category scan failed. Check the configured provider, model and role."}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def respond(self, status, data, content_type="application/json"):
        if isinstance(data, dict):
            data = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(data)

    def authenticated(self) -> bool:
        cookies = SimpleCookie(self.headers.get("Cookie", ""))
        cookie = cookies.get("contextops_ui")
        return self.headers.get("Host") == self.server.host and bool(
            cookie and hmac.compare_digest(cookie.value, self.server.token))

    def do_GET(self):
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        params = {key: values[0] for key, values in query.items()}
        if (url.path == "/open" and self.headers.get("Host") == self.server.host
                and hmac.compare_digest(params.get("token", ""), self.server.token)):
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Set-Cookie", f"contextops_ui={self.server.token}; HttpOnly; SameSite=Strict; Path=/")
            self.send_header("Location", "/")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            return
        if not self.authenticated():
            self.respond(403, {"error": "Open the console from the local launcher."})
            return
        console = self.server.console
        try:
            if url.path in ASSETS:
                name, kind = ASSETS[url.path]
                self.respond(200, (WEB / name).read_bytes(), kind)
            elif url.path == "/api/projects":
                self.respond(200, {"projects": console.projects()})
            elif url.path == "/api/project":
                self.respond(200, console.load_project(params["project"]))
            elif url.path == "/api/commits":
                self.respond(200, console.project_commits(params["project"], params["branch"]))
            elif url.path == "/api/run":
                self.respond(200, console.run_detail(params["project"], params["run"]))
            elif url.path == "/api/scan":
                self.respond(200, console.scans.get(params["project"], {"status": "idle"}))
            elif url.path == "/api/events":
                path, _ = console.run_path(params["project"], params["run"])
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                index = int(self.headers.get("Last-Event-ID", "0"))
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    events = console.read_events(path)
                    for event in events[index:]:
                        index += 1
                        self.wfile.write(f"id: {index}\ndata: {json.dumps(event)}\n\n".encode())
                    self.wfile.flush()
                    if events and events[-1]["kind"] == "run_finished":
                        break
                    time.sleep(.25)
            else:
                self.respond(404, {"error": "Page not found"})
        except (BrokenPipeError, ConnectionResetError):
            return
        except (ValueError, KeyError, OSError, subprocess.SubprocessError):
            if url.path != "/api/events":
                self.respond(400, {"error": "Unable to read the project. Check or reconnect its local paths."})

    def do_POST(self):
        if not self.authenticated() or self.headers.get("Origin") != f"http://{self.server.host}":
            self.respond(403, {"error": "Request must come from the local console."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY or self.headers.get_content_type() != "application/json":
                raise ValueError("Provide a small JSON request")
            data = json.loads(self.rfile.read(length))
            self.respond(200, self.server.console.action(self.path.removeprefix("/api/"), data))
        except ValueError as exc:
            self.respond(400, {"error": str(exc)})
        except (KeyError, TypeError, OSError, subprocess.SubprocessError):
            self.respond(400, {"error": "The local operation failed. Check the paths, Git state or runtime setup."})


def serve():
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        server.host = f"127.0.0.1:{server.server_port}"
        server.token = secrets.token_urlsafe(32)
        server.console = Console(Path.home() / ".contextops")
        url = f"http://{server.host}/open?token={server.token}"
        if not webbrowser.open(url):
            print(f"Open this local session in your browser: {url}", flush=True)
        else:
            print(f"Context Ops console listening on http://{server.host}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
