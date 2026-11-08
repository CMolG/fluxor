"""tools/fluxor_sync.py `item publish` (card://JAVA-2007): a folder published as an own item, by
sha256. Runs against a small fake of the two routes it calls, in a throwaway project.
Run: python3 -m unittest discover -s tools/tests
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import os
import shutil
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import test_fluxor_sync as base
from test_fluxor_sync import PROJECT, TOKEN, fluxor_sync


class Store:
    """What the publish routes keep: the blob store, and each published item's last request."""

    def __init__(self):
        self.blobs: dict[str, bytes] = {}
        self.items: dict[str, dict] = {}
        self.versions: dict[str, int] = {}
        self.revision = 3
        self.selections: list[dict] = []


def serve(store: Store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, payload):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def body(self):
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                self.reply(401, {"error": "unauthorized", "message": "no"})
                return None
            return json.loads(self.rfile.read(int(self.headers["Content-Length"])))

        def do_GET(self):
            if self.body_less():
                self.reply(200, [{"id": PROJECT, "name": "web", "revision": store.revision}])

        def do_PATCH(self):
            body = self.body()
            if body is None:
                return
            if body["expectedRevision"] != store.revision:
                return self.reply(409, {"error": "harness_revision_conflict", "message": "read it again"})
            store.selections.append(body)
            store.revision += 1
            self.reply(200, {"project": {"id": PROJECT, "revision": store.revision},
                             "items": [{"key": c["key"]} for c in body["put"]]})

        def body_less(self):
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                self.reply(401, {"error": "unauthorized", "message": "no"})
                return False
            return True

        def do_POST(self):
            body = self.body()
            if body is not None:
                self.reply(200, {"missing": [s for s in body["sha256"] if s not in store.blobs]})

        def do_PUT(self):
            body = self.body()
            if body is None:
                return
            key = self.path.rsplit("/", 1)[1]
            for f in body["files"]:
                if "content" in f:
                    data = base64.b64decode(f["content"])
                    assert hashlib.sha256(data).hexdigest() == f["sha256"]
                    store.blobs[f["sha256"]] = data
                elif f["sha256"] not in store.blobs:
                    return self.reply(422, {"error": "harness_blob_missing", "message": f["path"]})
            store.items[key] = body
            store.versions[key] = store.versions.get(key, 0) + 1
            self.reply(200, {"key": key, "version": store.versions[key], "kind": body["kind"]})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class Publish(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "project"
        (self.root / ".harness").mkdir(parents=True)
        self.store = Store()
        self.server = serve(self.store)
        url = f"http://127.0.0.1:{self.server.server_address[1]}"
        env = {"FLUXOR_CONFIG_DIR": str(self.tmp / "config"), "FLUXOR_CACHE_DIR": str(self.tmp / "cache")}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        os.environ.pop("FLUXOR_SERVER", None)
        self.addCleanup(patcher.stop)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.root / ".harness/fluxor.json").write_text(json.dumps({"projectId": PROJECT, "server": url}))
        fluxor_sync.store_token(url, {"deviceToken": TOKEN, "deviceId": "d1", "name": "test"})

    def run_sync(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            try:
                code = fluxor_sync.main(["--root", str(self.root), *args])
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue()

    def folder(self, files: dict[str, bytes]) -> Path:
        folder = self.tmp / "publish"
        for rel, data in files.items():
            (folder / rel).parent.mkdir(parents=True, exist_ok=True)
            (folder / rel).write_bytes(data)
        return folder

    def test_a_files_folder_is_published_with_its_paths_and_binary_bytes(self):
        folder = self.folder({".harness/INDEX.md": b"# Index\n", ".harness/references/a.png": b"\x89PNG\x00\x01",
                              ".harness/__pycache__/x.pyc": b"skip"})

        code, out = self.run_sync("item", "publish", str(folder), "--key", "javadaba.harness", "--kind", "files")

        self.assertEqual(code, 0, out)
        sent = self.store.items["javadaba.harness"]
        self.assertEqual(sorted(f["path"] for f in sent["files"]), [".harness/INDEX.md", ".harness/references/a.png"])
        self.assertEqual(sent["visibility"], "project")
        self.assertEqual(sent["harnessProjectId"], PROJECT)
        self.assertIn(b"\x89PNG\x00\x01", self.store.blobs.values())
        self.assertIn("2 file(s), 2 sent, 0 already in Fluxor", out)

    def test_publishing_an_unchanged_folder_again_sends_no_bytes(self):
        folder = self.folder({".harness/INDEX.md": b"# Index\n"})
        self.run_sync("item", "publish", str(folder), "--key", "javadaba.harness", "--kind", "files")

        code, out = self.run_sync("item", "publish", str(folder), "--key", "javadaba.harness", "--kind", "files")

        self.assertEqual(code, 0, out)
        self.assertNotIn("content", self.store.items["javadaba.harness"]["files"][0])
        self.assertIn("version 2: 1 file(s), 0 sent, 1 already in Fluxor", out)

    def test_a_hook_folder_sends_its_manifest_and_its_files_inline(self):
        folder = self.folder({"hook.json": json.dumps({"event": "preTool", "tools": "shell"}).encode(),
                              "fallback.md": b"Never push to main.\n", "hook.sh": b"#!/bin/sh\nexit 0\n"})

        code, out = self.run_sync("item", "publish", str(folder), "--key", "javadaba.guard", "--kind", "hook",
                                  "--visibility", "private")

        self.assertEqual(code, 0, out)
        sent = self.store.items["javadaba.guard"]
        self.assertEqual(sent["hook"], {"event": "preTool", "tools": "shell"})
        self.assertEqual(sorted(f["path"] for f in sent["files"]), ["fallback.md", "hook.sh"])
        self.assertTrue(all("content" in f for f in sent["files"]))
        self.assertNotIn("harnessProjectId", sent)

    @unittest.skipIf(os.name == "nt", "symlinks need privileges on Windows")
    def test_a_link_that_leaves_the_folder_is_not_published(self):
        folder = self.folder({".harness/INDEX.md": b"# Index\n"})
        (self.tmp / "secret.txt").write_text("secret")
        os.symlink(self.tmp / "secret.txt", folder / ".harness/secret.txt")

        code, out = self.run_sync("item", "publish", str(folder), "--key", "javadaba.harness", "--kind", "files")

        self.assertEqual(code, 0, out)
        self.assertEqual([f["path"] for f in self.store.items["javadaba.harness"]["files"]], [".harness/INDEX.md"])


if __name__ == "__main__":
    unittest.main()


class PublishMore(Publish):
    """card://JAVA-2011: what a workspace's migration needs besides files: its own atoms and its selection."""

    def test_a_local_mod_is_published_with_its_card_rendered_as_the_market_renders_it(self):
        folder = self.folder({"ds-javadaba.md": b"# ds-javadaba: House\n",
                              "card.json": json.dumps({"name": "ds-javadaba", "tags": ["ui", "ü"]}).encode()})

        code, out = self.run_sync("item", "publish", str(folder), "--key", "javadaba.ds-javadaba", "--kind",
                                  "directive", "--atom", "mod")

        self.assertEqual(code, 0, out)
        sent = self.store.items["javadaba.ds-javadaba"]
        self.assertEqual(sent["atom"], "mod")
        self.assertEqual(sent["card"], '{\n  "name": "ds-javadaba",\n  "tags": [\n    "ui",\n    "ü"\n  ]\n}')
        self.assertEqual([f["path"] for f in sent["files"]], ["ds-javadaba.md"])

    def test_select_puts_and_removes_items_at_the_projects_revision(self):
        code, out = self.run_sync("select", "--put", "backlog", "english@2", "--remove", "old")

        self.assertEqual(code, 0, out)
        self.assertEqual(self.store.selections, [{"expectedRevision": 3, "put": [{"key": "backlog"},
                                                  {"key": "english", "version": 2}], "remove": ["old"]}])
        self.assertIn("revision 4 with 2 item(s)", out)


def load_tests(loader, tests, pattern):
    """Each class's own cases once: PublishMore inherits Publish's setUp, not its tests."""
    suite = unittest.TestSuite(loader.loadTestsFromTestCase(Publish))
    suite.addTests(PublishMore(name) for name in loader.getTestCaseNames(PublishMore) if name in PublishMore.__dict__)
    return suite
