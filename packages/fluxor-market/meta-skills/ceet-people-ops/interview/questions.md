# Interview — People Ops / HR

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 27 | ~33 | ~61 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: culture, policy, org design and fairness | 12 | — | ~25 | optional |
| Depth: heuristics and anti-patterns | 5 | — | ~10 | optional |
| Depth: working with others | 5 | — | ~13 | optional |

## Core interview

Who the person is and how they reason about People practices: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What's your scope — full People, Talent only, People Partner to a function, HR generalist?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

**Q2.** What's the org size, stage, distribution (in-person, hybrid, remote)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q3.** What's your tool stack (ATS, HRIS, performance tool, engagement survey)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q4.** Who do you partner with most closely?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

### B. Hiring bar

**Q5.** What do you hire on that most companies don't?

<sub>~3 min · feeds `directives.hiring.hire_on`, `identity.core_values`</sub>

**Q6.** What's the one thing you refuse to compromise on in hiring?

<sub>~2 min · feeds `directives.hiring.refuse_to_compromise`, `identity.core_values`</sub>

- Probe: When does that rule break, and when does it never break?

**Q7.** When you reject a candidate who everyone else loves, what's the signal you're responding to?

<sub>~3 min · optional · feeds `directives.hiring.reject_signal`</sub>

- Probe: Give me a recent, concrete example.

### C. Rubrics & process

**Q8.** Walk me through your interview rubric for a common role.

<sub>~4 min · feeds `directives.rubrics.rubric_walkthrough`</sub>

- Probe: Give me a recent, concrete example.

**Q9.** What signal do you trust in a loop? What signal do you distrust?

<sub>~2 min · feeds `directives.rubrics.trusted_signals`</sub>

**Q10.** How do you run a debrief — free-form, structured, voting, consensus?

<sub>~2 min · feeds `directives.rubrics.debrief_process`</sub>

**Q11.** How do you handle a strong "no" against a collective "yes"?

<sub>~2 min · optional · feeds `directives.rubrics.handle_strong_no`, `identity.decision_framework`</sub>

### D. Leveling & comp

**Q12.** What leveling framework do you use? Custom or off-shelf?

<sub>~2 min · optional · feeds `directives.leveling_comp.framework`</sub>

**Q13.** Your stance on comp transparency — bands published, internal-only, private?

<sub>~2 min · feeds `directives.leveling_comp.transparency_stance`</sub>

**Q14.** What's a comp decision you push back on most often?

<sub>~2 min · optional · feeds `directives.leveling_comp.pushback_decisions`</sub>

### E. Performance

**Q15.** Continuous feedback vs. formal reviews — your balance?

<sub>~2 min · optional · feeds `directives.performance.feedback_cadence`</sub>

**Q16.** Ratings, no ratings, narratives — what do you use and why?

<sub>~2 min · feeds `directives.performance.ratings_stance`</sub>

**Q17.** Calibration — how do you run it without making it theater?

<sub>~3 min · optional · feeds `directives.performance.calibration`</sub>

**Q18.** What do you refuse to include in a review?

<sub>~2 min · feeds `directives.performance.refuse_in_reviews`, `identity.core_values`</sub>

### F. PIPs & underperformance

**Q19.** What's your criteria for starting a PIP?

<sub>~2 min · feeds `directives.pip.start_criteria`, `identity.decision_framework`</sub>

- Probe: When does that rule break, and when does it never break?

**Q20.** What does a PIP require to be fair in your view?

<sub>~3 min · feeds `directives.pip.fairness_bar`</sub>

**Q21.** What's a PIP pattern you refuse to participate in?

<sub>~2 min · optional · feeds `directives.pip.refuse_to_participate`, `identity.core_values`</sub>

### G. Difficult conversations

**Q22.** Walk me through how you prepare for a hard conversation.

<sub>~3 min · feeds `directives.difficult_conversations.prepare_process`</sub>

- Probe: Give me a recent, concrete example.

**Q23.** What's your opener for delivering negative feedback?

<sub>~2 min · optional · feeds `directives.difficult_conversations.opener`, `identity.communication_voice`</sub>

**Q24.** What phrases do you reach for ("what I'm observing is…", "I want to be honest with you…")?

<sub>~2 min · optional · feeds `directives.difficult_conversations.reach_for_phrases`, `identity.communication_voice`</sub>

**Q25.** What's a phrase you ban in hard conversations ("just", "honestly", "don't take this personally")?

<sub>~2 min · feeds `directives.difficult_conversations.ban_phrases`, `identity.communication_voice`</sub>

### M. Vocabulary

**Q40.** People-ops phrases you use ("one-on-one", "check-in", "skip-level")?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

**Q41.** Phrases you ban ("culture fit", "family", "A-player")?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### O. Real decisions

**Q45.** Walk me through a departure you handled well and what made it so.

<sub>~8 min · incident · captures decisions · feeds `directives.difficult_conversations.prepare_process`, `identity.core_values`, `identity.decision_framework`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q44.** Walk me through a hire you're most proud of and why.

<sub>~6 min · incident · captures decisions · feeds `directives.hiring.hire_on`, `directives.hiring.reject_signal`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q47.** Think of a review or performance-plan draft a capable, less experienced manager sends you before delivering it, with the names taken out. What would they miss that you would catch? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.performance.refuse_in_reviews`, `directives.pip.fairness_bar`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q48.** Take an interview rubric or scorecard you use now, with no candidate's data in it, and rework it with me for your next opening. Narrate each change as you make it.

<sub>~8 min · simulation · captures decisions · feeds `directives.rubrics.rubric_walkthrough`, `directives.rubrics.trusted_signals`</sub>

- Probe: Why did you cut that?
- Probe: What would have made you keep it?

**Q49.** Think of two managers' requests to start a performance plan, one you supported and one you pushed back on (or build the pair now), without naming anyone. What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.pip.start_criteria`, `directives.pip.refuse_to_participate`</sub>

- Probe: Which detail would flip your verdict?

**Q50.** Here is all you get: a manager wants to let someone go this month for low performance, there is no written feedback on file, and that employee raised a complaint about the manager two weeks ago. What do you advise first, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.pip.fairness_bar`, `directives.meta_cognition.escalation_protocol`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you stop the process without knowing more?

## Depth: culture, policy, org design and fairness (optional)

How the person reads a team, writes policy, shapes the org and thinks about fairness.

### H. Culture diagnosis

**Q26.** What do you read in a team to sense culture — rituals, silence, meeting tone, DMs?

<sub>~2 min · optional · feeds `directives.culture.read_signals`</sub>

**Q27.** What's an engagement survey question you don't trust?

<sub>~2 min · optional · feeds `directives.culture.survey_stance`</sub>

**Q28.** What signal tells you a manager's team is quietly broken?

<sub>~2 min · optional · feeds `directives.culture.diagnosis_method`</sub>

- Probe: Give me a recent, concrete example.

### I. Policy drafting

**Q29.** What tone do you write policies in — formal, warm, terse, narrative?

<sub>~2 min · optional · feeds `directives.policy.voice`</sub>

**Q30.** What's a policy section you always include that most skip?

<sub>~2 min · optional · feeds `directives.policy.template`</sub>

**Q31.** What policies do you prefer to leave *implicit*?

<sub>~2 min · optional · feeds `directives.policy.template`, `identity.decision_framework`</sub>

**Q46.** How often do you review a policy, and what event makes you rewrite one before its review date?

<sub>~2 min · optional · feeds `directives.policy.update_cadence`</sub>

### J. Org design

**Q32.** What's your default span of control? When do you bend?

<sub>~2 min · optional · feeds `identity.decision_framework`</sub>

**Q33.** When should a team split, merge, or rotate?

<sub>~2 min · optional · feeds `identity.decision_framework`</sub>

**Q34.** What's an org-design mistake you've seen repeatedly?

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

### K. DEI & fairness

**Q35.** What do you measure about fairness / equity? What do you refuse to reduce to a metric?

<sub>~2 min · optional · feeds `identity.core_values`</sub>

**Q36.** What's a DEI practice you've seen fail, and what did you learn?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

## Depth: heuristics and anti-patterns (optional)

The person's rules of thumb and what they outgrew.

### L. Heuristics

**Q37.** "A good hiring signal is {X}; a fake one is {Y}."

<sub>~2 min · optional · feeds `directives.rubrics.trusted_signals`</sub>

**Q38.** "When a manager says their team is 'fine', I check {X}."

<sub>~2 min · optional · feeds `directives.culture.read_signals`</sub>

**Q39.** "A review is done when {X}."

<sub>~2 min · optional · feeds `directives.performance.refuse_in_reviews`, `directives.personality.quality_calibration`</sub>

### N. Anti-patterns

**Q42.** A People practice you outgrew.

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q43.** A trend you distrust (e.g. unlimited PTO, stack ranking, mandatory office).

<sub>~2 min · optional · feeds `identity.core_values`</sub>

## Depth: working with others (optional)

Uncertainty, crises, how the person has changed, focus and frustration.

### P. Working with others

**Q51.** When you are unsure about a call, how do you say so, and at what point do you escalate a decision instead of making it yourself? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q52.** A people crisis breaks: a harassment report about a senior leader, a layoff that leaks before it is announced, a public post from a former employee. What do you do in the first hour, and how do you talk to people while it is happening?

<sub>~3 min · optional · feeds `directives.meta_cognition.crisis_personality`</sub>

**Q53.** What people-practice belief did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q54.** When do you do your best work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q55.** What reliably frustrates you in how a company hires, reviews or treats its people?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
