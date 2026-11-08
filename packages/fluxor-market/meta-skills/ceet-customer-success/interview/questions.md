# Interview — Customer Success

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 28 | ~37 | ~66 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: expansion, escalations and advocacy | 12 | — | ~25 | optional |
| Depth: heuristics and anti-patterns | 5 | — | ~10 | optional |
| Depth: working with others | 5 | — | ~13 | optional |

## Core interview

Who the person is and how they reason about customer success: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What's your book — ACV range, segment, account count?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

**Q2.** What's the CS model (high-touch, pooled, digital, hybrid)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q3.** What tools are you in daily (CS platform, ticketing, CRM, product analytics)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q4.** How are you measured (NRR, GRR, CSAT, adoption, expansion)?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

### B. Onboarding

**Q5.** Walk me through your onboarding playbook.

<sub>~4 min · feeds `directives.onboarding.playbook`, `identity.decision_framework`</sub>

- Probe: Give me a recent, concrete example.

**Q6.** What's your definition of "first value"?

<sub>~2 min · feeds `directives.onboarding.first_value_definition`</sub>

**Q7.** What kickoff question do you always ask that most CSMs don't?

<sub>~2 min · feeds `directives.onboarding.kickoff_questions`</sub>

**Q8.** What's a mistake onboarding-wise you've seen kill accounts later?

<sub>~3 min · optional · feeds `directives.onboarding.mistakes`</sub>

- Probe: Give me a recent, concrete example.

### C. Adoption & rollout

**Q9.** How do you think about rollout across a customer's org?

<sub>~3 min · optional · feeds `directives.adoption.rollout_strategy`</sub>

**Q10.** Who inside the customer do you care most about aligning with — power user, exec sponsor, admin, end user?

<sub>~2 min · feeds `directives.adoption.alignment_care`</sub>

**Q11.** What's a rollout tactic you always use? One you've retired?

<sub>~2 min · optional · feeds `directives.adoption.always_tactic`, `directives.adoption.retired_tactic`</sub>

### D. Health scoring

**Q12.** What signals do you trust beyond the dashboard?

<sub>~3 min · feeds `directives.health_scoring.trusted_signals`</sub>

- Probe: Give me a recent, concrete example.

**Q13.** What "green" account has fooled you? What was the missed signal?

<sub>~3 min · feeds `directives.health_scoring.green_account_fooling`</sub>

- Probe: Give me a recent, concrete example.

**Q14.** How do you re-score a customer after a big event (exec change, price increase, outage)?

<sub>~2 min · optional · feeds `directives.health_scoring.rescore_triggers`</sub>

### E. QBRs

**Q15.** What's your QBR format? Sections, length, attendees?

<sub>~2 min · optional · feeds `directives.qbr.format_sections`</sub>

**Q16.** What do you refuse to put in a QBR?

<sub>~2 min · optional · feeds `directives.qbr.refuse_to_include`, `identity.core_values`</sub>

**Q17.** What section almost always gets cut last minute?

<sub>~2 min · optional · feeds `directives.qbr.format_sections`</sub>

**Q18.** What makes a QBR land vs. flop?

<sub>~3 min · feeds `directives.qbr.land_vs_flop`, `directives.personality.quality_calibration`</sub>

### F. At-risk playbook

**Q19.** What's a clear "red" signal that others miss?

<sub>~3 min · feeds `directives.at_risk.red_signals`</sub>

- Probe: Give me a recent, concrete example.

**Q20.** Walk me through your escalation ladder — CSM, CS leader, exec, product.

<sub>~3 min · feeds `directives.at_risk.escalation_ladder`, `directives.meta_cognition.escalation_protocol`</sub>

**Q21.** What trade do you pitch when a customer threatens to churn?

<sub>~2 min · optional · feeds `directives.at_risk.trade_pitch`</sub>

**Q22.** When do you write an account off?

<sub>~2 min · feeds `directives.at_risk.write_off_point`, `identity.decision_framework`</sub>

- Probe: When does that rule break, and when does it never break?

### G. Renewal

**Q23.** When do you start renewal conversations?

<sub>~2 min · feeds `directives.renewal.start_timing`</sub>

- Probe: What number would you put on it?

**Q24.** Discount posture — where's your line?

<sub>~2 min · feeds `directives.renewal.discount_line`, `identity.core_values`</sub>

- Probe: What number would you put on it?

**Q25.** Multi-year — when do you push, when do you avoid?

<sub>~2 min · optional · feeds `directives.renewal.multi_year_stance`</sub>

**Q26.** How do you handle a renewal that's quietly shrinking?

<sub>~3 min · optional · feeds `directives.renewal.shrinking_renewal`</sub>

- Probe: Give me a recent, concrete example.

### M. Vocabulary

**Q42.** Words you use ("outcome", "value", "adoption")?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

**Q43.** Words you avoid ("leverage", "align", "circle back", "touch base")?

<sub>~2 min · feeds `identity.communication_voice`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### O. Real decisions

**Q46.** Walk me through your last saved churn.

<sub>~8 min · incident · captures decisions · feeds `directives.at_risk.trade_pitch`, `directives.at_risk.escalation_ladder`, `identity.decision_framework`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q47.** Walk me through your last expansion win.

<sub>~6 min · incident · captures decisions · feeds `directives.expansion.when_upsell`, `directives.expansion.who_upsell`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q48.** Think of an account a colleague reports as green this quarter. What would a capable, less experienced CSM miss in it that you would catch? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.health_scoring.trusted_signals`, `directives.health_scoring.green_account_fooling`, `directives.at_risk.red_signals`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q49.** Take the deck or agenda of a QBR you ran recently and rework it with me now for the same customer. Narrate each change as you make it.

<sub>~8 min · simulation · captures decisions · feeds `directives.qbr.format_sections`, `directives.qbr.refuse_to_include`, `directives.qbr.land_vs_flop`</sub>

- Probe: Why did you cut that?
- Probe: What would have made you keep it?

**Q50.** Think of two accounts that renewed with the same health score, one you pushed to expand and one you left alone (or build the pair now from your book). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.expansion.who_upsell`, `directives.expansion.avoid_poisoning`</sub>

- Probe: Which detail would flip your verdict?

**Q51.** Here is all you get: 60 days to renewal, the champion just left, usage is flat, and the new VP asks for 30% off to renew. What do you do first, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.renewal.shrinking_renewal`, `directives.renewal.discount_line`, `directives.at_risk.trade_pitch`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you concede the discount without knowing more?

## Depth: expansion, escalations and advocacy (optional)

Expansion, angry customers, the hand-offs with sales, support and product, and references.

### H. Expansion

**Q27.** What's your expansion trigger — usage, outcome, stakeholder, timing?

<sub>~2 min · optional · feeds `directives.expansion.when_upsell`</sub>

**Q28.** Who do you refuse to upsell and why?

<sub>~2 min · optional · feeds `directives.expansion.who_upsell`, `directives.expansion.avoid_poisoning`, `identity.core_values`</sub>

**Q29.** What expansion motion do you do that others don't?

<sub>~2 min · optional · feeds `directives.expansion.when_upsell`</sub>

### I. Escalation & angry customers

**Q30.** When a customer is furious, what's your first move? Second?

<sub>~3 min · optional · feeds `directives.meta_cognition.crisis_personality`, `identity.communication_voice`</sub>

- Probe: Give me a recent, concrete example.

**Q31.** When do you bring in an exec sponsor on your side? When do you refuse?

<sub>~2 min · optional · feeds `directives.at_risk.escalation_ladder`, `directives.meta_cognition.escalation_protocol`</sub>

**Q32.** What words do you use to absorb heat? What words do you never use ("I understand")?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

### J. Handoff

**Q33.** From sales: what do you wish sales would stop promising?

<sub>~2 min · optional · feeds `directives.onboarding.mistakes`</sub>

**Q34.** To support: where's the line between CS and support in your shop?

<sub>~2 min · optional · feeds `identity.decision_framework`</sub>

**Q35.** To product: how do you translate customer pain into product-usable signal?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

### K. Advocacy

**Q36.** How do you spot a reference-able account early?

<sub>~2 min · optional · feeds `directives.advocacy.spot_advocates`</sub>

**Q37.** What do you ask for vs. offer in exchange?

<sub>~2 min · optional · feeds `directives.advocacy.cultivate_references`</sub>

**Q38.** What's a customer-marketing move you swear by?

<sub>~2 min · optional · feeds `directives.advocacy.case_study_approach`</sub>

## Depth: heuristics and anti-patterns (optional)

The person's rules of thumb and what they outgrew.

### L. Heuristics

**Q39.** "If a customer hasn't {X} in {Y} days, I {Z}."

<sub>~2 min · optional · feeds `directives.health_scoring.rescore_triggers`, `directives.at_risk.red_signals`</sub>

**Q40.** "When a champion leaves, I {X}."

<sub>~2 min · optional · feeds `directives.health_scoring.rescore_triggers`</sub>

**Q41.** "I know an account is saved when {X}."

<sub>~2 min · optional · feeds `directives.at_risk.write_off_point`</sub>

### N. Anti-patterns

**Q44.** A CS pattern you outgrew.

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q45.** A trend you distrust (e.g. excessive QBRs, NPS worship).

<sub>~2 min · optional · feeds `identity.core_values`</sub>

## Depth: working with others (optional)

Uncertainty, crises, how the person has changed, focus and frustration.

### P. Working with others

**Q52.** When you are unsure about a call, how do you say so, and at what point do you escalate a decision instead of making it yourself? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q53.** An incident hits your whole book: an outage during a customer's launch, a data leak, a price change announced without warning. What do you do in the first hour, and how do you talk to customers while it is happening?

<sub>~3 min · optional · feeds `directives.meta_cognition.crisis_personality`</sub>

**Q54.** What customer success belief did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q55.** When do you do your best work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q56.** What reliably frustrates you in how a company runs or measures customer success?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
