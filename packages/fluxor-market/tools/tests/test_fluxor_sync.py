"""tools/fluxor_sync.py: a project's harness pulled from Fluxor online (card://JAVA-162, ADR 0019).

Runs the writer against a local `http.server` fake of the snapshot contract JAVA-555 serves
(`doc://contracts/catalog-format`, `format: 1`), in a throwaway project folder.
Run: python3 -m unittest discover -s tools/tests
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import fluxor_sync  # noqa: E402

PROJECT = "3f2c1a9e-7b1d-4c55-9a0e-2d6f8b4c1e70"
# What the server wires at session start (HarnessSnapshotService, card://JAVA-834).
CLAUDE_PULL = f'{fluxor_sync.PYTHON} "$CLAUDE_PROJECT_DIR/.harness/bin/fluxor-sync.py" pull'
CODEX_PULL = {"command": "python3 .harness/bin/fluxor-sync.py pull --print-directives",
              "commandWindows": "python .harness/bin/fluxor-sync.py pull --print-directives"}
CODE = "enroll-code-123"
TOKEN = "jdbx_device_test"


def session_start(**handler) -> str:
    return json.dumps({"hooks": {"SessionStart": [{"hooks": [{"type": "command", **handler}]}]}}) + "\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Fluxor:
    """What the server holds: the project's files at its revision, and the blob store."""

    def __init__(self, token: str = TOKEN):
        self.token = token
        self.revision = 1
        self.items: dict[str, dict] = {}
        self.blobs: dict[str, bytes] = {}
        self.format = 1
        self.requests: list[str] = []
        # card://JAVA-625: every Authorization header received, so a test can prove none was sent.
        self.authorizations: list[str] = []
        # card://JAVA-625: when set, every authorized request is answered with a redirect there.
        self.redirect_to: str | None = None
        self.enrolled = 0
        self.codes = {CODE}
        self.broken_blobs = False
        # card://JAVA-286: packs published per account, attached to this project.
        self.packs: dict[str, dict[str, str]] = {}
        self.attached: set[str] = set()
        self.uploads: list[list[str]] = []

    def generated(self, path, content, item=None, mode="file"):
        data = content.encode("utf-8")
        self.items[path] = {"path": path, "sha256": sha(data), "size": len(data), "executable": False,
                            "item": item, "mode": mode, "content": content}

    def blob(self, path, data: bytes, item, executable=False):
        self.blobs[sha(data)] = data
        self.items[path] = {"path": path, "sha256": sha(data), "size": len(data), "executable": executable,
                            "item": item, "mode": "file"}

    def drop(self, path):
        del self.items[path]

    def hook(self, key, event, sh=None, ps1=None, **fields):
        """A catalog hook as the server renders it (card://JAVA-556): its fallback directive, its
        scripts, and its manifest, whose sha256 is what the user consents to."""
        self.generated(f".harness/rules/{key}.md", f"Fallback of {key}.\n", key)
        scripts = {}
        for kind, text in (("sh", sh), ("ps1", ps1)):
            if text is not None:
                path = f".harness/hooks/{key}.{kind}"
                self.generated(path, text, key)
                self.items[path]["executable"] = kind == "sh"
                scripts[kind] = {"path": path, "sha256": sha(text.encode("utf-8"))}
        manifest = {"key": key, "title": key.title(), "description": f"What {key} does", "event": event,
                    "fallback": f".harness/rules/{key}.md", "scripts": scripts, **fields}
        self.generated(f".harness/hooks/{key}.json", json.dumps(manifest, sort_keys=True) + "\n", key, mode="hook")

    def wiring(self, always=("english",), skills=("research",)):
        block = ("<!-- fluxor:begin -->\n## Rules\n\n"
                 + "".join(f"@.harness/rules/{k}.md\n" for k in always)
                 + ("\n## Skills\n\n" + "".join(f"- `.harness/skills/{k}/`\n" for k in skills) if skills else "")
                 + "<!-- fluxor:end -->\n")
        self.generated("AGENTS.md", block, mode="block")
        self.generated("CLAUDE.md", "@AGENTS.md\n")
        self.generated(".claude/settings.json", session_start(command=CLAUDE_PULL), mode="json-merge")
        self.generated(".codex/hooks.json", session_start(**CODEX_PULL), mode="json-merge")

    def publish(self, pack_id, files) -> tuple[int, dict]:
        """The server's checks that matter to the writer: nothing private, every hash proven."""
        by_path = {f["path"]: f["content"] for f in files}
        if any(p.startswith("private/") for p in by_path):
            return 422, {"error": "pack_private_path", "message": "private/ is never published"}
        manifest = json.loads(by_path["pack.json"])
        for entry in manifest["files"]:
            if sha(by_path.get(entry["path"], "").encode("utf-8")) != entry["sha256"]:
                return 422, {"error": "pack_hash_mismatch", "message": f"{entry['path']} does not match"}
        self.uploads.append(sorted(by_path))
        self.packs[pack_id] = by_path
        self.attached.add(pack_id)
        return 200, {"packId": pack_id, "files": len(by_path)}

    def pack_items(self) -> list[dict]:
        """Each attached pack as HarnessSnapshotService.packFiles renders it."""
        items = []
        for pack_id in sorted(self.attached):
            files, folder = self.packs[pack_id], f".harness/packs/{pack_id}/"
            for rel, text in files.items():
                data = text.encode("utf-8")
                items.append({"path": folder + rel, "sha256": sha(data), "size": len(data), "executable": False,
                              "item": pack_id, "mode": "file", "content": text})
            wanted = files.get("adapters/claude-code/settings.hooks.json", "")
            for key, event, script, mode, tools in (("ceet-check", "preTool", "bin/ceet_check.py", "claude-code",
                                                     "shell"),
                                                    ("examples", "promptSubmit", "bin/examples.py", "inject", None)):
                if script not in files or f"{script} {mode}" not in wanted:
                    continue
                manifest = {"key": key, "pack": pack_id, "title": key, "description": f"The pack's {key}",
                            "event": event, "run": {"script": script, "args": [mode]},
                            "runs": [{"path": script, "sha256": sha(files[script].encode("utf-8"))}]}
                if tools:
                    manifest["tools"] = tools
                text = json.dumps(manifest, sort_keys=True) + "\n"
                items.append({"path": f"{folder}.fluxor/hooks/{key}.json", "sha256": sha(text.encode("utf-8")),
                              "size": len(text), "executable": False, "item": pack_id, "mode": "hook",
                              "content": text})
        return items

    def snapshot(self, packs=False) -> dict:
        files = sorted(list(self.items.values()) + (self.pack_items() if packs else []), key=lambda f: f["path"])
        files = [{k: v for k, v in f.items() if v is not None} for f in files]
        lines = "".join(f"{f['path']}\t{f['sha256']}\t{'true' if f['executable'] else 'false'}\n" for f in files)
        return {"format": self.format, "projectId": PROJECT, "revision": self.revision,
                "hash": sha(lines.encode("utf-8")), "files": files}


def serve(state: Fluxor):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, body=b"", headers=None):
            self.send_response(status)
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            if self.headers.get("Authorization"):
                state.authorizations.append(self.headers["Authorization"])
            if self.headers.get("Authorization") != f"Bearer {state.token}":
                self.reply(401, b'{"error":"unauthorized","message":"Invalid device token"}')
                return False
            if state.redirect_to:
                self.reply(302, headers={"Location": state.redirect_to + self.path})
                return False
            return True

        def do_POST(self):
            state.requests.append(f"POST {self.path}")
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path != "/fluxor/v1/sync/enrollments" or body.get("code") not in state.codes:
                return self.reply(401, b'{"error":"enrollment_invalid","message":"not valid"}')
            state.codes.discard(body["code"])
            state.enrolled += 1
            self.reply(201, json.dumps({"deviceToken": state.token, "deviceId": f"d{state.enrolled}",
                                        "name": f"fluxor-sync on {body['hostname']} ({state.enrolled})"}).encode())

        def do_PUT(self):
            state.requests.append(f"PUT {self.path}")
            if not self.authorized():
                return
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            prefix = f"/fluxor/v1/sync/harness/projects/{PROJECT}/packs/"
            if not self.path.startswith(prefix):
                return self.reply(404, b'{"error":"harness_project_not_found","message":"nope"}')
            status, answer = state.publish(self.path[len(prefix):], body["files"])
            self.reply(status, json.dumps(answer).encode())

        def do_DELETE(self):
            state.requests.append(f"DELETE {self.path}")
            if not self.authorized():
                return
            pack_id = self.path.rsplit("/", 1)[1]
            if self.path == f"/fluxor/v1/sync/harness/projects/{PROJECT}/packs/{pack_id}" \
                    and pack_id in state.attached:
                state.attached.discard(pack_id)
                return self.reply(204)
            if self.path == f"/fluxor/v1/sync/harness/packs/{pack_id}" and pack_id in state.packs:
                del state.packs[pack_id]
                state.attached.discard(pack_id)
                return self.reply(204)
            self.reply(404, b'{"error":"pack_not_found","message":"no such pack"}')

        def do_GET(self):
            state.requests.append(f"GET {self.path}")
            if not self.authorized():
                return
            prefix = "/fluxor/v1/sync/harness/"
            path, _, query = self.path.partition("?")
            if path == f"{prefix}projects/{PROJECT}/snapshot":
                snap = state.snapshot(packs=query == "include=packs")
                tag = f'"{snap["hash"]}"'
                if self.headers.get("If-None-Match") == tag:
                    return self.reply(304, headers={"ETag": tag})
                return self.reply(200, json.dumps(snap).encode(), {"ETag": tag})
            if self.path.startswith(prefix + "blobs/") and self.path.rsplit("/", 1)[1] in state.blobs:
                # The real route produces application/octet-stream and answers 406 to a JSON-only Accept.
                if self.headers.get("Accept") == "application/json":
                    return self.reply(406, b'{"message":"The accept header value did not match"}')
                if state.broken_blobs:
                    return self.reply(500, b'{"message":"down"}')
                return self.reply(200, state.blobs[self.path.rsplit("/", 1)[1]])
            self.reply(404, b'{"error":"not_found","message":"nope"}')

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class Sync(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "project"
        self.root.mkdir()
        self.fluxor = Fluxor()
        self.fluxor.generated(".harness/rules/english.md", "Write everything in American English.\n",
                              "english")
        self.fluxor.generated(".harness/rules/review.md", "Review before merging.\n", "review")
        self.fluxor.blob(".harness/skills/research/SKILL.md", b"---\nname: research\n---\nSearch first.\n",
                         "research")
        self.fluxor.blob(".harness/skills/research/scripts/run.sh", b"#!/bin/sh\necho run\n", "research", True)
        self.fluxor.wiring()
        self.server = serve(self.fluxor)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        env = {"FLUXOR_CONFIG_DIR": str(self.tmp / "config"), "FLUXOR_CACHE_DIR": str(self.tmp / "cache")}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        os.environ.pop("FLUXOR_SERVER", None)
        self.addCleanup(patcher.stop)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_sync(self, *args) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = fluxor_sync.main(["--root", str(self.root), *args])
        return code, out.getvalue()

    def init(self):
        code, out = self.run_sync("init", "--enroll", CODE, "--project", PROJECT, "--server", self.url)
        self.assertEqual(code, 0, out)
        return out

    def blob_downloads(self):
        return [r for r in self.fluxor.requests if "/blobs/" in r]

    def read(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")

    # ── first pull ───────────────────────────────────────────────────────────────────────────────

    def test_init_enrolls_and_materializes_the_harness(self):
        out = self.init()
        self.assertIn("revision 1", out)
        self.assertEqual(self.read(".harness/rules/english.md"), "Write everything in American English.\n")
        self.assertEqual(self.read(".harness/skills/research/SKILL.md"), "---\nname: research\n---\nSearch first.\n")
        self.assertEqual(self.read("CLAUDE.md"), "@AGENTS.md\n")
        self.assertIn("@.harness/rules/english.md", self.read("AGENTS.md"))
        token = self.tmp / "config" / "device-tokens.json"
        self.assertEqual(json.loads(token.read_text())[self.url]["token"], TOKEN)
        self.assertFalse((self.tmp / "config" / "device-token").exists())
        config = json.loads(self.read(".harness/fluxor.json"))
        self.assertEqual(config, {"projectId": PROJECT, "server": self.url})
        self.assertNotIn(TOKEN, json.dumps(config))
        lock = json.loads(self.read(".harness/harness.lock.json"))
        self.assertEqual(lock["source"], {"kind": "fluxor", "projectId": PROJECT, "revision": 1,
                                          "hash": self.fluxor.snapshot()["hash"]})
        self.assertEqual(lock["schemaVersion"], 1)
        self.assertEqual(lock["files"][".harness/rules/english.md"]["atom"], "english")
        self.assertTrue((self.root / fluxor_sync.WRITER).is_file())
        self.assertEqual(len(self.blob_downloads()), 2)
        if os.name != "nt":
            self.assertEqual(token.stat().st_mode & 0o777, 0o600)
            self.assertEqual(token.parent.stat().st_mode & 0o777, 0o700)
            self.assertTrue(os.access(self.root / ".harness/skills/research/scripts/run.sh", os.X_OK))
            self.assertTrue(os.access(self.root / fluxor_sync.WRITER, os.X_OK))

    def test_a_spent_or_wrong_code_enrolls_nothing(self):
        self.init()
        code, out = self.run_sync("init", "--enroll", CODE, "--project", PROJECT, "--server", self.url)
        self.assertEqual(code, 1)
        self.assertIn("enrollment", out)

    def test_a_code_starting_with_a_dash_enrolls_in_the_bootstrap_form(self):
        # card://JAVA-162: base64url codes start with `-` one time in 64. `harness.bootstrap` emits
        # `--enroll=<code>`, which argparse does not mistake for an option.
        dash = "-Ab3_x9QkZ"
        self.fluxor.codes.add(dash)
        code, out = self.run_sync("init", f"--enroll={dash}", f"--project={PROJECT}", f"--server={self.url}")
        self.assertEqual(code, 0, out)
        self.assertEqual(fluxor_sync.token_for(self.url), TOKEN)
        self.assertNotIn(dash, self.fluxor.codes)

    def test_init_refuses_a_harness_installed_from_a_local_catalog(self):
        (self.root / ".harness").mkdir()
        (self.root / ".harness/harness.json").write_text("{}")
        code, out = self.run_sync("init", "--enroll", CODE, "--project", PROJECT, "--server", self.url)
        self.assertEqual(code, 1)
        self.assertIn("marketplace.py install", out)
        self.assertNotIn(f"POST /fluxor/v1/sync/enrollments", self.fluxor.requests)

    # ── idempotence ──────────────────────────────────────────────────────────────────────────────

    def test_a_second_pull_with_nothing_changed_writes_and_downloads_nothing(self):
        self.init()
        files = [p for p in self.root.rglob("*") if p.is_file()]
        before = {p: p.stat().st_mtime_ns for p in files}
        downloads = len(self.blob_downloads())
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertIn("up to date", out)
        self.assertEqual({p: p.stat().st_mtime_ns for p in files}, before)
        self.assertEqual(len(self.blob_downloads()), downloads)

    def test_the_cache_spares_a_download_the_disk_does_not_have(self):
        self.init()
        downloads = len(self.blob_downloads())
        shutil.rmtree(self.root / ".harness/skills")
        code, out = self.run_sync("pull", "--force")
        self.assertEqual(code, 0, out)
        self.assertTrue((self.root / ".harness/skills/research/SKILL.md").is_file())
        self.assertEqual(len(self.blob_downloads()), downloads)

    # ── update, conflict, removal ────────────────────────────────────────────────────────────────

    def test_a_change_on_the_web_reaches_the_next_pull(self):
        self.init()
        self.fluxor.generated(".harness/rules/english.md", "Write everything in British English.\n", "english")
        self.fluxor.revision = 2
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertIn("revision 2: 1 file(s) written", out)
        self.assertEqual(self.read(".harness/rules/english.md"), "Write everything in British English.\n")

    def test_a_locally_edited_file_is_kept_and_reported_until_force(self):
        self.init()
        (self.root / ".harness/rules/english.md").write_text("Mine.\n")
        self.fluxor.generated(".harness/rules/english.md", "Write it in plain English.\n", "english")
        self.fluxor.revision = 2
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertIn("kept local edit: .harness/rules/english.md", out)
        self.assertIn("fluxor-sync pull --force takes Fluxor's", out)
        self.assertEqual(self.read(".harness/rules/english.md"), "Mine.\n")
        code, out = self.run_sync("pull")
        self.assertIn("kept local edit: .harness/rules/english.md", out)
        code, out = self.run_sync("pull", "--force")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(".harness/rules/english.md"), "Write it in plain English.\n")
        code, out = self.run_sync("pull")
        self.assertNotIn("kept local edit", out)

    def test_a_dropped_item_is_removed_and_an_edited_one_kept(self):
        self.init()
        (self.root / ".harness/rules/review.md").write_text("My own review rule.\n")
        self.fluxor.drop(".harness/rules/review.md")
        self.fluxor.drop(".harness/skills/research/SKILL.md")
        self.fluxor.drop(".harness/skills/research/scripts/run.sh")
        self.fluxor.wiring(skills=())
        self.fluxor.revision = 2
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.root / ".harness/skills/research").exists())
        self.assertEqual(self.read(".harness/rules/review.md"), "My own review rule.\n")
        self.assertIn("kept local edit: .harness/rules/review.md (Fluxor dropped it)", out)
        self.assertNotIn(".harness/rules/review.md", json.loads(self.read(".harness/harness.lock.json"))["files"])

    def test_a_file_fluxor_never_wrote_is_not_overwritten(self):
        (self.root / "CLAUDE.md").write_text("My own instructions.\n")
        out = self.init()
        self.assertIn("kept local edit: CLAUDE.md (a file Fluxor did not write is in the way)", out)
        self.assertEqual(self.read("CLAUDE.md"), "My own instructions.\n")

    def test_the_writer_updates_itself_without_a_conflict(self):
        self.init()
        newer = fluxor_sync.disk_bytes(Path(fluxor_sync.__file__)) + b"# a newer writer\n"
        self.fluxor.generated(fluxor_sync.WRITER, newer.decode("utf-8"))
        self.fluxor.items[fluxor_sync.WRITER]["executable"] = True
        self.fluxor.revision = 2
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertNotIn("kept", out)
        self.assertTrue(self.read(fluxor_sync.WRITER).endswith("# a newer writer\n"))
        # card://JAVA-625, decision 5: the writer's update needs no consent, so it is announced.
        self.assertIn(f"fluxor-sync updated itself from {self.url} (revision 2)", out)
        code, out = self.run_sync("pull")
        self.assertNotIn("updated itself", out)

    # ── wiring ───────────────────────────────────────────────────────────────────────────────────

    def test_the_agents_block_is_merged_into_the_users_file(self):
        (self.root / "AGENTS.md").write_text("# My project\n\nKeep this.\n")
        self.init()
        text = self.read("AGENTS.md")
        self.assertTrue(text.startswith("# My project\n\nKeep this.\n\n<!-- fluxor:begin -->"))
        self.fluxor.wiring(always=("english", "review"))
        self.fluxor.revision = 2
        self.run_sync("pull")
        text = self.read("AGENTS.md")
        self.assertEqual(text.count("<!-- fluxor:begin -->"), 1)
        self.assertIn("@.harness/rules/review.md", text)
        self.assertTrue(text.startswith("# My project\n\nKeep this.\n"))

    def test_session_start_is_merged_once_and_other_keys_survive(self):
        (self.root / ".claude").mkdir()
        (self.root / ".claude/settings.json").write_text(json.dumps(
            {"permissions": {"allow": ["Bash(ls)"]},
             "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}}))
        self.init()
        self.fluxor.revision = 2
        self.fluxor.generated(".harness/rules/english.md", "Changed.\n", "english")
        self.run_sync("pull")
        settings = json.loads(self.read(".claude/settings.json"))
        self.assertEqual(settings["permissions"], {"allow": ["Bash(ls)"]})
        commands = [h["command"] for e in settings["hooks"]["SessionStart"] for h in e["hooks"]]
        self.assertEqual(commands, ["echo mine", CLAUDE_PULL])
        codex = json.loads(self.read(".codex/hooks.json"))
        self.assertEqual(codex["hooks"]["SessionStart"][0]["hooks"][0], {"type": "command", **CODEX_PULL})

    def test_a_changed_session_start_entry_replaces_the_old_one(self):
        self.init()
        hook = '{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python3 x pull"}]}]}}\n'
        self.fluxor.generated(".codex/hooks.json", hook, mode="json-merge")
        self.fluxor.revision = 2
        self.run_sync("pull")
        entries = json.loads(self.read(".codex/hooks.json"))["hooks"]["SessionStart"]
        self.assertEqual([h["command"] for e in entries for h in e["hooks"]], ["python3 x pull"])

    def test_a_project_wired_with_the_old_python3_pull_ends_with_only_the_new_one(self):
        # card://JAVA-834: what the server wired before it picked the interpreter.
        old = 'python3 "$CLAUDE_PROJECT_DIR/.harness/bin/fluxor-sync.py" pull'
        self.fluxor.generated(".claude/settings.json", session_start(command=old), mode="json-merge")
        self.init()
        self.fluxor.generated(".claude/settings.json", session_start(command=CLAUDE_PULL), mode="json-merge")
        self.fluxor.revision = 2
        self.run_sync("pull")
        entries = json.loads(self.read(".claude/settings.json"))["hooks"]["SessionStart"]
        self.assertEqual([h["command"] for e in entries for h in e["hooks"]], [CLAUDE_PULL])

    @unittest.skipIf(not os.access("/bin/sh", os.X_OK), "Claude Code runs hooks in a POSIX shell")
    def test_every_wired_python_command_starts_whichever_python_the_machine_has(self):
        # card://JAVA-834: on Windows python3 is often the Microsoft Store stub, which exits 49.
        commands = [CLAUDE_PULL, fluxor_sync.STATUS_LINE_WRAPPER,
                    fluxor_sync.hook_handler("claude", {"dispatch": True, "event": "preTool"})["command"]]
        windows = {"python3": "exit 49", "python": 'echo python "$@"'}
        linux = {"python3": 'echo python3 "$@"'}
        for command in commands:
            for fakes, started in ((windows, "python"), (linux, "python3")):
                bin_dir = self.tmp / f"bin-{started}"
                bin_dir.mkdir(exist_ok=True)
                for name, body in fakes.items():
                    (bin_dir / name).write_text(f"#!/bin/sh\n{body}\n")
                    (bin_dir / name).chmod(0o755)
                run = subprocess.run(["/bin/sh", "-c", command], capture_output=True, text=True,
                                     env={"PATH": str(bin_dir), "CLAUDE_PROJECT_DIR": "/project"})
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertTrue(run.stdout.startswith(f"{started} /project/.harness/bin/fluxor-sync.py "),
                                (command, run.stdout))

    def test_both_clients_find_the_skills(self):
        self.init()
        for link in fluxor_sync.SKILL_LINKS:
            self.assertEqual((self.root / link / "research/SKILL.md").read_text(),
                             "---\nname: research\n---\nSearch first.\n")

    def test_a_managed_copy_where_the_os_refuses_a_symlink(self):
        with mock.patch.object(fluxor_sync.os, "symlink", side_effect=OSError("symlinks not allowed")):
            self.init()
        for link in fluxor_sync.SKILL_LINKS:
            self.assertFalse((self.root / link).is_symlink())
            self.assertTrue((self.root / link / "research/scripts/run.sh").is_file())
        lock = json.loads(self.read(".harness/harness.lock.json"))
        self.assertIn("research/SKILL.md", lock["mirrors"][".claude/skills"])
        self.fluxor.drop(".harness/skills/research/scripts/run.sh")
        self.fluxor.revision = 2
        self.run_sync("pull")
        self.assertFalse((self.root / ".claude/skills/research/scripts/run.sh").exists())
        self.assertTrue((self.root / ".claude/skills/research/SKILL.md").exists())

    def test_codex_gets_the_always_on_directives_printed(self):
        self.init()
        code, out = self.run_sync("pull", "--print-directives")
        self.assertEqual(code, 0, out)
        self.assertIn("Write everything in American English.", out)
        self.assertNotIn("Review before merging.", out.split("up to date", 1)[1].replace(
            "Write everything in American English.", ""))

    def test_printed_directives_never_leave_the_project(self):
        self.init()
        secret = self.tmp / "secret.txt"
        secret.write_text("private key material\n")
        agents = self.read("AGENTS.md").replace(
            "<!-- fluxor:end -->", f"@{secret}\n@../secret.txt\n<!-- fluxor:end -->")
        (self.root / "AGENTS.md").write_text(agents, encoding="utf-8")
        code, out = self.run_sync("pull", "--print-directives")
        self.assertEqual(code, 0, out)
        self.assertIn("Write everything in American English.", out)
        self.assertNotIn("private key material", out)
        self.assertIn("skipped an import outside the project", out)

    def test_a_failed_download_writes_nothing(self):
        self.init()
        self.fluxor.generated(".harness/rules/english.md", "Changed with the skill.\n", "english")
        self.fluxor.blob(".harness/skills/research/SKILL.md", b"---\nname: research\n---\nNewer.\n", "research")
        self.fluxor.revision = 2
        self.fluxor.broken_blobs = True
        lock = self.read(".harness/harness.lock.json")
        code, out = self.run_sync("pull")
        self.assertEqual(code, 1)
        self.assertIn("HTTP 500", out)
        self.assertEqual(self.read(".harness/rules/english.md"), "Write everything in American English.\n")
        self.assertEqual(self.read(".harness/harness.lock.json"), lock)

    def test_files_it_creates_are_readable_by_others(self):
        if os.name == "nt":
            self.skipTest("POSIX permissions")
        self.init()
        for rel in (".claude/settings.json", "AGENTS.md", ".harness/rules/english.md", ".harness/fluxor.json"):
            self.assertEqual((self.root / rel).stat().st_mode & 0o777, 0o644, rel)

    # ── refusals and the rest ────────────────────────────────────────────────────────────────────

    def test_a_newer_format_is_refused_without_writing(self):
        self.init()
        self.fluxor.format = 2
        self.fluxor.revision = 2
        self.fluxor.generated(".harness/rules/english.md", "Format two.\n", "english")
        code, out = self.run_sync("pull")
        self.assertEqual(code, 1)
        self.assertIn("update fluxor-sync", out)
        self.assertEqual(self.read(".harness/rules/english.md"), "Write everything in American English.\n")

    def test_a_revoked_device_is_told_to_enroll_again(self):
        self.init()
        store = self.tmp / "config/device-tokens.json"
        store.write_text(json.dumps({self.url: {"token": "jdbx_device_revoked"}}))
        code, out = self.run_sync("pull")
        self.assertEqual(code, 1)
        self.assertIn("enroll it again", out)

    # ── the token goes only to the server that issued it (card://JAVA-625) ───────────────────────

    def other_server(self, token="jdbx_device_other") -> tuple[Fluxor, str]:
        state = Fluxor(token)
        state.wiring()
        server = serve(state)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return state, f"http://127.0.0.1:{server.server_address[1]}"

    def sync_at(self, root: Path, *args) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = fluxor_sync.main(["--root", str(root), *args])
        return code, out.getvalue()

    def name_server(self, url):
        path = self.root / fluxor_sync.CONFIG
        path.write_text(json.dumps(dict(json.loads(path.read_text()), server=url)))

    def assert_refused(self, out, project_server, issuer):
        self.assertIn(project_server, out)
        self.assertIn(issuer, out)
        self.assertIn(f"fluxor-sync init --server {project_server}", out)

    def test_a_project_naming_another_server_sends_it_no_token(self):
        self.init()
        other, url = self.other_server(token=TOKEN)
        self.name_server(url)
        for args in (("pull",), ("status",), ("pack", "detach", "backend-engineer-ada")):
            code, out = self.run_sync(*args)
            self.assertEqual(code, 1, (args, out))
            self.assert_refused(out, url, self.url)
        self.assertEqual(other.requests, [])
        self.assertEqual(other.authorizations, [])

    def test_a_redirect_from_the_issuer_never_carries_the_token_elsewhere(self):
        # urllib copies Authorization onto a redirect to any host, so the issuer's own redirects
        # (an OAuth error answer, say) would hand the token to whoever they point at.
        self.init()
        other, url = self.other_server()
        self.fluxor.redirect_to = url
        for args in (("pull", "--force"), ("status",)):
            code, out = self.run_sync(*args)
            self.assertEqual(code, 1, (args, out))
            self.assertIn("redirect", out)
        self.assertEqual(other.requests, [])
        self.assertEqual(other.authorizations, [])

    def test_a_project_id_that_is_not_one_is_refused_before_any_request(self):
        # The id is spliced into the URL the token goes to: dot segments, `?` or `#` would aim the
        # request at another route of the issuer, one that redirects.
        self.init()
        self.fluxor.requests.clear()
        config = self.root / fluxor_sync.CONFIG
        for bad in ("x/../../../../oauth/v1/authorize?client_id=c&redirect_uri=x#", "../packs",
                    f"{PROJECT}?include=all", f"{PROJECT}#", "%2e%2e", 42):
            config.write_text(json.dumps(dict(json.loads(config.read_text()), projectId=bad)))
            for args in (("pull",), ("status",), ("pack", "detach", "backend-engineer-ada")):
                code, out = self.run_sync(*args)
                self.assertEqual(code, 1, (bad, args, out))
                self.assertIn("is not a Fluxor project id", out)
        code, out = self.run_sync("init", "--enroll", CODE, "--project", "../x", "--server", self.url)
        self.assertEqual(code, 1, out)
        self.assertIn("is not a Fluxor project id", out)
        self.assertEqual(self.fluxor.requests, [])

    def test_fluxor_server_picks_a_server_but_never_hands_it_another_ones_token(self):
        self.init()
        other, url = self.other_server(token=TOKEN)
        with mock.patch.dict(os.environ, {"FLUXOR_SERVER": url}):
            code, out = self.run_sync("pull")
        self.assertEqual(code, 1, out)
        self.assert_refused(out, url, self.url)
        self.assertEqual(other.authorizations, [])

    def test_each_enrolled_server_gets_only_its_own_token(self):
        self.init()
        other, url = self.other_server()
        other.codes.add("other-code")
        second = self.tmp / "second"
        second.mkdir()
        code, out = self.sync_at(second, "init", "--enroll", "other-code", "--project", PROJECT, "--server", url)
        self.assertEqual(code, 0, out)
        for root in (self.root, second):
            code, out = self.sync_at(root, "pull", "--force")
            self.assertEqual(code, 0, out)
        self.assertTrue(self.fluxor.authorizations and other.authorizations)
        self.assertEqual(set(self.fluxor.authorizations), {f"Bearer {TOKEN}"})
        self.assertEqual(set(other.authorizations), {"Bearer jdbx_device_other"})

    def test_init_never_takes_its_server_from_the_project(self):
        other, url = self.other_server()
        (self.root / ".harness").mkdir()
        (self.root / fluxor_sync.CONFIG).write_text(json.dumps({"declined": True, "server": url}))
        with mock.patch.object(fluxor_sync, "DEFAULT_SERVER", self.url):
            code, out = self.run_sync("init", "--enroll", CODE, "--project", PROJECT)
        self.assertEqual(code, 0, out)
        self.assertEqual(other.requests, [])
        self.assertIn("POST /fluxor/v1/sync/enrollments", self.fluxor.requests)
        self.assertEqual(json.loads(self.read(fluxor_sync.CONFIG))["server"], self.url)

    def test_init_refuses_cleartext_to_a_server_off_this_machine(self):
        for server in ("http://example.com", "http://10.0.0.5:8088/api", "ftp://example.com"):
            code, out = self.run_sync("init", "--enroll", CODE, "--project", PROJECT, "--server", server)
            self.assertEqual(code, 1, (server, out))
            self.assertIn("https", out)
        self.assertFalse((self.tmp / "config").exists())
        for server in ("https://javadaba.com/api", "http://localhost:8088", "http://127.0.0.1", "http://[::1]:9"):
            self.assertIsNone(fluxor_sync.cleartext_off_machine(server), server)
        port = self.server.server_address[1]
        code, out = self.run_sync("init", "--enroll", CODE, "--project", PROJECT, "--server",
                                  f"http://localhost:{port}")
        self.assertEqual(code, 0, out)

    def test_a_legacy_token_counts_as_the_default_servers_only(self):
        self.init()
        (self.tmp / "config/device-tokens.json").unlink()
        (self.tmp / "config/device-token").write_text(TOKEN + "\n")
        self.fluxor.authorizations.clear()
        code, out = self.run_sync("pull")
        self.assertEqual(code, 1, out)
        self.assert_refused(out, self.url, fluxor_sync.DEFAULT_SERVER)
        self.assertEqual(self.fluxor.authorizations, [])
        with mock.patch.object(fluxor_sync, "DEFAULT_SERVER", self.url):
            code, out = self.run_sync("pull", "--force")
        self.assertEqual(code, 0, out)
        self.assertEqual(set(self.fluxor.authorizations), {f"Bearer {TOKEN}"})

    def test_enrolling_on_the_default_server_retires_the_legacy_token(self):
        (self.tmp / "config").mkdir()
        (self.tmp / "config/device-token").write_text("jdbx_device_legacy\n")
        with mock.patch.object(fluxor_sync, "DEFAULT_SERVER", self.url):
            code, out = self.run_sync("init", "--enroll", CODE, "--project", PROJECT)
        self.assertEqual(code, 0, out)
        self.assertIn("replaced this machine's earlier device", out)
        self.assertFalse((self.tmp / "config/device-token").exists())
        self.assertEqual(fluxor_sync.token_for(self.url), TOKEN)

    def test_re_enrolling_on_the_same_server_names_the_replaced_device(self):
        self.init()
        self.fluxor.codes.add("again")
        code, out = self.run_sync("init", "--enroll", "again", "--project", PROJECT, "--server", self.url)
        self.assertEqual(code, 0, out)
        self.assertIn("replaced this machine's earlier device", out)
        self.assertIn(f"fluxor-sync on {fluxor_sync.socket.gethostname()} (1)", out)
        other, url = self.other_server()
        other.codes.add("other-code")
        code, out = self.run_sync("init", "--enroll", "other-code", "--project", PROJECT, "--server", url)
        self.assertEqual(code, 0, out)
        self.assertNotIn("replaced", out)
        self.assertEqual(fluxor_sync.token_for(self.url), TOKEN)

    def test_status_writes_nothing_and_says_what_is_new(self):
        self.init()
        (self.root / ".harness/rules/english.md").write_text("Mine.\n")
        self.fluxor.revision = 2
        self.fluxor.generated(".harness/rules/review.md", "Review twice.\n", "review")
        before = {p: p.stat().st_mtime_ns for p in self.root.rglob("*") if p.is_file()}
        code, out = self.run_sync("status")
        self.assertEqual(code, 0, out)
        self.assertIn("edited locally: .harness/rules/english.md", out)
        self.assertIn("remote: revision 2 is available", out)
        self.assertEqual({p: p.stat().st_mtime_ns for p in self.root.rglob("*") if p.is_file()}, before)

    def test_declining_is_remembered_and_init_resumes(self):
        code, out = self.run_sync("decline")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(self.read(".harness/fluxor.json")), {"declined": True})
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0)
        self.assertIn("declined", out)
        self.init()
        self.assertEqual(json.loads(self.read(".harness/fluxor.json"))["projectId"], PROJECT)

    def test_a_snapshot_path_outside_the_project_is_refused(self):
        self.fluxor.generated("../escape.md", "nope\n")
        code, out = self.run_sync("init", "--enroll", CODE, "--project", PROJECT, "--server", self.url)
        self.assertEqual(code, 1)
        self.assertIn("outside the project", out)
        self.assertFalse((self.tmp / "escape.md").exists())

    # ── hooks: wired only after consent to their exact hash (card://JAVA-556) ────────────────────

    GUARD = "#!/bin/sh\necho guard\n"

    def with_hooks(self):
        self.fluxor.hook("guard", "preTool", sh=self.GUARD, ps1="Write-Output guard\n", tools="shell",
                         timeoutMs=4500)
        self.fluxor.hook("blocked", "notification", sh="#!/bin/sh\necho blocked\n",
                         notifications=["permission", "question"])
        self.fluxor.hook("bar", "statusLine", sh="#!/bin/sh\necho ours\n")
        self.fluxor.wiring(always=("english", "guard", "blocked", "bar"))

    def settings(self, client="claude"):
        return json.loads(self.read(fluxor_sync.CLIENT_FILES[client]))

    def commands(self, client="claude"):
        hooks = self.settings(client).get("hooks", {})
        return {event: [h["command"] for e in entries for h in e["hooks"]] for event, entries in hooks.items()}

    def lock(self):
        return json.loads(self.read(".harness/harness.lock.json"))

    def test_an_unapproved_hook_is_on_disk_unwired_with_its_fallback_read(self):
        self.with_hooks()
        out = self.init()
        self.assertEqual(self.read(".harness/hooks/guard.sh"), self.GUARD)
        self.assertIn("@.harness/rules/guard.md", self.read("AGENTS.md"))
        self.assertEqual(self.commands(), {"SessionStart": [CLAUDE_PULL]})
        self.assertNotIn("statusLine", self.settings())
        self.assertNotIn("PreToolUse", self.commands("codex"))
        self.assertIn("waiting for the user's consent: bar, blocked, guard", out)
        if os.name != "nt":
            self.assertTrue(os.access(self.root / ".harness/hooks/guard.sh", os.X_OK))

    def test_approving_without_consent_refuses_and_prints_what_to_ask(self):
        self.with_hooks()
        self.init()
        before = self.read(".claude/settings.json")
        code, out = self.run_sync("approve", "--all")
        self.assertEqual(code, 2, out)
        self.assertIn("only on a yes run `fluxor-sync approve --consented --all`", out)
        self.assertIn("- guard (Guard): What guard does. It runs on preTool (shell tools), in Claude Code and Codex:"
                      " .harness/hooks/guard.sh, .harness/hooks/guard.ps1", out)
        self.assertIn("- bar (Bar): What bar does. It draws Claude Code's status line, in Claude Code", out)
        self.assertEqual(self.read(".claude/settings.json"), before)
        self.assertNotIn("approvedHooks", self.lock())

    def test_a_failed_tool_call_event_is_wired_for_claude_only_with_its_matcher(self):
        manifest = {"key": "failed", "event": "postToolFailure", "tools": ["shell"],
                    "scripts": {"sh": {"path": ".harness/hooks/failed.sh"}}}
        self.assertEqual(fluxor_sync.EVENTS["claude"]["postToolFailure"], "PostToolUseFailure")
        self.assertNotIn("postToolFailure", fluxor_sync.EVENTS["codex"])
        self.assertEqual(fluxor_sync.hook_matcher("claude", manifest), "Bash")
        self.assertEqual(fluxor_sync.hook_clients(manifest), ["claude"])
        self.assertIn("(shell tools)", fluxor_sync.describe_hook(manifest))

    def test_consent_wires_each_client_and_the_fallback_steps_back(self):
        self.with_hooks()
        self.init()
        code, out = self.run_sync("approve", "--consented", "guard", "blocked")
        self.assertEqual(code, 0, out)
        self.assertIn("approved guard", out)
        self.assertIn("wired for Claude Code and Codex", out)
        self.assertIn("take effect from the next session", out)
        claude = self.settings()["hooks"]
        self.assertIn({"matcher": "Bash", "hooks": [
            {"type": "command", "command": '"$CLAUDE_PROJECT_DIR"/.harness/hooks/guard.sh', "timeout": 5}]},
            claude["PreToolUse"])
        self.assertIn({"matcher": "permission_prompt|elicitation_dialog", "hooks": [
            {"type": "command", "command": '"$CLAUDE_PROJECT_DIR"/.harness/hooks/blocked.sh'}]},
            claude["Notification"])
        codex = self.settings("codex")["hooks"]
        self.assertEqual(codex["PreToolUse"], [{"matcher": "Bash", "hooks": [{
            "type": "command", "command": ".harness/hooks/guard.sh", "timeout": 5,
            "commandWindows": 'powershell -NoProfile -ExecutionPolicy Bypass -File ".harness/hooks/guard.ps1"'}]}])
        self.assertNotIn("Notification", codex)  # Codex has no such event
        agents = self.read("AGENTS.md")
        self.assertNotIn("@.harness/rules/guard.md", agents)
        self.assertNotIn("@.harness/rules/blocked.md", agents)
        self.assertIn("@.harness/rules/bar.md", agents)  # not approved: still read
        self.assertEqual({a["key"] for a in self.lock()["approvedHooks"]}, {"guard", "blocked"})
        code, out = self.run_sync("status", "--offline")
        self.assertIn("hook guard: approved and wired", out)
        self.assertIn("hook bar: waiting for consent", out)
        self.assertEqual(self.run_sync("approve", "--consented", "guard")[1].strip(),
                         "fluxor-sync: no hook is waiting for consent")

    def test_a_pull_with_nothing_changed_keeps_the_wiring_and_touches_nothing(self):
        self.with_hooks()
        self.init()
        self.run_sync("approve", "--consented", "--all")
        files = [p for p in self.root.rglob("*") if p.is_file()]
        before = {p: p.stat().st_mtime_ns for p in files}
        self.fluxor.revision = 2
        self.fluxor.generated(".harness/rules/review.md", "Review twice.\n", "review")
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertIn("1 file(s) written", out)
        self.assertEqual({p: p.stat().st_mtime_ns for p in files if p.name != "review.md"
                          and p.name != "harness.lock.json"},
                         {p: t for p, t in before.items() if p.name != "review.md" and p.name != "harness.lock.json"})
        self.assertIn("PreToolUse", self.commands())

    def test_a_changed_hash_unwires_the_hook_and_brings_its_fallback_back(self):
        self.with_hooks()
        self.init()
        self.run_sync("approve", "--consented", "guard")
        self.fluxor.revision = 2
        self.fluxor.hook("guard", "preTool", sh="#!/bin/sh\necho guard v2\n", ps1="Write-Output guard\n",
                         tools="shell", timeoutMs=4500)
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertIn("hook guard changed (script sh)", out)
        self.assertIn("`fluxor-sync approve --consented guard`", out)
        self.assertNotIn("PreToolUse", self.commands())
        self.assertNotIn("PreToolUse", self.commands("codex"))
        self.assertIn("@.harness/rules/guard.md", self.read("AGENTS.md"))
        self.assertNotIn("approvedHooks", self.lock())
        self.assertEqual(self.read(".harness/hooks/guard.sh"), "#!/bin/sh\necho guard v2\n")
        code, out = self.run_sync("approve", "--consented", "guard")
        self.assertEqual(code, 0, out)
        self.assertIn("PreToolUse", self.commands())

    def test_revoking_unwires_and_restores_the_fallback(self):
        self.with_hooks()
        self.init()
        self.run_sync("approve", "--consented", "--all")
        code, out = self.run_sync("revoke", "guard")
        self.assertEqual(code, 0, out)
        self.assertNotIn("PreToolUse", self.commands())
        self.assertIn("Notification", self.commands())
        self.assertIn("@.harness/rules/guard.md", self.read("AGENTS.md"))
        self.assertNotIn("@.harness/rules/blocked.md", self.read("AGENTS.md"))
        self.assertEqual(self.run_sync("revoke", "guard")[0], 1)

    def test_a_dropped_hook_is_unwired_and_its_files_removed(self):
        self.with_hooks()
        self.init()
        self.run_sync("approve", "--consented", "guard")
        self.fluxor.revision = 2
        for suffix in ("sh", "ps1", "json"):
            self.fluxor.drop(f".harness/hooks/guard.{suffix}")
        self.fluxor.drop(".harness/rules/guard.md")
        self.fluxor.wiring(always=("english", "blocked", "bar"))
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.root / ".harness/hooks/guard.json").exists())
        self.assertNotIn("PreToolUse", self.commands())
        self.assertNotIn("approvedHooks", self.lock())
        # A window opened before this pull still calls guard.sh: it answers as a quiet no-op (JAVA-775).
        script = self.root / ".harness/hooks/guard.sh"
        run = subprocess.run(["sh", str(script)], input="{}", capture_output=True, text=True)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "", ""))
        self.assertTrue(os.access(script, os.X_OK))
        self.assertIn("exit 0", self.read(".harness/hooks/guard.ps1"))
        # A change pulled within the week keeps it; the first one after deletes it.
        self.fluxor.revision = 3
        self.fluxor.generated(".harness/rules/later.md", "later\n")
        self.assertEqual(self.run_sync("pull")[0], 0)
        self.assertTrue(script.exists())
        lock = self.lock()
        lock["files"][".harness/hooks/guard.sh"]["tombstoneSince"] -= fluxor_sync.TOMBSTONE_DAYS * 86400
        (self.root / ".harness/harness.lock.json").write_text(json.dumps(lock))
        self.fluxor.revision = 4
        self.fluxor.generated(".harness/rules/later.md", "later, again\n")
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertFalse(script.exists())
        self.assertTrue((self.root / ".harness/hooks/guard.ps1").exists())

    def test_the_users_own_settings_survive_approving_and_revoking(self):
        self.with_hooks()
        (self.root / ".claude").mkdir()
        mine = {"permissions": {"allow": ["Bash(ls)"]},
                "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "mine.sh"}]}]}}
        (self.root / ".claude/settings.json").write_text(json.dumps(mine))
        self.init()
        self.run_sync("approve", "--consented", "guard")
        self.assertEqual(self.commands()["PreToolUse"],
                         ["mine.sh", '"$CLAUDE_PROJECT_DIR"/.harness/hooks/guard.sh'])
        self.run_sync("revoke", "guard")
        settings = self.settings()
        self.assertEqual(settings["permissions"], mine["permissions"])
        self.assertEqual(settings["hooks"]["PreToolUse"], mine["hooks"]["PreToolUse"])

    def test_our_status_line_stands_alone_when_the_user_has_none(self):
        self.with_hooks()
        self.init()
        self.run_sync("approve", "--consented", "bar")
        self.assertEqual(self.settings()["statusLine"],
                         {"type": "command", "command": '"$CLAUDE_PROJECT_DIR"/.harness/hooks/bar.sh'})
        self.run_sync("revoke", "bar")
        self.assertNotIn("statusLine", self.settings())

    def test_a_users_own_status_line_is_wrapped_then_restored(self):
        self.with_hooks()
        (self.root / ".claude").mkdir()
        theirs = {"type": "command", "command": "echo theirs", "padding": 0}
        (self.root / ".claude/settings.json").write_text(json.dumps({"statusLine": theirs}))
        self.init()
        self.run_sync("approve", "--consented", "bar")
        self.assertEqual(self.settings()["statusLine"]["command"], fluxor_sync.STATUS_LINE_WRAPPER)
        self.assertEqual(self.lock()["hookWiring"]["claude"]["statusLine"]["wrapped"], theirs)
        self.run_sync("revoke", "bar")
        self.assertEqual(self.settings()["statusLine"], theirs)

    @unittest.skipIf(shutil.which("bash") is None, "the status line runs commands with bash")
    def test_the_wrapper_draws_the_users_line_and_feeds_ours_in_the_background(self):
        seen = self.tmp / "seen.json"
        self.fluxor.hook("bar", "statusLine", sh=f"#!/bin/sh\ncat > '{seen}'\necho ours\n")
        self.fluxor.wiring(always=("english", "bar"))
        (self.root / ".claude").mkdir()
        (self.root / ".claude/settings.json").write_text(json.dumps(
            {"statusLine": {"type": "command", "command": "cat >/dev/null; echo theirs"}}))
        self.init()
        self.run_sync("approve", "--consented", "bar")
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.root)
        out = io.BytesIO()
        stdin = io.TextIOWrapper(io.BytesIO(b'{"session_id": "s1"}'))
        stdout = io.TextIOWrapper(out, write_through=True)
        with mock.patch.object(sys, "stdin", stdin), mock.patch.object(sys, "stdout", stdout):
            self.assertEqual(fluxor_sync.main(["--root", str(self.root), "statusline"]), 0)
        self.assertEqual(out.getvalue(), b"theirs\n")
        for _ in range(100):
            if seen.is_file() and seen.read_text():
                break
            threading.Event().wait(0.05)
        self.assertEqual(seen.read_text(), '{"session_id": "s1"}')

    def test_an_edited_manifest_is_never_wired(self):
        self.with_hooks()
        self.init()
        manifest = self.root / ".harness/hooks/guard.json"
        manifest.write_text(manifest.read_text().replace("guard.sh", "evil.sh"))
        code, out = self.run_sync("approve", "--consented", "guard")
        self.assertEqual(code, 1)
        self.assertIn("no hook guard", out)
        self.assertNotIn("PreToolUse", self.commands())

    # card://JAVA-670: consent is to the manifest, which names each script's sha256.
    EDITED_GUARD = ("hook guard: script .harness/hooks/guard.sh edited locally, unwired until "
                    "fluxor-sync pull --force restores Fluxor's (the approval stands)")

    def assert_guard_unwired(self):
        self.assertNotIn("PreToolUse", self.commands())
        self.assertNotIn("PreToolUse", self.commands("codex"))
        self.assertIn("@.harness/rules/guard.md", self.read("AGENTS.md"))
        self.assertIn("guard", {a["key"] for a in self.lock()["approvedHooks"]})

    def test_an_approved_script_edited_on_disk_is_unwired_by_the_next_up_to_date_pull(self):
        self.with_hooks()
        self.init()
        self.run_sync("approve", "--consented", "guard")
        self.assertIn("PreToolUse", self.commands())
        (self.root / ".harness/hooks/guard.sh").write_text("#!/bin/sh\necho mine\n")
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertIn("up to date", out)
        self.assertIn(self.EDITED_GUARD, out)
        self.assert_guard_unwired()
        code, out = self.run_sync("status", "--offline")
        self.assertIn(self.EDITED_GUARD, out)
        self.assertNotIn("hook guard: approved and wired", out)
        code, out = self.run_sync("pull", "--force")
        self.assertEqual(code, 0, out)
        self.assertNotIn("edited locally", out)
        self.assertEqual(self.read(".harness/hooks/guard.sh"), self.GUARD)
        self.assertIn('"$CLAUDE_PROJECT_DIR"/.harness/hooks/guard.sh', self.commands()["PreToolUse"])
        self.assertIn("PreToolUse", self.commands("codex"))
        self.assertNotIn("@.harness/rules/guard.md", self.read("AGENTS.md"))
        self.assertIn("hook guard: approved and wired", self.run_sync("status", "--offline")[1])

    def test_a_deleted_script_or_an_edited_ps1_alone_unwires_the_hook_too(self):
        self.with_hooks()
        self.init()
        self.run_sync("approve", "--consented", "guard")
        (self.root / ".harness/hooks/guard.sh").unlink()
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertIn(self.EDITED_GUARD, out)
        self.assert_guard_unwired()
        self.assertEqual(self.run_sync("pull", "--force")[0], 0)
        self.assertIn("PreToolUse", self.commands())
        # Codex runs the ps1 on Windows, so it is checked as much as the sh is.
        (self.root / ".harness/hooks/guard.ps1").write_text("Write-Output mine\n")
        code, out = self.run_sync("pull")
        self.assertIn("hook guard: script .harness/hooks/guard.ps1 edited locally", out)
        self.assert_guard_unwired()

    def test_approving_a_hook_whose_script_was_edited_records_it_but_wires_nothing(self):
        self.with_hooks()
        self.init()
        (self.root / ".harness/hooks/guard.sh").write_text("#!/bin/sh\necho mine\n")
        code, out = self.run_sync("approve", "--consented", "guard")
        self.assertEqual(code, 0, out)
        self.assertIn("approved guard", out)
        self.assertIn("not wired yet", out)
        self.assertNotIn("wired for", out)
        self.assertIn(self.EDITED_GUARD, out)
        self.assert_guard_unwired()

    def test_an_up_to_date_pull_with_wired_hooks_writes_nothing(self):
        self.with_hooks()
        self.init()
        self.run_sync("approve", "--consented", "--all")
        files = [p for p in self.root.rglob("*") if p.is_file()]
        before = {p: p.stat().st_mtime_ns for p in files}
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertIn("up to date", out)
        self.assertNotIn("edited locally", out)
        self.assertEqual({p: p.stat().st_mtime_ns for p in files}, before)
        self.assertIn("PreToolUse", self.commands())

    def test_approve_with_neither_all_nor_keys_says_what_it_takes(self):
        for args, message in ((("approve",), "approve takes --all or hook keys\n"),
                              (("approve", "--all", "guard"), "approve takes --all or hook keys, not both")):
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out), \
                    self.assertRaises(SystemExit):
                fluxor_sync.main(["--root", str(self.root), *args])
            self.assertIn(message, out.getvalue())

    def test_a_script_path_that_could_break_out_of_the_command_is_not_wired(self):
        self.fluxor.hook("odd", "stop", sh="#!/bin/sh\n")
        manifest = json.loads(self.fluxor.items[".harness/hooks/odd.json"]["content"])
        manifest["scripts"]["sh"]["path"] = '.harness/hooks/x"; rm -rf ~; ".sh'
        self.fluxor.generated(".harness/hooks/odd.json", json.dumps(manifest) + "\n", "odd", mode="hook")
        self.fluxor.wiring(always=("english", "odd"))
        self.init()
        code, out = self.run_sync("approve", "--consented", "odd")
        self.assertEqual(code, 0, out)
        self.assertIn("wired for no client", out)
        self.assertNotIn("Stop", self.commands())
        self.assertIn("@.harness/rules/odd.md", self.read("AGENTS.md"))

    # ── packs (card://JAVA-286) ──────────────────────────────────────────────────────────────────

    PACK = "backend-engineer-alex"

    def render_pack(self, storage: str = "local") -> Path:
        """A pack rendered on the author's machine, as ceet-core's own tests build one, kept under
        ceet-consent-2 (the statement Fluxor keeps a pack under)."""
        sys.path.insert(0, str(REPO / "meta-skills" / "ceet-core" / "tests"))
        import support  # noqa: E402  (ceet-core's test helpers)
        pack = support.synthetic_pack(REPO / "meta-skills" / "ceet-backend-engineer", self.root / ".harness" / "packs")
        for rel in ("private/answers.json", "cognitive-profile.json"):
            data = json.loads((pack / rel).read_text(encoding="utf-8"))
            data["consent"]["statementVersion"] = "ceet-consent-2"
            data["consent"]["storage"] = storage
            (pack / rel).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        out = support.run("render_pack.py", "--project", str(self.root), "render", str(pack),
                          "--adapter", "claude-code", "--write")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        return pack

    def second_checkout(self) -> Path:
        """Another project folder of the same Fluxor project, enrolled with its own code."""
        other = self.tmp / "checkout"
        other.mkdir()
        self.fluxor.codes.add("second-code")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = fluxor_sync.main(["--root", str(other), "init", "--enroll", "second-code", "--project", PROJECT,
                                     "--server", self.url])
        self.assertEqual(code, 0, out.getvalue())
        return other

    def sync_at(self, root: Path, *args) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = fluxor_sync.main(["--root", str(root), *args])
        return code, out.getvalue()

    def published(self, storage: str = "local") -> Path:
        self.init()
        source = self.render_pack(storage)
        code, out = self.run_sync("pack", "publish", self.PACK)
        self.assertEqual(code, 0, out)
        return source

    def test_a_published_pack_reaches_another_checkout_and_validates_there(self):
        source = self.published()
        self.assertTrue(self.fluxor.uploads and not any(p.startswith("private/") for p in self.fluxor.uploads[0]))
        self.assertIn(".gitignore", self.fluxor.uploads[0])

        other = self.second_checkout()
        synced = other / ".harness/packs" / self.PACK
        self.assertEqual((synced / "core.md").read_bytes(), (source / "core.md").read_bytes())
        self.assertFalse((synced / "private").exists())
        self.assertFalse(os.access(synced / "bin/ceet_check.py", os.X_OK) and os.name != "nt")
        check = subprocess.run([sys.executable, str(REPO / "meta-skills/ceet-core/scripts/validate_pack.py"),
                                str(synced), "--role-dir", str(REPO / "meta-skills/ceet-backend-engineer")],
                               capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn("a shared copy?", check.stdout)
        self.assertEqual([w for w in check.stdout.splitlines() if w.startswith("warning")],
                         [w for w in check.stdout.splitlines() if "a shared copy?" in w])

    def test_no_committed_file_names_the_pack(self):
        self.published()
        other = self.second_checkout()
        for rel in (".harness/harness.lock.json", "AGENTS.md", "CLAUDE.md", ".claude/settings.json",
                    ".codex/hooks.json", ".harness/fluxor.json"):
            self.assertNotIn(self.PACK, (other / rel).read_text(encoding="utf-8"), rel)
        lock = json.loads((other / ".harness/packs" / self.PACK / ".fluxor/lock.json").read_text())
        self.assertIn(f".harness/packs/{self.PACK}/core.md", lock["files"])
        self.assertEqual((other / ".harness/packs" / self.PACK / ".gitignore").read_text().split()[-1], "*")

    def test_the_writers_state_is_never_committed_even_when_the_pack_is(self):
        """card://JAVA-713: a pack kept in the repository has no root `.gitignore`, and a committed
        lock would make another clone delete the pack's files and inherit its hook approvals."""
        self.published("repository")
        other = self.second_checkout()
        pack = other / ".harness/packs" / self.PACK
        self.assertFalse((pack / ".gitignore").exists(), "a repository pack is committed, by the person's choice")
        manifests = sorted((pack / ".fluxor/hooks").glob("*.json"))
        self.assertTrue(manifests)
        subprocess.run(["git", "init", "-q"], cwd=other, check=True)
        paths = [p.relative_to(other).as_posix() for p in (pack / ".fluxor/lock.json", *manifests)]
        ignored = subprocess.run(["git", "check-ignore", *paths], cwd=other, capture_output=True, text=True)
        self.assertEqual(sorted(ignored.stdout.split()), sorted(paths), ignored.stderr)
        subprocess.run(["git", "add", "-A"], cwd=other, check=True)
        staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=other, check=True,
                                capture_output=True, text=True).stdout.splitlines()
        self.assertIn(f".harness/packs/{self.PACK}/core.md", staged)
        self.assertEqual([p for p in staged if "/.fluxor/" in p], [])

    def test_the_core_reaches_both_clients_at_session_start(self):
        self.published()
        other = self.second_checkout()
        core = (other / ".harness/packs" / self.PACK / "core.md").read_text(encoding="utf-8").rstrip()
        for flag in ("--print-packs", "--print-directives"):
            code, out = self.sync_at(other, "pull", flag)
            self.assertEqual(code, 0, out)
            self.assertIn(f"<!-- .harness/packs/{self.PACK}/core.md -->\n{core}", out, flag)
        code, out = self.sync_at(other, "pull")
        self.assertNotIn(core, out)

    def test_a_hand_edit_to_a_synced_pack_file_is_kept_and_reported(self):
        self.published()
        other = self.second_checkout()
        core = other / ".harness/packs" / self.PACK / "core.md"
        core.write_text("my own core\n", encoding="utf-8")
        self.fluxor.revision = 2
        self.fluxor.generated(".harness/rules/new.md", "New.\n", "new")
        code, out = self.sync_at(other, "pull")
        self.assertEqual(code, 0, out)
        self.assertIn(f"kept local edit: .harness/packs/{self.PACK}/core.md", out)
        self.assertEqual(core.read_text(encoding="utf-8"), "my own core\n")
        code, out = self.sync_at(other, "status", "--offline")
        self.assertIn(f"edited locally: .harness/packs/{self.PACK}/core.md", out)

    def test_a_pack_hook_waits_for_consent_and_is_wired_through_one_entry_naming_no_pack(self):
        self.published()
        other = self.second_checkout()
        settings = lambda: json.loads((other / ".claude/settings.json").read_text())  # noqa: E731
        self.assertNotIn("PreToolUse", settings()["hooks"])

        code, out = self.sync_at(other, "approve", f"{self.PACK}:ceet-check")
        self.assertEqual(code, 2, out)
        self.assertIn(f"with Python: .harness/packs/{self.PACK}/bin/ceet_check.py claude-code", out)
        self.assertNotIn("PreToolUse", settings()["hooks"])

        code, out = self.sync_at(other, "approve", "--consented", f"{self.PACK}:ceet-check")
        self.assertEqual(code, 0, out)
        entry = settings()["hooks"]["PreToolUse"]
        self.assertEqual(entry, [{"matcher": "Bash", "hooks": [{
            "type": "command", "command": f'{fluxor_sync.PYTHON} "$CLAUDE_PROJECT_DIR/.harness/bin/fluxor-sync.py" pack-hook preTool',
            "timeout": 60}]}])
        self.assertNotIn(self.PACK, (other / ".claude/settings.json").read_text())
        self.assertNotIn(self.PACK, (other / ".harness/harness.lock.json").read_text())
        self.assertNotIn("UserPromptSubmit", settings()["hooks"], "examples was not approved")

        # A changed script is a new hash: unwired, and asked again.
        self.fluxor.packs[self.PACK]["bin/ceet_check.py"] += "# changed\n"
        code, out = self.sync_at(other, "pull")
        self.assertIn(f"hook {self.PACK}:ceet-check changed", out)
        self.assertNotIn("PreToolUse", settings()["hooks"])

    def test_the_dispatcher_runs_only_the_approved_script_and_its_block_blocks(self):
        self.published()
        other = self.second_checkout()
        self.sync_at(other, "approve", "--consented", f"{self.PACK}:ceet-check")
        writer = other / ".harness/bin/fluxor-sync.py"
        subprocess.run(["git", "init", "-q"], cwd=other, check=True)
        secret = "AKIA" + "Q" * 16
        (other / "leak.txt").write_text(f"key = {secret}\n")
        subprocess.run(["git", "add", "leak.txt"], cwd=other, check=True)
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -m leak"}})
        run = lambda: subprocess.run([sys.executable, str(writer), "--root", str(other), "pack-hook", "preTool"],  # noqa: E731
                                     input=payload, capture_output=True, text=True, cwd=other)
        blocked = run()
        self.assertEqual(blocked.returncode, 2, blocked.stdout + blocked.stderr)

        script = other / ".harness/packs" / self.PACK / "bin/ceet_check.py"
        script.write_text(script.read_text() + "# tampered\n")
        tampered = run()
        self.assertEqual(tampered.returncode, 0)
        self.assertIn("is not the approved one", tampered.stderr)

    def test_a_dropped_pack_is_removed_where_fluxor_wrote_it_and_left_where_it_was_rendered(self):
        source = self.published()
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        other = self.second_checkout()

        code, out = self.run_sync("pack", "unpublish", self.PACK)
        self.assertEqual(code, 0, out)
        code, out = self.sync_at(other, "pull")
        self.assertEqual(code, 0, out)
        self.assertFalse((other / ".harness/packs" / self.PACK).exists(), out)

        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assertTrue((source / "core.md").is_file(), "the author's rendered pack stays")
        self.assertTrue((source / "private/answers.json").is_file())
        self.assertFalse((source / ".fluxor").exists())
        self.assertIn(f"render_pack.py erase {self.PACK} --yes", out)

    def test_detaching_drops_the_pack_from_this_project(self):
        self.published()
        other = self.second_checkout()
        code, out = self.sync_at(other, "pack", "detach", self.PACK)
        self.assertEqual(code, 0, out)
        self.sync_at(other, "pull")
        self.assertFalse((other / ".harness/packs" / self.PACK).exists())
        code, out = self.sync_at(other, "pack", "detach", self.PACK)
        self.assertEqual(code, 1)
        self.assertIn("not found", out)

    def test_publishing_refuses_a_file_edited_since_the_render(self):
        self.init()
        source = self.render_pack()
        (source / "core.md").write_text("edited\n", encoding="utf-8")
        code, out = self.run_sync("pack", "publish", self.PACK)
        self.assertEqual(code, 1)
        self.assertIn("core.md was edited since the pack was rendered", out)
        self.assertEqual(self.fluxor.uploads, [])

    def test_a_snapshot_pack_path_outside_a_pack_folder_is_refused(self):
        self.init()
        self.fluxor.generated(".harness/packs/Not_A_Pack/core.md", "x\n", "x")
        code, out = self.run_sync("pull")
        self.assertEqual(code, 1)
        self.assertIn("not a pack's", out)

    # ── a path resolves inside the project, links followed (card://JAVA-873) ─────────────────────

    SECRET = "private key material\n"

    def link(self, path: Path, target) -> Path:
        """`path` replaced by a symlink to `target`; the test skips where the OS refuses one."""
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(target, path, target_is_directory=Path(path.parent, target).is_dir())
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"this OS refuses symlinks ({exc})")
        return path

    def outside(self, name: str, text: str = SECRET) -> Path:
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_a_directive_linked_outside_is_never_printed(self):
        self.init()
        self.link(self.root / ".harness/rules/x.md", self.outside("secret.txt"))
        agents = self.read("AGENTS.md").replace("<!-- fluxor:end -->", "@.harness/rules/x.md\n<!-- fluxor:end -->")
        (self.root / "AGENTS.md").write_text(agents, encoding="utf-8")
        code, out = self.run_sync("pull", "--print-directives")
        self.assertEqual(code, 0, out)
        self.assertIn("Write everything in American English.", out)
        self.assertNotIn(self.SECRET.strip(), out)
        self.assertIn(".harness/rules/x.md", out)
        self.assertIn("outside the project", out)

    def test_a_pack_core_linked_outside_is_never_printed(self):
        self.published()
        other = self.second_checkout()
        self.link(other / ".harness/packs" / self.PACK / "core.md", self.outside("core-secret.txt"))
        code, out = self.sync_at(other, "pull", "--print-packs")
        self.assertEqual(code, 0, out)
        self.assertNotIn(self.SECRET.strip(), out)
        self.assertIn(f".harness/packs/{self.PACK}/core.md", out)

    def test_a_pull_writes_nothing_through_a_link_and_still_writes_the_rest(self):
        self.init()
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        self.link(self.root / ".harness/rules", elsewhere)
        victim = self.outside("victim.txt", "mine\n")
        self.link(self.root / ".harness/skills/research/SKILL.md", victim)
        self.fluxor.revision = 2
        self.fluxor.generated(".harness/rules/english.md", "Write in American English, always.\n", "english")
        self.fluxor.blob(".harness/skills/research/SKILL.md", b"---\nname: research\n---\nSearch twice.\n",
                         "research")
        self.fluxor.blob(".harness/skills/research/scripts/run.sh", b"#!/bin/sh\necho run twice\n", "research", True)
        for force in ((), ("--force",)):
            code, out = self.run_sync("pull", *force)
            self.assertEqual(code, 0, out)
            self.assertEqual(os.listdir(elsewhere), [], force)
            self.assertEqual(victim.read_text(), "mine\n", force)
            self.assertTrue((self.root / ".harness/skills/research/SKILL.md").is_symlink(), force)
            self.assertIn(".harness/rules/english.md", out)
            self.assertIn(".harness/skills/research/SKILL.md", out)
            self.assertIn("outside the project", out)
            self.assertEqual(self.read(".harness/skills/research/scripts/run.sh"), "#!/bin/sh\necho run twice\n")

    def test_a_client_folder_linked_outside_gets_no_settings_and_no_skills(self):
        home = self.tmp / "home-claude"
        home.mkdir()
        (home / "settings.json").write_text('{"theme": "dark"}\n', encoding="utf-8")
        self.link(self.root / ".claude", home)
        out = self.init()
        self.assertEqual(sorted(os.listdir(home)), ["settings.json"])
        self.assertEqual((home / "settings.json").read_text(), '{"theme": "dark"}\n')
        self.assertIn(".claude/settings.json", out)
        self.assertIn(".claude/skills", out)
        self.assertNotIn(".claude/settings.json", self.lock()["files"])
        self.assertEqual(self.read(".agents/skills/research/SKILL.md"), "---\nname: research\n---\nSearch first.\n")

    def test_a_dropped_hook_script_linked_outside_is_left_alone_even_with_force(self):
        self.with_hooks()
        self.init()
        victim = self.outside("victim.sh", "#!/bin/sh\necho mine\n")
        self.link(self.root / ".harness/hooks/guard.sh", victim)
        self.fluxor.revision = 2
        for suffix in ("sh", "ps1", "json"):
            self.fluxor.drop(f".harness/hooks/guard.{suffix}")
        code, out = self.run_sync("pull", "--force")
        self.assertEqual(code, 0, out)
        self.assertEqual(victim.read_text(), "#!/bin/sh\necho mine\n")
        self.assertIn(".harness/hooks/guard.sh", out)
        self.assertIn("outside the project", out)

    def test_publishing_sends_nothing_through_a_link(self):
        self.init()
        source = self.render_pack()
        gitignore = source / ".gitignore"
        self.assertTrue(gitignore.is_file())
        self.link(gitignore, self.outside("secret.txt"))
        code, out = self.run_sync("pack", "publish", self.PACK)
        self.assertEqual(code, 1, out)
        self.assertIn(".gitignore", out)
        self.assertEqual(self.fluxor.uploads, [])

        gitignore.unlink()
        answers = (source / "private/answers.json").read_bytes()
        self.link(source / "core.md", "private/answers.json")
        manifest = json.loads((source / "pack.json").read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            if entry["path"] == "core.md":
                entry["sha256"] = sha(answers.replace(b"\r\n", b"\n"))
        (source / "pack.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        code, out = self.run_sync("pack", "publish", self.PACK)
        self.assertEqual(code, 1, out)
        self.assertIn("core.md", out)
        self.assertEqual(self.fluxor.uploads, [])

    def test_an_approved_hook_whose_script_links_outside_is_unwired(self):
        self.with_hooks()
        self.init()
        self.run_sync("approve", "--consented", "guard")
        self.assertIn("PreToolUse", self.commands())
        self.link(self.root / ".harness/hooks/guard.sh", self.outside("guard.sh", self.GUARD))
        code, out = self.run_sync("pull")
        self.assertEqual(code, 0, out)
        self.assert_guard_unwired()
        self.assertIn(".harness/hooks/guard.sh", out)

    def test_a_link_loop_is_named_and_crashes_nothing(self):
        self.init()
        self.link(self.root / ".harness/rules", "rules")
        self.fluxor.revision = 2
        self.fluxor.generated(".harness/rules/english.md", "Write in American English, always.\n", "english")
        self.fluxor.blob(".harness/skills/research/SKILL.md", b"---\nname: research\n---\nSearch twice.\n",
                         "research")
        code, out = self.run_sync("pull", "--force", "--print-directives")
        self.assertEqual(code, 0, out)
        self.assertIn(".harness/rules/english.md", out)
        self.assertEqual(self.read(".harness/skills/research/SKILL.md"), "---\nname: research\n---\nSearch twice.\n")

    def test_a_harness_folder_linked_outside_refuses_every_command(self):
        self.init()
        elsewhere = self.tmp / "elsewhere"
        shutil.copytree(self.root / ".harness", elsewhere)
        self.link(self.root / ".harness", elsewhere)
        before = sorted(p.relative_to(elsewhere).as_posix() for p in elsewhere.rglob("*"))
        requests = len(self.fluxor.requests)
        for command in (("pull", "--force"), ("status", "--offline"), ("approve", "--all"), ("decline",)):
            code, out = self.run_sync(*command)
            self.assertEqual(code, 1, (command, out))
            self.assertIn(".harness", out)
            self.assertIn("outside the project", out)
        self.assertEqual(sorted(p.relative_to(elsewhere).as_posix() for p in elsewhere.rglob("*")), before)
        self.assertEqual(len(self.fluxor.requests), requests, "nothing was asked of Fluxor either")


if __name__ == "__main__":
    unittest.main()
