#!/usr/bin/env python3
"""fluxor-sync: keeps a project's harness in step with what its owner configures in Fluxor online.

  fluxor-sync init --enroll CODE --project ID [--server URL] [--no-pull] [--storage local|repository]
  fluxor-sync pull [--force] [--print-directives] [--print-packs]
  fluxor-sync item publish FOLDER --key NS.NAME --kind skill|hook|files|directive [--atom A] [--visibility V]
  fluxor-sync select [--put KEY[@VERSION]...] [--remove KEY...]
  fluxor-sync status [--offline]
  fluxor-sync decline
  fluxor-sync approve --consented (--all | KEY...)
  fluxor-sync revoke KEY...
  fluxor-sync pack (publish | detach | unpublish) PACK-ID

ADR 0019 (card://JAVA-162). An MCP server cannot write to this disk, so the harness is PULLED: at
every session start (each client's `SessionStart` runs `pull`) and whenever someone asks. The
snapshot's hash is its ETag, so an unchanged harness answers 304 and nothing here is touched.

- `init` trades the one-time code the Fluxor MCP's `harness.bootstrap` minted for a device token,
  kept with the server that issued it (`~/.config/fluxor/device-tokens.json`, mode 0600), writes
  `.harness/fluxor.json`, installs this file as `.harness/bin/fluxor-sync.py` and pulls. From then on
  the writer is a managed file of every snapshot, so it updates itself, and a pull says when it did.
- A token goes only to the server that issued it (card://JAVA-625): the project's `server` and
  `FLUXOR_SERVER` pick which server to ask, never which token to send, so a committed change to
  `.harness/fluxor.json` cannot carry this machine's token to another host. For the same reason no
  request follows a redirect, and the project id must be a UUID before it goes into a URL.
- `pull` materializes the snapshot (`format: 1`, `doc://contracts/catalog-format`): skill
  files come from the blob store, fetched only when neither the file on disk nor the local cache has
  them; generated files carry their content. It writes `.harness/harness.lock.json` in
  `installer.py`'s format, plus `source`.
- A managed file edited locally is never overwritten silently: it is kept and listed, and
  `pull --force` takes Fluxor's. The writer only ever touches the paths in its lock.
- `decline` records that this project's owner said no, so an agent does not ask again; `init`
  resumes.
- A catalog hook arrives as its scripts plus a manifest (`.harness/hooks/<key>.json`), and is wired
  into `.claude/settings.json` and `.codex/hooks.json` only once its manifest's exact sha256 is in
  the lock's `approvedHooks` (ADR 0020, card://JAVA-556). `approve --consented` records it, and the
  agent runs it only after the user said yes in the conversation; without the flag it refuses and
  prints what to ask. Until then, and again whenever a pull brings a new hash, the hook's `fallback`
  directive is what the agent reads. A script edited on disk is not the one the manifest names, so
  every pull, up to date or not, unwires its hook until `pull --force` restores it (card://JAVA-670).
- A CEET pack (card://JAVA-286) is a person's: `pack publish` uploads the one rendered at
  `.harness/packs/<pack-id>/` (its shared files, never `private/`) and attaches it to this project,
  and every pull of a project it is attached to writes it there. Nothing a project commits names it:
  its lock is `.harness/packs/<pack-id>/.fluxor/lock.json`, beside the hook manifests in
  `.fluxor/hooks/`, and the writer ignores that folder with its own `.fluxor/.gitignore` whatever the
  pack's storage (card://JAVA-713): it is this machine's state, and a committed lock would make
  another clone delete the pack's files and inherit its hook approvals; its `core.md` reaches the session through the session start's output (`--print-packs`,
  and `--print-directives` for Codex), never through `AGENTS.md`; and its hooks, approved like a
  catalog hook as `<pack-id>:<hook>`, run through one `pack-hook` entry that names no pack. Files a
  pull finds already there (the machine the pack was rendered on) stay the person's: a dropped pack
  never removes them.

Python 3.9+, standard library only: it runs on any machine an agent runs on. `installer.py`
imports its lock and edited-file logic from here, so the two never disagree about either.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import ipaddress
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

FORMAT = 1
DEFAULT_SERVER = "https://javadaba.com/api"
CONFIG = ".harness/fluxor.json"
LOCK = ".harness/harness.lock.json"
WRITER = ".harness/bin/fluxor-sync.py"
SKILLS = ".harness/skills"
# Each client finds skills in its own folder; both point at the harness's (ADR 0019, decision 5).
SKILL_LINKS = (".claude/skills", ".agents/skills")
BLOCK_BEGIN = "<!-- fluxor:begin -->"
BLOCK_END = "<!-- fluxor:end -->"
USER_AGENT = "fluxor-sync/1"
TIMEOUT = 30
# A catalog hook's neutral events (spike JAVA-156, decision 4, plus JAVA-556's two), per client.
# Codex has no Notification event and no status line (its Hooks docs, read 2026-10-01).
EVENTS = {
    "claude": {"sessionStart": "SessionStart", "promptSubmit": "UserPromptSubmit", "preTool": "PreToolUse",
               "postTool": "PostToolUse", "postToolFailure": "PostToolUseFailure", "stop": "Stop",
               "notification": "Notification"},
    "codex": {"sessionStart": "SessionStart", "promptSubmit": "UserPromptSubmit", "preTool": "PreToolUse",
              "postTool": "PostToolUse", "stop": "Stop"},
}
STATUS_LINE = "statusLine"
TOOL_MATCHERS = {
    "claude": {"shell": "Bash", "edit": "Write|Edit|MultiEdit|NotebookEdit"},
    "codex": {"shell": "Bash", "edit": "apply_patch|Edit|Write"},
}
NOTIFICATIONS = {"permission": "permission_prompt", "question": "elicitation_dialog", "idle": "idle_prompt"}
CLIENT_FILES = {"claude": ".claude/settings.json", "codex": ".codex/hooks.json"}
# card://JAVA-2010 (ADR 0038): a harness kept out of git (`"storage": "local"` in fluxor.json) is this
# machine's state. Claude Code's hooks are wired in its per-machine settings file; Codex has none, and
# asks its user to trust each hook itself.
LOCAL_CLIENT_FILES = {"claude": ".claude/settings.local.json", "codex": ".codex/hooks.json"}
# The committed files that bridge each client to the harness: the same on every machine.
BRIDGES = ("AGENTS.md", "CLAUDE.md", ".claude/settings.json", ".codex/hooks.json")
# With local storage `AGENTS.md`'s block only imports this file, which holds this machine's list.
AGENTS_LIST = ".harness/agents.md"
STABLE_BLOCK = (f"{BLOCK_BEGIN}\n<!-- Managed by Fluxor (fluxor-sync): this machine's list of rules is "
                f"{AGENTS_LIST}. -->\n@{AGENTS_LIST}\n{BLOCK_END}\n")
EXCLUDE_BEGIN = "# fluxor-sync:begin: this machine's pulled harness, never committed (card://JAVA-2010)"
EXCLUDE_END = "# fluxor-sync:end"
CLIENT_NAMES = {"claude": "Claude Code", "codex": "Codex"}
# The paths a hook's commands are built from: interpolated into a shell command, so nothing else.
HOOK_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
HOOK_SCRIPT = re.compile(r"\.harness/hooks/[A-Za-z0-9][A-Za-z0-9._-]*\.(sh|ps1)")
SHA256 = re.compile(r"[0-9a-f]{64}")
# How long a dropped hook script stays as a no-op: longer than a window is reasonably left open on
# the hooks it started with. The first pull that changes something after that deletes it.
TOMBSTONE_DAYS = 7
TOMBSTONE_SH = "#!/bin/sh\n# Dropped by Fluxor; a no-op for windows opened before the sync that dropped it.\nexit 0\n"
TOMBSTONE_PS1 = "# Dropped by Fluxor; a no-op for windows opened before the sync that dropped it.\nexit 0\n"
# card://JAVA-834: what starts Python in a command wired into the committed client files. On
# Windows `python3` is often the Microsoft Store stub (exit 49), so the shell tries it and falls back
# to `python`. Never `sys.executable`: the file is shared, and that path is one machine's.
PYTHON = "py=python3; \"$py\" -c '' </dev/null >/dev/null 2>&1 || py=python; \"$py\""
STATUS_LINE_WRAPPER = f'{PYTHON} "$CLAUDE_PROJECT_DIR/{WRITER}" statusline'
# card://JAVA-286: where packs are delivered (ceet-core's pack contract), and each one's lock in it.
PACKS = ".harness/packs"
PACK_LOCK = ".fluxor/lock.json"
# card://JAVA-713: the pack's own `.gitignore` covers `.fluxor/` only when it is kept local, so the
# writer ignores its state itself, whatever the pack's storage.
PACK_IGNORE = ".fluxor/.gitignore"
PACK_IGNORE_TEXT = "# fluxor-sync's state for this machine (lock, approvals, hook manifests): never committed.\n*\n"
PACK_ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
# A Fluxor project id is a UUID, the sync API's path parameter. It is spliced into the URL a token
# goes to, so anything else (dot segments, `?`, `#`) could aim that request elsewhere (card://JAVA-625).
PROJECT_ID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
# A pack hook runs a script of its pack: the path and arguments its manifest names, nothing else.
PACK_SCRIPT = re.compile(r"bin/[A-Za-z0-9_-]+\.py")
PACK_ARG = re.compile(r"[a-z][a-z-]*")
PACK_HOOK_TIMEOUT = 60


class SyncError(Exception):
    """A failure the user can act on: the message says what happened and what to do."""


# ─── Shared with installer.py: what a lock says, and what on disk no longer matches it ─────────────

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def disk_bytes(path: Path) -> bytes:
    """A text file's bytes with CRLF folded to LF, so a checkout with autocrlf is not an edit."""
    data = path.read_bytes()
    return data.replace(b"\r\n", b"\n") if b"\0" not in data[:8000] else data


def disk_executable(path: Path) -> bool | None:
    """None where the filesystem can't say (Windows reports every file one way)."""
    return None if os.name == "nt" else os.access(path, os.X_OK)


def read_lock(path: Path) -> dict:
    """The lock at `path`, or {} when there is none or it is unreadable (the next write replaces it)."""
    if not path.is_file():
        return {}
    try:
        lock = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return lock if isinstance(lock, dict) else {}


def managed_block(text: str) -> str | None:
    """`AGENTS.md`'s managed block, markers included and ending in a newline, or None."""
    start = text.find(BLOCK_BEGIN)
    end = text.find(BLOCK_END, start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        return None
    return text[start:end + len(BLOCK_END)] + "\n"


def edited_files(base: Path, lock: dict) -> list[tuple[str, str]]:
    """(path, reason) for every locked file whose bytes or mode no longer match the lock. Paths are
    relative to `base`. A `block` entry is checked on its block alone, the rest of the file being the
    user's; a `json-merge` entry is never an edit, because it is merged in, not owned."""
    edited = []
    for rel, entry in sorted(lock.get("files", {}).items()):
        mode = entry.get("mode", "file")
        if mode == "json-merge":
            continue
        path = base / rel
        if escapes(base, path):
            edited.append((rel, OUTSIDE))  # never read: its bytes are someone else's file
            continue
        if not path.is_file():
            edited.append((rel, "deleted"))
            continue
        if mode == "block":
            block = managed_block(disk_bytes(path).decode("utf-8", errors="replace"))
            if block is None:
                edited.append((rel, "managed block removed"))
            elif sha256_bytes(block.encode("utf-8")) != entry["sha256"]:
                edited.append((rel, "content differs"))
            continue
        if sha256_bytes(disk_bytes(path)) != entry["sha256"]:
            edited.append((rel, "content differs"))
        elif disk_executable(path) not in (None, entry.get("executable", False)):
            edited.append((rel, "executable bit differs"))
    return edited


# ─── Where things live ─────────────────────────────────────────────────────────────────────────────

def project_root(arg: str | None) -> Path:
    """`--root`, else `$CLAUDE_PROJECT_DIR`, else the git top level, else the current directory."""
    if arg:
        return Path(arg).resolve()
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        return Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve()
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                             check=True).stdout.strip()
        if top:
            return Path(top).resolve()
    except (OSError, subprocess.CalledProcessError):
        pass
    return Path.cwd().resolve()


def config_dir() -> Path:
    if os.environ.get("FLUXOR_CONFIG_DIR"):
        return Path(os.environ["FLUXOR_CONFIG_DIR"])
    return Path.home() / ".config" / "fluxor"


def cache_dir() -> Path:
    if os.environ.get("FLUXOR_CACHE_DIR"):
        return Path(os.environ["FLUXOR_CACHE_DIR"])
    base = os.environ.get("XDG_CACHE_HOME")
    return (Path(base) if base else Path.home() / ".cache") / "fluxor"


def token_store() -> Path:
    """This machine's device tokens, one per server that issued one (card://JAVA-625)."""
    return config_dir() / "device-tokens.json"


def legacy_token_path() -> Path:
    """The single token of writers before card://JAVA-625. It records no issuer, so it counts as the
    default server's, where every enrollment of those writers came from."""
    return config_dir() / "device-token"


def read_config(root: Path) -> dict:
    path = root / CONFIG
    if not path.is_file():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SyncError(f"{CONFIG} is not valid JSON ({exc})") from exc
    return config if isinstance(config, dict) else {}


def checked_project(project_id: object) -> str:
    if not isinstance(project_id, str) or not PROJECT_ID.fullmatch(project_id):
        raise SyncError(f"{project_id!r} is not a Fluxor project id (a UUID): check `projectId` in {CONFIG} "
                        "or `--project`; nothing was sent")
    return project_id


def normalize_server(url: str) -> str:
    """One spelling per server, so a token's issuer compares equal however the URL was typed."""
    parts = urllib.parse.urlsplit(url.strip())
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "",
                                    "")) if parts.scheme and parts.netloc else url.strip().rstrip("/")


def server_url(config: dict, arg: str | None = None) -> str:
    """The server a command talks to. Only a token that server issued is ever sent to it."""
    return normalize_server(arg or os.environ.get("FLUXOR_SERVER") or config.get("server") or DEFAULT_SERVER)


def enrollment_server(arg: str | None) -> str:
    """Where `init` enrolls: never the project file, which a branch can change (card://JAVA-625)."""
    return normalize_server(arg or os.environ.get("FLUXOR_SERVER") or DEFAULT_SERVER)


def cleartext_off_machine(server: str) -> str | None:
    """Why a token must not travel to `server`, or None. Plain HTTP only reaches this machine."""
    parts = urllib.parse.urlsplit(server)
    if parts.scheme == "https" and parts.hostname:
        return None
    if parts.scheme == "http" and parts.hostname:
        if parts.hostname == "localhost":
            return None
        try:
            if ipaddress.ip_address(parts.hostname).is_loopback:
                return None
        except ValueError:
            pass
        return f"{server} is plain HTTP off this machine: a device token travels only over https (or to localhost)"
    return f"{server} is not an https URL"


def read_tokens() -> dict[str, dict]:
    path = token_store()
    if not path.is_file():
        return {}
    try:
        tokens = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SyncError(f"{path} is not valid JSON ({exc}): delete it and enroll this machine again") from exc
    return {k: v for k, v in tokens.items() if isinstance(v, dict) and v.get("token")} \
        if isinstance(tokens, dict) else {}


def issuers() -> list[str]:
    """Every server this machine holds a token from."""
    found = set(read_tokens())
    if legacy_token_path().is_file():
        found.add(normalize_server(DEFAULT_SERVER))
    return sorted(found)


def token_for(server: str) -> str:
    """The token `server` issued to this machine. Never another server's: a project names its
    server, and a project is whatever the last branch checked out says."""
    server = normalize_server(server)
    entry = read_tokens().get(server)
    if entry:
        return entry["token"]
    if server == normalize_server(DEFAULT_SERVER) and legacy_token_path().is_file():
        return legacy_token_path().read_text(encoding="utf-8").strip()
    enroll = (f"enroll this machine there with that server's Fluxor MCP `harness.bootstrap`, then "
              f"`fluxor-sync init --server {server} --enroll CODE --project ID`")
    held = issuers()
    if not held:
        raise SyncError(f"no device token on this machine ({token_store()}): {enroll}")
    raise SyncError(f"this project asks {server}, and this machine's device token was issued by "
                    f"{', '.join(held)}. A token goes only to the server that issued it. If {server} is "
                    f"the Fluxor you use, {enroll}; if not, `.harness/fluxor.json` names the wrong server")


def store_token(server: str, enrolled: dict) -> str | None:
    """Keep `server`'s new token beside the other servers'; returns the device it replaced."""
    tokens = read_tokens()
    previous = tokens.get(server)
    replaced = (previous.get("name") or previous.get("deviceId") or "unnamed") if previous else None
    if server == normalize_server(DEFAULT_SERVER) and legacy_token_path().is_file():
        replaced = replaced or "the one enrolled before its name was recorded"
    tokens[server] = {"token": enrolled["deviceToken"], "deviceId": enrolled.get("deviceId"),
                      "name": enrolled.get("name")}
    write_secret(token_store(), dump_json(tokens).encode("utf-8"))
    if server == normalize_server(DEFAULT_SERVER) and legacy_token_path().is_file():
        legacy_token_path().unlink()
    return replaced


# ─── Writing ───────────────────────────────────────────────────────────────────────────────────────

def dump_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_atomic(path: Path, data: bytes, executable: bool | None = None) -> None:
    """Replace `path` in one rename, so a reader (this very script, when it updates itself) never
    sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        if os.name != "nt":
            if executable is not None:
                mode = 0o755 if executable else 0o644
            else:
                mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_secret(path: Path, data: bytes) -> None:
    """Replace `path` with a file only its owner can read, in a folder only its owner can enter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.parent.chmod(0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")  # created 0600
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def set_executable(path: Path, executable: bool) -> None:
    if os.name != "nt" and disk_executable(path) != executable:
        path.chmod(0o755 if executable else 0o644)


def prune_empty(path: Path, stop: Path) -> None:
    parent = path.parent
    while parent != stop and stop in parent.parents and not parent.is_symlink() and parent.is_dir() \
            and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent


def safe_path(root: Path, rel: str) -> Path:
    """A snapshot path, refused unless it stays inside the project."""
    parts = PurePosixPath(rel).parts
    if not rel or rel.startswith("/") or "\\" in rel or ".." in parts or (parts and ":" in parts[0]):
        raise SyncError(f"the snapshot lists a path outside the project: {rel!r}")
    return root / rel


# Why a path was left alone, worded so it names the path and never where a link points.
OUTSIDE = "resolves outside the project (a symlink leads out of it, or loops)"


def escapes(base: Path, path: Path) -> bool:
    """True unless `path`, every symlink on it followed, is `base` or inside it.

    card://JAVA-873: `safe_path` checks a path's text, and a symlink anywhere along it (committed, or
    the user's own) takes a read or a write wherever it points. So the deepest part of the path that
    exists is resolved strictly; what is left below it does not exist, so it holds no link. A path
    that cannot be resolved (a loop: `RuntimeError` up to Python 3.12, `OSError` from 3.13) escapes."""
    try:
        inside = base.resolve(strict=True)
        probe = path
        while not os.path.lexists(probe) and probe.parent != probe:
            probe = probe.parent
        real = probe.resolve(strict=True)
    except (OSError, RuntimeError):
        return True
    return real != inside and inside not in real.parents


def skipped(rel: str) -> None:
    """A path a print leaves out, named on stderr so the session's context stays the project's."""
    print(f"fluxor-sync: skipped {rel}: it {OUTSIDE}", file=sys.stderr)


def check_state(root: Path) -> None:
    """The writer's own state must be the project's before anything is read from it or written to it:
    with `.harness` elsewhere every managed path would be too."""
    for rel in (".harness", CONFIG, LOCK):
        if escapes(root, root / rel):
            raise SyncError(f"{rel} {OUTSIDE}; nothing was read or written. Make it a folder or file of "
                            "this project and run the command again")


# ─── HTTP ──────────────────────────────────────────────────────────────────────────────────────────

class NoRedirects(urllib.request.HTTPRedirectHandler):
    """urllib copies `Authorization` onto a redirect to any host, so following one would hand the
    token to whatever the issuer points at. Fluxor's sync API never redirects (card://JAVA-625)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        raise SyncError(f"Fluxor answered {req.full_url} with a redirect (HTTP {code}) to {newurl}; fluxor-sync "
                        "never follows one, so nothing was sent there and the harness on disk is unchanged")


OPENER = urllib.request.build_opener(NoRedirects)


def http(method: str, url: str, token: str | None = None, body: dict | None = None,
         etag: str | None = None, accept: str = "application/json") -> tuple[int, dict, bytes]:
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if etag:
        headers["If-None-Match"] = f'"{etag}"'
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with OPENER.open(request, timeout=TIMEOUT) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read() if exc.fp else b""
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise SyncError(f"could not reach Fluxor at {url} ({reason}); the harness on disk is unchanged") from exc


def explain(status: int, body: bytes, what: str) -> SyncError:
    try:
        detail = json.loads(body.decode("utf-8")).get("message", "")
    except (ValueError, AttributeError):
        detail = ""
    if status == 401:
        hint = ("this machine's device token is unknown or was revoked in Fluxor: enroll it again with the "
                "Fluxor MCP's `harness.bootstrap`")
    elif status == 404:
        hint = "not found for this device's account"
    else:
        hint = f"HTTP {status}"
    return SyncError(f"{what}: {hint}" + (f" ({detail})" if detail else ""))


def fetch_snapshot(server: str, token: str, project_id: str, etag: str | None) -> dict | None:
    """The snapshot, or None when the server answered 304 to `etag`."""
    project_id = checked_project(project_id)
    status, _, body = http("GET", f"{server}/fluxor/v1/sync/harness/projects/{project_id}/snapshot"
                           "?include=packs", token, etag=etag)
    if status == 304:
        return None
    if status != 200:
        raise explain(status, body, f"project {project_id}")
    snapshot = json.loads(body.decode("utf-8"))
    if snapshot.get("format") != FORMAT:
        raise SyncError(f"Fluxor serves snapshot format {snapshot.get('format')} and this writer reads "
                        f"format {FORMAT}: update fluxor-sync (download it again from the Fluxor MCP's "
                        "`harness.bootstrap`)")
    if snapshot_hash(snapshot["files"]) != snapshot["hash"]:
        raise SyncError("the snapshot's file list does not match its hash; nothing was written")
    return snapshot


def snapshot_hash(files: list[dict]) -> str:
    """The contract's hash: sha256 of the sorted `path<TAB>sha256<TAB>executable` lines."""
    lines = "".join(f"{f['path']}\t{f['sha256']}\t{'true' if f['executable'] else 'false'}\n"
                    for f in sorted(files, key=lambda f: f["path"]))
    return sha256_bytes(lines.encode("utf-8"))


class Blobs:
    """Skill files by sha256: the local cache first, the server only for what it lacks."""

    def __init__(self, server: str, token: str):
        self.server, self.token, self.downloaded = server, token, 0
        self.held: dict[str, bytes] = {}

    def prefetch(self, root: Path, files: list[dict]) -> None:
        """Fetch every blob the disk does not already hold, before anything is written: a download
        that fails then leaves the harness exactly as it was."""
        for f in files:
            if "content" not in f:
                target = safe_path(root, f["path"])
                if escapes(root, target):
                    continue  # never written (`apply` refuses it), so neither read nor fetched
                if not (target.is_file() and sha256_bytes(disk_bytes(target)) == f["sha256"]):
                    self.get(f["sha256"])

    def get(self, sha256: str) -> bytes:
        if sha256 in self.held:
            return self.held[sha256]
        cached = cache_dir() / "blobs" / sha256
        if cached.is_file():
            data = cached.read_bytes()
            if sha256_bytes(data) == sha256:
                self.held[sha256] = data
                return data
        status, _, body = http("GET", f"{self.server}/fluxor/v1/sync/harness/blobs/{sha256}", self.token,
                               accept="application/octet-stream")
        if status != 200:
            raise explain(status, body, f"blob {sha256}")
        if sha256_bytes(body) != sha256:
            raise SyncError(f"blob {sha256} arrived with different bytes; nothing was written")
        self.downloaded += 1
        self.held[sha256] = body
        try:
            write_atomic(cached, body)
        except OSError:
            pass  # a cache that can't be written costs a download next time, nothing else
        return body


# ─── Applying a snapshot ───────────────────────────────────────────────────────────────────────────

def merge_entries(document: dict, add: dict, drop: dict | None) -> bool:
    """Merge `add`'s `hooks.<event>` entries into `document`, after removing the ones a previous pull
    merged (`drop`). Every other key is left alone. True when `document` changed."""
    hooks = document.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SyncError("its `hooks` is not an object")
    before = json.dumps(document, sort_keys=True)
    for event, entries in (drop or {}).get("hooks", {}).items():
        if isinstance(hooks.get(event), list):
            hooks[event] = [e for e in hooks[event] if e not in entries]
            if not hooks[event]:
                del hooks[event]
    for event, entries in add.get("hooks", {}).items():
        current = hooks.setdefault(event, [])
        if not isinstance(current, list):
            raise SyncError(f"its `hooks.{event}` is not a list")
        current.extend(e for e in entries if e not in current)
    return json.dumps(document, sort_keys=True) != before


class Report:
    def __init__(self):
        self.written, self.removed, self.kept = 0, 0, []

    def keep(self, rel: str, why: str) -> None:
        if why == OUTSIDE:
            self.refuse(rel)
        else:
            self.kept.append(f"kept local edit: {rel} ({why}); fluxor-sync pull --force takes Fluxor's")

    def refuse(self, rel: str) -> None:
        """A path that escapes the project: left alone, `--force` included (card://JAVA-873)."""
        line = f"left alone: {rel} {OUTSIDE}, so nothing was read or written there, --force included"
        if line not in self.kept:
            self.kept.append(line)


def apply(root: Path, snapshot: dict, lock: dict, blobs: Blobs, force: bool,
          hide: set[str] = frozenset()) -> tuple[dict, Report]:
    """Write the snapshot's files; returns the new lock's `files` and what happened. `hide` are the
    `AGENTS.md` block lines of wired hooks' fallbacks, left out of the block written."""
    report = Report()
    blobs.prefetch(root, snapshot["files"])
    old = lock.get("files", {}) if lock.get("source", {}).get("kind") == "fluxor" else {}
    edited = dict(edited_files(root, {"files": old}))
    files: dict[str, dict] = {}
    for f in snapshot["files"]:
        rel, mode = f["path"], f.get("mode", "file")
        target = safe_path(root, rel)
        if escapes(root, target):
            report.refuse(rel)
            if rel in old:
                files[rel] = old[rel]  # still the writer's: the next pull retries it
            continue
        entry = {"sha256": f["sha256"], "executable": bool(f["executable"]), "atom": f.get("item"), "mode": mode}
        files[rel] = entry
        if mode == "json-merge":
            merge_file(target, rel, f["content"], old.get(rel, {}).get("merged"), entry, report)
        elif mode == "block":
            # The lock keeps the snapshot's block, so approving or revoking a hook re-renders it offline.
            block = effective_block(f["content"], hide)
            entry.update(sha256=sha256_bytes(block.encode("utf-8")), block=f["content"])
            write_block(target, rel, block, edited.get(rel), force, report)
        else:
            write_file(target, rel, f, rel in old, edited.get(rel), force, blobs, report)
    for rel in sorted(set(old) - set(files)):
        if rel == WRITER:
            files[rel] = old[rel]  # the writer the session start runs stays managed, whatever a snapshot lists
            continue
        if old[rel].get("mode", "file") in ("block", "json-merge"):
            continue  # wiring every snapshot carries; never removed from a user's file
        target = safe_path(root, rel)
        if escapes(root, target):
            report.refuse(rel)
            files[rel] = old[rel]
            continue
        if rel in edited and not force:
            if edited[rel] != "deleted":
                report.keep(rel, "Fluxor dropped it")
            continue
        if HOOK_SCRIPT.fullmatch(rel) and target.is_file() and not tombstone_expired(old[rel]):
            files[rel] = tombstone(target, rel, old[rel])
            continue
        if target.is_file():
            target.unlink()
            report.removed += 1
            prune_empty(target, root)
    return files, report


def tombstone(target: Path, rel: str, entry: dict) -> dict:
    """A dropped hook script becomes a quiet no-op instead of disappearing (JAVA-775): Claude Code
    keeps the hooks a session started with, so a window opened before this sync would otherwise
    print "No such file or directory" on every tool call until it restarts."""
    if "tombstoneSince" in entry:
        return entry
    data = (TOMBSTONE_PS1 if rel.endswith(".ps1") else TOMBSTONE_SH).encode("utf-8")
    write_atomic(target, data, True)  # a rename: a write in place goes through a link at the end
    return {"sha256": sha256_bytes(data), "executable": True, "atom": entry.get("atom"), "mode": "file",
            "tombstoneSince": int(time.time())}


def tombstone_expired(entry: dict) -> bool:
    since = entry.get("tombstoneSince")
    return since is not None and time.time() - since >= TOMBSTONE_DAYS * 86400


def write_file(target: Path, rel: str, f: dict, managed: bool, edit: str | None, force: bool,
               blobs: Blobs, report: Report) -> None:
    exists = target.is_file()
    current = disk_bytes(target) if exists else None
    if current is not None and sha256_bytes(current) == f["sha256"]:
        set_executable(target, bool(f["executable"]))
        return
    if not force and exists:
        if edit and edit != "deleted":
            report.keep(rel, edit)
            return
        if not managed:
            report.keep(rel, "a file Fluxor did not write is in the way")
            return
    data = f["content"].encode("utf-8") if "content" in f else blobs.get(f["sha256"])
    if sha256_bytes(data) != f["sha256"]:
        raise SyncError(f"{rel}: the snapshot's content does not match its sha256; nothing more was written")
    write_atomic(target, data, bool(f["executable"]))
    report.written += 1


def write_block(target: Path, rel: str, block: str, edit: str | None, force: bool, report: Report) -> None:
    text = disk_bytes(target).decode("utf-8") if target.is_file() else ""
    current = managed_block(text)
    if current == block:
        return
    if edit == "content differs" and not force:
        report.keep(rel, "its Fluxor block was edited")
        return
    if current is None:
        updated = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block
    else:
        start = text.find(BLOCK_BEGIN)
        end = text.find(BLOCK_END, start) + len(BLOCK_END)
        updated = text[:start] + block.rstrip("\n") + text[end:]
        if not updated.endswith("\n"):
            updated += "\n"
    write_atomic(target, updated.encode("utf-8"))
    report.written += 1


def merge_file(target: Path, rel: str, content: str, merged_before: dict | None, entry: dict,
               report: Report) -> None:
    add = json.loads(content)
    entry["merged"] = add
    document = {}
    if target.is_file():
        try:
            document = json.loads(disk_bytes(target).decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            report.kept.append(f"left alone: {rel} is not valid JSON, so the session-start pull is not wired "
                               "there; fix it and pull again")
            entry["merged"] = merged_before
            return
        if not isinstance(document, dict):
            report.kept.append(f"left alone: {rel} is not a JSON object")
            entry["merged"] = merged_before
            return
    try:
        changed = merge_entries(document, add, merged_before)
    except SyncError as exc:
        report.kept.append(f"left alone: {rel}: {exc}")
        entry["merged"] = merged_before
        return
    if changed or not target.is_file():
        write_atomic(target, dump_json(document).encode("utf-8"))
        report.written += 1


def wire_skills(root: Path, lock: dict, report: Report) -> dict:
    """`.claude/skills` and `.agents/skills` point at `.harness/skills`: a relative symlink, or a
    managed copy where the OS refuses one or the folder already holds the user's own skills.
    Returns the copies made, `{folder: {path: sha256}}`, for the lock."""
    source = root / SKILLS
    previous = lock.get("mirrors", {}) if isinstance(lock.get("mirrors"), dict) else {}
    mirrors = {}
    if not source.is_dir():
        return mirrors
    for link in SKILL_LINKS:
        target = root / link
        if target.is_symlink() and not escapes(root, target):
            if target.resolve() != source.resolve():
                report.kept.append(f"left alone: {link} is a symlink to somewhere else; skills are in {SKILLS}")
            continue
        if escapes(root, target):
            report.refuse(link)
            if link in previous:
                mirrors[link] = previous[link]
            continue
        if not target.exists() and link not in previous:
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.symlink(os.path.relpath(source, target.parent), target, target_is_directory=True)
                continue
            except (OSError, NotImplementedError):
                pass  # Windows without developer mode: a managed copy instead
        mirrors[link] = mirror(root, source, target, previous.get(link, {}), report)
    return mirrors


def mirror(root: Path, source: Path, target: Path, previous: dict, report: Report) -> dict:
    copied = {}
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        rel = path.relative_to(source).as_posix()
        dest = target / rel
        refused = next((p for p in (path, dest) if escapes(root, p)), None)
        if refused is not None:
            report.refuse(refused.relative_to(root).as_posix())
            if rel in previous:
                copied[rel] = previous[rel]
            continue
        data = disk_bytes(path)
        copied[rel] = sha256_bytes(data)
        if dest.is_file() and disk_bytes(dest) == data:
            continue
        if dest.is_file() and rel not in previous:
            report.keep(f"{target.name}/{rel}", "a file Fluxor did not write is in the way")
            continue
        write_atomic(dest, data, disk_executable(path))
        report.written += 1
    for rel, sha in previous.items():
        dest = target / rel
        if rel not in copied and escapes(root, dest):
            report.refuse(dest.relative_to(root).as_posix())
            copied[rel] = sha
            continue
        if rel not in copied and dest.is_file() and sha256_bytes(disk_bytes(dest)) == sha:
            dest.unlink()
            report.removed += 1
            prune_empty(dest, target)
    return copied


def lock_document(snapshot: dict, files: dict, mirrors: dict) -> dict:
    by_item: dict[str, list[str]] = {}
    for rel, entry in sorted(files.items()):
        if entry.get("atom"):
            by_item.setdefault(entry["atom"], []).append(f"{rel}\t{entry['sha256']}\n")
    atoms = {item: {"kind": "fluxor", "hash": sha256_bytes("".join(lines).encode("utf-8"))}
             for item, lines in sorted(by_item.items())}
    document = {"schemaVersion": 1, "snapshot": snapshot["hash"], "atoms": atoms, "files": files,
                "source": {"kind": "fluxor", "projectId": snapshot["projectId"],
                           "revision": snapshot["revision"], "hash": snapshot["hash"]}}
    if mirrors:
        document["mirrors"] = mirrors
    return document


# ─── Hooks: wired only once the user consented to their exact hash (ADR 0020) ────────────────────

def effective_block(block: str, hide: set[str]) -> str:
    """The managed block without the `@` lines in `hide`: a wired hook's fallback is not also read."""
    return "".join(line for line in block.splitlines(True) if line.rstrip("\n") not in hide)


def snapshot_hooks(snapshot: dict) -> dict[str, tuple[str, str, dict]]:
    """key -> (manifest path, sha256, manifest) for each hook a snapshot carries."""
    hooks = {}
    for f in snapshot["files"]:
        if f.get("mode") == "hook" and "content" in f:
            manifest = parse_manifest(f["content"])
            if manifest:
                hooks[manifest["key"]] = (f["path"], f["sha256"], manifest)
    return hooks


def installed_hooks(root: Path, lock: dict) -> dict[str, tuple[str, str, dict]]:
    """The same for what is on disk, counting only a manifest whose bytes still match the lock: an
    edited one is not what the user consented to, so it is never wired (the pull reports the edit)."""
    hooks = {}
    for rel, entry in sorted(lock.get("files", {}).items()):
        if entry.get("mode") != "hook":
            continue
        path = root / rel
        if escapes(root, path) or not path.is_file() or sha256_bytes(disk_bytes(path)) != entry.get("sha256"):
            continue
        manifest = parse_manifest(disk_bytes(path).decode("utf-8", errors="replace"))
        if manifest:
            hooks[manifest["key"]] = (rel, entry["sha256"], manifest)
    return hooks


def parse_manifest(text: str) -> dict | None:
    try:
        manifest = json.loads(text)
    except ValueError:
        return None
    if not isinstance(manifest, dict) or not HOOK_KEY.fullmatch(str(manifest.get("key", ""))):
        return None
    return manifest


def hook_scripts(manifest: dict) -> dict[str, str]:
    """`{"sh": path, "ps1": path}`, keeping only paths that are safe to put in a shell command."""
    scripts = manifest.get("scripts") if isinstance(manifest.get("scripts"), dict) else {}
    paths = {}
    for kind in ("sh", "ps1"):
        path = (scripts.get(kind) or {}).get("path") if isinstance(scripts.get(kind), dict) else None
        if isinstance(path, str) and HOOK_SCRIPT.fullmatch(path) and path.endswith("." + kind):
            paths[kind] = path
    return paths


def edited_scripts(root: Path, manifest: dict) -> list[str]:
    """The scripts a hook would run that are not on disk with the sha256 its manifest names. The
    approval is of the manifest, so it covers these bytes only: a hook with any such script runs code
    nobody consented to, and is not wired (card://JAVA-670). No sha256 to check against counts too."""
    scripts = manifest.get("scripts") if isinstance(manifest.get("scripts"), dict) else {}
    edited = []
    for kind, rel in hook_scripts(manifest).items():
        expected = scripts[kind].get("sha256")
        path = root / rel
        # A script linked outside is run through the link: the hash proved nothing about it.
        if not (isinstance(expected, str) and SHA256.fullmatch(expected)) or escapes(root, path) \
                or not path.is_file() or sha256_bytes(disk_bytes(path)) != expected:
            edited.append(rel)
    return edited


def script_edited(key: str, scripts: list[str]) -> str:
    return (f"hook {key}: script {', '.join(scripts)} edited locally, unwired until fluxor-sync pull --force "
            "restores Fluxor's (the approval stands)")


def powershell(path: str) -> str:
    return f'powershell -NoProfile -ExecutionPolicy Bypass -File "{path}"'


def hook_handler(client: str, manifest: dict) -> dict | None:
    """The command entry that runs a hook in `client`, or None when it has no script to run."""
    if manifest.get("dispatch"):
        # The packs' hooks for one event, run by this writer: the entry names no pack (card://JAVA-286).
        if client != "claude":
            return None
        return {"type": "command", "command": f'{PYTHON} "$CLAUDE_PROJECT_DIR/{WRITER}" pack-hook {manifest["event"]}',
                "timeout": PACK_HOOK_TIMEOUT}
    scripts = hook_scripts(manifest)
    if client == "claude":
        if "sh" in scripts:
            command = f'"$CLAUDE_PROJECT_DIR"/{scripts["sh"]}'
        elif "ps1" in scripts:
            command = powershell(f'$CLAUDE_PROJECT_DIR/{scripts["ps1"]}')
        else:
            return None
        handler = {"type": "command", "command": command}
    else:
        # Codex runs a hook from the session's folder, like the pull entry, and has a Windows override.
        if not scripts:
            return None
        handler = {"type": "command", "command": scripts["sh"] if "sh" in scripts else powershell(scripts["ps1"])}
        if "sh" in scripts and "ps1" in scripts:
            handler["commandWindows"] = powershell(scripts["ps1"])
    timeout = manifest.get("timeoutMs")
    if isinstance(timeout, int) and timeout > 0:
        handler["timeout"] = -(-timeout // 1000)
    return handler


def hook_matcher(client: str, manifest: dict) -> str | None:
    if manifest.get("event") == "notification":
        kinds = manifest.get("notifications") or []
        names = [NOTIFICATIONS[k] for k in kinds if k in NOTIFICATIONS] if isinstance(kinds, list) else []
        return "|".join(names) or None
    if manifest.get("event") in ("preTool", "postTool", "postToolFailure"):
        tools = manifest.get("tools", "any")
        tools = [tools] if isinstance(tools, str) else tools if isinstance(tools, list) else []
        if "any" in tools:
            return None
        return "|".join(TOOL_MATCHERS[client][t] for t in tools if t in TOOL_MATCHERS[client]) or None
    return None


def hook_clients(manifest: dict) -> list[str]:
    """The clients that can run this hook's event."""
    event = manifest.get("event")
    if event == STATUS_LINE:
        return ["claude"] if hook_handler("claude", manifest) else []
    return [c for c in EVENTS if event in EVENTS[c] and hook_handler(c, manifest)]


def desired_wiring(hooks: dict[str, dict]) -> dict:
    """What the wired hooks add to each client's file: `{client: {"hooks": {Event: [entry]},
    "statusLine": [command]}}`, one entry per hook, in key order."""
    wiring: dict = {}
    for key in sorted(hooks):
        manifest = hooks[key]
        for client in hook_clients(manifest):
            handler = hook_handler(client, manifest)
            target = wiring.setdefault(client, {"hooks": {}})
            if manifest["event"] == STATUS_LINE:
                target.setdefault("statusLine", []).append(handler["command"])
                continue
            entry: dict = {}
            matcher = hook_matcher(client, manifest)
            if matcher:
                entry["matcher"] = matcher
            entry["hooks"] = [handler]
            target["hooks"].setdefault(EVENTS[client][manifest["event"]], []).append(entry)
    return wiring


def wire_status_line(document: dict, ours: list[str], before: dict | None) -> dict | None:
    """Point `statusLine` at ours, wrapping the user's own instead of replacing it, and restore the
    user's when ours goes. Returns what to remember: what was written, and what it wraps."""
    current = document.get(STATUS_LINE)
    if before and current != before.get("written"):
        before = None  # someone changed it since: theirs now, and the base to wrap
    base = before.get("wrapped") if before else current
    if not ours:
        if before:
            if base is None:
                document.pop(STATUS_LINE, None)
            else:
                document[STATUS_LINE] = base
        return None
    command = ours[0] if base is None and len(ours) == 1 else STATUS_LINE_WRAPPER
    written = {"type": "command", "command": command}
    document[STATUS_LINE] = written
    return {"written": written, "wrapped": base, "commands": ours}


def wire_hooks(root: Path, before: dict, hooks: dict[str, dict], report: Report) -> dict:
    """Bring each client's file to the wiring `hooks` need, removing exactly what the last wiring
    added (`before`, from the lock) and leaving every other key alone. Returns the new record."""
    desired = desired_wiring(hooks)
    record = {}
    for client, rel in client_files(root).items():
        want, had = desired.get(client, {}), before.get(client) or {}
        moved_from = had.get("file", CLIENT_FILES[client])
        if had and moved_from != rel:
            # card://JAVA-2010: the wiring a pull put in the committed file moves to this machine's.
            unwire_from(root, client, moved_from, had, report)
            had = {}
        if not want and not had:
            continue
        target = safe_path(root, rel)
        if escapes(root, target):
            report.refuse(rel)
            if had:
                record[client] = had
            continue
        document = {}
        if target.is_file():
            try:
                document = json.loads(disk_bytes(target).decode("utf-8") or "{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                document = None
            if not isinstance(document, dict):
                report.kept.append(f"left alone: {rel} is not a JSON object, so no hook is wired there")
                if had:
                    record[client] = had
                continue
        snapshot, had_hooks = json.dumps(document, sort_keys=True), "hooks" in document
        try:
            merge_entries(document, {"hooks": want.get("hooks", {})}, {"hooks": had.get("hooks", {})})
        except SyncError as exc:
            report.kept.append(f"left alone: {rel}: {exc}")
            if had:
                record[client] = had
            continue
        if not document["hooks"] and not had_hooks:
            del document["hooks"]
        status_line = wire_status_line(document, want.get("statusLine", []), had.get("statusLine")) \
            if client == "claude" else None
        if json.dumps(document, sort_keys=True) != snapshot:
            write_atomic(target, dump_json(document).encode("utf-8"))
            report.written += 1
        entry = {"hooks": want["hooks"]} if want.get("hooks") else {}
        if status_line:
            entry["statusLine"] = status_line
        if entry and rel != CLIENT_FILES[client]:
            entry["file"] = rel
        if entry:
            record[client] = entry
    return record


def unwire_from(root: Path, client: str, rel: str, had: dict, report: Report) -> None:
    """Take out of `rel` exactly what an earlier wiring merged there (`had`), and the status line
    back to the user's own, leaving every other key alone."""
    target = safe_path(root, rel)
    if escapes(root, target) or not target.is_file():
        return
    try:
        document = json.loads(disk_bytes(target).decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return
    if not isinstance(document, dict):
        return
    before = json.dumps(document, sort_keys=True)
    try:
        merge_entries(document, {"hooks": {}}, {"hooks": had.get("hooks", {})})
    except SyncError:
        return
    if not document.get("hooks"):
        document.pop("hooks", None)
    if client == "claude":
        wire_status_line(document, [], had.get("statusLine"))
    if json.dumps(document, sort_keys=True) != before:
        write_atomic(target, dump_json(document).encode("utf-8"))
        report.written += 1
        report.kept.append(f"moved this machine's hook wiring out of {rel}: it is never committed")


def local_storage(root: Path) -> bool:
    """Whether the harness is kept out of git (card://JAVA-2010): what `init --storage local` records."""
    return read_config(root).get("storage") == "local"


def client_files(root: Path) -> dict[str, str]:
    return LOCAL_CLIENT_FILES if local_storage(root) else CLIENT_FILES


def agents_list(block: str) -> str:
    """`.harness/agents.md`: the block's lines without its markers, each import made relative to
    `.harness/`, since an `@` resolves from the file that holds it."""
    lines = [line for line in block.splitlines(True) if line.strip() not in (BLOCK_BEGIN, BLOCK_END)]
    body = "".join(("@" + line[len("@.harness/"):]) if line.startswith("@.harness/") else line for line in lines)
    return body.lstrip("\n")


def exclude_local(root: Path, lock: dict, report: Report) -> None:
    """Keep this machine's pulled harness out of git: a managed block in the clone's
    `.git/info/exclude` (shared by its worktrees, never committed) naming `.harness/` but its
    `fluxor.json`, the per-machine settings and every managed file outside `.harness/` that is not a
    committed bridge. Outside git, or with the harness committed, it does nothing."""
    git = shutil.which("git")
    if not local_storage(root) or not git:
        return
    try:
        # Windows' git refuses a clone it reaches through WSL's share ("dubious ownership"), and the
        # harness then sat untracked in git status. This read only locates `.git`, so it trusts the folder.
        run = subprocess.run([git, "-c", "safe.directory=*", "-C", str(root), "rev-parse", "--git-common-dir",
                              "--show-prefix"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return
    lines = run.stdout.splitlines()
    if run.returncode != 0 or not lines:
        return
    common = Path(lines[0]) if Path(lines[0]).is_absolute() else (root / lines[0]).resolve()
    prefix = lines[1] if len(lines) > 1 else ""
    outside = sorted(p for p in lock.get("files", {}) if not p.startswith(".harness/") and p not in BRIDGES)
    links = [link for link in SKILL_LINKS if (root / link).is_symlink() or link in lock.get("mirrors", {})]
    paths = [f"/{prefix}.harness/*", f"!/{prefix}.harness/fluxor.json", f"/{prefix}.claude/settings.local.json",
             *(f"/{prefix}{p}" for p in outside + links)]
    block = "\n".join([EXCLUDE_BEGIN, *dict.fromkeys(paths), EXCLUDE_END]) + "\n"
    target = common / "info" / "exclude"
    text = target.read_text(encoding="utf-8") if target.is_file() else ""
    start, end = text.find(EXCLUDE_BEGIN), text.find(EXCLUDE_END)
    if start >= 0 and end > start:
        updated = text[:start] + block + text[end + len(EXCLUDE_END):].lstrip("\n")
    else:
        updated = (text.rstrip("\n") + "\n" if text.strip() else "") + block
    if updated != text:
        target.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(target, updated.encode("utf-8"))


def wsl_share(path: str) -> tuple[str, str] | None:
    """(distro, Linux path) of a path Windows reaches through WSL's share, `\\\\wsl.localhost\\<distro>\\...`."""
    match = re.match(r"^\\\\wsl(?:\.localhost|\$)\\([^\\]+)(.*)$", path, re.IGNORECASE)
    return (match.group(1), match.group(2).replace("\\", "/") or "/") if match else None


def wsl_modes(root: Path, lock: dict) -> None:
    """Windows writes a WSL tree through a share that keeps no Linux mode, so every pulled script landed
    non-executable for WSL's own tools. The lock knows which ones are: WSL itself sets them."""
    where = wsl_share(str(root)) if os.name == "nt" else None
    scripts = sorted(p for p, f in lock.get("files", {}).items()
                     if isinstance(f, dict) and f.get("executable") and (root / p).is_file())
    if not where or not scripts:
        return
    try:
        subprocess.run(["wsl.exe", "-d", where[0], "--cd", where[1], "--", "chmod", "755", "--", *scripts],
                       capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        pass


def keep_machine_copy(root: Path) -> None:
    """This machine's copy of the writer, which the session start runs where the project has none
    yet: a fresh clone or worktree of an enrolled machine pulls at its first session (card://JAVA-2010)."""
    writer = root / WRITER
    source = writer if writer.is_file() and not escapes(root, writer) else Path(__file__).resolve()
    data = disk_bytes(source)
    target = config_dir() / "bin" / "fluxor-sync.py"
    if not target.is_file() or disk_bytes(target) != data:
        target.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(target, data, True)


def render_block(root: Path, lock: dict, hide: set[str], report: Report) -> None:
    """Re-render `AGENTS.md`'s block from the snapshot's, without the wired hooks' fallbacks."""
    entry = lock.get("files", {}).get("AGENTS.md")
    if not entry or entry.get("mode") != "block" or "block" not in entry:
        return
    block = effective_block(entry["block"], hide)
    if local_storage(root):
        # card://JAVA-2010: the committed block stays the same on every machine; the list moves here.
        listing = root / AGENTS_LIST
        if escapes(root, listing):
            report.refuse(AGENTS_LIST)
        elif not listing.is_file() or disk_bytes(listing).decode("utf-8") != agents_list(block):
            write_atomic(listing, agents_list(block).encode("utf-8"))
            report.written += 1
        block = STABLE_BLOCK
    target = root / "AGENTS.md"
    if escapes(root, target):
        report.refuse("AGENTS.md")
        return
    current = managed_block(disk_bytes(target).decode("utf-8")) if target.is_file() else None
    if current == block:
        entry["sha256"] = sha256_bytes(block.encode("utf-8"))
        return
    if current is not None and sha256_bytes(current.encode("utf-8")) != entry["sha256"]:
        report.keep("AGENTS.md", "its Fluxor block was edited, so hook fallbacks there were not updated")
        return
    write_block(target, "AGENTS.md", block, None, False, report)
    entry["sha256"] = sha256_bytes(block.encode("utf-8"))


def reconcile(root: Path, lock: dict, report: Report) -> dict[str, dict]:
    """Wire exactly the approved hooks whose manifest on disk still has the approved hash and whose
    scripts still have the manifest's, and keep the fallback of every other one in the block. Returns
    the wired hooks."""
    installed = installed_hooks(root, lock)
    approved = {a.get("key"): a.get("sha256") for a in lock.get("approvedHooks", []) if isinstance(a, dict)}
    wired = {}
    for key, (_, sha, manifest) in installed.items():
        # A hook no client can run stays unwired, so its fallback keeps standing in for it.
        if approved.get(key) != sha or not hook_clients(manifest):
            continue
        edited = edited_scripts(root, manifest)
        if edited:
            report.kept.append(script_edited(key, edited))
        else:
            wired[key] = manifest
    wiring = wire_hooks(root, lock.get("hookWiring") or {}, {**wired, **pack_dispatchers(root)}, report)
    lock.pop("hookWiring", None)
    if wiring:
        lock["hookWiring"] = wiring
    render_block(root, lock, fallback_lines(wired), report)
    return wired


def fallback_lines(hooks: dict[str, dict]) -> set[str]:
    return {f"@{m['fallback']}" for m in hooks.values() if isinstance(m.get("fallback"), str)}


def what_changed(old: dict | None, new: dict) -> str:
    if old is None:
        return "its manifest"
    fields = [k for k in ("event", "tools", "notifications", "timeoutMs", "fallback") if old.get(k) != new.get(k)]
    old_scripts, new_scripts = old.get("scripts") or {}, new.get("scripts") or {}
    fields += [f"script {kind}" for kind in sorted(set(old_scripts) | set(new_scripts))
               if old_scripts.get(kind) != new_scripts.get(kind)]
    return ", ".join(fields) or "its description"


def describe_hook(manifest: dict) -> str:
    event = manifest.get("event")
    when = "draws Claude Code's status line" if event == STATUS_LINE else f"runs on {event}"
    tools = manifest.get("tools")
    if event in ("preTool", "postTool", "postToolFailure") and tools not in (None, "any", ["any"]):
        when += f" ({tools if isinstance(tools, str) else ', '.join(tools)} tools)"
    clients = " and ".join(CLIENT_NAMES[c] for c in hook_clients(manifest)) or "no client"
    scripts = ", ".join(hook_scripts(manifest).values())
    title = manifest.get("title") or manifest["key"]
    description = f": {manifest['description']}" if manifest.get("description") else ""
    return f"- {manifest['key']} ({title}){description}. It {when}, in {clients}: {scripts}"


def always_directives(root: Path) -> list[str]:
    """The `@` imports of `AGENTS.md`'s managed block: what Claude Code expands and Codex does not."""
    agents = root / "AGENTS.md"
    if escapes(root, agents):
        return []
    block = managed_block(disk_bytes(agents).decode("utf-8")) if agents.is_file() else None
    imports = [line[1:].strip() for line in (block or "").splitlines() if line.startswith("@")]
    listing = root / AGENTS_LIST
    if imports == [AGENTS_LIST] and listing.is_file() and not escapes(root, listing):
        # card://JAVA-2010: this machine's list, its imports relative to `.harness/`.
        text = disk_bytes(listing).decode("utf-8")
        return [".harness/" + line[1:].strip() for line in text.splitlines() if line.startswith("@")]
    return imports


def print_directives(root: Path) -> None:
    if escapes(root, root / "AGENTS.md"):
        skipped("AGENTS.md")
    for rel in always_directives(root):
        # The block can be edited by hand: an absolute or `..` import would print a file from
        # outside the project into the session's context, and so would a link (card://JAVA-873).
        try:
            path = safe_path(root, rel)
        except SyncError:
            print(f"fluxor-sync: skipped an import outside the project: {rel!r}", file=sys.stderr)
            continue
        if escapes(root, path):
            skipped(rel)
        elif path.is_file():
            print(f"\n<!-- {rel} -->\n{disk_bytes(path).decode('utf-8').rstrip()}\n")


# ─── Packs: a person's, delivered without a committed file naming them (card://JAVA-286) ──────────

def pack_of(rel: str) -> str | None:
    """The pack a snapshot path belongs to, or None for the rest of the harness."""
    if not rel.startswith(PACKS + "/"):
        return None
    pack_id = rel[len(PACKS) + 1:].split("/", 1)[0]
    if not PACK_ID.fullmatch(pack_id) or "/" not in rel[len(PACKS) + 1:]:
        raise SyncError(f"the snapshot lists a pack path that is not a pack's: {rel!r}")
    return pack_id


def pack_lock_path(root: Path, pack_id: str) -> Path:
    return root / PACKS / pack_id / PACK_LOCK


def synced_packs(root: Path) -> dict[str, dict]:
    """pack id -> lock, for every pack a pull wrote here."""
    folder = root / PACKS
    packs = {}
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            # A lock read through a link would be a stranger's file deciding what is managed here.
            lock = read_lock(path / PACK_LOCK) if path.is_dir() and PACK_ID.fullmatch(path.name) \
                and not escapes(root, path / PACK_LOCK) else {}
            if lock.get("source", {}).get("kind") == "fluxor" and lock["source"].get("pack") == path.name:
                packs[path.name] = lock
    return packs


def managed(lock: dict) -> dict:
    """The lock's files the writer wrote: one it found already there (adopted) stays the person's."""
    return {rel: entry for rel, entry in lock.get("files", {}).items() if not entry.get("adopted")}


def merge_report(report: Report, other: Report) -> None:
    report.written += other.written
    report.removed += other.removed
    report.kept += other.kept


def apply_packs(root: Path, files: list[dict], blobs: Blobs, force: bool, report: Report) -> None:
    """Write each pack the snapshot carries, under its own lock, and remove the ones it dropped."""
    incoming: dict[str, list[dict]] = {}
    for f in files:
        incoming.setdefault(pack_of(f["path"]), []).append(f)
    synced = synced_packs(root)
    for pack_id in sorted(set(incoming) | set(synced)):
        if pack_id in incoming:
            write_pack(root, pack_id, incoming[pack_id], synced.get(pack_id, {}), blobs, force, report)
        else:
            drop_pack(root, pack_id, synced[pack_id], force, report)


def write_pack(root: Path, pack_id: str, files: list[dict], lock: dict, blobs: Blobs, force: bool,
               report: Report) -> None:
    owned = managed(lock)
    adopted = {rel for rel in lock.get("files", {}) if rel not in owned}
    found = {f["path"] for f in files if f["path"] not in owned and safe_path(root, f["path"]).is_file()}
    written, sub = apply(root, {"files": files}, {"source": {"kind": "fluxor"}, "files": owned}, blobs, force)
    merge_report(report, sub)
    for rel in (adopted | found) & set(written):
        written[rel]["adopted"] = True
    incoming = {key: sha for key, (_, sha, _) in snapshot_hooks({"files": files}).items()}
    approvals = [a for a in lock.get("approvedHooks", []) if isinstance(a, dict)
                 and incoming.get(a.get("key")) == a.get("sha256")]
    for a in lock.get("approvedHooks", []):
        if isinstance(a, dict) and a not in approvals and a.get("key") in incoming:
            report.kept.append(f"hook {pack_id}:{a['key']} changed: it is unwired until the user consents again. "
                               f"Ask them, and on a yes run `fluxor-sync approve --consented {pack_id}:{a['key']}`")
    pending = sorted(set(incoming) - {a["key"] for a in lock.get("approvedHooks", []) if isinstance(a, dict)})
    if pending:
        report.kept.append("hook(s) waiting for the user's consent: "
                           + ", ".join(f"{pack_id}:{k}" for k in pending) + " (`fluxor-sync approve` lists what to ask)")
    document = {"schemaVersion": 1, "source": {"kind": "fluxor", "pack": pack_id}, "files": written}
    if approvals:
        document["approvedHooks"] = approvals
    for path, data in ((root / PACKS / pack_id / PACK_IGNORE, PACK_IGNORE_TEXT),
                       (pack_lock_path(root, pack_id), dump_json(document))):
        if escapes(root, path):
            report.refuse(path.relative_to(root).as_posix())
        else:
            write_atomic(path, data.encode("utf-8"))


def drop_pack(root: Path, pack_id: str, lock: dict, force: bool, report: Report) -> None:
    """Remove what the writer wrote of a pack Fluxor no longer delivers; leave the person's own files."""
    owned = managed(lock)
    edited = dict(edited_files(root, {"files": owned}))
    for rel in sorted(owned):
        target = safe_path(root, rel)
        if escapes(root, target):
            report.refuse(rel)
            continue
        if rel in edited and edited[rel] != "deleted" and not force:
            report.keep(rel, "Fluxor dropped its pack")
            continue
        if target.is_file():
            target.unlink()
            report.removed += 1
            prune_empty(target, root)
    for lock_file in (pack_lock_path(root, pack_id), root / PACKS / pack_id / PACK_IGNORE):
        if escapes(root, lock_file):
            report.refuse(lock_file.relative_to(root).as_posix())
        elif lock_file.is_file():
            lock_file.unlink()
            prune_empty(lock_file, root)
    folder = root / PACKS / pack_id
    if (folder / "private").exists():
        report.kept.append(f"pack {pack_id} is no longer in Fluxor; its private/ folder (the verbatim answers) is "
                           f"left here: `render_pack.py erase {pack_id} --yes` (ceet-core) erases the pack")
    elif folder.is_dir():
        report.kept.append(f"pack {pack_id} is no longer in Fluxor; the files Fluxor did not write are left in "
                           f"{PACKS}/{pack_id}/")


def pack_edits(root: Path) -> list[tuple[str, str]]:
    return [edit for lock in synced_packs(root).values() for edit in edited_files(root, {"files": managed(lock)})]


def print_packs(root: Path) -> None:
    """Each synced pack's always-on core, for the session's context: never an `AGENTS.md` line."""
    for pack_id, lock in synced_packs(root).items():
        rel = f"{PACKS}/{pack_id}/core.md"
        path = root / rel
        if rel in lock.get("files", {}) and escapes(root, path):
            skipped(rel)
        elif rel in lock.get("files", {}) and path.is_file():
            print(f"\n<!-- {rel} -->\n{disk_bytes(path).decode('utf-8').rstrip()}\n")


def pack_approvals(lock: dict) -> dict[str, str]:
    return {a.get("key"): a.get("sha256") for a in lock.get("approvedHooks", []) if isinstance(a, dict)}


def approved_pack_hooks(root: Path):
    """(pack id, manifest) for every pack hook whose manifest on disk is the one the user approved."""
    for pack_id, lock in synced_packs(root).items():
        approved = pack_approvals(lock)
        for key, (_, sha, manifest) in installed_hooks(root, lock).items():
            if approved.get(key) == sha and manifest.get("event") in EVENTS["claude"]:
                yield pack_id, manifest


def pack_dispatchers(root: Path) -> dict[str, dict]:
    """One wiring entry per event the approved pack hooks run on, naming no pack: `pack-hook <event>`."""
    events: dict[str, set] = {}
    for _, manifest in approved_pack_hooks(root):
        tools = manifest.get("tools", "any")
        events.setdefault(manifest["event"], set()).update([tools] if isinstance(tools, str) else tools)
    return {f"fluxor-packs-{event}": {"key": f"fluxor-packs-{event}", "event": event, "dispatch": True,
                                      "tools": "any" if "any" in tools else sorted(tools)}
            for event, tools in events.items()}


def pack_command(pack_dir: Path, manifest: dict) -> list[str] | None:
    """The argv a pack hook runs, from its manifest, when every script it names still has the hash
    the user approved; None otherwise."""
    run = manifest.get("run") if isinstance(manifest.get("run"), dict) else {}
    script, args = run.get("script"), run.get("args", [])
    if not isinstance(script, str) or not PACK_SCRIPT.fullmatch(script) or not isinstance(args, list) \
            or not all(isinstance(a, str) and PACK_ARG.fullmatch(a) for a in args):
        return None
    runs = manifest.get("runs") if isinstance(manifest.get("runs"), list) else []
    if script not in {r.get("path") for r in runs if isinstance(r, dict)}:
        return None
    for entry in runs:
        path = pack_dir / str(entry.get("path", ""))
        if not PACK_SCRIPT.fullmatch(str(entry.get("path", ""))) or escapes(pack_dir, path) \
                or not path.is_file() or sha256_bytes(disk_bytes(path)) != entry.get("sha256"):
            return None
    return [sys.executable, str(pack_dir / script), *args, "--pack", str(pack_dir)]


def pack_hook(root: Path, event: str) -> int:
    """Run the approved pack hooks for `event` with the session's payload. A hook that exits 2 blocks,
    as Claude Code reads it; anything that fails otherwise lets the work through."""
    data = sys.stdin.buffer.read()
    out = []
    for pack_id, manifest in approved_pack_hooks(root):
        if manifest.get("event") != event:
            continue
        argv = pack_command(root / PACKS / pack_id, manifest)
        if argv is None:
            print(f"fluxor-sync: skipped {pack_id}:{manifest['key']}: its script is not the approved one",
                  file=sys.stderr)
            continue
        try:
            done = subprocess.run(argv, input=data, capture_output=True, cwd=root, timeout=PACK_HOOK_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"fluxor-sync: {pack_id}:{manifest['key']} did not run ({exc})", file=sys.stderr)
            continue
        sys.stderr.buffer.write(done.stderr)
        if done.returncode == 2:
            return 2
        out.append(done.stdout)
    sys.stdout.buffer.write(b"".join(out))
    return 0


def pack_upload(root: Path, pack_id: str) -> list[dict]:
    """The files `pack publish` sends: what pack.json lists, each still as rendered, plus pack.json
    and the root .gitignore. Never `private/`."""
    folder = root / PACKS / pack_id
    if escapes(root, folder):
        raise SyncError(f"{PACKS}/{pack_id} {OUTSIDE}; nothing was sent")
    shared(folder, "pack.json")
    if not (folder / "pack.json").is_file():
        raise SyncError(f"no pack at {PACKS}/{pack_id}/: render it first (ceet-core's render_pack.py render --write)")
    try:
        manifest = json.loads(disk_bytes(folder / "pack.json").decode("utf-8"))
    except ValueError as exc:
        raise SyncError(f"{PACKS}/{pack_id}/pack.json is not valid JSON ({exc})") from exc
    if manifest.get("source") != "interview":
        raise SyncError("only a pack from the person's own interview is published (this one is "
                        f"{manifest.get('source')!r})")
    files = []
    for entry in manifest.get("files", []):
        rel = entry.get("path", "") if isinstance(entry, dict) else ""
        path = safe_path(folder, rel)
        if rel.startswith("private/") or not path.is_file():
            raise SyncError(f"pack.json lists {rel!r}, which is not a shared file of the pack")
        shared(folder, rel)
        data = disk_bytes(path)
        if sha256_bytes(data) != entry.get("sha256"):
            raise SyncError(f"{rel} was edited since the pack was rendered: re-render it "
                            "(render_pack.py render --write) before publishing")
        files.append({"path": rel, "content": data.decode("utf-8")})
    files.append({"path": "pack.json", "content": disk_bytes(folder / "pack.json").decode("utf-8")})
    shared(folder, ".gitignore")
    if (folder / ".gitignore").is_file():
        files.append({"path": ".gitignore", "content": disk_bytes(folder / ".gitignore").decode("utf-8")})
    return files


def shared(folder: Path, rel: str) -> None:
    """Refuse the whole publish unless `rel`, links followed, is in the pack and outside its
    `private/` (card://JAVA-873): what is sent reaches every project the pack is attached to."""
    path, private = folder / rel, folder / "private"
    if escapes(folder, path) or not escapes(private, path):
        raise SyncError(f"{PACKS}/{folder.name}/{rel} resolves outside the pack's shared files (a symlink leads "
                        "out of the pack or into private/, or loops); nothing was sent")


def pack(root: Path, action: str, pack_id: str) -> int:
    if not PACK_ID.fullmatch(pack_id):
        raise SyncError(f"{pack_id!r} is not a pack id (<role>-<person>, kebab-case)")
    config = read_config(root)
    project_id = config.get("projectId")
    if not project_id:
        raise SyncError(f"{CONFIG} names no project: run `fluxor-sync init` first")
    project_id = checked_project(project_id)
    server = server_url(config)
    token = token_for(server)
    base = f"{server}/fluxor/v1/sync/harness"
    if action == "publish":
        files = pack_upload(root, pack_id)
        status, _, body = http("PUT", f"{base}/projects/{project_id}/packs/{pack_id}", token, body={"files": files})
        if status != 200:
            raise explain(status, body, f"publishing pack {pack_id}")
        print(f"fluxor-sync: published {pack_id} ({len(files)} files) and attached it to this project; a pull on "
              "any machine of a project it is attached to delivers it")
    elif action == "detach":
        status, _, body = http("DELETE", f"{base}/projects/{project_id}/packs/{pack_id}", token)
        if status != 204:
            raise explain(status, body, f"detaching pack {pack_id}")
        print(f"fluxor-sync: detached {pack_id} from this project; the next pull removes the files Fluxor wrote")
    else:
        status, _, body = http("DELETE", f"{base}/packs/{pack_id}", token)
        if status != 204:
            raise explain(status, body, f"unpublishing pack {pack_id}")
        print(f"fluxor-sync: deleted {pack_id} from Fluxor; each project drops it on its next pull")
    return 0


# ─── Commands ──────────────────────────────────────────────────────────────────────────────────────

def pull(root: Path, force: bool = False, directives: bool = False, packs: bool = False,
         announce: bool = True) -> int:
    config = read_config(root)
    if config.get("declined"):
        print("fluxor-sync: this project declined Fluxor's harness; `fluxor-sync init` sets it up")
        return 0
    project_id = config.get("projectId")
    if not project_id:
        raise SyncError(f"{CONFIG} names no project: run `fluxor-sync init` first")
    server = server_url(config)
    token = token_for(server)
    lock = read_lock(root / LOCK)
    source = lock.get("source", {})
    # card://JAVA-2010: the first pull of a fresh clone or worktree runs after the client read
    # AGENTS.md, so it prints the always-read rules for that first session itself.
    fresh = announce and not source.get("hash")
    etag = None if force or source.get("projectId") != project_id else source.get("hash")
    snapshot = fetch_snapshot(server, token, project_id, etag)
    if snapshot is None:
        report = Report()
        for rel, why in edited_files(root, lock) + pack_edits(root):
            if why != "deleted":
                report.keep(rel, why)
        # Every session start lands here while Fluxor is quiet, so a hook script edited since the last
        # change is unwired here too (card://JAVA-670). Unchanged, it writes nothing.
        before = json.dumps(lock, sort_keys=True)
        reconcile(root, lock, report)
        if json.dumps(lock, sort_keys=True) != before:
            write_atomic(root / LOCK, dump_json(lock).encode("utf-8"))
        print(f"fluxor-sync: up to date (revision {source.get('revision')})")
    else:
        blobs = Blobs(server, token)
        # Packs are locked apart, in their own folders: the harness lock may be committed.
        pack_files = [f for f in snapshot["files"] if pack_of(f["path"])]
        snapshot = dict(snapshot, files=[f for f in snapshot["files"] if not pack_of(f["path"])])
        # An approval holds only for the hash it was given to: a new one waits for consent again.
        before, incoming = installed_hooks(root, lock), snapshot_hooks(snapshot)
        approvals, changed = [], []
        for approval in lock.get("approvedHooks", []):
            key = approval.get("key") if isinstance(approval, dict) else None
            if key in incoming and incoming[key][1] == approval.get("sha256"):
                approvals.append(approval)
            elif key in incoming:
                changed.append(key)
        hide = fallback_lines({k: incoming[k][2] for k in (a["key"] for a in approvals)
                               if hook_clients(incoming[k][2])})
        writer = root / WRITER
        writer_before = sha256_bytes(disk_bytes(writer)) if writer.is_file() and not escapes(root, writer) else None
        files, report = apply(root, snapshot, lock, blobs, force, hide)
        apply_packs(root, pack_files, blobs, force, report)
        mirrors = wire_skills(root, lock, report)
        updated = lock_document(snapshot, files, mirrors)
        if approvals:
            updated["approvedHooks"] = approvals
        if lock.get("hookWiring"):
            updated["hookWiring"] = lock["hookWiring"]
        reconcile(root, updated, report)
        write_atomic(root / LOCK, dump_json(updated).encode("utf-8"))
        if report.written:
            wsl_modes(root, updated)
        print(f"fluxor-sync: revision {snapshot['revision']}: {report.written} file(s) written, "
              f"{report.removed} removed, {blobs.downloaded} downloaded")
        # card://JAVA-625, decision 5: the writer updates itself with no consent asked, so it says so.
        if writer_before and writer.is_file() and sha256_bytes(disk_bytes(writer)) != writer_before:
            print(f"fluxor-sync: fluxor-sync updated itself from {server} (revision {snapshot['revision']}); "
                  "the next session start runs the new version")
        for key in changed:
            old = before.get(key, (None, None, None))[2]
            report.kept.append(f"hook {key} changed ({what_changed(old, incoming[key][2])}): it is unwired and "
                               "its fallback is back until the user consents again. Ask them, naming what "
                               f"changed, and on a yes run `fluxor-sync approve --consented {key}`")
        pending = sorted(set(incoming) - {a["key"] for a in approvals} - set(changed))
        if pending:
            report.kept.append(f"hook(s) waiting for the user's consent: {', '.join(pending)} "
                               "(`fluxor-sync approve` lists what to ask)")
    exclude_local(root, read_lock(root / LOCK), report)
    keep_machine_copy(root)
    for line in report.kept:
        print(f"fluxor-sync: {line}")
    if directives or fresh:
        print_directives(root)
    if directives or packs:
        print_packs(root)
    return 0


# ─── Publishing a person's own items from a folder (card://JAVA-2007) ───────────────────────────────

PUBLISH_SKIPPED = ("__pycache__", ".DS_Store")


def publish_files(folder: Path, kind: str) -> list[dict]:
    """The folder's files, by path relative to it: links that leave it and caches stay out."""
    files = []
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder).as_posix()
        if any(part in PUBLISH_SKIPPED for part in rel.split("/")) or rel.endswith(".pyc"):
            continue
        if escapes(folder, path):
            skipped(rel)
            continue
        if not path.is_file() or (kind == "hook" and rel == "hook.json") or (kind == "directive" and rel == "card.json"):
            continue
        data = disk_bytes(path)
        files.append({"path": rel, "sha256": sha256_bytes(data), "size": len(data),
                      "executable": bool(disk_executable(path)), "data": data})
    return files


def item_publish(root: Path, folder: Path, key: str, kind: str, visibility: str, project: str | None,
                 title: str | None, description: str | None, atom: str | None = None) -> int:
    """Publish `folder` as the next version of the own item `key`: ask which files Fluxor lacks, then
    send the item with only those files' bytes (a hook's and a skill's SKILL.md always travel inline,
    since Fluxor renders them). Visibility applies when the key is new; the web page changes it later."""
    config = read_config(root)
    server = server_url(config)
    token = token_for(server)
    if not folder.is_dir():
        raise SyncError(f"{folder} is not a folder")
    files = publish_files(folder.resolve(), kind)
    if not files:
        raise SyncError(f"{folder} has no file to publish")
    hook = None
    if kind == "hook":
        manifest = folder / "hook.json"
        if not manifest.is_file():
            raise SyncError(f"{folder} has no hook.json: a hook names its event there")
        hook = json.loads(disk_bytes(manifest).decode("utf-8"))
    card = None
    if atom:
        # card://JAVA-2011: an atom's inventory card, rendered as marketplace.py renders inventory.json.
        card_file = folder / "card.json"
        if not card_file.is_file():
            raise SyncError(f"{folder} has no card.json: an atom carries its inventory card")
        card = json.dumps(json.loads(disk_bytes(card_file).decode("utf-8")), indent=2, ensure_ascii=False)
    status, _, body = http("POST", f"{server}/fluxor/v1/sync/harness/items/blobs", token,
                           {"sha256": [f["sha256"] for f in files]})
    if status != 200:
        raise explain(status, body, "the publish")
    missing = set(json.loads(body.decode("utf-8")).get("missing", []))
    sent = 0
    payload = []
    for f in files:
        entry = {k: f[k] for k in ("path", "sha256", "size", "executable")}
        if f["sha256"] in missing or kind in ("hook", "directive") or f["path"] == "SKILL.md":
            entry["content"] = base64.b64encode(f["data"]).decode("ascii")
            sent += 1
        payload.append(entry)
    request = {"kind": kind, "title": title, "description": description, "visibility": visibility,
               "hook": hook, "files": payload, "atom": atom, "card": card}
    if visibility == "project":
        request["harnessProjectId"] = project or config.get("projectId")
    status, _, body = http("PUT", f"{server}/fluxor/v1/sync/harness/items/{urllib.parse.quote(key, safe='.')}",
                           token, request)
    if status != 200:
        raise explain(status, body, "the publish")
    item = json.loads(body.decode("utf-8"))
    print(f"fluxor-sync: published {key} version {item.get('version')}: {len(files)} file(s), {sent} sent, "
          f"{len(files) - sent} already in Fluxor")
    return 0


def select(root: Path, put: list[str], remove: list[str]) -> int:
    """Add (`KEY` or `KEY@VERSION`) and remove items of this project's harness in one revision, as its
    page does (card://JAVA-2011): what a script sets a workspace's selection with."""
    config = read_config(root)
    project_id = checked_project(config.get("projectId"))
    server = server_url(config)
    token = token_for(server)
    status, _, body = http("GET", f"{server}/fluxor/v1/sync/harness/projects", token)
    if status != 200:
        raise explain(status, body, "the project list")
    current = next((p for p in json.loads(body.decode("utf-8")) if p.get("id") == project_id), None)
    if current is None:
        raise SyncError(f"Fluxor has no harness project {project_id} this machine can read")
    changes = []
    for entry in put:
        key, _, version = entry.partition("@")
        changes.append({"key": key, **({"version": int(version)} if version else {})})
    status, _, body = http("PATCH", f"{server}/fluxor/v1/sync/harness/projects/{project_id}/items", token,
                           {"expectedRevision": current.get("revision", 0), "put": changes, "remove": remove})
    if status != 200:
        raise explain(status, body, "the selection")
    harness = json.loads(body.decode("utf-8"))
    print(f"fluxor-sync: the harness is at revision {harness['project']['revision']} with "
          f"{len(harness['items'])} item(s); pull to bring it here")
    return 0


def init(root: Path, code: str, project_id: str, server: str | None, run_pull: bool = True,
         storage: str | None = None) -> int:
    if (root / ".harness" / "harness.json").is_file():
        raise SyncError("this harness is installed from a local catalog (.harness/harness.json, "
                        "`marketplace.py install`); fluxor-sync manages one Fluxor serves, so it won't take over")
    project_id = checked_project(project_id)
    config = read_config(root)
    base = enrollment_server(server)
    refused = cleartext_off_machine(base)
    if refused:
        raise SyncError(f"{refused}; nothing was sent")
    status, _, body = http("POST", f"{base}/fluxor/v1/sync/enrollments",
                           body={"code": code, "hostname": socket.gethostname()})
    if status != 201:
        raise explain(status, body, "enrollment")
    enrolled = json.loads(body.decode("utf-8"))
    replaced = store_token(base, enrolled)
    config = {k: v for k, v in config.items() if k != "declined"}
    config.update({"projectId": project_id, "server": base})
    if storage:
        # card://JAVA-2010: `local` keeps the pulled harness out of git; `repository` commits it.
        config["storage"] = storage
    write_atomic(root / CONFIG, dump_json(config).encode("utf-8"))
    install_self(root)
    print(f"fluxor-sync: enrolled as {enrolled.get('name')} on {base}; the token is in {token_store()}")
    if replaced:
        print(f"fluxor-sync: this replaced this machine's earlier device on {base} ({replaced}); it is still "
              "live until you revoke it in Fluxor's devices")
    return pull(root, announce=False) if run_pull else 0


def install_self(root: Path) -> None:
    """Put this file at `.harness/bin/fluxor-sync.py`, where each client's session start runs it, and
    lock it, so the first pull replaces it with the snapshot's copy instead of reporting a conflict."""
    me = Path(__file__).resolve()
    target = root / WRITER
    if escapes(root, target):
        raise SyncError(f"{WRITER} {OUTSIDE}: the session start would run a file from outside the project. "
                        "Make it a file of this project (or remove it) and run init again")
    data = disk_bytes(me)
    if not (target.is_file() and target.resolve() == me):
        write_atomic(target, data, True)
    lock = read_lock(root / LOCK)
    if lock.get("source", {}).get("kind") != "fluxor":
        lock = {"schemaVersion": 1, "atoms": {}, "files": {}, "source": {"kind": "fluxor"}}
    lock["files"].setdefault(WRITER, {"sha256": sha256_bytes(data), "executable": True, "atom": None,
                                      "mode": "file"})
    write_atomic(root / LOCK, dump_json(lock).encode("utf-8"))
    keep_machine_copy(root)


def status(root: Path, offline: bool = False) -> int:
    config = read_config(root)
    lock = read_lock(root / LOCK)
    source = lock.get("source", {})
    if config.get("declined"):
        print("project: declined (`fluxor-sync init` sets it up)")
        return 0
    print(f"project: {config.get('projectId') or 'not set up (run fluxor-sync init)'}")
    server = server_url(config)
    held = issuers()
    print(f"server: {server}")
    print("device token: " + ("issued by this server" if server in held else
                              f"none from this server (issued by {', '.join(held)})" if held else "missing")
          + f" ({token_store()})")
    print(f"installed: revision {source.get('revision', '-')}, {len(lock.get('files', {}))} file(s)")
    for rel, why in edited_files(root, lock) if source.get("kind") == "fluxor" else []:
        print(f"edited locally: {rel} ({why})")
    approved = {a.get("key"): a.get("sha256") for a in lock.get("approvedHooks", []) if isinstance(a, dict)}
    for key, (_, sha, manifest) in installed_hooks(root, lock).items():
        edited = edited_scripts(root, manifest)
        if approved.get(key) != sha:
            print(f"hook {key}: waiting for consent (fluxor-sync approve --consented {key})")
        elif edited:
            print(script_edited(key, edited))
        else:
            print(f"hook {key}: approved and wired")
    for pack_id, pack_lock in synced_packs(root).items():
        print(f"pack {pack_id}: {len(managed(pack_lock))} file(s) from Fluxor")
        for rel, why in edited_files(root, {"files": managed(pack_lock)}):
            print(f"edited locally: {rel} ({why})")
        for key, (_, sha, _) in installed_hooks(root, pack_lock).items():
            state = "approved and wired" if pack_approvals(pack_lock).get(key) == sha else \
                f"waiting for consent (fluxor-sync approve --consented {pack_id}:{key})"
            print(f"hook {pack_id}:{key}: {state}")
    if not offline and config.get("projectId") and held:
        snapshot = fetch_snapshot(server, token_for(server), config["projectId"], source.get("hash"))
        print("remote: up to date" if snapshot is None
              else f"remote: revision {snapshot['revision']} is available (fluxor-sync pull)")
    return 0


def decline(root: Path) -> int:
    write_atomic(root / CONFIG, dump_json({"declined": True}).encode("utf-8"))
    print(f"fluxor-sync: declined; {CONFIG} records it, and `fluxor-sync init` sets the project up")
    return 0


def fluxor_lock(root: Path) -> dict:
    lock = read_lock(root / LOCK)
    if lock.get("source", {}).get("kind") != "fluxor":
        raise SyncError("this project has no harness from Fluxor: run `fluxor-sync init` first")
    return lock


def hook_key(key: str) -> str:
    """A hook's key in its own lock: `<pack-id>:<hook>` is `<hook>` in that pack's."""
    return key.split(":", 1)[1] if ":" in key else key


def all_hooks(root: Path, lock: dict) -> dict[str, tuple[str | None, str, dict]]:
    """key -> (pack id or None, manifest sha256, manifest): the harness's hooks, then each pack's as
    `<pack-id>:<hook>`."""
    hooks = {key: (None, sha, manifest) for key, (_, sha, manifest) in installed_hooks(root, lock).items()}
    for pack_id, pack_lock in synced_packs(root).items():
        for key, (_, sha, manifest) in installed_hooks(root, pack_lock).items():
            hooks[f"{pack_id}:{key}"] = (pack_id, sha, manifest)
    return hooks


def describe_any(key: str, hook: tuple[str | None, str, dict]) -> str:
    pack_id, _, manifest = hook
    if pack_id is None:
        return describe_hook(manifest)
    run = manifest.get("run") if isinstance(manifest.get("run"), dict) else {}
    command = " ".join([f"{PACKS}/{pack_id}/{run.get('script')}", *map(str, run.get("args", []))])
    return (f"- {key} ({manifest.get('title') or manifest['key']}): {manifest.get('description', '')}. "
            f"It runs on {manifest.get('event')}, in Claude Code, with Python: {command}")


def approve(root: Path, keys: list[str], every: bool, consented: bool) -> int:
    """Record the user's consent to these hooks' exact hashes, and wire them. The agent passes
    `--consented` only after the user said yes to the list this prints without it."""
    lock = fluxor_lock(root)
    hooks = all_hooks(root, lock)
    unknown = [k for k in keys if k not in hooks]
    if unknown:
        raise SyncError(f"no hook {', '.join(unknown)} in this harness; it has: {', '.join(sorted(hooks)) or 'none'}")
    locks = {None: lock, **synced_packs(root)}
    chosen = sorted(hooks) if every else keys
    chosen = [k for k in chosen if pack_approvals(locks[hooks[k][0]]).get(hook_key(k)) != hooks[k][1]]
    if not chosen:
        print("fluxor-sync: no hook is waiting for consent")
        return 0
    if not consented:
        print("fluxor-sync: not approved. A hook runs code on this machine, so it is wired only after the user "
              "says yes in the conversation. Show them these, and only on a yes run "
              f"`fluxor-sync approve --consented {' '.join(chosen) if not every else '--all'}`:")
        for key in chosen:
            print(describe_any(key, hooks[key]))
        return 2
    for key in chosen:
        owner = locks[hooks[key][0]]
        approved = {a.get("key"): a for a in owner.get("approvedHooks", []) if isinstance(a, dict)}
        approved[hook_key(key)] = {"key": hook_key(key), "sha256": hooks[key][1]}
        owner["approvedHooks"] = [approved[k] for k in sorted(approved)]
    for pack_id in {hooks[k][0] for k in chosen} - {None}:
        write_atomic(pack_lock_path(root, pack_id), dump_json(locks[pack_id]).encode("utf-8"))
    report = Report()
    wired = reconcile(root, lock, report)
    write_atomic(root / LOCK, dump_json(lock).encode("utf-8"))
    for key in chosen:
        manifest = hooks[key][2]
        if hooks[key][0] is None and hook_clients(manifest) and key not in wired:
            # Consent is to Fluxor's bytes: it is recorded, and wires once they are back (card://JAVA-670).
            print(f"fluxor-sync: approved {key} (sha256 {hooks[key][1][:12]}), not wired yet (below)")
            continue
        clients = "Claude Code" if hooks[key][0] else \
            " and ".join(CLIENT_NAMES[c] for c in hook_clients(manifest)) or "no client (nothing to run)"
        print(f"fluxor-sync: approved {key} (sha256 {hooks[key][1][:12]}), wired for {clients}")
    print("fluxor-sync: hooks take effect from the next session; tell the user to start a new one")
    for line in report.kept:
        print(f"fluxor-sync: {line}")
    return 0


def revoke(root: Path, keys: list[str]) -> int:
    lock = fluxor_lock(root)
    locks = {None: lock, **synced_packs(root)}
    owners = {key: (key.split(":", 1)[0] if ":" in key else None) for key in keys}
    unknown = [k for k, owner in owners.items()
               if owner not in locks or hook_key(k) not in pack_approvals(locks[owner])]
    if unknown:
        raise SyncError(f"no approved hook {', '.join(unknown)}")
    for owner in set(owners.values()):
        target = locks[owner]
        gone = {hook_key(k) for k, o in owners.items() if o == owner}
        target["approvedHooks"] = [a for a in target.get("approvedHooks", [])
                                   if isinstance(a, dict) and a.get("key") not in gone]
        if not target["approvedHooks"]:
            del target["approvedHooks"]
        if owner is not None:
            write_atomic(pack_lock_path(root, owner), dump_json(target).encode("utf-8"))
    report = Report()
    reconcile(root, lock, report)
    write_atomic(root / LOCK, dump_json(lock).encode("utf-8"))
    print(f"fluxor-sync: revoked {', '.join(keys)}: unwired (a catalog hook's fallback is read instead)")
    for line in report.kept:
        print(f"fluxor-sync: {line}")
    return 0


def shell(command: str) -> tuple[list[str] | str, dict]:
    """Claude Code runs a status line with bash, on Windows too: so does this. The command travels in
    the environment, because Git Bash re-parses a Windows command line and mangles its quotes."""
    bash = git_bash() if os.name == "nt" else shutil.which("bash")
    if not bash:
        return command, dict(os.environ)
    return [bash, "-c", 'eval "$FLUXOR_STATUS_LINE_COMMAND"'], dict(os.environ, FLUXOR_STATUS_LINE_COMMAND=command)


def git_bash() -> str | None:
    """The Git Bash Claude Code uses on Windows. `bash` on PATH there is usually WSL's launcher,
    which would run the command on another machine's filesystem."""
    configured = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if configured and Path(configured).is_file():
        return configured
    git = shutil.which("git")
    candidate = Path(git).resolve().parents[1] / "bin" / "bash.exe" if git else None
    return str(candidate) if candidate and candidate.is_file() else None


def statusline(root: Path) -> int:
    """Claude Code's status line when ours wraps the user's (or several of ours share it): every one
    of ours gets the session's JSON in the background, and the one drawn is the user's."""
    record = read_lock(root / LOCK).get("hookWiring", {}).get("claude", {}).get(STATUS_LINE) or {}
    data = sys.stdin.buffer.read()
    ours = [c for c in record.get("commands", []) if isinstance(c, str)]
    wrapped = record.get("wrapped") if isinstance(record.get("wrapped"), dict) else {}
    drawn = wrapped.get("command") if isinstance(wrapped.get("command"), str) else None
    if drawn is None and ours:
        drawn, ours = ours[0], ours[1:]
    detach = {"start_new_session": True} if os.name != "nt" else \
        {"creationflags": getattr(subprocess, "DETACHED_PROCESS", 0)}
    for command in ours:
        argv, env = shell(command)
        try:
            child = subprocess.Popen(argv, shell=isinstance(argv, str), env=env, stdin=subprocess.PIPE,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **detach)
            child.stdin.write(data)
            child.stdin.close()
        except OSError:
            pass  # a status line never fails the bar
    if drawn:
        argv, env = shell(drawn)
        try:
            done = subprocess.run(argv, shell=isinstance(argv, str), env=env, input=data, capture_output=True,
                                  timeout=10)
            sys.stdout.buffer.write(done.stdout)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="fluxor-sync", description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", help="the project folder (default: $CLAUDE_PROJECT_DIR, git, the cwd)")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("init", help="enroll this machine and set the project up")
    p.add_argument("--enroll", required=True, metavar="CODE", help="the code harness.bootstrap returned")
    p.add_argument("--project", required=True, metavar="ID", help="the Fluxor project's id")
    p.add_argument("--server", help=f"Fluxor's API (default {DEFAULT_SERVER})")
    p.add_argument("--no-pull", action="store_true", help="enroll only; pull later")
    p.add_argument("--storage", choices=("local", "repository"),
                   help="local: the pulled harness is this machine's, kept out of git; repository: committed")
    p = commands.add_parser("pull", help="bring the harness up to date")
    p.add_argument("--force", action="store_true", help="take Fluxor's version of locally edited files")
    p.add_argument("--print-directives", action="store_true",
                   help="print the always-on directives and the packs' cores (for clients that expand no @ imports)")
    p.add_argument("--print-packs", action="store_true", help="print the synced packs' always-on cores")
    p = commands.add_parser("status", help="what is installed, and whether Fluxor has more (writes nothing)")
    p.add_argument("--offline", action="store_true", help="don't ask the server")
    commands.add_parser("decline", help="record that this project does not want Fluxor's harness")
    p = commands.add_parser("approve", help="wire hooks, after the user consented in the conversation")
    p.add_argument("--consented", action="store_true",
                   help="the user said yes to exactly these hooks; without it, prints what to ask")
    p.add_argument("--all", action="store_true", help="every hook waiting for consent")
    p.add_argument("keys", nargs="*", metavar="KEY")
    p = commands.add_parser("revoke", help="unwire approved hooks; their fallback is read instead")
    p.add_argument("keys", nargs="+", metavar="KEY")
    commands.add_parser("statusline", help="Claude Code's status line when ours wraps the user's (internal)")
    p = commands.add_parser("pack", help="publish a pack rendered here to Fluxor, or take it back")
    p.add_argument("action", choices=("publish", "detach", "unpublish"),
                   help="publish and attach to this project; detach from it; or delete it from Fluxor")
    p.add_argument("pack_id", metavar="PACK-ID")
    p = commands.add_parser("item", help="publish a folder as an item of your own (a skill, a hook or files)")
    p.add_argument("action", choices=("publish",))
    p.add_argument("folder", metavar="FOLDER", help="a skill's folder, a hook's (hook.json, fallback.md, hook.sh), "
                   "or files laid out as in the project (.harness/..., .claude/rules/...)")
    p.add_argument("--key", required=True, help="<namespace>.<name>, like team.review")
    p.add_argument("--kind", required=True, choices=("skill", "hook", "files", "directive"))
    p.add_argument("--atom", choices=("role", "mod", "step", "flow"),
                   help="a directive that is an atom of the atoms layout; its folder holds card.json")
    p.add_argument("--visibility", default="project", choices=("private", "project", "organization", "public"))
    p.add_argument("--project", help="the harness project a project item belongs to (default: this one's)")
    p.add_argument("--title")
    p.add_argument("--description")
    p = commands.add_parser("select", help="add and remove items of this project's harness, in one revision")
    p.add_argument("--put", nargs="*", default=[], metavar="KEY[@VERSION]")
    p.add_argument("--remove", nargs="*", default=[], metavar="KEY")
    p = commands.add_parser("pack-hook", help="run the approved pack hooks for an event (internal)")
    p.add_argument("event", choices=sorted(EVENTS["claude"]))
    args = parser.parse_args(argv)
    if args.command == "approve" and bool(args.all) == bool(args.keys):
        parser.error("approve takes --all or hook keys, not both" if args.all else "approve takes --all or hook keys")
    root = project_root(args.root)
    try:
        check_state(root)
        if args.command == "init":
            return init(root, args.enroll, args.project, args.server, not args.no_pull, args.storage)
        if args.command == "item":
            return item_publish(root, Path(args.folder), args.key, args.kind, args.visibility, args.project,
                                args.title, args.description, args.atom)
        if args.command == "select":
            return select(root, args.put, args.remove)
        if args.command == "pull":
            return pull(root, args.force, args.print_directives, args.print_packs)
        if args.command == "status":
            return status(root, args.offline)
        if args.command == "approve":
            return approve(root, args.keys, args.all, args.consented)
        if args.command == "revoke":
            return revoke(root, args.keys)
        if args.command == "statusline":
            return statusline(root)
        if args.command == "pack":
            return pack(root, args.action, args.pack_id)
        if args.command == "pack-hook":
            return pack_hook(root, args.event)
        return decline(root)
    except SyncError as exc:
        print(f"fluxor-sync: {exc}", file=sys.stderr)
        if args.command == "pull" and args.print_directives:
            print_directives(root)  # a session still gets the harness it already has
        if args.command == "pull" and (args.print_directives or args.print_packs):
            print_packs(root)
        return 1


if __name__ == "__main__":
    sys.exit(main())
