# Interview — Marketing

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 27 | ~40 | ~67 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: creative, launches and competition | 9 | — | ~21 | optional |
| Depth: heuristics and anti-patterns | 5 | — | ~10 | optional |
| Depth: working with others | 5 | — | ~13 | optional |

## Core interview

Who the person is and how they reason about marketing: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What's your scope — brand, demand, growth, PMM, all of it?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

**Q2.** What stage and shape is your company / product?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

**Q3.** What's your reporting structure and budget authority?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q4.** What channels are you actually running right now?

<sub>~2 min · optional · feeds `directives.channels.channel_mix`</sub>

### B. Positioning

**Q5.** Describe your product's positioning in one sentence. Now again, as if you were explaining to a skeptical analyst.

<sub>~4 min · feeds `directives.positioning.one_sentence`</sub>

**Q6.** What category are you in, and what alternatives do you position against (without naming competitors if that's your style)?

<sub>~3 min · feeds `directives.positioning.category`, `directives.positioning.alternative_positioning`</sub>

**Q7.** What positioning frame do you use (April Dunford-ish, Crossing the Chasm, Kim & Mauborgne, or something else)?

<sub>~2 min · optional · feeds `directives.positioning.framework`</sub>

### C. ICP

**Q8.** Who's your ideal customer — specific company shape, role, trigger event?

<sub>~3 min · feeds `directives.icp.ideal_customer`</sub>

- Probe: Give me a recent, concrete example.

**Q9.** Who's a bad-fit customer that you push away? Why?

<sub>~3 min · feeds `directives.icp.bad_fit_pushaway`</sub>

- Probe: When does that rule break, and when does it never break?

### D. Messaging

**Q11.** What's your one-liner, three messaging pillars, and key proof points?

<sub>~4 min · feeds `directives.messaging.one_liner`, `directives.messaging.three_pillars`, `directives.messaging.proof_points`</sub>

**Q12.** How does messaging cascade from positioning to headline to ad?

<sub>~3 min · optional · feeds `directives.messaging.three_pillars`, `identity.decision_framework`</sub>

**Q13.** What phrase or framing do you refuse to use even when it tests well?

<sub>~2 min · feeds `directives.messaging.refused_phrases`, `identity.core_values`</sub>

- Probe: Give me a recent, concrete example.

### E. Channels

**Q14.** What's your channel mix today? What % of attention and budget?

<sub>~3 min · feeds `directives.channels.channel_mix`</sub>

- Probe: What number would you put on it?

**Q15.** What channel is underperforming that people expect to work?

<sub>~2 min · optional · feeds `directives.channels.underperforming`</sub>

**Q16.** What channel surprises you by working?

<sub>~2 min · optional · feeds `directives.channels.surprising_wins`</sub>

**Q17.** What channel have you deliberately killed, and why?

<sub>~3 min · feeds `directives.channels.deliberately_killed`, `identity.decision_framework`</sub>

### F. Funnel / growth loops

**Q18.** How do you model your funnel — AARRR, bowtie, jobs funnel, custom?

<sub>~2 min · optional · feeds `directives.funnel.funnel_model`</sub>

**Q19.** Do you think primarily in funnels, loops, or both?

<sub>~2 min · optional · feeds `directives.funnel.loops_vs_funnels`</sub>

**Q20.** What's the biggest leak in your funnel right now, and what's your hypothesis?

<sub>~3 min · feeds `directives.funnel.biggest_leak`</sub>

### H. Brand vs. demand

**Q25.** How do you split brand and demand — budget, time, measurement?

<sub>~3 min · feeds `directives.brand_vs_demand.budget_split`, `directives.brand_vs_demand.measurement`</sub>

- Probe: What number would you put on it?

**Q26.** What's something you refuse to measure by ROI?

<sub>~2 min · optional · feeds `directives.brand_vs_demand.refuse_to_measure_by_roi`</sub>

**Q27.** When pressured for "why'd you spend on that?", what's your standard answer?

<sub>~2 min · optional · feeds `directives.brand_vs_demand.refuse_to_measure_by_roi`, `identity.communication_voice`</sub>

### I. Attribution & honesty

**Q28.** What attribution model do you use, and how much do you trust it?

<sub>~3 min · feeds `directives.attribution.actually_believe`</sub>

**Q29.** What do you tell the board vs. what you actually believe?

<sub>~2 min · optional · feeds `directives.attribution.report_to_board`, `directives.attribution.actually_believe`</sub>

**Q30.** How do you handle dark-social / unmeasured influence?

<sub>~2 min · optional · feeds `directives.brand_vs_demand.measurement`</sub>

### M. Vocabulary

**Q39.** Words you use repeatedly (e.g. "category", "wedge", "POV")?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

**Q40.** Words you ban ("disruptive", "world-class", "cutting-edge")?

<sub>~2 min · feeds `identity.communication_voice`, `directives.messaging.refused_phrases`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### P. Real decisions

**Q44.** Pick a hard marketing decision from the last few months, one where reasonable marketers would have disagreed: a positioning change, a channel bet, a budget shift, a campaign you stopped. Walk me through it from the first signal: what you noticed, the options you had, what you chose, and what made the difference.

<sub>~8 min · incident · captures decisions · feeds `identity.decision_framework`, `directives.brand_vs_demand.budget_split`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q10.** What's an ICP mistake you made in the past?

<sub>~6 min · incident · captures decisions · feeds `directives.icp.past_mistake`, `directives.icp.ideal_customer`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q45.** Think of a campaign plan or messaging document a capable, less experienced marketer hands you. What would they miss that you would catch? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.messaging.proof_points`, `directives.icp.bad_fit_pushaway`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q43.** Walk me through the last full campaign you owned — insight, positioning, creative, channels, measurement, result.

<sub>~8 min · simulation · captures decisions · feeds `directives.creative.great_campaign`, `directives.attribution.actually_believe`</sub>

- Probe: Why that channel and not another?
- Probe: What result would have made you stop it earlier?

**Q46.** Think of two channels or campaigns with similar numbers, one you doubled down on and one you cut (or build the pair now from your current mix). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.channels.underperforming`, `directives.channels.surprising_wins`</sub>

- Probe: Which number would flip your verdict?

**Q47.** Here is all you get: paid social's cost per lead doubled this quarter, pipeline from it is flat, last-touch attribution credits it with 40% of revenue, and the CFO asks whether to cut it. What do you answer, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.attribution.actually_believe`, `directives.attribution.report_to_board`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you cut it without knowing more?

## Depth: creative, launches and competition (optional)

Creative standards, the launch playbook and positioning against competitors.

### G. Creative & craft

**Q21.** What makes a great campaign in your view?

<sub>~2 min · optional · feeds `directives.creative.great_campaign`</sub>

**Q22.** What makes a great piece of content?

<sub>~2 min · optional · feeds `directives.creative.great_content`</sub>

**Q23.** How do you brief creative — tight brief, loose brief, co-create?

<sub>~2 min · optional · feeds `directives.creative.brief_style`</sub>

**Q24.** What's a campaign you're proud of? One you'd re-do?

<sub>~3 min · optional · feeds `directives.creative.great_campaign`, `directives.personality.quality_calibration`</sub>

- Probe: Give me a recent, concrete example.

### J. Launches & PMM

**Q31.** What's your launch playbook skeleton?

<sub>~3 min · optional · feeds `identity.decision_framework`</sub>

**Q32.** Tier-1 vs tier-2 vs tier-3 launches — your criteria?

<sub>~2 min · optional · feeds `identity.decision_framework`</sub>

**Q33.** How do you handle a launch that lands flat?

<sub>~2 min · optional · feeds `directives.meta_cognition.crisis_personality`</sub>

- Probe: Give me a recent, concrete example.

### K. Competitive

**Q34.** Do you name competitors or not? Why?

<sub>~2 min · optional · feeds `directives.positioning.alternative_positioning`</sub>

**Q35.** How do you position against a category leader? Against a cheaper alternative?

<sub>~3 min · optional · feeds `directives.positioning.alternative_positioning`, `directives.positioning.category`</sub>

## Depth: heuristics and anti-patterns (optional)

The person's rules of thumb and what they outgrew.

### L. Heuristics

**Q36.** "A good headline earns {X}."

<sub>~2 min · optional · feeds `directives.creative.great_content`</sub>

**Q37.** "If we can't pick a single target customer, we {X}."

<sub>~2 min · optional · feeds `directives.icp.ideal_customer`</sub>

**Q38.** "I kill a campaign when {X}."

<sub>~2 min · optional · feeds `directives.channels.deliberately_killed`</sub>

### N. Anti-patterns

**Q41.** Marketing patterns you outgrew.

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q42.** Trends you distrust right now.

<sub>~2 min · optional · feeds `identity.core_values`</sub>

## Depth: working with others (optional)

Uncertainty, crises, how the person has changed, focus and frustration.

### Q. Working with others

**Q48.** When you are unsure about a call, how do you say so, and at what point do you escalate a decision instead of making it yourself? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q49.** A campaign blows up in public: a claim you cannot back, an ad that offends, a promo code that leaks. What do you do in the first hour, and how do you talk to people while it is happening?

<sub>~3 min · optional · feeds `directives.meta_cognition.crisis_personality`</sub>

**Q50.** What marketing belief did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q51.** When do you do your best work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q52.** What reliably frustrates you in how a company plans, funds or judges marketing?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
