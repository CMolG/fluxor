# Interview — Product Manager

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 24 | ~36 | ~63 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: roadmap and specs | 7 | — | ~17 | optional |
| Depth: partners, heuristics and anti-patterns | 8 | — | ~17 | optional |
| Depth: working with others | 5 | — | ~13 | optional |

## Core interview

Who the person is and how they reason about product: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What product (or product area) do you own, and what stage is it at?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

**Q2.** Who are your users, and what's the primary job they hire your product for?

<sub>~3 min · feeds `identity.cognitive_signature`, `directives.problem_framing.real_problem_test`</sub>

**Q3.** What's your team shape (eng, design, data, GTM support)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q4.** How are you measured, and how's your product measured?

<sub>~2 min · optional · feeds `identity.cognitive_signature`, `directives.success_metrics.define_before_ship`</sub>

### B. Problem framing

**Q5.** When someone comes to you with a feature request, what's the first thing you do?

<sub>~3 min · feeds `directives.problem_framing.feature_vs_problem`, `identity.decision_framework`</sub>

- Probe: Give me a recent, concrete example.

**Q6.** How do you distinguish a real user problem from a requested solution?

<sub>~3 min · feeds `directives.problem_framing.real_problem_test`, `directives.problem_framing.feature_vs_problem`</sub>

- Probe: When does that rule break, and when does it never break?

### C. Discovery

**Q8.** What's your cadence for talking to users directly?

<sub>~2 min · feeds `directives.discovery.user_talk_cadence`</sub>

- Probe: What number would you put on it?

**Q9.** What signal are you most likely to *over*-weight? Most likely to *under*-weight?

<sub>~3 min · optional · feeds `directives.discovery.signal_weighting`</sub>

- Probe: Give me a recent, concrete example.

**Q10.** What do you do when quantitative data says one thing and qualitative says another?

<sub>~3 min · optional · feeds `directives.discovery.quant_vs_qual_conflicts`</sub>

- Probe: Give me a recent, concrete example.

### D. Prioritization

**Q11.** Walk me through how you actually prioritize — not the framework you'd post on LinkedIn.

<sub>~4 min · feeds `directives.prioritization.actual_process`, `identity.decision_framework`</sub>

- Probe: Give me a recent, concrete example.

**Q12.** What weight do you really give to each of: revenue, retention, strategic moat, team morale, tech debt, customer promises, exec asks?

<sub>~3 min · feeds `directives.prioritization.weight_factors`, `identity.core_values`</sub>

- Probe: What number would you put on it?

**Q13.** When two things look equally important, what's your tiebreaker?

<sub>~2 min · feeds `directives.prioritization.tiebreakers`, `identity.decision_framework`</sub>

### G. Success metrics

**Q21.** How do you define success *before* shipping?

<sub>~3 min · feeds `directives.success_metrics.define_before_ship`</sub>

**Q22.** What's a guardrail metric you always include?

<sub>~2 min · optional · feeds `directives.success_metrics.guardrails`</sub>

**Q23.** How do you decide a feature "didn't work"? What's the kill criteria?

<sub>~3 min · feeds `directives.success_metrics.kill_criteria`</sub>

- Probe: What number would you put on it?

### H. Shipping judgment

**Q24.** Polish vs. ship — where's your default, and what pulls you off it?

<sub>~3 min · feeds `directives.shipping.polish_vs_ship`, `directives.personality.quality_calibration`</sub>

- Probe: When does that rule break, and when does it never break?

**Q25.** Vertical slice vs. horizontal foundation — what's your instinct?

<sub>~2 min · optional · feeds `directives.shipping.vertical_vs_horizontal`</sub>

**Q26.** Build vs. buy vs. partner — how do you decide?

<sub>~3 min · optional · feeds `identity.decision_framework`</sub>

**Q27.** Feature vs. fix — how do you balance new work and quality work?

<sub>~2 min · optional · feeds `identity.decision_framework`, `identity.core_values`</sub>

### I. Stakeholder management

**Q28.** When an exec drops in with "we should do X", what's your standard response pattern?

<sub>~3 min · feeds `directives.stakeholder.exec_escalation`</sub>

- Probe: Give me a recent, concrete example.

**Q29.** When sales asks for a feature to close a deal, what's your framework?

<sub>~3 min · optional · feeds `directives.stakeholder.sales_asks`</sub>

**Q30.** How do you say no to a peer team's ask?

<sub>~3 min · optional · feeds `directives.stakeholder.saying_no_script`</sub>

- Probe: Give me a recent, concrete example.

### L. Vocabulary

**Q37.** Do you use "user story" / "JTBD" / "opportunity" / "problem" — and how strictly?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

**Q38.** What phrases do you ban in your team's writing (e.g. "leverage", "synergies", "MVP")?

<sub>~2 min · feeds `identity.communication_voice`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### O. Real decisions

**Q42.** Pick a hard product decision from the last few months, one where reasonable product managers would have disagreed: a scope cut, a bet, a sequencing call, a change of metric. Walk me through it from the first signal: what you noticed, the options you had, what you chose, and what made the difference.

<sub>~8 min · incident · captures decisions · feeds `identity.decision_framework`, `directives.prioritization.actual_process`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q7.** What's a feature you killed that everyone else wanted shipped? Why?

<sub>~6 min · incident · captures decisions · feeds `directives.problem_framing.killed_features`, `directives.stakeholder.saying_no_script`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q43.** Think of a PRD or a feature request landing on your desk this week. What would a capable, less experienced product manager miss in it that you would catch? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.problem_framing.real_problem_test`, `directives.specs.refuse_insist`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q41.** Walk me through the last spec you wrote end-to-end. The frame, the cuts, the arguments, the final shipped version.

<sub>~8 min · simulation · captures decisions · feeds `directives.specs.template_sections`, `directives.specs.length_policy`</sub>

- Probe: Why did you cut that?
- Probe: What would have made you keep it?

**Q44.** Think of two roadmap items that looked equally important, one you put first and one you pushed back (or build the pair now from your backlog). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.prioritization.tiebreakers`, `directives.prioritization.weight_factors`</sub>

- Probe: Which detail would flip your verdict?

**Q45.** Here is all you get: two weeks after launch, the feature's adoption is 4% against a 15% target, retention of the users who adopted it is up, and sales says three deals depend on it. What do you do first, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.success_metrics.kill_criteria`, `directives.success_metrics.guardrails`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you kill it without knowing more?

## Depth: roadmap and specs (optional)

How the roadmap communicates and what a spec carries.

### E. Roadmap

**Q14.** Dates vs. outcomes vs. themes — what does your roadmap actually communicate?

<sub>~3 min · optional · feeds `directives.roadmap.dates_vs_outcomes`</sub>

**Q15.** How do you handle asks for firm dates on things that shouldn't have them yet?

<sub>~3 min · optional · feeds `directives.roadmap.firm_date_handling`</sub>

- Probe: Give me a recent, concrete example.

**Q16.** What goes *above* the roadmap (too strategic), and what's *below* it (too tactical)?

<sub>~2 min · optional · feeds `directives.roadmap.above_below_roadmap`</sub>

### F. Specs / PRDs

**Q17.** Do you have a default PRD template? Walk me through the sections.

<sub>~3 min · optional · feeds `directives.specs.template_sections`</sub>

**Q18.** What's one section most PMs include that you refuse to?

<sub>~2 min · optional · feeds `directives.specs.refuse_insist`</sub>

**Q19.** What's one section you insist on that most skip?

<sub>~2 min · optional · feeds `directives.specs.refuse_insist`</sub>

**Q20.** How long is too long for a PRD in your view?

<sub>~2 min · optional · feeds `directives.specs.length_policy`</sub>

- Probe: What number would you put on it?

## Depth: partners, heuristics and anti-patterns (optional)

Working with engineering, design and data, the person's rules of thumb, and what they outgrew.

### J. Cross-functional

**Q31.** What's the ideal working relationship with your eng lead? What breaks it?

<sub>~3 min · optional · feeds `directives.stakeholder.eng_pushback`</sub>

**Q32.** What do you want design to bring to kickoff that they often don't?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q33.** How do you use data/analytics — embedded, as-service, or DIY SQL?

<sub>~2 min · optional · feeds `directives.discovery.quant_vs_qual_conflicts`</sub>

### K. Heuristics

**Q34.** "If I can't state the user problem in one sentence, {X}."

<sub>~2 min · optional · feeds `directives.problem_framing.real_problem_test`</sub>

**Q35.** "When a feature has three primary metrics, {X}."

<sub>~2 min · optional · feeds `directives.success_metrics.define_before_ship`, `directives.success_metrics.guardrails`</sub>

**Q36.** "I stop discovery when {X}."

<sub>~2 min · optional · feeds `directives.discovery.signal_weighting`</sub>

### M. Anti-patterns

**Q39.** What's a PM pattern you used to follow and now reject?

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q40.** What's a trend in product culture that you distrust?

<sub>~2 min · optional · feeds `identity.core_values`</sub>

## Depth: working with others (optional)

Uncertainty, crises, how the person has changed, focus and frustration.

### P. Working with others

**Q46.** When you are unsure about a call, how do you say so, and at what point do you escalate a decision instead of making it yourself? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q47.** A launch goes wrong in public: a pricing error, an outage on launch day, a change that angers your best customers. What do you do in the first hour, and how do you talk to people while it is happening?

<sub>~3 min · optional · feeds `directives.meta_cognition.crisis_personality`</sub>

**Q48.** What product belief did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q49.** When do you do your best work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q50.** What reliably frustrates you in a team's product habits or in how decisions get made?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
