# Synthesis Rules

> This document defines exactly how to turn raw interview responses into a cognitive profile and behavioral directives. Apply these rules rigorously — they are what prevents the system from sliding back into archetype classification.

---

## Rule 1: Verbatim Is Sacred

Raw responses must be stored **exactly** as the person said them.

- Do not fix grammar
- Do not shorten for concision
- Do not "clean up" language
- Do not paraphrase into a more "professional" version
- Do not merge multiple follow-ups into one synthesized response

If the person said "honestly I just vibe it" — that goes into `private/answers.json` exactly as written (`interview.py answer` records it). It is data, not embarrassment. The verbatim answers stay private; the shared profile carries the directives written from them.

---

## Rule 2: Never Classify

At no point during synthesis do you assign the person to a category.

**Forbidden:**
- "You are a Pragmatic Architect"
- "You fit the Growth Marketer archetype"
- "Your style is Early Adopter"
- "Based on your answers, you are a Strict Reviewer"

**Required:**
- Capture the specific behavior they described
- Write it in their voice
- Reference the questions it came from

If you find yourself typing "this person is X type" — delete it and write what they actually do instead.

---

## Rule 3: Directive Voice = Person's Voice

Directives are written as if the person is explaining their own approach.

**Wrong (external description):**
> "This engineer prefers strict typing and blocks PRs that loosen type safety."

**Right (first-person directive):**
> "I use strict mode always. `any` requires a comment explaining why, reviewed by me. If a PR adds `any` without justification I block it — no exceptions for deadline pressure. [Q6, Q8]"

The AI loading this directive should be able to act on it without translation.

---

## Rule 4: Concrete Over Abstract

If the person gave a number, include the number. If they gave an example, include the example. If they named a tool, name the tool.

**Wrong:**
> "I care about performance for critical endpoints."

**Right:**
> "Anything user-facing above 200ms at p95 I profile. I use `perf`, then flamegraphs, then statistical profiling in that order. Database queries over 50ms get an EXPLAIN before I move on. [Q16, Q19]"

Abstraction removes the fingerprint. Specifics preserve it.

---

## Rule 5: Contradictions Are Data

When two answers genuinely conflict, **do not reconcile them into a clean position**. Record the tension.

Example contradiction entry:
```json
{
  "tension": "Self-reports 6/10 on perfectionism but always creates separate refactoring tickets even for small messes, and insists on strict typing with zero exceptions.",
  "question_a": "Q2",
  "question_b": "Q26",
  "resolution": "In code quality this person acts at 8–9/10 perfectionism. In shipping deadlines they drop to 5–6. The 6/10 self-report is a shipping-context self-image that does not reflect their code review behavior."
}
```

The AI using this profile should consult contradictions when a request spans both contexts.

---

## Rule 6: Traceability Is Mandatory

Every directive must include `[Q<n>]` references in square brackets to the source questions. `Q<n>` is the question's **stable id** in the role's `interview/form.json` (ids are never renumbered; `cognitive-profile.json` records the `formVersion` they resolve against), and every cited question must have an answer in `private/answers.json`. A simulated pack cites rows of its evidence map as `[E<n>]` instead; the person's own wording from the teachback is cited as `[teachback]`. `validate_pack.py` checks all three.

Example:
> "I hash passwords with Argon2id, memory cost 19 MiB, time cost 2, parallelism 1. bcrypt is acceptable on legacy systems with cost 12+ until they can migrate. I do not accept SHA-anything for passwords — I have had to argue this three times in my career. [Q20, Q22]"

Traceability means when someone asks "why does the agent behave this way?", the answer is always: "Because the person said X in question Q.".

---

## Rule 7: No Scores

Never rate the person. Earlier versions put 16 composite scores (0–100) in every profile; they had no rubric, no question produced them, and a number like "perfectionism: 74" is profiling data about a person with no evidence behind it. Packs have no scores, and the validator rejects any that reappear.

**Wrong:**
> "This person's security paranoia is 9/10, so enforce strict rules..."

**Right:**
> "I do not trust internal-network service-to-service calls. I require mTLS or signed JWTs with short TTL between internal services. [Q57]"

Directives decide; nothing summarizes the person into a number.

---

## Rule 8: Identity Reflects All Answers

When writing `cognitive_signature`, `core_values`, and `decision_framework`, synthesize from the WHOLE interview. Do not write identity from just the universal questions — role-specific answers often reveal the strongest values.

Pattern to look for:
- A value the person mentions across 3+ unrelated questions is a core value, even if they never named it
- A phrase or metaphor the person repeats is a voice signature — preserve it
- A trade-off the person makes the same way across multiple questions is their decision framework

---

## Rule 9: Preserve Exceptions

The person's exceptions and edge cases are as important as their defaults. Every directive should include, where mentioned:

- The default rule
- The specific conditions under which they break it
- The specific conditions where they will not break it no matter what

Example:
> "I do not use emojis in commit messages. Exception: our team convention uses `:emoji:` prefixes and I comply to avoid churn. I never use emojis in code comments or customer-facing copy — that one I will not bend. [Q34, Q35]"

---

## Rule 10: Silence Is Also Data

What the person did NOT say matters.

What you infer from silence is an inference about the person, so it is **private**: write it to `private/reflection.md`, for their eyes only, never into a shared file, and never for a simulated pack. Look for:
- Domains they treated as obvious that may not be
- Groups of questions they answered thinly
- Trade-offs they did not acknowledge
- Stakeholders they did not mention
- Edge cases they did not consider

Derive it only from the content of the answers themselves, and phrase it as a question for the person, not a verdict.

Example (in `private/reflection.md`):
> "Across Q12–Q19 you described database design with strong performance instincts but never mentioned compliance, data retention policy, or deletion workflows. Is that deliberate, or worth a depth question?"

If the person wants an agent to act on it, it becomes a directive in their own words at the teachback, cited `[teachback]`.

---

## Rule 11: Do Not Generate Directives for Domains Not Covered

If a slot of the role's profile has no evidence in the answers, mark **that slot** not synthesized with a `_note`; the render writes "Not synthesized: <note>" in its place. Do not invent directives from thin air, and do not fill the gap with what a typical practitioner would do: where the person is silent, the base model's defaults would speak for them. `interview.py status` lists the slots without evidence; a depth question usually closes them.

Example in `cognitive-profile.json`:
```json
"directives": {
  "database": {
    "migration_playbook": {
      "_status": "not_synthesized",
      "_note": "Q46 was skipped. Ask it to complete this directive."
    }
  }
}
```

This keeps the clone honest about what it actually knows.

---

## Rule 12: Output Is Portable

Every generated artifact must be readable as standalone context by any AI system. That means:

- Full text, not placeholders, in the final output
- No references to "see other file" without the full content alongside
- No tool-specific syntax (no `@decorators`, no `::commands::`, no XML-only structures)
- Plain markdown headers and lists
- JSON only where structure matters (profile, decisions, answers)

Tool-specific wrappers (Claude Code agents and skills, Cursor rules, Copilot instructions, `AGENTS.md`, Agent Skills) are generated as **adapters** by `render_pack.py` on top of the portable output. The portable output is always the source of truth.

---

## Rule 13: Decisions Are Data

Every real decision the person described (the decision-capture answers above all, but any answer that told one) becomes an entry of `examples/decisions.json`: the situation, the cues they noticed, the options, what they chose, why, what a less experienced person would have done, and the question it came from. Use their words. One decision per entry; do not merge two cases into a composite. A few of these, retrieved for the task at hand, move a model toward the person more than pages of directives do.

---

## Rule 14: Checks Only From Precise Statements

A rule goes into `checks` (a commit message pattern, a banned construct in given files) only when the person stated it precisely enough that a machine can apply it without judgment, and only with the question it came from and, for a banned pattern, a line it must block and one it must pass. Everything else stays a directive: a check that enforces a preference ends up disabled, taking down what it really protected.

---

## Rule 15: A Re-profile Is a Diff, Not an Overwrite

When the person re-profiles, write the new synthesis to a scratch file (a copy of `cognitive-profile.json` with only the affected slots re-synthesized, and a copy of `examples/decisions.json` if decisions changed) and run `render_pack.py reprofile <pack> --profile <scratch>`. Never overwrite `cognitive-profile.json` in place: the old profile is what the diff is taken against, and `profile-changelog.md` is how the person, and anyone they share the pack with, sees what moved and why. Show the dry run to the person; `--write` only with their approval.
