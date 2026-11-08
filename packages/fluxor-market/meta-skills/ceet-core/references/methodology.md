# CEET Methodology

How a Cognitive Extraction Engine converts a conversation with a role-holder into a portable cognitive clone and a working AI environment.

## Why role-specific CEETs

A single generic "software professional" skill underfits every role. A backend engineer's cognitive model (systems, invariants, blast radius, data integrity) is almost disjoint from a copywriter's (voice, audience state-of-mind, conversion, brand consistency). Even inside engineering, a frontend engineer and an SRE watch for fundamentally different failure signals.

Each CEET is tuned to:

- The **artifacts** that role produces (code, docs, designs, contracts, forecasts, campaigns…)
- The **failure modes** that role is paid to prevent
- The **heuristics** that experienced practitioners use and novices don't
- The **tools and rituals** that role lives inside day-to-day

## The four stages

### 1. Interview

Each CEET ships a role-specific form in `interview/form.json` (rendered for people as
`interview/questions.md`): stable question ids, and for each question the profile slots its answer
feeds. It has three parts:

- **The core** — context, mental models, quality bar, heuristics, anti-patterns, voice: enough
  evidence for how the person reasons.
- **Real decisions** — cognitive task analysis on the person's own cases: a Critical Decision Method
  walk through real incidents, a knowledge audit ("what would a novice miss?"), a simulation on one of
  their real artifacts, a contrast between two options, and a decision with deliberately partial
  information. Experts leave out most of their decision steps when asked in general; specific cases
  recover them, and the answers become the pack's examples.
- **Depth modules** — optional, asked where the profile still lacks evidence.

The interview should feel conversational. The goal isn't to fill a form — it's to surface the *implicit* knowledge the person would never think to write down.

### 2. Extract

After the interview, the AI:

- Groups raw answers into themes
- Names each recurring heuristic
- Notes contradictions (these are usually where the best insights hide)
- Pulls out the person's vocabulary — the specific words they use for concepts
- Identifies the decisions they make **differently from the textbook**

### 3. Synthesize — the Cognitive Clone

The core output. Its layout is the role's `templates/cognitive-profile.md` (identity and directives by domain, every directive traced to the questions it came from), filled by following the [synthesis rules](synthesis-rules.md), plus the person's real decisions as examples. Whatever the layout, a cognitive clone captures six things:

1. **Identity & Context** — who, role, domain, stack, company shape
2. **Mental Models** — the models they use to think (e.g. "backend is a state machine", "copy is a conversation you're interrupting")
3. **Heuristics** — named, reusable rules of thumb
4. **Decision Procedures** — step-by-step workflows for recurring decisions
5. **Quality Signals** — how they tell good from bad
6. **Vocabulary & Voice** — the words they use, the tone they take

### 4. Activate — the AI Environment

`scripts/render_pack.py` renders every template in the role's `templates/` directory with the clone's values into a **pack**: a short always-on core, agents, skills, commands, rules and, for engineering roles, hooks whose mechanical part runs as checks. It's tool-agnostic Markdown that can be dropped into any AI assistant, with adapters for the tools that have native formats; its layout is the [pack contract](pack-contract.md), and loading it is [`tool-integration.md`](tool-integration.md).

### Then: measure

A pack claims to decide like the person. That claim is earned per person, against held-out decisions
and the person's own consistency, and against a baseline of their raw answers ([fidelity](fidelity.md)).

## Design principles

- **Role depth over breadth.** Better to ask 15 sharp role-specific questions than 50 generic ones.
- **Tool-neutral artifacts.** Nothing in the output assumes a specific AI vendor.
- **The clone is a document, not a prompt.** It should be readable by a human and usable by any model.
- **Make the implicit explicit.** The highest-value answers are the ones the person has never said out loud.
- **Update-friendly.** The clone is a living file. Re-run the CEET quarterly or after major role changes.

## When to use which CEET

Pick the CEET that matches the person's **primary accountability**, not their title. A "full-stack engineer" who spends 80% of their time on APIs and data should run the backend CEET. A "marketing manager" who actually writes most of the copy should run the copywriter CEET (or both).

If a person wears two hats, run two CEETs and merge the resulting clones by hand. Don't try to build a hybrid in one session — the interview questions drive the quality of the extraction, and a merged question set dilutes both.
