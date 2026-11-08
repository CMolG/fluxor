# Extending CEET with a New Role

> Adding a role takes one folder: a form, a profile template, its artifact templates, and a few
> hours of careful work. The catalog checks the coverage for you.

---

## When to Add a New Role

Add a role when:

- The existing roles do not capture a distinct cognitive domain
- You need a significantly different set of questions, not just adjustments
- The directive domains differ meaningfully from existing roles

**Do not add a role** when an existing one covers 80% of what you need — add questions and slots to
that role instead.

---

## The Files

A role is a meta-skill: a skill whose output depends on a form. It lives in
`meta-skills/ceet-<role>/`:

```
ceet-<role>/
├── skill.json                  manifest: packaging "meta", the form block, requires ceet-core@2
├── SKILL.md                    what the role listens for; the run order is ceet-core's protocol
├── README.md                   for people browsing the repository (not installed)
├── interview/
│   ├── form.json               the form, as data (schemas/form.schema.json)
│   └── questions.md            generated from form.json by `tools/marketplace.py forms`
├── templates/
│   ├── cognitive-profile.md    the profile: every {slot} the answers fill
│   ├── agents/ skills/ commands/ rules/
│   └── hooks/                  engineering roles only
└── evals/
    └── trigger-evals.json      queries that should and should not trigger the skill (not installed)
```

### `skill.json`

```json
{
  "$schema": "../../schemas/skill.schema.json",
  "id": "ceet-<role>",
  "kind": "skill",
  "version": "1.0.0",
  "packaging": "meta",
  "description": "One or two sentences for the catalog card.",
  "tags": ["ceet", "cognitive-profile", "<role>"],
  "domains": ["universal"],
  "requires": { "capabilities": ["fs.read", "fs.write"], "atoms": ["ceet-core@2"] },
  "form": {
    "questions": "interview/form.json",
    "profile": "templates/cognitive-profile.md",
    "templates": "templates"
  },
  "install": { "exclude": ["README.md", "evals/**"] }
}
```

### `SKILL.md`

Front matter `name` (equal to the folder) and `description` (what triggers it, under 1024
characters). The body follows the existing roles: what the skill does, when to use it and what it is
never for, the run order as a summary of [the interview protocol](interview-protocol.md), the
**role-specific things to listen for** (the signals that separate a senior practitioner of this role
from a textbook one, used as probes), synthesis guardrails specific to the role, and when to stop.

### `interview/form.json`

The form is data (`schemas/form.schema.json` in the repository):

- **Stable ids.** Questions are `Q1`, `Q2`, …; packs cite them. A new question takes the next free
  number wherever it goes; an id is never renumbered or reused. Changing what an id asks is a major
  bump of `formVersion`.
- **`feeds`.** The profile slots each answer is honest evidence for. Not wishful: a slot is fed only
  if a person answering the question would say something the slot needs.
- **Modules.** `core` (required; about 12–15 required questions that give evidence for the identity
  and the most consequential directives), `decisions` (required; five or six cognitive task analysis
  questions with `captures: ["decisions"]`: two incidents, a knowledge audit, a simulation on the
  person's own artifact, a contrast, a decision with limited information — see the protocol), and
  optional `depth-*` modules for the rest. Accuracy levels off once a domain has enough evidence, so
  depth is optional and `interview.py next` asks it where the profile is thin.
- **`derived`** for slots synthesized across the whole interview (`identity.contradictions`), and
  **`profileOnly`** for slots that stay in the profile (values, contradictions), each with a reason.
- **`routing.keywords`** for `ceet-autodiscover`: a new role needs no code change to be routed.

**Question writing rules:**

1. **Ask for specifics.** Bake "give a number", "give an example", "give an exception" into the question itself.
2. **Avoid yes/no questions.** Always ask for the reasoning.
3. **Favor real over ideal.** "What do you actually do" beats "what do you think is best"; a real
   case beats a general statement.
4. **Include the boundary.** Every question should also elicit when the rule breaks.
5. **One concept per question.** Do not combine unrelated ideas.

### `templates/cognitive-profile.md`

The profile: identity (`{identity.*}`), directives by domain (`{directives.<domain>.<field>}`), the
header slots (`{meta.*}`) and the role's name slot, with the front matter from the
[pack contract](pack-contract.md). Every slot is a value the synthesis must produce or mark not
synthesized. No scores, and nothing inferred about the person: those were removed on purpose.

### Artifact templates

Plain Markdown with `{slot}` placeholders and no logic. Each starts with a `<!-- CEET Source: ... -->`
comment naming the directives it consumes, then a `# Title` and a one-line `> ` description (the
adapters use it as the tool's `description`). Values and contradictions stay out of task templates.
Hooks describe judgment at a git event; what is mechanical goes to `checks` in the profile.

**Fewer, sharper artifacts.** Focused skills beat exhaustive documentation. Do not add an artifact
until a fidelity measurement ([fidelity](fidelity.md)) shows the ones you have are not enough.

---

## What the catalog checks

`python3 tools/marketplace.py validate` fails unless:

- `form.json` is valid and `questions.md` is its current rendering (`tools/marketplace.py forms`);
- every slot a template uses is declared by the profile;
- every slot the profile declares is fed by a question (or `derived`), every question feeds a slot
  (or captures decisions), and every slot is rendered by an artifact template (or `profileOnly`).

Then `python3 tools/marketplace.py lock` records the new atom, and `ceet-core`'s tests render a
synthetic pack for every role and validate it.

---

## Testing Your New Role

1. **Run the interview on yourself** with `interview.py`. If you cannot answer a question, rewrite it.
2. **Check for archetypes.** Read every question and directive domain — if any sounds like "Type A
   vs Type B", rewrite.
3. **Write trigger evals** (`evals/trigger-evals.json`): about 20 queries, half that should trigger
   the role and half near misses (a neighboring role, a simulation, doing the work without cloning
   anyone, evaluating people).
4. **Measure** a real pack with [fidelity](fidelity.md) before adding artifacts.
