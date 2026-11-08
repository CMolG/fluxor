# Interview — UX Researcher

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 24 | ~37 | ~61 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: interview craft and influence | 12 | — | ~28 | optional |
| Depth: heuristics and anti-patterns | 5 | — | ~10 | optional |
| Depth: working with others | 5 | — | ~13 | optional |

## Core interview

Who the person is and how they reason about research: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What research function do you own — embedded, center-of-excellence, solo?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

**Q2.** What product domain(s) do you work in?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q3.** How is research scoped into projects, and what's your typical cadence?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q4.** Who are your primary "customers" internally (PM, design, eng, exec)?

<sub>~2 min · feeds `identity.cognitive_signature`, `directives.communicating.show_to_team_vs_leadership`</sub>

### B. Framing

**Q5.** A stakeholder asks "can you study X?" — how do you reshape that into a research question?

<sub>~3 min · feeds `directives.research_framing.reshape_process`, `identity.decision_framework`</sub>

- Probe: Give me a recent, concrete example.

**Q6.** What's a request you routinely refuse (or reframe) before accepting?

<sub>~3 min · feeds `directives.research_framing.refuse_reframe`</sub>

- Probe: Give me a recent, concrete example.

**Q7.** How do you define *done* for a research project?

<sub>~2 min · feeds `directives.research_framing.done_definition`, `directives.personality.quality_calibration`</sub>

### C. Method selection

**Q8.** Walk me through your mental tree: when do you pick interviews, diary study, usability test, survey, analytics, ethnography?

<sub>~4 min · feeds `directives.method_selection.decision_tree`, `identity.decision_framework`</sub>

- Probe: When does that rule break, and when does it never break?

**Q9.** What's a method you rarely use but everyone else seems to reach for? Why?

<sub>~2 min · optional · feeds `directives.method_selection.rarely_used`</sub>

**Q10.** How do you decide between qualitative and quantitative for a given question?

<sub>~3 min · feeds `directives.method_selection.qual_vs_quant`</sub>

### D. Behavioral vs. attitudinal

**Q11.** What do you trust more — what users say, or what users do? When does that flip?

<sub>~3 min · feeds `directives.behavioral_vs_attitudinal.trust_hierarchy`, `identity.core_values`</sub>

- Probe: When does that rule break, and when does it never break?

**Q12.** How do you design a study that catches the gap between said and done?

<sub>~3 min · optional · feeds `directives.behavioral_vs_attitudinal.study_design`</sub>

### E. Recruiting

**Q14.** What are your recruiting standards? Who would you refuse to include?

<sub>~3 min · feeds `directives.recruiting.standards`, `directives.recruiting.refused_participants`</sub>

**Q15.** How do you handle incentives — amount, form, ethics?

<sub>~2 min · optional · feeds `directives.recruiting.incentives`, `directives.ethics.compensation`</sub>

- Probe: What number would you put on it?

**Q16.** What's your stance on convenience samples, and when is it OK to relax?

<sub>~2 min · optional · feeds `directives.recruiting.convenience_samples`</sub>

- Probe: When does that rule break, and when does it never break?

### G. Synthesis

**Q22.** Walk me through your synthesis workflow from raw notes to a claim.

<sub>~4 min · feeds `directives.synthesis.workflow`</sub>

- Probe: Give me a recent, concrete example.

**Q23.** Affinity, tagging, JTBD, behavioral archetype, user journey — what tools do you actually use and which do you distrust?

<sub>~3 min · optional · feeds `directives.synthesis.affinity_tools`, `directives.synthesis.jtbd_archetypes`</sub>

**Q24.** How many participants do you typically want before you'll make a claim? How do you justify that?

<sub>~3 min · feeds `directives.synthesis.saturation_criterion`</sub>

- Probe: What number would you put on it?

**Q25.** What's your saturation criterion?

<sub>~2 min · optional · feeds `directives.synthesis.saturation_criterion`</sub>

### I. Ethics & validity

**Q30.** What consent and recording policy do you enforce?

<sub>~3 min · feeds `directives.ethics.consent_protocol`, `directives.ethics.recording_policy`</sub>

**Q31.** What bias are you most worried about in your own work?

<sub>~2 min · optional · feeds `directives.meta_cognition.uncertainty_voice`</sub>

**Q32.** How do you handle sensitive topics (money, health, grief, frustration)?

<sub>~2 min · optional · feeds `directives.ethics.consent_protocol`, `directives.ethics.anonymization`</sub>

### L. Vocabulary

**Q39.** JTBD, need, goal, outcome, problem, opportunity — which do you use, strictly?

<sub>~2 min · optional · feeds `identity.communication_voice`, `directives.synthesis.jtbd_archetypes`</sub>

**Q40.** What phrases do you refuse to put in a readout ("users want", "proves", "validates")?

<sub>~2 min · feeds `identity.communication_voice`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### O. Real decisions

**Q44.** Pick a hard research decision from the last few months, one where reasonable researchers would have disagreed: a method, a sample, a claim you made or held back. Walk me through it from the first signal: what you noticed, the options you had, what you chose, and what made the difference.

<sub>~8 min · incident · captures decisions · feeds `identity.decision_framework`, `directives.method_selection.decision_tree`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q13.** What's a study you've run where stated preference and behavior diverged — what happened?

<sub>~6 min · incident · captures decisions · feeds `directives.behavioral_vs_attitudinal.divergence_examples`, `directives.behavioral_vs_attitudinal.trust_hierarchy`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q45.** Think of a study plan or discussion guide a colleague hands you for review. What would a capable, less experienced researcher miss in it that you would catch? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.interview_craft.unique_questions`, `directives.behavioral_vs_attitudinal.study_design`, `directives.recruiting.convenience_samples`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q43.** Walk me through the last study you ran — question, recruit, guide, sessions, synthesis, readout, impact.

<sub>~8 min · simulation · captures decisions · feeds `directives.synthesis.workflow`, `directives.communicating.readout_format`, `directives.research_framing.reshape_process`</sub>

- Probe: Why did you drop that thread?
- Probe: What would have made you run more sessions?

**Q46.** Think of two findings from the same study, one you put at the top of the readout and one you left out or softened (or build the pair now from a recent study). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.communicating.readout_format`, `directives.synthesis.saturation_criterion`</sub>

- Probe: Which detail would flip your verdict?

**Q47.** Here is all you get: five usability sessions, three participants failed the checkout task, two of them were recruited from your own customer list, and the team launches on Friday. What do you tell the team, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.synthesis.saturation_criterion`, `directives.recruiting.convenience_samples`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you tell them to hold the launch?

## Depth: interview craft and influence (optional)

How the person runs a session, reports findings and makes research change decisions.

### F. Interview craft

**Q17.** What's your go-to opener? Closer?

<sub>~2 min · optional · feeds `directives.interview_craft.opener_closer`</sub>

**Q18.** What question do you ask that most researchers don't?

<sub>~2 min · optional · feeds `directives.interview_craft.unique_questions`</sub>

**Q19.** How do you handle silence in an interview?

<sub>~2 min · optional · feeds `directives.interview_craft.silence_handling`</sub>

**Q20.** What's a technique (laddering, critical incident, think-aloud) you use most, and what's your twist on it?

<sub>~3 min · optional · feeds `directives.interview_craft.laddering_twist`</sub>

- Probe: Give me a recent, concrete example.

**Q21.** When a participant says something you strongly disagree with, what do you do?

<sub>~2 min · optional · feeds `identity.core_values`</sub>

### H. Communicating findings

**Q26.** What format do you use for a readout — deck, doc, video?

<sub>~2 min · optional · feeds `directives.communicating.readout_format`</sub>

**Q27.** What goes at the top of a readout?

<sub>~2 min · optional · feeds `directives.communicating.readout_format`</sub>

**Q28.** What do you show leadership vs. the team?

<sub>~2 min · optional · feeds `directives.communicating.show_to_team_vs_leadership`</sub>

**Q29.** What's a finding you're proud of that changed a decision? How'd you make it land?

<sub>~3 min · optional · feeds `directives.communicating.influence_pattern`</sub>

- Probe: Give me a recent, concrete example.

### J. Influence & politics

**Q33.** What do you do when leadership ignores research?

<sub>~3 min · optional · feeds `directives.communicating.influence_pattern`</sub>

**Q34.** What do you do when research says "don't ship" and the team ships anyway?

<sub>~3 min · optional · feeds `directives.communicating.influence_pattern`, `directives.meta_cognition.escalation_protocol`</sub>

- Probe: Give me a recent, concrete example.

**Q35.** How do you build trust with skeptical engineers or execs?

<sub>~2 min · optional · feeds `directives.communicating.influence_pattern`</sub>

## Depth: heuristics and anti-patterns (optional)

The person's rules of thumb and what they outgrew.

### K. Heuristics

**Q36.** "When a participant says 'I would pay for that', I {X}."

<sub>~2 min · optional · feeds `directives.behavioral_vs_attitudinal.trust_hierarchy`</sub>

**Q37.** "I don't trust usability data from fewer than {N} participants doing {X}."

<sub>~2 min · optional · feeds `directives.synthesis.saturation_criterion`</sub>

**Q38.** "If a behavior shows up in {X}% of participants, I consider it {Y}."

<sub>~2 min · optional · feeds `directives.synthesis.saturation_criterion`</sub>

### M. Anti-patterns

**Q41.** What's a research pattern you outgrew?

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q42.** What's a method or artifact that's trendy now but you don't trust?

<sub>~2 min · optional · feeds `identity.core_values`, `directives.synthesis.affinity_tools`</sub>

## Depth: working with others (optional)

Uncertainty, crises, how the person has changed, focus and frustration.

### P. Working with others

**Q48.** When you are unsure about a call, how do you say so, and at what point do you escalate a decision instead of making it yourself? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q49.** A session goes wrong: a participant is distressed, or a recording with personal data ends up where it should not. What do you do in the first hour, and how do you talk to people while it is happening?

<sub>~3 min · optional · feeds `directives.meta_cognition.crisis_personality`</sub>

**Q50.** What research belief did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q51.** When do you do your best work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q52.** What reliably frustrates you in how a team commissions, runs or uses research?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
