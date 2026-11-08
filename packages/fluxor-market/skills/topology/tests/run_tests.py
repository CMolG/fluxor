#!/usr/bin/env python3
"""Fixture tests for topology.py: a validator that has only ever been seen passing is untested.

Builds three small synthetic workspaces in a temporary directory (git-initialized, since the script
prefers `git grep`), runs topology.py against each, and checks that every check fires where it
must and stays quiet where it must not.

    python3 tests/run_tests.py               # exit 0 if every assertion holds
    python3 tests/run_tests.py --keep DIR    # also leave the fixtures in DIR for inspection

  clean    pnpm workspace + layering config; every tricky-but-legal import (alias, baseUrl,
           builtin, self-import, type-only, root devDependency, comment, Buffer.from) -> exit 0
  broken   npm workspaces; a cycle, two phantoms, a forbidden edge, an isolated-group edge, a leaf
           edge, an exception with and without a reason, an ignore without a reason, a config typo
           -> exit 1 with each one reported; the same again with git unavailable
  maven    yarn-style workspaces + a Maven reactor; no config -> generic checks and `route`
           autodetection; a config via HARNESS_DIR adds TypeScript packages to `route`
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "topology.py"


def pkg(name: str, deps=None, dev=None, peer=None) -> str:
    data = {"name": name, "version": "0.0.0"}
    for key, val in (("dependencies", deps), ("devDependencies", dev), ("peerDependencies", peer)):
        if val:
            data[key] = {d: "workspace:*" if d.startswith("@fx/") else "*" for d in val}
    return json.dumps(data, indent=2)


JAVA = "package x;\npublic class {0} {{}}\n"
POM = "<project><artifactId>{0}</artifactId>{1}</project>\n"

FIXTURES = {
    "clean": {
        "pnpm-workspace.yaml": "packages:\n  # apps and libraries\n  - \"apps/*\"\n  - 'packages/*'\n"
                               "catalog:\n  react: ^19\n",
        "package.json": pkg("fx-root", dev=["typescript"]),
        "apps/host/package.json": pkg("@fx/host", deps=["@fx/ui", "react"], dev=["@types/node"]),
        "apps/host/tsconfig.json": "// JSONC, as tsc allows\n{\"compilerOptions\": {\"baseUrl\": \".\",\n"
                                   "  \"paths\": {\"@/*\": [\"./src/*\"], \"shared/*\": [\"./src/shared/*\"]},},}\n",
        "apps/host/lib/helper.ts": "export const helper = 1;\n",
        "apps/host/src/index.tsx": (
            'import { Button } from "@fx/ui";\nimport React from \'react\';\n'
            'import fs from "node:fs";\nimport path from "path";\nimport { readFile } from "fs/promises";\n'
            'import { local } from "./local";\nimport { thing } from "@/thing";\n'
            'import { util } from "shared/util";\n'
            'import { helper } from "lib/helper";\nimport type { CompilerOptions } from "typescript";\n'
            '// import { secret } from "@fx/app-a";\n'
            "const b = Buffer.from('not-a-package');\n"
            'export const lazy = () => import("@fx/host/extra");\n'),
        "apps/app-a/package.json": pkg("@fx/app-a", deps=["@fx/ui"]),
        "apps/app-a/src/page.tsx": 'import { Button } from "@fx/ui/button";\nconst ui = require("@fx/ui");\n',
        "apps/app-b/package.json": pkg("@fx/app-b", deps=["@fx/ui"]),
        "apps/app-b/src/page.test.tsx": 'import { Button } from "@fx/ui";\nvi.mock("@fx/ui");\n',
        "packages/ui/package.json": pkg("@fx/ui", deps=["@fx/tokens"], peer=["react"]),
        "packages/ui/src/index.ts": 'export * from "@fx/tokens";\nimport type { FC } from "react";\n',
        "packages/tokens/package.json": pkg("@fx/tokens"),
        "packages/tokens/src/index.ts": "export const spacing = 4;\n",
        ".harness/config/topology.json": json.dumps({
            "groups": {
                "host": {"packages": ["apps/host"]},
                "miniapp": {"packages": ["@fx/app-*"], "isolated": True},
                "design-system": {"packages": ["packages/*"], "leaf": True},
            },
            "forbidden": [{"from": "host", "to": "miniapp", "reason": "Apps are mounted, not imported."}],
        }, indent=2),
    },
    "broken": {
        "package.json": json.dumps({"name": "fx-root", "private": True,
                                    "workspaces": ["apps/*", "packages/*"]}),
        "apps/host/package.json": pkg("@fx/host", deps=["@fx/app-a", "@fx/app-c"]),
        "apps/host/src/index.ts": 'import a from "@fx/app-a";\nimport c from "@fx/app-c";\n',
        "apps/app-a/package.json": pkg("@fx/app-a", deps=["@fx/app-b"]),
        "apps/app-a/src/index.ts": 'export { b } from "@fx/app-b";\n',
        "apps/app-b/package.json": pkg("@fx/app-b"),
        "apps/app-b/src/index.ts": 'import _ from "lodash";\nimport pad from "left-pad";\n'
                                   'import { core } from "@fx/core";\nexport const b = 1;\n',
        "apps/app-c/package.json": pkg("@fx/app-c"),
        "packages/ui/package.json": pkg("@fx/ui", deps=["@fx/app-b"]),
        "packages/ui/src/index.ts": 'import { b } from "@fx/app-b";\n',
        "packages/core/package.json": pkg("@fx/core", deps=["@fx/util"]),
        "packages/core/src/index.ts": 'import { u } from "@fx/util";\nexport const core = u;\n',
        "packages/util/package.json": pkg("@fx/util", deps=["@fx/core"]),
        "packages/util/src/index.ts": 'export const u = 1;\n',
        ".harness/config/topology.json": json.dumps({
            "phantoms": {"ignore": [{"import": "left-pad"}]},
            "groups": {
                "host": {"packages": ["@fx/host"]},
                "miniapp": {"packages": ["@fx/app-*"], "isolated": True, "reason": "Deployed apart."},
                "design-system": {"packages": ["packages/ui"], "leaf": True, "isolate": True},
            },
            "forbidden": [{"from": "host", "to": "miniapp", "reason": "Apps are mounted, not imported."}],
            "exceptions": [
                {"from": "@fx/host", "to": "@fx/app-c", "reason": "Illustrative: a decided exception."},
                {"from": "@fx/host", "to": "@fx/app-a"},
            ],
        }, indent=2),
    },
    "maven": {
        "package.json": json.dumps({"name": "fx-root", "private": True,
                                    "workspaces": {"packages": ["libs/*"]}}),
        "libs/model/package.json": pkg("model"),
        "libs/model/src/index.ts": "export interface Invoice { id: string }\n"
                                   "export class InvoiceRepository {}\nexport type Money = number;\n",
        "backend/pom.xml": POM.format("backend", "<modules><!-- <module>gone</module> -->"
                                      "<module>contexts/billing/billing-domain</module>"
                                      "<module>contexts/billing/billing-application</module>"
                                      "<module>contexts/iam/iam-domain</module></modules>"),
        "backend/contexts/billing/billing-domain/pom.xml": POM.format("billing-domain", ""),
        "backend/contexts/billing/billing-domain/src/main/java/x/Wallet.java": JAVA.format("Wallet"),
        "backend/contexts/billing/billing-domain/src/main/java/x/WalletRepository.java":
            JAVA.format("WalletRepository"),
        "backend/contexts/billing/billing-application/pom.xml": POM.format("billing-application", ""),
        "backend/contexts/billing/billing-application/src/main/java/x/RefundService.java":
            JAVA.format("RefundService"),
        "backend/contexts/iam/iam-domain/pom.xml": POM.format("iam-domain", ""),
        "backend/contexts/iam/iam-domain/src/main/java/x/ApiKey.java": JAVA.format("ApiKey"),
        "alt-harness/config/topology.json": json.dumps({"route": {"packages": ["libs/*"]}}),
    },
}


def build(base: Path) -> None:
    for name, files in FIXTURES.items():
        root = base / name
        for rel, content in files.items():
            f = root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(content.encode("utf-8"))
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "-c", "core.autocrlf=false", "add", "-A"], cwd=root, check=True)


def run(root: Path, *args: str, harness: Path | None = None, no_git: bool = False):
    env = {k: v for k, v in os.environ.items() if k not in ("HARNESS_DIR", "GIT_DIR")}
    env["CLAUDE_PROJECT_DIR"] = str(root)
    if harness:
        env["HARNESS_DIR"] = str(harness)
    if no_git:
        env["GIT_DIR"] = str(root / "no-such-git-dir")  # every git call fails -> fallback walk
    p = subprocess.run([sys.executable, str(SCRIPT)] + list(args), cwd=str(root), env=env,
                       capture_output=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


FAILED: list[str] = []


def remove(path: Path) -> None:
    """rmtree that also works on Windows, where git makes its object files read-only."""
    def force(func, target, _exc):
        os.chmod(target, 0o700)
        func(target)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=force)
    else:
        shutil.rmtree(path, onerror=force)


def expect(label: str, result, code: int, present=(), absent=()) -> None:
    rc, out = result
    problems = [f"exit {rc}, expected {code}"] if rc != code else []
    problems += [f"missing: {s!r}" for s in present if s not in out]
    problems += [f"unexpected: {s!r}" for s in absent if s in out]
    print(("PASS  " if not problems else "FAIL  ") + label)
    if problems:
        FAILED.append(label)
        print("      " + "\n      ".join(problems) + "\n      --- output ---\n      "
              + out.replace("\n", "\n      "))


def main() -> int:
    keep = sys.argv[sys.argv.index("--keep") + 1] if "--keep" in sys.argv else None
    base = Path(keep) if keep else Path(tempfile.mkdtemp(prefix="topology-fixtures-"))
    if keep and base.exists():
        remove(base)
    build(base)
    clean, broken, maven = base / "clean", base / "broken", base / "maven"

    expect("clean: verify passes", run(clean, "verify"), 0,
           ["Clean topology: 5 packages", "3 layering rule(s)"], ["PHANTOM", "CYCLE"])
    expect("clean: map shows edges and groups", run(clean, "map"), 0,
           ["@fx/host", "-> ui", "[miniapp]", "[design-system]", "5 packages, 4 edges."])
    graph = json.loads(run(clean, "graph")[1])
    expect("clean: graph is JSON with deps and groups", (0, json.dumps(graph, sort_keys=True)), 0,
           ['"@fx/host": {"deps": ["@fx/ui"], "dir": "apps/host", "groups": ["host"]}'])
    expect("clean: route without Maven or config explains how to configure", run(clean, "route"), 0,
           ["Nothing to route", '"route"'])

    violations = [
        "CYCLE between workspace packages: @fx/core -> @fx/util -> @fx/core",
        "PHANTOM DEPENDENCY: @fx/app-b imports lodash",
        "PHANTOM DEPENDENCY: @fx/app-b imports @fx/core",
        "PHANTOM DEPENDENCY: @fx/app-b imports left-pad",
        "npm install lodash -w @fx/app-b",
        "FORBIDDEN EDGE (host -> miniapp): @fx/host -> @fx/app-a",
        "ISOLATED GROUP 'miniapp': @fx/app-a -> @fx/app-b",
        "LEAF GROUP 'design-system' depends on a consumer: @fx/ui -> @fx/app-b",
        "EXCEPTION WITHOUT A REASON: @fx/host -> @fx/app-a",
        "PHANTOM IGNORE WITHOUT A REASON",
        "CONFIG: unknown key 'isolate' in group 'design-system'",
    ]
    with_git = run(broken, "verify")
    expect("broken: every check fires", with_git, 1, violations,
           ["@fx/host -> @fx/app-c", "Why: Illustrative"])
    without_git = run(broken, "verify", no_git=True)
    expect("broken: same verdict without git (fallback walk)", without_git, 1, violations)
    same = sorted(line for line in with_git[1].splitlines() if line.startswith("  - ")) == \
        sorted(line for line in without_git[1].splitlines() if line.startswith("  - "))
    expect("broken: git and fallback report identical violations", (0, "" if same else "differs"), 0,
           absent=["differs"])

    expect("maven: verify with no config runs only the generic checks", run(maven, "verify"), 0,
           ["Clean topology: 1 packages", "only the generic checks ran"])
    expect("maven: route autodetects contexts from the reactor", run(maven, "route"), 0,
           ["Maven contexts", "billing", "Wallet, WalletRepository", "iam", "ApiKey", "2 contexts."],
           ["TypeScript packages", "gone"])
    expect("maven: route <term> finds the context", run(maven, "route", "wallet"), 0,
           ["'wallet' lives in:", "backend/contexts/billing", "Wallet"])
    expect("maven: route falls back to non-domain modules for operations",
           run(maven, "route", "refund"), 0, ["RefundService"])
    expect("maven: route says so when a term is unknown", run(maven, "route", "zzqx"), 0,
           ["does not appear"])
    expect("maven: route adds TS packages from config via HARNESS_DIR",
           run(maven, "route", harness=maven / "alt-harness"), 0,
           ["TypeScript packages", "model", "Money, Invoice, InvoiceRepository"])

    print(f"\n{'All assertions hold' if not FAILED else f'{len(FAILED)} failing'}"
          + (f"; fixtures kept in {base}" if keep else ""))
    if not keep:
        remove(base)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
