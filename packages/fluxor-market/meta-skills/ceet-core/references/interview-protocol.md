# Interview protocol

The run order every `ceet-<role>` skill follows. The role supplies the form
(`interview/form.json`), the profile and the templates; this page and the scripts in
`../scripts/` supply the rest. Paths to scripts are relative to `ceet-core`; `<role>` is the role's
skill id (`ceet-backend-engineer`), `<pack>` the pack id or folder (`backend-engineer-alex`).

```
consent → held-out decisions (optional) → core → real decisions → depth (optional)
       → synthesis → teachback → render (dry run, approval, write) → validate → adapters
```

## 1. Consent

Read the statement (`python3 scripts/interview.py statement`) and follow
[`consent.md`](consent.md). Only when the person agrees:

```bash
python3 scripts/interview.py start --role <role> --person alex --name Alex \
  --use "help me review code the way I do" --storage local --consented
```

This creates `.harness/packs/<role without ceet->-alex/` with `private/answers.json` (the consent
record and, from now on, every answer) and the `.gitignore` files that keep it private.

## 2. Held-out decisions (optional, before the interview)

If the person wants to know how well the clone decides like them, collect 20–40 of their real past
decisions **before** the interview, with `scripts/fidelity.py add`, and never show them to the
synthesis. See [`fidelity.md`](fidelity.md). Ask the person not to retell those cases in the
interview; `fidelity.py prompts` warns about overlaps.

## 3. The interview

```bash
python3 scripts/interview.py next --pack <pack>            # what to ask next, and why
python3 scripts/interview.py answer --pack <pack> --question Q5 --text "..."
python3 scripts/interview.py answer --pack <pack> --question Q5 --probe "Give me a recent example" --text "..."
python3 scripts/interview.py skip --pack <pack> --question Q3 --reason "..."
python3 scripts/interview.py status --pack <pack>          # slots still without evidence, minutes left
```

- **One question at a time**, conversationally, in the form's order. Never dump the list.
- **Record verbatim** (synthesis rule 1): paste the person's words, not your summary. A follow-up is
  recorded with `--probe`, under the question it followed.
- **Probe vague answers** with the question's `probes`, or: a recent example, a number, the exception,
  what would change their mind. When the person says "it depends", ask what it depends on.
- **The core and the real decisions are required.** The depth modules are optional; `next` proposes
  the depth questions that give evidence to slots nobody has answered yet, so the person's time goes
  where the profile is thin. A slot left without evidence is "not synthesized", never invented.
- **Resume** any time: the state is the file. `status` says what is left.

### Real decisions: how to run them

The decision-capture module applies cognitive task analysis to the person's own cases. Experts leave
out most of their decision steps when asked in general; walking through a specific case recovers them.

| Kind | How to run it |
| --- | --- |
| `incident` (Critical Decision Method) | Ask for one real, recent, non-routine case. Let them tell it once. Then walk the timeline again and stop at each decision point: what did you notice (the cues), what did you expect, what options did you consider, what did you choose, what would a less experienced person have done, what would have changed your mind. |
| `knowledge-audit` | Ask what a capable but less experienced practitioner would miss in a familiar situation, and for the cues they see. Ask how they would teach someone to see each cue. |
| `simulation` | The person brings one of their real artifacts (a pull request they reviewed, a PRD, a contract they redlined). They walk through it the way they did: where they slowed down, what they flagged, what they let go, and why. |
| `contrastive` | Two concrete options for the same problem (two proposals they saw, or a pair you build from their own context). Which one, and exactly what made the difference; which detail would flip the verdict. |
| `limited-information` | A short situation with deliberately partial information. What do they do first, and what is the one extra piece of information they ask for, and why that one. |

Every decision-capture answer becomes one or more entries of `examples/decisions.json`
(`../schemas/decisions.schema.json`): the situation, the cues, the options, the choice, the
rationale, what a novice would do, and the question it came from.

## 4. Synthesis

When `status` says the required questions are done, write, in the pack folder:

| File | Holds | Rules |
| --- | --- | --- |
| `cognitive-profile.json` | Every slot of the role's profile as data (`../schemas/cognitive-profile.schema.json`): `name`, `consent` (copied from `private/answers.json`), `identity`, `directives`, `contradictions`, and `checks` when the person stated a rule precisely enough to check. | [Synthesis rules](synthesis-rules.md): verbatim-rooted, first person, `[Q<n>]` references to answered questions, not synthesized when there is no evidence. |
| `examples/decisions.json` | The real decisions from the decision-capture answers (and any other answer that told one). | Their words; no decision the person did not describe. |
| `private/reflection.md` | What you infer that they did not say: possible blind spots, thin areas, unacknowledged trade-offs. | For the person's eyes only; never in a shared file; never for a simulated pack. |

`cognitive-profile.md` is not written by hand: the render produces it from the JSON.

## 5. Teachback

```bash
python3 scripts/render_pack.py teachback <pack>
```

writes `private/teachback.md` (each directive with the answers it came from) and
`private/teachback.json` (one verdict per directive). Go through it with the person: **accept**,
**edit** (their wording goes in `text`), or **reject**. Then:

```bash
python3 scripts/render_pack.py apply-teachback <pack> --write
```

An edit replaces the directive (cited as `[teachback]` when the person's wording cites no question);
a rejection marks it not synthesized. The edits are the most direct evidence of how the person
thinks: keep them.

## 6. Render, approve, validate

```bash
python3 scripts/render_pack.py render <pack> [--adapter claude-code --adapter cursor ...]     # dry run
python3 scripts/render_pack.py render <pack> --diff                                          # what changes
python3 scripts/render_pack.py render <pack> --adapter ... --write
python3 scripts/validate_pack.py .harness/packs/<pack>
```

The dry run lists every file the render would add or change, and every value the sanitizer changed
or flagged. Show it to the person before `--write`. The render refuses to write while any check
fails: no consent record, a slot with neither a value nor "not synthesized", a directive without
references, a reference to an unanswered question, a special-category detail the person did not
clear. The pack layout is the [pack contract](pack-contract.md).

## 7. Load it

Install the adapters the person uses (`render_pack.py install <pack> --adapter <tool>`, dry run
first, `--yes` after approval) or follow [tool integration](tool-integration.md). Hooks are wired only
when `bin/ceet_check.py bench` is green, and only after the person approves them.

## Re-profiling

Keep the previous pack. Show the person their previous answers (`private/answers.json`); record what
changed with `interview.py answer --replace`, and re-synthesize only the affected directives into a
**scratch copy** of `cognitive-profile.json` (never the pack's own file). Then
`render_pack.py reprofile <pack> --profile <scratch>`: show the person what moved, and with their yes
re-run it with `--write`, which bumps `meta.version`, adds the entry to `profile-changelog.md` and
re-renders ([pack contract](pack-contract.md)). If the role's form has a new major version, map old
answers to the new question ids by hand and synthesize against the new form: the changelog entry says
the form changed.
