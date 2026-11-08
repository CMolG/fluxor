# Interview — Data / Analytics

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 23 | ~38 | ~61 | required |
| Real decisions | 6 | ~37 | ~37 | required |
| Depth: statistics, models and experiments | 12 | — | ~36 | optional |
| Depth: tools and heuristics | 6 | — | ~14 | optional |
| Depth: working with others | 5 | — | ~13 | optional |

## Core interview

Who the person is and how they reason about questions, metrics and data they can trust: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What's your role and who do you report into?

<sub>~3 min · feeds `identity.cognitive_signature`</sub>

**Q2.** What's your stack (warehouse, transformation, BI, notebooks, ML tools)?

<sub>~2 min · feeds `identity.cognitive_signature`, `directives.tools_workflow.sql_dialect`</sub>

**Q3.** Who are your primary stakeholders (product, growth, finance, exec)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q4.** What decisions does your team's work actually drive?

<sub>~3 min · feeds `identity.cognitive_signature`, `identity.decision_framework`</sub>

### B. Question framing

**Q5.** A stakeholder comes with a vague question. Walk me through how you reshape it into something answerable.

<sub>~4 min · feeds `directives.question_framing.reshape_process`</sub>

- Probe: Give me a recent, concrete example.

**Q6.** What's a question you routinely refuse to answer, or reframe, before working on it?

<sub>~3 min · feeds `directives.question_framing.refuse_before_working`</sub>

- Probe: When does that rule break, and when does it never break?

**Q7.** How do you decide whether a question needs a dashboard, a one-off analysis, or a model?

<sub>~2 min · optional · feeds `identity.decision_framework`, `directives.modeling.simple_vs_complex`</sub>

### C. Metric design

**Q8.** What makes a metric good or bad in your view?

<sub>~3 min · feeds `directives.metric_design.good_vs_bad`</sub>

**Q9.** How do you think about *input* vs. *output* metrics? Leading vs. lagging?

<sub>~3 min · feeds `directives.metric_design.leading_lagging`</sub>

- Probe: Give me a recent, concrete example.

**Q10.** Give me an example of a metric you designed that was gameable — what happened, what did you change?

<sub>~4 min · incident · optional · captures decisions · feeds `directives.metric_design.gaming_resistance`</sub>

**Q11.** How do you name metrics? Any conventions you insist on?

<sub>~2 min · optional · feeds `directives.metric_design.naming_conventions`</sub>

### D. Data quality

**Q12.** Before you trust a new table, what do you check?

<sub>~3 min · feeds `directives.data_quality.trust_checklist`</sub>

**Q13.** How do you smell a bad join? What does "suspicious" look like?

<sub>~3 min · feeds `directives.data_quality.suspicious_joins`</sub>

- Probe: Give me a recent, concrete example.

**Q14.** What's your stance on staging models, tests, and freshness in dbt (or equivalent)?

<sub>~3 min · optional · feeds `directives.data_quality.freshness_policy`</sub>

- Probe: What number would you put on it?

**Q15.** What's an error class in data you've become allergic to?

<sub>~2 min · optional · feeds `directives.data_quality.allergies`</sub>

### I. Communication

**Q31.** How do you structure a write-up — TL;DR first? Methods first? Story arc?

<sub>~3 min · feeds `directives.communication.writeup_structure`</sub>

**Q32.** What's your stance on charts — bar vs. line vs. small multiples vs. tables?

<sub>~2 min · optional · feeds `directives.communication.chart_preferences`</sub>

**Q33.** What phrase do you use when asked "can you just give me the number?" and the answer is "not really"?

<sub>~2 min · optional · feeds `directives.communication.just_the_number_response`</sub>

### K. Vocabulary

**Q37.** Any local terms (e.g. "north star", "guardrail", "canary metric", "kitchen-sink model")?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

**Q38.** Any words you refuse to use in write-ups ("proves", "causes", "significant" without context)?

<sub>~2 min · feeds `identity.communication_voice`, `directives.statistical_rigor.uncertainty_language`</sub>

### L. Anti-patterns

**Q39.** What's a chart type or analysis pattern you consistently reject?

<sub>~2 min · optional · feeds `directives.communication.chart_preferences`</sub>

**Q40.** What's a common data request you push back on, and how do you reframe it?

<sub>~3 min · feeds `directives.question_framing.refuse_before_working`, `directives.question_framing.reshape_process`</sub>

- Probe: Give me a recent, concrete example.

### O. Lines you hold

**Q47.** What would you refuse to publish or sign off on, no matter who is asking or how urgent it is? What's the story behind that line?

<sub>~3 min · feeds `identity.core_values`, `directives.data_quality.allergies`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### N. Real decisions

**Q42.** Pick a hard analytical call from the last few months, one where reasonable analysts would have disagreed: a method, a metric definition, a result you would or would not stand behind. Walk me through it from the first signal: what you noticed, the options you had, what you chose, and what made the difference.

<sub>~8 min · incident · captures decisions · feeds `identity.decision_framework`, `directives.statistical_rigor.method_selection`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q43.** Tell me about a number you published that turned out to be wrong. How did you find out, what did you do in the first hour, and what do you do differently since?

<sub>~6 min · incident · captures decisions · feeds `directives.meta_cognition.crisis_personality`, `directives.data_quality.allergies`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q44.** Think of a query or dashboard a capable mid-level analyst hands you for review. What would they miss that you would catch? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.data_quality.suspicious_joins`, `directives.data_quality.trust_checklist`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q41.** Walk me through the last real analysis you did — end to end. Every branch, every rejection, every "I almost did X but did Y because…".

<sub>~10 min · simulation · captures decisions · feeds `identity.decision_framework`, `directives.communication.writeup_structure`</sub>

- Probe: Where did you almost go another way, and why didn't you?
- Probe: What did you leave out of the write-up, and why?

**Q45.** Think of two metric or dashboard proposals for the same need, one you approved and one you sent back (or build the pair now from your work). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.metric_design.good_vs_bad`, `identity.decision_framework`</sub>

- Probe: Which detail would flip your verdict?

**Q46.** Here is all you get: weekly active users dropped 12% last week, nothing shipped, and the pipeline dashboard is all green. What do you do first, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.data_quality.trust_checklist`, `directives.meta_cognition.escalation_protocol`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you tell stakeholders before you know more?

## Depth: statistics, models and experiments (optional)

Causal methods, uncertainty, modeling and experimentation.

### E. Statistical rigor

**Q16.** RCT, diff-in-diff, synthetic control, observational — when do you reach for which?

<sub>~4 min · optional · feeds `directives.statistical_rigor.method_selection`</sub>

- Probe: When does that rule break, and when does it never break?

**Q17.** How do you talk about uncertainty in a write-up? What phrases do you avoid?

<sub>~3 min · optional · feeds `directives.statistical_rigor.uncertainty_language`</sub>

**Q18.** What's your practice around multiple comparisons?

<sub>~3 min · optional · feeds `directives.statistical_rigor.multiple_comparisons`</sub>

**Q19.** When do you trust a p-value, and when do you not?

<sub>~3 min · optional · feeds `directives.statistical_rigor.p_value_trust`</sub>

- Probe: Give me a recent, concrete example.

### F. Modeling

**Q20.** Simple vs. complex — where's your default?

<sub>~3 min · optional · feeds `directives.modeling.simple_vs_complex`</sub>

**Q21.** How do you know a model is "good enough" to ship?

<sub>~3 min · optional · feeds `directives.modeling.good_enough_bar`</sub>

- Probe: What number would you put on it?

**Q22.** What's your monitoring story for a deployed model?

<sub>~3 min · optional · feeds `directives.modeling.monitoring_story`</sub>

**Q23.** What's a model-building shortcut you used to take and now refuse?

<sub>~2 min · optional · feeds `directives.modeling.shortcuts_refused`</sub>

### G. Experimentation

**Q24.** How do you set up a power calculation / MDE for a new experiment?

<sub>~4 min · optional · feeds `directives.experimentation.power_calculation`, `directives.experimentation.mde_policy`</sub>

- Probe: What number would you put on it?

**Q25.** What guardrail metrics do you always include?

<sub>~2 min · optional · feeds `directives.experimentation.guardrail_metrics`</sub>

**Q26.** What's your stance on peeking / sequential testing / early stopping?

<sub>~3 min · optional · feeds `directives.experimentation.peeking_stance`</sub>

**Q27.** How do you handle experiments that "fail to reject" — what do you tell the stakeholder?

<sub>~3 min · optional · feeds `directives.statistical_rigor.uncertainty_language`</sub>

## Depth: tools and heuristics (optional)

The tools the person reaches for and the rules of thumb they apply.

### H. Tools & workflow

**Q28.** SQL dialect you write in, pandas vs. Polars vs. DuckDB, viz library — pick your defaults and tell me why.

<sub>~3 min · optional · feeds `directives.tools_workflow.sql_dialect`, `directives.tools_workflow.dataframe_library`, `directives.tools_workflow.viz_library`</sub>

**Q29.** Notebooks vs. scripts vs. dbt — where does each belong?

<sub>~3 min · optional · feeds `identity.decision_framework`</sub>

**Q30.** What's in your personal utility library / snippets?

<sub>~2 min · optional · feeds `directives.tools_workflow.utilities`</sub>

### J. Heuristics

**Q34.** "I always {X} before trusting a new data source."

<sub>~2 min · optional · feeds `directives.data_quality.trust_checklist`</sub>

**Q35.** "If a metric moves more than {X}%, I immediately check {Y}."

<sub>~2 min · optional · feeds `identity.decision_framework`, `directives.data_quality.trust_checklist`</sub>

- Probe: What number would you put on it?

**Q36.** "A good experiment pre-registers {X}."

<sub>~2 min · optional · feeds `directives.experimentation.guardrail_metrics`, `directives.statistical_rigor.multiple_comparisons`</sub>

## Depth: working with others (optional)

Uncertainty, the quality bar, how the person has changed, focus and frustration.

### P. Working with others

**Q48.** When you are unsure about a result or stuck on an analysis, how do you say so, and at what point do you escalate or ask for help? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q49.** What is the difference between a quick number you would send in chat and an analysis you would put your name on? Where exactly is the line?

<sub>~3 min · optional · feeds `directives.personality.quality_calibration`</sub>

**Q50.** What belief about data or analysis did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q51.** When do you do your best analytical work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q52.** What reliably frustrates you in a data stack or in how people use data?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
