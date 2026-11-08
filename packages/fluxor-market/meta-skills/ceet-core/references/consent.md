# Consent and personal data

A pack holds someone's verbatim answers and a profile of their working judgment. Under the GDPR
that is personal data, and a profile of "performance at work, reliability, behaviour" is
profiling. This page is what every CEET interview does about it. It is not legal advice; an
organization deploying packs for its staff needs its own assessment (see *Employers* below).

## Before the first question

Read the statement to the person, in full, and answer their questions about it. Then record their
answers with `scripts/interview.py start`; it refuses to start without `--consented`, and the
render refuses a pack without the consent record it writes.

```text
Before we start (CEET consent statement, version ceet-consent-1):

I am going to interview you about how you work, and turn your answers into a "pack": a profile of
your working judgment and files that make an AI assistant work the way you do.

- What is kept: your answers, word for word, and the profile written from them. Your answers stay
  in a private folder that is never shared or committed. The profile and the rest of the pack are
  what an assistant loads.
- What it is for: only the uses you name now. You can narrow them at any time.
- What it is never for: evaluating your performance, hiring or screening, allocating work by your
  traits, promotion or termination decisions, or monitoring you. Nobody may use the pack for these,
  whatever else you agree to.
- Where it lives: on this machine and out of version control, unless you choose to commit the shared
  part of it for your team. You decide who sees it.
- Your control: you can skip any question, read and correct everything written about you before it
  is used (the teachback), and have the whole pack erased, installed copies included.
- Sensitive details: health, beliefs, and other special categories stay out of the pack unless you
  decide a detail is about your work and want it kept.

Do you agree to go ahead on these terms? Which uses do you agree to, where should the pack be kept,
and who may see it?
```

### When Fluxor online keeps the answers

An interview answered in Fluxor online (instead of with `interview.py` on the person's machine)
keeps the answers on Javadaba's servers, so it reads a statement of its own. Fluxor shows it before
the first question and refuses an answer until the person agrees to it; `interview.py statement
--version ceet-consent-2` prints it.

```text
Before we start (CEET consent statement, version ceet-consent-2):

I am going to interview you about how you work, and turn your answers into a "pack": a profile of
your working judgment and files that make an AI assistant work the way you do. Fluxor online keeps
this interview on Javadaba's servers, under your Javadaba account.

- What is kept: your answers, word for word, and the pack made from them. Only your account can
  read them. Fluxor itself never sends your answers to an AI model: only the assistant you run, in
  your own session, reads them when you use it to answer or to write your profile.
- What it is for: only the uses you name now. You can narrow them at any time.
- What it is never for: evaluating your performance, hiring or screening, allocating work by your
  traits, promotion or termination decisions, or monitoring you. Nobody may use the pack for these,
  whatever else you agree to.
- Where it goes: Fluxor delivers the pack only to the projects you choose, on your own machines.
  Your word-for-word answers are never delivered to a project.
- How long: until you erase it, or until your account has been inactive for two years. You are
  reminded before anything is deleted.
- Your control: you can skip any question, read and download everything you answered at any time,
  correct any answer, and erase the interview. Withdrawing this consent erases your answers and
  the packs Fluxor keeps; copies already on your machines are removed there.
- Sensitive details: health, beliefs, and other special categories stay out of the pack unless you
  decide a detail is about your work and want it kept.

Do you agree to go ahead on these terms? Which uses do you agree to, and who may see the pack?
```

## The record

`interview.py start` writes the record into `private/answers.json`, and the synthesis copies it into
`cognitive-profile.json` and `pack.json` (`schemas/common.schema.json#/$defs/consent`):

| Field | Holds |
| --- | --- |
| `statementVersion` | `ceet-consent-1` for an interview on the person's machine, `ceet-consent-2` for one Fluxor online keeps (the statements above). A new version of the statement is a new consent. |
| `subject` | The person, by the name or alias they chose. |
| `basis` | `consent` for an interview. `public-work` only for a simulated pack of a public figure (below). |
| `recordedAt`, `recordedBy` | When, and who ran the interview. |
| `uses` | What the person agreed the pack is for, in their words. |
| `storage` | `local` (default: the pack is git-ignored) or `repository` (the person opted in to committing the shared part). |
| `sharedWith`, `retention` | Who may see it, and until when. |
| `excludedUses` | Always at least `performance-evaluation`, `hiring-or-screening`, `task-allocation-by-traits`, `promotion-or-termination`, `monitoring`. The validator rejects a record without them. |

Consent is specific to its uses. A new use (a team wants the pack, a new tool) is a new
conversation, and the record is updated with the person's answer.

## Minimization, built into the format

- **Private by default.** `private/` (verbatim answers, the interview state, the private reflection,
  the teachback) always carries a `.gitignore` that ignores everything. With `storage: local` the
  whole pack does too. Nothing loaded by an agent doing work reads `private/`.
- **No scores.** Composite scores had no method and never ship.
- **Inferred traits stay private.** What synthesis infers about the person (blind spots, patterns
  they did not state) goes to `private/reflection.md`, for their eyes only, never into a shared file.
  A simulated pack never infers traits at all.
- **Special categories stay out.** `validate_pack.py` rejects a shared directive that mentions health,
  religion, politics, sexuality, union membership and similar details, unless the person reviewed it
  and listed the slot in `review.specialCategoryCleared` because it is about their work.
- **Hidden text is removed.** Every value is sanitized before rendering: invisible and bidirectional
  characters are stripped, hidden comments and import lines are escaped, and instruction-like text is
  flagged for the person to review.

## Access, correction and erasure

- **Access:** the pack is plain files in the project; `private/answers.json` is the complete record.
- **Correction:** the teachback, or an edit to `cognitive-profile.json` and a re-render.
- **Erasure:** `render_pack.py erase <pack> --yes` removes the pack, the installed adapter files it
  recorded in `pack.json`, and its held-out decisions under `.harness/fidelity/<pack-id>/`. Copies
  outside the project (a chat's knowledge, another machine) must be removed there; the command says so.
- **In Fluxor online** (`ceet-consent-2`): the person downloads the interview as an
  `answers.json` (this schema, so `render_pack.py` reads it), replaces any answer, erases the
  interview, or withdraws the consent, which erases it too. The consent record itself is kept as
  proof of what was agreed.

## Simulated packs

`ceet-impersonator` builds packs without an interview. The rules are in its safety policy; in short:

- a **private individual** (a colleague, a repository author) is simulated only with that person's own
  consent, recorded as above (`basis: consent`); an operator's authorization is not enough;
- a **public figure** is simulated only from public, work-related material (`basis: public-work`),
  never used commercially or under their name in marketing, and every file carries the Simulation
  Notice.

## Employers

An organization that asks its staff to be profiled is in a different position from a person cloning
themselves: an employee's consent is rarely freely given, profiling employees with a new technology
usually calls for a data protection impact assessment, and in some countries (Germany, for example) a
works council co-decides on systems able to monitor behavior or performance. Using packs to evaluate
people, allocate tasks by their traits or screen candidates would make the system high-risk under the
EU AI Act. CEET does not support any of those uses; an employer deployment needs its own legal basis
and assessment before the first interview.
