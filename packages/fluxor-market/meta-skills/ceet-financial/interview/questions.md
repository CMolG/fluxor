# Interview — Finance

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 26 | ~34 | ~60 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: budgeting, close and scenarios | 11 | — | ~24 | optional |
| Depth: heuristics and anti-patterns | 5 | — | ~10 | optional |
| Depth: working with others | 5 | — | ~13 | optional |

## Core interview

Who the person is and how they reason about finance: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What's your role — CFO, controller, FP&A, business partner to a function?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

**Q2.** What stage / scale is your company? Revenue model (SaaS, marketplace, transactional)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q3.** What's your reporting cadence (monthly close, board cadence, weekly flash)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`, `directives.controls.close_process`</sub>

**Q4.** Who are your internal customers (exec, board, investors, functional leaders)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

### B. Model taste

**Q5.** Walk me through how you structure a new model — sheets, naming, color coding, driver sheet.

<sub>~4 min · feeds `directives.model_taste.structure`, `directives.model_taste.conventions`</sub>

- Probe: Give me a recent, concrete example.

**Q6.** Monolithic vs. modular workbooks — where's your default and why?

<sub>~2 min · optional · feeds `directives.model_taste.monolithic_vs_modular`</sub>

**Q7.** Your stance on circular references, Excel vs. Google Sheets vs. specialized tools (Pigment, Cube, Mosaic, Anaplan)?

<sub>~2 min · optional · feeds `directives.model_taste.circular_references`, `directives.model_taste.tools`</sub>

**Q8.** What's a model convention you fight for?

<sub>~2 min · feeds `directives.model_taste.conventions`, `identity.core_values`</sub>

### C. Assumptions

**Q9.** What's your process for choosing a key assumption — sales-provided, historical, market, gut?

<sub>~3 min · feeds `directives.assumptions.choose_process`, `identity.decision_framework`</sub>

- Probe: Give me a recent, concrete example.

**Q10.** What's an assumption you refuse to use without a written source?

<sub>~2 min · feeds `directives.assumptions.refuse_without_source`</sub>

- Probe: When does that rule break, and when does it never break?

**Q11.** Where do you intentionally stay conservative? Where do you allow optimism?

<sub>~3 min · feeds `directives.assumptions.conservative_vs_optimistic`</sub>

### D. Forecasting

**Q12.** Bottoms-up vs. tops-down — which do you lead with and why?

<sub>~3 min · feeds `directives.forecasting.bottoms_up_vs_tops_down`, `identity.decision_framework`</sub>

**Q13.** How do you reconcile FP&A forecast with the sales forecast?

<sub>~3 min · optional · feeds `directives.forecasting.reconcile_sales`</sub>

- Probe: Give me a recent, concrete example.

**Q14.** What variance band (actual vs. forecast) triggers action for you?

<sub>~2 min · feeds `directives.forecasting.variance_trigger`</sub>

- Probe: What number would you put on it?

**Q15.** How do you re-forecast mid-quarter without re-forecasting every week?

<sub>~2 min · optional · feeds `directives.forecasting.mid_quarter_reforecast`</sub>

### E. Unit economics

**Q16.** Which unit economic metric do you actually trust — CAC, CAC payback, LTV/CAC, contribution margin?

<sub>~3 min · feeds `directives.unit_economics.trust_metrics`</sub>

- Probe: When does that rule break, and when does it never break?

**Q17.** When do you include fully-loaded costs vs. direct?

<sub>~2 min · optional · feeds `directives.unit_economics.fully_loaded_vs_direct`</sub>

**Q18.** What's a unit-economics number people cite that you distrust?

<sub>~2 min · feeds `directives.unit_economics.mistrusted_numbers`</sub>

- Probe: Give me a recent, concrete example.

### G. Capital allocation

**Q22.** Your ROI / payback bar for discretionary spend?

<sub>~2 min · feeds `directives.capital_allocation.roi_bar`</sub>

- Probe: What number would you put on it?

**Q23.** How do you evaluate a "strategic" request with no clear ROI?

<sub>~3 min · optional · feeds `directives.capital_allocation.evaluate_strategic`</sub>

**Q24.** What's a line item you refuse to fund, no matter the argument?

<sub>~2 min · feeds `directives.capital_allocation.refuse_to_fund`, `identity.core_values`</sub>

### H. Board & investor voice

**Q25.** Default structure of your board memo?

<sub>~2 min · optional · feeds `directives.board_voice.memo_structure`</sub>

**Q26.** What do you emphasize, and what do you refuse to bury?

<sub>~2 min · feeds `directives.board_voice.emphasize`, `directives.board_voice.refuse_to_hide`, `identity.communication_voice`</sub>

**Q27.** What's a metric you show because it's asked for, vs. one you show because it matters?

<sub>~2 min · optional · feeds `directives.board_voice.emphasize`</sub>

### M. Vocabulary

**Q39.** Finance phrases you use ("bridge", "walk", "waterfall", "normalized", "run-rate")?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

**Q40.** Phrases you avoid or redefine?

<sub>~2 min · feeds `identity.communication_voice`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### O. Real decisions

**Q44.** Pick a hard finance call from the last few months, one where reasonable finance leads would have disagreed: a forecast you cut, a budget you refused, a number you would not put in front of the board. Walk me through it from the first signal: what you noticed, the options you had, what you chose, and what made the difference.

<sub>~8 min · incident · captures decisions · feeds `identity.decision_framework`, `directives.capital_allocation.evaluate_strategic`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q45.** Tell me about a forecast that missed badly, by 20% or more. What did you notice first, how did you re-forecast, and what did you change in the model afterward?

<sub>~6 min · incident · captures decisions · feeds `directives.forecasting.mid_quarter_reforecast`, `directives.forecasting.variance_trigger`, `directives.meta_cognition.knowledge_evolution`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q46.** Think of an operating model or budget a capable, less experienced analyst hands you for review. What would they miss that you would catch? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.model_taste.conventions`, `directives.model_taste.circular_references`, `directives.assumptions.refuse_without_source`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q43.** Walk me through the last scenario / forecast / model you built — end to end, assumptions, decisions, readout.

<sub>~8 min · simulation · captures decisions · feeds `directives.model_taste.structure`, `directives.assumptions.choose_process`, `directives.board_voice.memo_structure`</sub>

- Probe: Why did you cut that?
- Probe: What would have made you keep it?

**Q47.** Think of two spend requests with similar projected returns, one you funded and one you turned down (or build the pair now from this year's asks). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.capital_allocation.roi_bar`, `directives.capital_allocation.evaluate_strategic`, `directives.budgeting.handle_over_asks`</sub>

- Probe: Which number would flip your verdict?

**Q48.** Here is all you get: mid-quarter, bookings are 18% under forecast, sales says three large deals will close in the last week, and the board meets in ten days. What do you tell the CEO, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.forecasting.reconcile_sales`, `directives.board_voice.refuse_to_hide`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you re-forecast without knowing more?

## Depth: budgeting, close and scenarios (optional)

How the person budgets, runs the close, models scenarios and works on pricing.

### F. Budgeting

**Q19.** Zero-based, last-year-plus, or outcome-tied?

<sub>~2 min · optional · feeds `directives.budgeting.approach`</sub>

**Q20.** How do you handle a function leader who consistently over-asks?

<sub>~3 min · optional · feeds `directives.budgeting.handle_over_asks`</sub>

- Probe: Give me a recent, concrete example.

**Q21.** What's your stance on re-opening budgets mid-year?

<sub>~2 min · optional · feeds `directives.budgeting.mid_year_reopening`</sub>

### I. Close & controls

**Q28.** What are your non-negotiables in month-end close?

<sub>~2 min · optional · feeds `directives.controls.non_negotiables`, `directives.controls.close_process`</sub>

**Q29.** Where do you accept materiality thresholds, and where do you not?

<sub>~2 min · optional · feeds `directives.controls.non_negotiables`, `directives.personality.quality_calibration`</sub>

- Probe: When does that rule break, and when does it never break?

**Q30.** What's a control you've added after being burned?

<sub>~3 min · optional · feeds `directives.controls.non_negotiables`, `directives.meta_cognition.knowledge_evolution`</sub>

- Probe: Give me a recent, concrete example.

### J. Scenario modeling

**Q31.** Base / bull / bear — how do you pick the variables you flex?

<sub>~2 min · optional · feeds `directives.assumptions.conservative_vs_optimistic`</sub>

**Q32.** Sensitivity tables — which variables, which ranges?

<sub>~2 min · optional · feeds `directives.model_taste.structure`</sub>

**Q33.** When do you run Monte Carlo / stochastic models vs. deterministic scenarios?

<sub>~2 min · optional · feeds `directives.model_taste.tools`</sub>

### K. Pricing partnership

**Q34.** When does finance engage in pricing decisions?

<sub>~2 min · optional · feeds `identity.decision_framework`</sub>

**Q35.** What pricing move do you always push for? Always push against?

<sub>~2 min · optional · feeds `identity.decision_framework`, `identity.core_values`</sub>

## Depth: heuristics and anti-patterns (optional)

The person's rules of thumb and what they outgrew.

### L. Heuristics

**Q36.** "If a forecast shows {X}% growth with flat headcount, I {Y}."

<sub>~2 min · optional · feeds `directives.assumptions.conservative_vs_optimistic`</sub>

**Q37.** "If an assumption needs more than {X} qualifiers, I {Y}."

<sub>~2 min · optional · feeds `directives.assumptions.refuse_without_source`</sub>

**Q38.** "A clean model has {X}."

<sub>~2 min · optional · feeds `directives.model_taste.conventions`, `directives.personality.quality_calibration`</sub>

### N. Anti-patterns

**Q41.** A modeling or forecasting pattern you outgrew.

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q42.** A trend you distrust right now.

<sub>~2 min · optional · feeds `identity.core_values`</sub>

## Depth: working with others (optional)

Uncertainty, crises, how the person has changed, focus and frustration.

### P. Working with others

**Q49.** When you are unsure about a call, how do you say so, and at what point do you escalate a decision instead of making it yourself? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q50.** A number goes out wrong: a restated quarter, a board deck with a formula error, a cash shortfall found late. What do you do in the first hour, and how do you talk to people while it is happening?

<sub>~3 min · optional · feeds `directives.meta_cognition.crisis_personality`</sub>

**Q51.** What finance belief did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q52.** When do you do your best work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q53.** What reliably frustrates you in how a company plans, budgets or reports its numbers?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
