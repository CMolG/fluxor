# Fluxor

**The rules, skills and hooks your AI agents work with, in one place, installed into every repo
that needs them.**

An agent is only as good as the harness around it: what it knows about your project, the skills
it can load, the checks that stop it before it breaks something. Fluxor keeps that harness as
versioned items, assembles the right set for each project, and installs it into the repository
with one command (`fluxor-sync`), for Claude Code and Codex alike.

This repository is **Fluxor Local**: the free, self-hosted edition, running on your machine with
Docker. **[Fluxor Cloud](https://javadaba.com/catalogue/fluxor)** is the hosted edition that keeps
every machine and every teammate on the same harness.

## Quick start

You need Docker and Python 3.

```sh
git clone https://github.com/CMolG/fluxor.git
cd fluxor
docker compose up -d --build
```

The API listens on `http://127.0.0.1:18191/api`, and the MCP endpoint for your agents is
`http://127.0.0.1:18191/api/fluxor/mcp`.

1. Connect your agent and let it set up a harness project:

   ```sh
   claude mcp add --transport http fluxor http://127.0.0.1:18191/api/fluxor/mcp
   ```

   Ask it to create a harness project and pick items from the catalog (`harness.project.create`,
   `harness.catalog`, `harness.project.update`), or to run `harness.bootstrap`, which answers with
   the exact commands for your repository.

2. Install the harness into a repository:

   ```sh
   cd /path/to/your/repo
   mkdir -p .harness/bin
   curl -fsS http://127.0.0.1:18191/api/fluxor/v1/writer/fluxor-sync.py -o .harness/bin/fluxor-sync.py
   python3 .harness/bin/fluxor-sync.py init --server http://127.0.0.1:18191/api --enroll local --project <project-id>
   ```

3. From then on, `python3 .harness/bin/fluxor-sync.py pull` brings the repository up to date, and
   `fluxor-sync item publish` turns a folder of yours into an item (a skill, a hook or files).

Hooks run code on your machine, so `fluxor-sync` never wires one without your consent
(`fluxor-sync approve`). Everything listens on `127.0.0.1`. To require a token, set
`FLUXOR_LOCAL_TOKEN` before `docker compose up`; it then also becomes the enrollment code.

## What Fluxor Local gives you

- **The base catalog, built in.** 176 items: skills, roles, mods, steps, flows, hooks and presets
  (`packages/fluxor-market`). It covers code review, code reduction, a workspace topology check,
  layout discipline, UI fluidity checks, UX psychology, landing pages, launch readiness and more.
- **Atoms.** A role plus mods plus steps assembled for each task by a deterministic engine
  (`market/motor.py`), so the agent gets the instructions the task calls for, not all of them.
- **autoloop.** A skill that runs several agent sessions in parallel, each on a different card in
  its own git worktree, all integrating into one control branch, with a supervisor that clears each
  session's context between cards. It works the backlog of [Officium](https://github.com/CMolG/officium).
- **Your own items.** Publish a folder as a skill, hook or files item and select it into any
  project.
- **One harness, every client.** Skills, `AGENTS.md` and hook wiring for Claude Code and Codex,
  kept out of git when you want (`--storage local`).

## Local or Cloud

| | Local | Cloud |
| --- | :---: | :---: |
| Harness projects, items, `fluxor-sync` pull and publish | ✓ | ✓ |
| The base catalog and the atoms engine | ✓ | ✓ |
| MCP server for agents | ✓ | ✓ |
| autoloop and the Officium integration | ✓ | ✓ |
| Runs on your machine, nothing leaves it | ✓ | |
| One harness shared by a team, across every machine | | ✓ |
| The community marketplace, beyond the base catalog | | ✓ |
| Personal packs from the CEET interview (your working judgment as agents and skills) | | ✓ |
| The Fluxor web app: flow designer and harness library | | ✓ |
| Nothing to host or back up | | ✓ |

**[Try Fluxor Cloud](https://javadaba.com/catalogue/fluxor)**

## Background

Fluxor carries the harness of FIERCE, a framework for software development where agents do the
implementation and a few experts hold the decisions:

> Molina Galindo, C. (2026). *FIERCE: Fast Implementation Ensuring Results by Capable Experts.*
> [doi:10.5281/zenodo.23972303](https://doi.org/10.5281/zenodo.23972303)

## Repository layout

- `server/`: the API (Java, Quarkus): sync under `/api/fluxor/v1`, MCP under `/api/fluxor/mcp`.
  `fluxor-sync.py` ships inside it and is served at `/api/fluxor/v1/writer/fluxor-sync.py`.
- `packages/fluxor-market/`: the base catalog, its schemas and `tools/marketplace.py`.
- `scripts/seed-catalog.mjs`: regenerates the server's catalog seed from the catalog.
- `scripts/smoke.sh`: an end-to-end check, from `docker compose up` to a pulled harness.

This repository is published from the private monorepo where Fluxor is developed. Issues are
welcome; pull requests are ported by hand.

## License

[Elastic License 2.0](LICENSE). You may use, modify and self-host Fluxor for your own work and
your company's. You may not offer it to third parties as a hosted or managed service. See
[NOTICE](NOTICE).
