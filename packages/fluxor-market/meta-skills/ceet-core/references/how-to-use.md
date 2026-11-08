# How to Use CEET

> A practical walk-through for the person being interviewed. The agent follows the
> [interview protocol](interview-protocol.md); this page is what to expect.

---

## Step 1: Pick Your Role

Browse the `ceet-<role>` meta-skills (or let `ceet-autodiscover` suggest one) and pick the one that
matches your **primary accountability**, not your title. You can run CEET once per role if you wear
several hats.

Common pairings:
- Technical founder → `founder-ceo` + `backend-engineer` or `frontend-engineer`
- Designer-developer → `ui-designer` + `frontend-engineer`
- Growth person → `marketing` + `copywriter`
- Solo operator → `founder-ceo` + whatever else you spend most time on

Each role produces its own pack. Do not try to merge.

---

## Step 2: Agree on the Terms

Before the first question the agent reads you a short consent statement
([consent](consent.md)): what is kept, what it is for, what it is never for (evaluating you, hiring,
allocating work by your traits, monitoring), where it lives, and that you can correct or erase all
of it. You say which uses you agree to and where the pack should live. Nothing starts without it.

---

## Step 3: Set Aside Some Real Decisions (Optional)

If you want to know how well the clone decides like you, give the agent 20–40 of your real past
decisions first (the situation, the options, what you chose). They are kept apart and never shown to
the synthesis; two weeks later you redo a few of them blind, and the clone is measured against your
own consistency ([fidelity](fidelity.md)).

---

## Step 4: The Interview

About **70 minutes** for the required part, which you can split across sessions:

- **The core**: how you reason and what you hold to, about 35–40 minutes.
- **Real decisions**: five or six of your own cases, walked through step by step (what you noticed,
  what you considered, what you chose, what someone newer would have done), about 30–35 minutes. These
  become the examples the clone learns from, so bring real ones.
- **Depth modules** (optional): the agent suggests the ones that fill gaps in your profile.

Answer honestly and specifically:

- **Be specific.** "I like clean code" is useless. "I set my linter to error on any `any` in TypeScript and I do not merge PRs that add them" is useful.
- **Use real examples.** Stories from the last 30 days beat abstract principles.
- **Include exceptions.** "I always X, except when Y" is gold.
- **Surface your contradictions.** If you say one thing in Q2 and another in Q26, the agent will notice — help it.
- **Skip what does not apply.** A skipped question leaves its part of the profile "not synthesized", never invented.

Your answers are recorded word for word in a private file.

---

## Step 5: The Teachback

The agent shows you every directive it wrote, each with the answers it came from. For each one you
say **accept**, **edit** (in your words) or **reject**. Your edits are kept: they are the most direct
evidence of how you think. Blind spots the agent inferred are shown to you privately and never ship
unless you turn one into a directive yourself.

---

## Step 6: The Pack

The agent renders the pack, shows you what it will write, and writes it once you approve
([pack contract](pack-contract.md)). The part an AI loads on every task is `core.md`, a short page;
everything else loads with the task that needs it, and your real decisions are retrieved when a task
resembles one.

---

## Step 7: Load It Into Your Tools

The agent renders adapters for the tools you use (Claude Code, Cursor, Copilot, `AGENTS.md`, Agent
Skills) and installs them after you approve ([tool integration](tool-integration.md)).

---

## Step 8: Test and Re-profile

Ask your AI to do something you would normally do. When it decides differently from you, find the
directive or the missing decision, correct it, and re-render. Re-run CEET every 6–12 months or after
a significant role change: you see your previous answers, say what changed, and a
`profile-changelog.md` records what moved.

---

## FAQ

**Can I skip questions?** Yes. Skipped questions show up as gaps in the clone, never as guesses.

**Can I do the interview in multiple sessions?** Yes. The interview state is a file; it resumes.

**Can I run this on a colleague?** Only with their consent, recorded as above, and only for uses
they agree to. Never to evaluate them.

**What if I hate the synthesis?** Say which parts feel wrong at the teachback; the agent revises
those, not everything.

**Can I hand-edit the profile?** Yes: edit `cognitive-profile.json`, keep the `[Q<n>]` references, and
re-render.

**How do I delete everything?** `render_pack.py erase <pack> --yes` removes the pack, the files it
installed in your tools, and the held-out decisions.
