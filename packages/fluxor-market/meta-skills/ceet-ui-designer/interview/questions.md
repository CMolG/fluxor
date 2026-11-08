# Interview — UI Designer

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 28 | ~39 | ~66 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: motion, icons and brand | 8 | — | ~17 | optional |
| Depth: tooling, heuristics and anti-patterns | 9 | — | ~20 | optional |
| Depth: working with others | 5 | — | ~13 | optional |

## Core interview

Who the person is and how they reason about visual and interface design: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What surface do you design for (marketing, app, dashboards, consumer, B2B, hardware UI)?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

**Q2.** What stack are you in — Figma, tokens tooling, design system tools, prototyping?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q3.** Who hands off to you (PM, research, brand) and who receives your handoff (front-end, marketing, brand)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q4.** What's the rough size and maturity of your design system?

<sub>~2 min · feeds `identity.cognitive_signature`, `directives.components.system_end_point`</sub>

### B. Taste through exemplars

**Q5.** Name 3 products whose UI craft you respect. What specifically — don't say "clean."

<sub>~3 min · feeds `directives.critique.heroes_and_anti_heroes`, `identity.core_values`, `directives.personality.quality_calibration`</sub>

- Probe: Give me a recent, concrete example.

**Q6.** Name 3 products that you think are over-hyped visually. Why?

<sub>~2 min · optional · feeds `directives.critique.heroes_and_anti_heroes`</sub>

**Q7.** Describe a single screen, anywhere, that's near-perfect to you. Walk me through what's working.

<sub>~4 min · feeds `directives.personality.quality_calibration`, `identity.decision_framework`</sub>

### C. Grid & spacing

**Q8.** What baseline unit do you work in (4, 8, other)?

<sub>~2 min · feeds `directives.grid_spacing.baseline_unit`</sub>

- Probe: What number would you put on it?

**Q9.** Tight or airy — where's your default, and what pushes you off it?

<sub>~2 min · feeds `directives.grid_spacing.tight_vs_airy`</sub>

- Probe: When does that rule break, and when does it never break?

**Q10.** What ratios recur in your work (12-col, golden, whatever you gravitate to)?

<sub>~2 min · optional · feeds `directives.grid_spacing.ratio_preferences`</sub>

### D. Type

**Q11.** Favorite typefaces for body, UI chrome, display? Any you refuse?

<sub>~3 min · optional · feeds `directives.typography.typeface_rules`</sub>

**Q12.** What's your type scale? How many steps?

<sub>~2 min · feeds `directives.typography.scale_system`</sub>

- Probe: What number would you put on it?

**Q13.** Line height and measure convictions?

<sub>~2 min · optional · feeds `directives.typography.line_height_measure`</sub>

- Probe: What number would you put on it?

**Q14.** What's one type mistake you see everywhere?

<sub>~2 min · optional · feeds `directives.typography.type_mistakes`</sub>

### E. Color

**Q15.** How do you think about a color system — semantic tokens, named ramps, raw hex?

<sub>~3 min · feeds `directives.color.system_approach`</sub>

**Q16.** What's your stance on dark mode — first-class, afterthought, or single-mode design?

<sub>~2 min · optional · feeds `directives.color.dark_mode_stance`</sub>

**Q17.** Contrast bar — do you go beyond WCAG? In which direction?

<sub>~2 min · feeds `directives.color.contrast_bar`</sub>

- Probe: What number would you put on it?

**Q18.** A color you overuse? One you avoid?

<sub>~2 min · optional · feeds `directives.color.over_under_used`</sub>

### F. Components

**Q19.** What's the smallest primitive you design from (tokens, atoms, molecules)?

<sub>~2 min · optional · feeds `directives.components.smallest_primitive`</sub>

**Q20.** At what level of the system do you stop — where does "system" end and "app" begin?

<sub>~3 min · feeds `directives.components.system_end_point`</sub>

- Probe: When does that rule break, and when does it never break?

**Q21.** How do you handle variants — props-based, multiple components, composition?

<sub>~3 min · feeds `directives.components.variant_approach`</sub>

- Probe: Give me a recent, concrete example.

**Q22.** Component naming conventions you insist on?

<sub>~2 min · optional · feeds `directives.components.naming_conventions`</sub>

### G. States & craft

**Q23.** Which state (default, hover, active, focus, disabled, loading, empty, error, success) gets the least love on teams you've worked with? How do you change that?

<sub>~3 min · feeds `directives.states_craft.neglected_state`</sub>

- Probe: Give me a recent, concrete example.

**Q24.** What's a micro-detail (ring width, shadow softness, button border) that you obsess over?

<sub>~2 min · optional · feeds `directives.states_craft.micro_detail_obsession`</sub>

**Q25.** What's something you always check before calling a mock done?

<sub>~3 min · feeds `directives.states_craft.done_checklist`</sub>

### K. Critique

**Q34.** When you critique someone's mock, what do you look at in what order?

<sub>~3 min · feeds `directives.critique.feedback_voice`, `identity.decision_framework`</sub>

**Q35.** What words do you reach for repeatedly ("weight", "rhythm", "heavy", "polite")?

<sub>~2 min · feeds `directives.critique.vocabulary`, `identity.communication_voice`</sub>

**Q36.** What phrases do you avoid giving as feedback?

<sub>~2 min · optional · feeds `directives.critique.feedback_voice`, `identity.communication_voice`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### P. Real decisions

**Q47.** Pick a hard design decision from the last few months, one where reasonable designers would have disagreed: a system change, a component API, a brand exception, a cut. Walk me through it from the first signal: what you noticed, the options you had, what you chose, and what made the difference.

<sub>~8 min · incident · captures decisions · feeds `identity.decision_framework`, `directives.components.variant_approach`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q48.** Tell me about a design that shipped and did not work: people missed it, engineering could not build it as drawn, or it broke the system. What did you notice first, and what did you change?

<sub>~6 min · incident · captures decisions · feeds `directives.states_craft.neglected_state`, `identity.decision_framework`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q49.** Think of a screen a capable mid-level designer hands you as done. What would they miss that you would catch before it ships? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.states_craft.done_checklist`, `directives.states_craft.micro_detail_obsession`, `directives.color.contrast_bar`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q45.** Walk me through the last piece you designed — inputs, decisions, cuts, final, rationale.

<sub>~8 min · simulation · captures decisions · feeds `identity.decision_framework`, `directives.personality.quality_calibration`</sub>

- Probe: Why did you cut that?
- Probe: What would have made you keep it?

**Q50.** Think of two variants of the same component or screen, one you shipped and one you rejected (or build the pair now from your files). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.components.variant_approach`, `directives.critique.vocabulary`</sub>

- Probe: Which detail would flip your verdict?

**Q51.** Here is all you get: engineering says the new card component ships in two days if you drop its hover, focus and empty states, and marketing needs it for Monday's launch. What do you decide, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.states_craft.neglected_state`, `directives.personality.quality_calibration`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you let it ship without the states?

## Depth: motion, icons and brand (optional)

Motion, icons and illustration, and where brand may bend usability.

### H. Motion

**Q26.** Where do you use motion deliberately? Where do you refuse?

<sub>~2 min · optional · feeds `directives.motion.where_deliberate`, `directives.motion.smell_animations`</sub>

**Q27.** Default easing and duration?

<sub>~2 min · optional · feeds `directives.motion.duration_easing`</sub>

- Probe: What number would you put on it?

**Q28.** Reduced-motion stance — strict or loose?

<sub>~2 min · optional · feeds `directives.motion.reduced_motion`</sub>

### I. Icons & illustration

**Q29.** Icon style and grid — what's your standard?

<sub>~2 min · optional · feeds `directives.grid_spacing.baseline_unit`</sub>

**Q30.** When do illustrations earn their keep? When are they decoration?

<sub>~2 min · optional · feeds `identity.core_values`</sub>

**Q31.** Illustration style references you use?

<sub>~2 min · optional · feeds `directives.critique.heroes_and_anti_heroes`</sub>

### J. Brand vs. usability

**Q32.** Where do you let brand override usability norms? Example.

<sub>~3 min · optional · feeds `identity.decision_framework`</sub>

- Probe: Give me a recent, concrete example.

**Q33.** Where do you refuse to let brand override?

<sub>~2 min · optional · feeds `identity.decision_framework`, `identity.core_values`</sub>

## Depth: tooling, heuristics and anti-patterns (optional)

How the person keeps design files, their rules of thumb, and what they refuse to ship.

### L. Tooling discipline

**Q37.** Figma file organization conventions?

<sub>~2 min · optional · feeds `directives.figma.naming_discipline`, `directives.figma.library_management`</sub>

**Q38.** Variables, modes, and tokens — how far are you in, and what's your strategy?

<sub>~3 min · optional · feeds `directives.figma.variables`</sub>

**Q39.** What handoff rituals do you insist on?

<sub>~2 min · optional · feeds `directives.figma.library_management`</sub>

**Q46.** How do you use auto layout and constraints: what do you always build with them, and where do you refuse to? Show me a frame you rebuilt because its layout fought you.

<sub>~3 min · optional · feeds `directives.figma.auto_layout`</sub>

- Probe: Give me a recent, concrete example.

### M. Heuristics

**Q40.** "If a screen has more than {X} primary actions, it's {Y}."

<sub>~2 min · optional · feeds `identity.decision_framework`</sub>

**Q41.** "When I can't decide between two variants, I {X}."

<sub>~2 min · optional · feeds `identity.decision_framework`</sub>

**Q42.** "I know a design is done when {X}."

<sub>~2 min · optional · feeds `directives.states_craft.done_checklist`</sub>

### N. Anti-patterns

**Q43.** A visual trend you distrust right now?

<sub>~2 min · optional · feeds `identity.core_values`</sub>

**Q44.** A UI pattern that looks impressive but you won't ship?

<sub>~2 min · optional · feeds `identity.core_values`, `directives.personality.quality_calibration`</sub>

## Depth: working with others (optional)

Uncertainty, crises, how the person has changed, focus and frustration.

### Q. Working with others

**Q52.** When you are unsure about a call, how do you say so, and at what point do you escalate a decision instead of making it yourself? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q53.** A release goes out with a broken visual: the wrong brand color, an unreadable dark mode, a layout that collapses on phones. What do you do in the first hour, and how do you talk to people while it is happening?

<sub>~3 min · optional · feeds `directives.meta_cognition.crisis_personality`</sub>

**Q54.** What design belief did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q55.** When do you do your best work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q56.** What reliably frustrates you in a design team's habits or in how design reviews go?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
