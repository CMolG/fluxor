# Interview — Legal / Compliance

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 23 | ~34 | ~55 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: policy, risk, IP and the business | 14 | — | ~28 | optional |
| Depth: heuristics and anti-patterns | 5 | — | ~10 | optional |
| Depth: working with others | 5 | — | ~13 | optional |

## Core interview

Who the person is and how they reason about legal and compliance work: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What's your role — GC, associate GC, compliance lead, DPO, legal ops, fractional?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

**Q2.** What jurisdictions do you practice in? What jurisdictions are you explicitly *not* advising on?

<sub>~2 min · feeds `identity.cognitive_signature`, `directives.privacy.jurisdiction_focus`</sub>

**Q3.** What's your company's stage, industry, and regulatory profile?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q4.** What's your team shape (solo, team, outside counsel relationships)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`, `directives.escalation.escalate_outside`</sub>

### B. Risk posture

**Q5.** Where on the spectrum are you — paranoid, protective, pragmatic, business-forward? Where's your instinct?

<sub>~3 min · feeds `directives.risk_posture.spectrum_position`, `identity.decision_framework`</sub>

**Q6.** Where do you think most in-house lawyers err too cautious? Too permissive?

<sub>~3 min · feeds `directives.risk_posture.where_most_err`</sub>

**Q7.** How do you frame "no" as "yes, if…"?

<sub>~3 min · feeds `directives.risk_posture.frame_no`, `identity.communication_voice`</sub>

- Probe: Give me a recent, concrete example.

### C. Contract playbook

**Q8.** Walk me through your standard redline positions on: liability cap, IP ownership, warranty, indemnity, termination, auto-renewal, data protection, MFN clauses.

<sub>~5 min · feeds `directives.contract.standard_redlines`</sub>

**Q9.** What's a clause you'll *always* push back on? One you'll *always* concede?

<sub>~2 min · feeds `directives.contract.always_push`, `directives.contract.always_concede`</sub>

- Probe: When does that rule break, and when does it never break?

**Q10.** What's your standard position on governing law and venue?

<sub>~2 min · optional · feeds `directives.contract.governing_law`</sub>

**Q11.** What's a clause most teams ignore that you flag every time?

<sub>~2 min · optional · feeds `directives.contract.standard_redlines`</sub>

### D. Escalation

**Q12.** What do you handle directly? What do you escalate to outside counsel?

<sub>~3 min · feeds `directives.escalation.handle_directly`, `directives.escalation.escalate_outside`, `directives.meta_cognition.escalation_protocol`</sub>

**Q13.** What partner-level decisions always go to your outside counsel regardless of size?

<sub>~2 min · optional · feeds `directives.escalation.escalate_outside`</sub>

**Q14.** What's a matter type where you refuse to be the final say?

<sub>~2 min · feeds `directives.escalation.refuse_final_say`, `identity.core_values`</sub>

### E. Privacy & data protection

**Q15.** GDPR / CCPA / CPRA / state-by-state US / global — where's your center of gravity?

<sub>~2 min · feeds `directives.privacy.jurisdiction_focus`</sub>

**Q16.** Default DPA posture — your own template or accept customer's?

<sub>~2 min · feeds `directives.privacy.dpa_stance`</sub>

**Q17.** Sub-processor discipline — how strict?

<sub>~2 min · optional · feeds `directives.privacy.sub_processor_strictness`</sub>

**Q18.** Cross-border data transfer — your default mechanism?

<sub>~2 min · optional · feeds `directives.privacy.cross_border`</sub>

### H. Disputes & incidents

**Q25.** Walk me through your breach-notification workflow.

<sub>~3 min · feeds `directives.disputes.breach_workflow`, `directives.meta_cognition.crisis_personality`</sub>

**Q26.** How do you handle a customer dispute that's heading toward termination?

<sub>~3 min · optional · feeds `directives.disputes.incident_flow`</sub>

- Probe: Give me a recent, concrete example.

**Q27.** When do you involve PR / communications?

<sub>~2 min · optional · feeds `directives.disputes.incident_flow`</sub>

### M. Vocabulary

**Q39.** Legal phrases you use carefully ("best efforts" vs. "commercially reasonable", "material", "including without limitation")?

<sub>~2 min · feeds `identity.communication_voice`</sub>

**Q40.** Phrases you ban (in business writing) or rewrite?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### O. Real decisions

**Q44.** Pick a hard legal call from the last few months, one where reasonable lawyers would have disagreed: a clause you let through, a launch you slowed down, a risk you accepted on the business's behalf. Walk me through it from the first signal: what you noticed, the options you had, what you chose, and what made the difference.

<sub>~8 min · incident · captures decisions · feeds `identity.decision_framework`, `directives.risk_posture.spectrum_position`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q45.** Tell me about a matter that went wrong or nearly did: a breach, a dispute that escalated, a clause that bit you a year later. What did you notice first, and what did you change afterward?

<sub>~6 min · incident · captures decisions · feeds `directives.disputes.incident_flow`, `directives.meta_cognition.knowledge_evolution`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q46.** Think of a contract a capable, less experienced lawyer marks as ready to sign. What would they miss that you would catch? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.contract.standard_redlines`, `directives.privacy.sub_processor_strictness`, `directives.ip.customer_data`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q43.** Walk me through the last contract you redlined — key positions, concessions, rationale.

<sub>~8 min · simulation · captures decisions · feeds `directives.contract.standard_redlines`, `directives.contract.always_concede`</sub>

- Probe: Why did you concede that?
- Probe: What would have made you hold the line?

**Q47.** Think of two product or sales requests that carried similar legal risk, one you approved and one you blocked (or build the pair now from recent asks). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.risk_posture.frame_no`, `directives.escalation.refuse_final_say`</sub>

- Probe: Which detail would flip your verdict?

**Q48.** Here is all you get: a customer's security team reports that one of your sub-processors may have exposed personal data, the facts will take a week to confirm, and a notification deadline may already be running. What do you do first, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.disputes.breach_workflow`, `directives.privacy.cross_border`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you notify without knowing more?

## Depth: policy, risk, IP and the business (optional)

Policy drafting, the risk register, IP, working with sales and keeping up with regulation.

### F. Policy drafting

**Q19.** What voice do you write policies in — legalistic, plain-English, example-driven?

<sub>~2 min · optional · feeds `directives.policy.voice`</sub>

**Q20.** What's in your standard skeleton (purpose, scope, definitions, roles, process, review)?

<sub>~2 min · optional · feeds `directives.policy.skeleton`</sub>

**Q21.** What do you insist on in a policy that most companies omit?

<sub>~2 min · optional · feeds `directives.policy.insist_on_sections`</sub>

### G. Risk register

**Q22.** What risks do you track explicitly? Re-review cadence?

<sub>~2 min · optional · feeds `directives.risk_register.tracking`, `directives.risk_register.review_cadence`</sub>

**Q23.** What's a risk people underweight at your stage?

<sub>~2 min · optional · feeds `directives.risk_register.tracking`</sub>

**Q24.** How do you communicate risk to execs — memo, heat map, narrative?

<sub>~2 min · optional · feeds `directives.risk_register.exec_communication`</sub>

### I. IP

**Q28.** Open-source license review stance — strict, reasonable, hands-off?

<sub>~2 min · optional · feeds `directives.ip.open_source_review`</sub>

**Q29.** Employee IP assignment and invention assignment conventions?

<sub>~2 min · optional · feeds `directives.ip.employee_ip`</sub>

**Q30.** Customer data — what contractual rights do you reserve for product improvement?

<sub>~2 min · optional · feeds `directives.ip.customer_data`</sub>

### J. Commercial partnership

**Q31.** How do you work with sales — embedded, requested, bottleneck?

<sub>~2 min · optional · feeds `directives.risk_posture.frame_no`</sub>

**Q32.** What's a sales ask you *always* refuse?

<sub>~2 min · optional · feeds `directives.contract.always_push`, `identity.core_values`</sub>

**Q33.** What's your SLA for turning around a contract?

<sub>~2 min · optional · feeds `directives.personality.quality_calibration`</sub>

- Probe: What number would you put on it?

### K. Regulatory reading

**Q34.** How do you stay current on relevant regulation?

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q35.** What's a framework or regulation you've recently started taking more seriously?

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

## Depth: heuristics and anti-patterns (optional)

The person's rules of thumb and what they outgrew.

### L. Heuristics

**Q36.** "If a contract has {X}, I immediately {Y}."

<sub>~2 min · optional · feeds `directives.contract.standard_redlines`</sub>

**Q37.** "When a product team wants to launch {X}, my first question is {Y}."

<sub>~2 min · optional · feeds `directives.risk_posture.frame_no`</sub>

**Q38.** "I know a policy is too long when {X}."

<sub>~2 min · optional · feeds `directives.policy.skeleton`, `directives.personality.quality_calibration`</sub>

### N. Anti-patterns

**Q41.** A legal pattern or process you've outgrown.

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q42.** A compliance trend you distrust (e.g. over-privileging an audit at the expense of real control).

<sub>~2 min · optional · feeds `identity.core_values`</sub>

## Depth: working with others (optional)

Uncertainty, crises, how the person has changed, focus and frustration.

### P. Working with others

**Q49.** When you are unsure about a call, how do you say so, and at what point do you escalate a decision instead of making it yourself? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q50.** A regulator's letter or a subpoena lands on a Friday afternoon, or a leaked document puts the company in the press. What do you do in the first hour, and how do you talk to people while it is happening?

<sub>~3 min · optional · feeds `directives.meta_cognition.crisis_personality`</sub>

**Q51.** What legal belief did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q52.** When do you do your best work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q53.** What reliably frustrates you in how a company works with its legal or compliance function?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
