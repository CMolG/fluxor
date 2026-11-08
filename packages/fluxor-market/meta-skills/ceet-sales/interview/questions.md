# Interview — Sales

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 26 | ~35 | ~60 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: champions, outreach and closing | 11 | — | ~24 | optional |
| Depth: heuristics and anti-patterns | 5 | — | ~10 | optional |
| Depth: working with others | 5 | — | ~13 | optional |

## Core interview

Who the person is and how they reason about selling: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What do you sell, to whom, at what ACV, with what sales cycle?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

**Q2.** What's your motion (inbound, outbound, SLG, PLG hybrid)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q3.** What's your territory / segment / quota shape?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q4.** Who's in your deal pod (SE / SC, AM, CS, exec sponsor)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`, `directives.multi_threading.when_bring_exec`</sub>

### B. ICP & qualification

**Q5.** Describe your best-fit buyer — role, company shape, trigger event.

<sub>~3 min · feeds `directives.icp_qualification.best_fit`</sub>

- Probe: Give me a recent, concrete example.

**Q6.** What's a fast disqualification signal you've learned the hard way?

<sub>~3 min · feeds `directives.icp_qualification.fast_disqualify`, `identity.decision_framework`</sub>

- Probe: When does that rule break, and when does it never break?

**Q7.** How do you tell "not now" from "not ever"?

<sub>~2 min · feeds `directives.icp_qualification.not_now_vs_not_ever`</sub>

### C. Discovery

**Q8.** What's your opening for a first call — literal words?

<sub>~2 min · feeds `directives.discovery.first_call_opening`, `identity.communication_voice`</sub>

**Q9.** What's your must-ask question that most reps skip?

<sub>~2 min · feeds `directives.discovery.must_ask_questions`</sub>

**Q10.** How do you avoid demo-leading when they push for a demo early?

<sub>~2 min · optional · feeds `directives.discovery.avoid_early_demo`</sub>

**Q11.** What do you listen for beneath the words — pauses, hedges, pronoun shifts?

<sub>~3 min · optional · feeds `directives.discovery.listen_beneath`</sub>

- Probe: Give me a recent, concrete example.

### D. Methodology

**Q12.** MEDDICC / SPICED / Challenger / Sandler — what do you use and how have you customized it?

<sub>~3 min · feeds `directives.methodology.framework_use`</sub>

**Q13.** What's a part of your methodology you enforce religiously? A part you ignore?

<sub>~2 min · optional · feeds `directives.methodology.enforced_vs_ignored`</sub>

- Probe: When does that rule break, and when does it never break?

**Q14.** How do you identify the economic buyer? The blocker?

<sub>~2 min · optional · feeds `directives.methodology.find_econ_buyer`</sub>

### E. Objections

**Q15.** What are the top 5 objections you hear? Walk me through your standard response to each.

<sub>~4 min · feeds `directives.objections.top_five`, `directives.objections.standard_responses`</sub>

**Q16.** What's an objection you used to fear and no longer do? What changed?

<sub>~2 min · optional · feeds `directives.objections.feared_no_longer_fear`, `directives.meta_cognition.knowledge_evolution`</sub>

**Q17.** What's a price objection move you refuse to make?

<sub>~2 min · feeds `directives.objections.price_objection`, `identity.core_values`</sub>

- Probe: When does that rule break, and when does it never break?

### F. Pricing & negotiation

**Q18.** How do you anchor? When do you introduce price?

<sub>~2 min · feeds `directives.pricing_negotiation.anchor_timing`</sub>

**Q19.** Your discount ladder — if you give X, what do you ask in return?

<sub>~3 min · feeds `directives.pricing_negotiation.discount_ladder`</sub>

- Probe: What number would you put on it?

**Q20.** What's a trade you always pitch (annual prepay, multi-year, logo rights)?

<sub>~2 min · optional · feeds `directives.pricing_negotiation.trades_pitched`</sub>

**Q21.** When do you walk?

<sub>~2 min · feeds `directives.pricing_negotiation.walk_criteria`, `identity.decision_framework`</sub>

- Probe: When does that rule break, and when does it never break?

### I. Forecasting

**Q29.** What counts as committed in your head vs. in the CRM?

<sub>~3 min · feeds `directives.forecasting.committed_vs_best_case`</sub>

**Q30.** How do you tell a rep a deal they love isn't real?

<sub>~2 min · optional · feeds `directives.forecasting.pipeline_hygiene`, `identity.communication_voice`</sub>

**Q31.** What signal screams "this slips" to you?

<sub>~2 min · optional · feeds `directives.forecasting.pipeline_hygiene`</sub>

### M. Vocabulary & voice

**Q39.** Your email voice — casual, tight, warm, blunt? Example phrases?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

**Q40.** Banned phrases ("Just circling back", "Looping you in")?

<sub>~2 min · feeds `identity.communication_voice`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### O. Real decisions

**Q43.** Walk me through your last won deal — end to end.

<sub>~8 min · incident · captures decisions · feeds `identity.decision_framework`, `directives.methodology.framework_use`, `directives.personality.quality_calibration`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q44.** Walk me through your last lost deal — honestly.

<sub>~6 min · incident · captures decisions · feeds `directives.objections.standard_responses`, `directives.meta_cognition.knowledge_evolution`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q45.** Think of a deal a colleague has marked as commit this quarter. What would a capable, less experienced rep miss in it that you would catch? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.forecasting.committed_vs_best_case`, `directives.forecasting.pipeline_hygiene`, `directives.discovery.listen_beneath`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q46.** Take a cold email or follow-up you sent this month and rewrite it with me now, for a prospect you are working. Narrate each change as you make it.

<sub>~8 min · simulation · captures decisions · feeds `directives.outreach.cold_email_length`, `directives.outreach.subject_line`, `directives.outreach.cta_style`, `directives.outreach.follow_up_cadence`</sub>

- Probe: Why did you cut that?
- Probe: What would have made you keep it?

**Q47.** Think of two opportunities that looked alike after the first call, one you pursued hard and one you disqualified (or build the pair now from your pipeline). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.icp_qualification.fast_disqualify`, `directives.icp_qualification.not_now_vs_not_ever`</sub>

- Probe: Which detail would flip your verdict?

**Q48.** Here is all you get: it is the last week of the quarter, your champion went quiet after a verbal yes, procurement asks for 25% off to sign by Friday, and you are 15% short of quota. What do you do, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.pricing_negotiation.walk_criteria`, `directives.pricing_negotiation.discount_ladder`, `directives.multi_threading.dark_champion`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you walk away without knowing more?

## Depth: champions, outreach and closing (optional)

Multi-threading, the outreach voice, losing deals and the hand-off to customer success.

### G. Multi-threading

**Q22.** When do you bring in an exec sponsor? When do you refuse to?

<sub>~2 min · optional · feeds `directives.multi_threading.when_bring_exec`, `directives.multi_threading.refuse_to`</sub>

**Q23.** How do you coach a champion who's new to the role?

<sub>~2 min · optional · feeds `directives.multi_threading.coach_champion`</sub>

**Q24.** What's your playbook when the champion goes dark?

<sub>~3 min · optional · feeds `directives.multi_threading.dark_champion`</sub>

- Probe: Give me a recent, concrete example.

### H. Outreach voice

**Q25.** Cold email — length, subject line style, CTA?

<sub>~2 min · optional · feeds `directives.outreach.cold_email_length`, `directives.outreach.subject_line`, `directives.outreach.cta_style`</sub>

- Probe: What number would you put on it?

**Q26.** Follow-up cadence — how many, how spaced, what changes each time?

<sub>~2 min · optional · feeds `directives.outreach.follow_up_cadence`</sub>

- Probe: What number would you put on it?

**Q27.** Video / voice memos / LinkedIn — what's in your rotation?

<sub>~2 min · optional · feeds `directives.outreach.follow_up_cadence`</sub>

**Q28.** What do you refuse to put in an email ("Just checking in", "Did you see my last…")?

<sub>~2 min · optional · feeds `identity.communication_voice`, `directives.outreach.cta_style`</sub>

### J. Losing

**Q32.** When a deal starts slipping, what's your next move — and what's the move you refuse to make?

<sub>~3 min · optional · feeds `identity.decision_framework`, `identity.core_values`</sub>

**Q33.** How do you handle a lost deal — postmortem, re-engage, walk away?

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

### K. Handoff

**Q34.** What do you tell CS at handoff — and what do you refuse to promise?

<sub>~2 min · optional · feeds `directives.personality.quality_calibration`</sub>

**Q35.** What's your win-wire format?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

## Depth: heuristics and anti-patterns (optional)

The person's rules of thumb and what they outgrew.

### L. Heuristics

**Q36.** "If they say {X}, they mean {Y}."

<sub>~2 min · optional · feeds `directives.discovery.listen_beneath`</sub>

**Q37.** "When a deal has {X} signal, I {Y}."

<sub>~2 min · optional · feeds `identity.decision_framework`</sub>

**Q38.** "Good discovery ends with {X}."

<sub>~2 min · optional · feeds `directives.discovery.must_ask_questions`</sub>

### N. Anti-patterns

**Q41.** A sales move you outgrew.

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q42.** A tactic you see others do that you're embarrassed by.

<sub>~2 min · optional · feeds `identity.core_values`</sub>

## Depth: working with others (optional)

Uncertainty, crises, how the person has changed, focus and frustration.

### P. Working with others

**Q49.** When you are unsure about a call, how do you say so, and at what point do you escalate a decision instead of making it yourself? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q50.** A deal blows up late: the customer finds a promise in the contract you cannot deliver, or a competitor's claim about you spreads through the account. What do you do in the first hour, and how do you talk to people while it is happening?

<sub>~3 min · optional · feeds `directives.meta_cognition.crisis_personality`</sub>

**Q51.** What sales belief did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q52.** When do you do your best work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q53.** What reliably frustrates you in a sales team's habits or in how deals get reviewed?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
