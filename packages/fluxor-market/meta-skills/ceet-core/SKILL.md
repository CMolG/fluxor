---
name: ceet-core
description: The shared method and tools behind the CEET meta-skills, the ceet-<role> skills that interview a professional (with consent) and turn the answers into a cognitive clone plus a pack of agents, skills, commands, rules and hooks. Holds the interview protocol and its resumable state, the consent record, the synthesis rules, the pack contract, the deterministic renderer with adapters for Claude Code, Cursor, Copilot, AGENTS.md and Agent Skills, the pack validator, the checks runner, decision retrieval, fidelity measurement, and how to add a role. Use when running, resuming or reviewing a CEET interview, synthesizing or correcting a cognitive profile, rendering, validating, installing or erasing a pack, measuring how well a pack decides like its person, or adding a new role. The role skills load its references.
---

# CEET core

CEET (Cognitive Extraction Engine Toolkit) captures how one person thinks in their role and makes
any AI tool work the same way for the same work. Each `ceet-<role>` skill is a **meta-skill**: it
ships the role's **form** (`interview/form.json`), its **profile** (the slots the answers fill) and
its **templates**. The output is a **pack** for that person. This skill holds what every role shares.

## The loop

```
CONSENT → INTERVIEW → SYNTHESIZE → TEACHBACK → RENDER → LOAD → MEASURE
record    core, real   profile,      the person   pack,     core     fidelity against
          decisions,   decisions,    accepts,     adapters, always,  held-out decisions
          depth        [Q<n>] refs   edits        checks    the rest and their own
                                     or rejects             on demand consistency
```

The protocol, step by step, is [`references/interview-protocol.md`](references/interview-protocol.md).

## Scripts

Standard-library Python 3.9+, run from this skill's folder. Each prints its usage with `--help`, and
locates the project from `$CLAUDE_PROJECT_DIR`, then git, then the current directory.

| Script | Does |
| --- | --- |
| `scripts/interview.py` | `statement`, `start` (records consent), `next` (what to ask, by the gaps in the profile), `answer` (verbatim), `skip`, `status`, `elicit` (a section as an MCP elicitation schema). The state is `<pack>/private/answers.json`. |
| `scripts/render_pack.py` | `render` (dry run, `--diff`, `--adapter ...`, `--write`), `teachback`, `apply-teachback`, `reprofile` (a new synthesis against the pack: what moved, the version bump, `profile-changelog.md`), `install` (adapters into the project, recorded for erasure), `erase`. |
| `scripts/validate_pack.py` | Validates a pack against its role, for interview and simulated packs alike. |
| `scripts/examples.py` | `select`: the person's decisions closest to a task. `inject`: the same as a Claude Code prompt hook. |
| `scripts/ceet_check.py` | The mechanical checks of a pack (secrets, commit message format, banned patterns): `bench`, git `pre-commit` / `commit-msg`, Claude Code `PreToolUse`. Fails open. |
| `scripts/fidelity.py` | Held-out decisions, the blind retest, prompts per arm, scoring with paired bootstrap intervals, blind pairwise judgments. |

## References

| File | Read it when |
| --- | --- |
| [`references/interview-protocol.md`](references/interview-protocol.md) | Running an interview from consent to a loaded pack; how to run each kind of decision-capture question. |
| [`references/consent.md`](references/consent.md) | Before the first question: the statement, the record, minimization, erasure, simulations, employers. |
| [`references/synthesis-rules.md`](references/synthesis-rules.md) | Before writing any directive. Fifteen rules: verbatim answers, never classify, first-person voice, concrete over abstract, contradictions as data, traceability, no scores, identity from all answers, exceptions, silence stays private, no directives without evidence, portable output, decisions as data, checks only from precise statements, a re-profile as a diff. |
| [`references/pack-contract.md`](references/pack-contract.md) | Writing, reading or validating a pack: layout, loading, rendering, `cognitive-profile.json`, `pack.json`, simulated packs, versioning. |
| [`references/tool-integration.md`](references/tool-integration.md) | Loading a pack into a specific AI tool; adapters; wiring checks. |
| [`references/fidelity.md`](references/fidelity.md) | Measuring whether a pack decides like its person. |
| [`references/how-to-use.md`](references/how-to-use.md) | Walking the person through what to expect, and the FAQ. |
| [`references/methodology.md`](references/methodology.md) | The why: role-specific engines, the stages, design principles, picking a role. |
| [`references/extending.md`](references/extending.md) | Adding a new role. |

The JSON formats are in `schemas/`: `cognitive-profile`, `pack`, `decisions`, `answers`, `heldout`.

## The family

| Skill | What it does |
| --- | --- |
| `ceet-<role>` | A meta-skill: the form, profile and templates of one role (list below). |
| `ceet-autodiscover` | Routes a request to a role (by each form's `routing.keywords`) and checks whether the project already has a pack for it. |
| `ceet-impersonator` | Fills a role's profile from evidence instead of an interview (public work, or the person's own consent): a simulated pack. |
| `ceet-sub-agent-orchestration` | Splits complex work across sub-agents, each bound to one role's pack, with validated handoffs. |

| Role | Focus |
| --- | --- |
| `ceet-backend-engineer` | Systems, data, invariants, failure modes, APIs |
| `ceet-frontend-engineer` | UI state, rendering, accessibility, client performance |
| `ceet-devops-sre` | Infrastructure, CI/CD, observability, incident response |
| `ceet-data-analytics` | Metrics, hypotheses, experimentation, SQL/Python |
| `ceet-product-manager` | Prioritization, discovery, roadmap, stakeholders |
| `ceet-ux-researcher` | Behavior, interviews, synthesis, jobs to be done |
| `ceet-ui-designer` | Visual system, components, motion, craft |
| `ceet-copywriter` | Voice, structure, conversion, brand tone |
| `ceet-marketing` | Positioning, channels, funnels, growth loops |
| `ceet-sales` | Discovery, objections, pipeline, closing |
| `ceet-customer-success` | Onboarding, retention, expansion, health signals |
| `ceet-financial` | Models, unit economics, forecasting, controls |
| `ceet-legal-compliance` | Contracts, risk, regulation, policy (a reasoning style, never legal advice) |
| `ceet-people-ops` | Hiring, performance, culture, policy design (never employment-law advice) |
| `ceet-founder-ceo` | Strategy, capital, narrative, org design |

Pick the role that matches the person's **primary accountability**, not their title. Someone who
wears two hats runs two interviews and gets two packs; merging question sets dilutes both.

## Rules that always hold

- **No consent, no interview**, and never for evaluating, hiring, allocating work to or monitoring the
  person ([consent](references/consent.md)).
- **Packs go to the project, never into a skill folder** (installed skills are managed files).
- **Never classify a person into an archetype, never score them**; capture what they actually do.
- **Never invent a directive** the answers do not support; mark the slot "not synthesized".
- **Inferences about the person stay private** (`private/reflection.md`), for their eyes only.
- **The person approves** the teachback and the rendered pack before anything is written or installed.
- **A simulated pack is labeled as one**: Simulation Notice on every file, a sourced evidence row for
  every directive, and the validator passes before anyone loads it.

## Evals

`evals/` (not installed) is a **smoke test**: three tasks scored for structure, required vocabulary
(whole words), planted-defect recall and forbidden phrases, across four arms (no pack, a persona, the
raw answers, the pack). It catches regressions; it does not measure fidelity, and no number from
hand-written outputs is published. See [`evals/README.md`](evals/README.md) and, for fidelity,
[`references/fidelity.md`](references/fidelity.md).
