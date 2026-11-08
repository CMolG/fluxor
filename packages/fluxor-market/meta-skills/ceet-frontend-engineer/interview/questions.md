# Interview — Frontend Engineer

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 25 | ~37 | ~62 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: rendering and performance | 6 | — | ~20 | optional |
| Depth: styling, motion, states and forms | 13 | — | ~31 | optional |
| Depth: types, tests and git | 8 | — | ~23 | optional |
| Depth: working with others | 5 | — | ~13 | optional |

## Core interview

Who the person is and how they reason about UI: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What surface do you own (marketing site, app, design system, internal tools)?

<sub>~3 min · feeds `identity.cognitive_signature`</sub>

**Q2.** What's your framework + build + styling stack?

<sub>~2 min · feeds `identity.cognitive_signature`, `directives.styling.methodology`</sub>

**Q3.** Who are your users (consumer, B2B, internal), and what's their typical device / network?

<sub>~2 min · feeds `identity.cognitive_signature`, `directives.performance.web_vitals_priority`</sub>

**Q4.** How large is your component library or design system, and are you a consumer or author of it?

<sub>~2 min · optional · feeds `identity.cognitive_signature`, `directives.styling.deviation_policy`</sub>

### B. Mental models

**Q5.** When you see a new screen in a design file, what do you mentally break it into first — layout regions, components, data dependencies, or states?

<sub>~3 min · feeds `identity.decision_framework`, `directives.component_design.composition_philosophy`</sub>

**Q6.** Do you think of a component primarily as a *unit of data*, a *unit of markup*, a *unit of behavior*, or a *unit of visual identity*? Has that answer changed over your career?

<sub>~3 min · feeds `identity.cognitive_signature`, `directives.component_design.composition_philosophy`</sub>

**Q7.** How do you explain "reactive UI" to someone who's never written any?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

### C. State

**Q8.** What goes in local state, what gets lifted, what belongs in a store, and what belongs in the URL?

<sub>~3 min · feeds `directives.state_management.local_vs_global_rules`, `directives.state_management.url_state_policy`</sub>

- Probe: When does that rule break, and when does it never break?

**Q9.** Server state vs. client state — where do you draw the line, and what library/pattern do you reach for?

<sub>~3 min · feeds `directives.state_management.server_vs_client_state`</sub>

**Q10.** What's an anti-pattern around state that you see constantly in other people's code?

<sub>~2 min · optional · feeds `directives.state_management.anti_patterns`</sub>

- Probe: Give me a recent, concrete example.

### D. Component architecture

**Q12.** What makes a component "too big" for you? What's your refactor trigger?

<sub>~3 min · feeds `directives.component_design.size_triggers`, `directives.code_review.refactoring_stance`</sub>

- Probe: What number would you put on it?

**Q13.** How do you feel about prop-drilling, render props, slots, composition, and context? Rank them, roughly.

<sub>~3 min · optional · feeds `directives.component_design.prop_drilling_stance`</sub>

**Q14.** Do you design for *composition* or *configuration* first? Example?

<sub>~3 min · feeds `directives.component_design.composition_vs_configuration`</sub>

- Probe: When does that rule break, and when does it never break?

**Q15.** What's a component pattern you reach for that most people don't?

<sub>~2 min · optional · feeds `directives.component_design.composition_philosophy`</sub>

- Probe: Give me a recent, concrete example.

### G. Accessibility

**Q24.** Walk me through what you check before merging a component. (If they don't say "keyboard," probe specifically.)

<sub>~4 min · feeds `directives.accessibility.pre_merge_checklist`, `directives.accessibility.keyboard_navigation`</sub>

- Probe: What do you check with the keyboard alone, and in what order?

**Q25.** What ARIA pattern do you reach for most often, and which one do you consistently see people misuse?

<sub>~2 min · optional · feeds `directives.accessibility.aria_patterns`</sub>

**Q26.** What's your stance on "div soup"? How militant are you on semantic HTML?

<sub>~2 min · optional · feeds `directives.accessibility.semantic_html_stance`</sub>

**Q27.** What automated / manual a11y checks are in your workflow?

<sub>~2 min · optional · feeds `directives.accessibility.testing_approach`</sub>

### L. Taste & heroes

**Q39.** Name 2-3 websites or apps whose frontend craft you admire. What specifically?

<sub>~3 min · feeds `identity.core_values`, `directives.personality.quality_calibration`</sub>

**Q40.** What's a UI pattern that looks fashionable right now but you distrust?

<sub>~2 min · optional · feeds `identity.core_values`</sub>

**Q41.** What's a small detail (focus rings, loading behavior, hover states) you care about that others overlook?

<sub>~2 min · optional · feeds `directives.personality.quality_calibration`</sub>

- Probe: Give me a recent, concrete example.

### M. Anti-patterns

**Q42.** What do you consistently reject in PRs?

<sub>~3 min · feeds `directives.code_review.blocking_criteria`</sub>

- Probe: Give me a recent, concrete example.

**Q43.** What's a pattern you outgrew — used to love, now avoid?

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

### N. Vocabulary

**Q44.** Any local vocabulary for components or patterns? (e.g. "composer", "island", "shell", "chrome"...)

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

**Q45.** Any words you refuse to use ("beautiful", "clean", "slick", "pop")?

<sub>~2 min · feeds `identity.communication_voice`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### O. Real decisions

**Q46.** Pick a hard frontend decision from the last few months, one where reasonable engineers would have disagreed: a state library, a rendering mode, a component API, a design-system break. Walk me through it from the first signal: what you noticed, the options you had, what you chose, and what made the difference.

<sub>~8 min · incident · captures decisions · feeds `identity.decision_framework`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q11.** Tell me about a time you regretted a state choice. What did you learn?

<sub>~6 min · incident · captures decisions · feeds `directives.state_management.anti_patterns`, `directives.state_management.local_vs_global_rules`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q47.** Think of an interactive component going into your app or design system: a combobox, a modal, a data table. What would a capable mid-level engineer miss when building or reviewing it that you would catch? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.code_review.blocking_criteria`, `directives.accessibility.keyboard_navigation`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q48.** Bring a real pull request touching UI that you reviewed recently. Walk through it the way you did: where you slowed down, what you flagged, what you let go, and what you wrote.

<sub>~8 min · simulation · captures decisions · feeds `directives.code_review.philosophy`, `directives.code_review.mentoring_voice`, `directives.code_review.blocking_criteria`</sub>

- Probe: Why did you let that one go?
- Probe: What would have made you block it?

**Q49.** Think of two component APIs for the same kind of need, one you approved and one you pushed back on (or build the pair now from your codebase). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.component_design.composition_vs_configuration`, `identity.decision_framework`</sub>

- Probe: Which detail would flip your verdict?

**Q50.** Here is all you get: after last week's release, INP at the 75th percentile on your busiest page went from 150 ms to 450 ms, lab scores are unchanged, and nobody has complained. What do you do first, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.performance.web_vitals_priority`, `directives.performance.memoization_stance`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you revert the release without knowing more?

## Depth: rendering and performance (optional)

Rendering modes, Web Vitals, bundles, media, memoization and hydration.

### F. Rendering & performance

**Q20.** SSR vs. SSG vs. CSR vs. streaming vs. islands — when do you pick which?

<sub>~4 min · optional · feeds `directives.rendering.ssr_ssg_csr_rules`, `directives.rendering.streaming_strategy`, `directives.rendering.islands_stance`</sub>

- Probe: When does that rule break, and when does it never break?

**Q21.** Which Web Vital do you chase first (LCP, INP, CLS)? What's your workflow when it regresses?

<sub>~3 min · optional · feeds `directives.performance.web_vitals_priority`</sub>

**Q22.** What's your approach to code-splitting and bundle size?

<sub>~3 min · optional · feeds `directives.performance.bundle_strategy`, `directives.performance.lazy_loading_rules`</sub>

- Probe: What number would you put on it?

**Q23.** What images / media strategy do you default to?

<sub>~2 min · optional · feeds `directives.performance.image_optimization`</sub>

### P. Under the hood

**Q52.** When do you reach for memoization (memo, useMemo, a compiler, signals), and when do you remove it? What did you measure the last time you decided?

<sub>~3 min · optional · feeds `directives.performance.memoization_stance`</sub>

- Probe: Give me a recent, concrete example.

**Q53.** Tell me about a hydration mismatch, a layout shift or a server/client divergence you chased. What did you look at, in what order, and what rule came out of it?

<sub>~5 min · incident · optional · captures decisions · feeds `directives.rendering.hydration_approach`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?

## Depth: styling, motion, states and forms (optional)

The design system in code, responsive layout, motion, the states of a component and forms.

### E. Styling & design system

**Q16.** Utility classes, CSS modules, CSS-in-JS, plain CSS, vanilla-extract — what's your stack and *why that one*?

<sub>~3 min · optional · feeds `directives.styling.methodology`</sub>

**Q17.** How do you handle design tokens and theming?

<sub>~3 min · optional · feeds `directives.styling.design_tokens`, `directives.styling.dark_mode_approach`</sub>

**Q18.** What's your stance on custom components vs. using a UI kit (Radix, shadcn, Headless UI, Chakra, etc.)?

<sub>~2 min · optional · feeds `directives.styling.deviation_policy`, `identity.decision_framework`</sub>

**Q19.** Where do you refuse to deviate from the design system, and where do you allow local overrides?

<sub>~2 min · optional · feeds `directives.styling.deviation_policy`</sub>

- Probe: When does that rule break, and when does it never break?

**Q51.** How do you make a layout work from a small phone to a wide screen: mobile first or desktop first, breakpoints or container queries? Show me the last layout that fought you.

<sub>~3 min · optional · feeds `directives.styling.responsive_strategy`</sub>

- Probe: Give me a recent, concrete example.

### I. Motion & micro-interactions

**Q31.** Where do you add motion deliberately? Where do you refuse?

<sub>~2 min · optional · feeds `directives.motion.where_deliberate`, `directives.motion.where_refuse`</sub>

**Q32.** What's a UI animation you consider a smell / overused?

<sub>~2 min · optional · feeds `directives.motion.where_refuse`</sub>

**Q33.** Default duration, easing, and reduced-motion stance?

<sub>~2 min · optional · feeds `directives.motion.easing_duration`, `directives.motion.reduced_motion`</sub>

- Probe: What number would you put on it?

### J. Empty / loading / error

**Q34.** Do you design all four states (empty, loading, error, success)? If not, which do you skip and why?

<sub>~3 min · optional · feeds `directives.ui_states.state_coverage`</sub>

**Q35.** Skeletons vs. spinners vs. optimistic UI — your defaults?

<sub>~2 min · optional · feeds `directives.ui_states.loading_pattern`</sub>

### H. Forms & validation

**Q28.** Where does validation live — on blur, on submit, on every keystroke? Why?

<sub>~3 min · optional · feeds `directives.forms_validation.validation_timing`, `directives.forms_validation.validation_location`</sub>

**Q29.** How do you design error states? Inline, summary, toast, field-level, or combination?

<sub>~2 min · optional · feeds `directives.forms_validation.error_states`</sub>

**Q30.** What's your default for controlled vs. uncontrolled inputs?

<sub>~2 min · optional · feeds `directives.forms_validation.controlled_vs_uncontrolled`</sub>

## Depth: types, tests and git (optional)

TypeScript, testing, reviews and git habits.

### K. Testing

**Q36.** Unit / component / integration / E2E / visual regression — what's your mix and where does each live?

<sub>~3 min · optional · feeds `directives.testing.unit_component_e2e_mix`, `directives.testing.visual_regression`</sub>

**Q37.** What do you refuse to test? What do you over-test?

<sub>~3 min · optional · feeds `directives.testing.unit_component_e2e_mix`, `directives.testing.coverage_expectations`</sub>

- Probe: What number would you put on it?

**Q38.** When do you reach for a Storybook-like tool, and what do you put in it?

<sub>~2 min · optional · feeds `directives.testing.storybook_stance`</sub>

### Q. Types, tests & git

**Q54.** How strict is your TypeScript: which compiler flags, and what do you do with `any`, `as` casts and non-null assertions? What would you block in a pull request?

<sub>~3 min · optional · feeds `directives.typescript.strictness_level`, `directives.typescript.any_policy`</sub>

**Q55.** Type aliases or interfaces, and when do you write a generic? Show me a generic you are proud of, or one you removed because it was too clever.

<sub>~3 min · optional · feeds `directives.typescript.type_vs_interface`, `directives.typescript.generic_patterns`</sub>

**Q56.** In component and end-to-end tests, what do you mock (the network, time, the browser, child components) and what do you insist is real? Tell me about a mock that lied to you.

<sub>~3 min · optional · feeds `directives.testing.mocking_philosophy`</sub>

- Probe: Give me a recent, concrete example.

**Q57.** How do you branch, and how do you write commit messages? Paste a real commit message of yours that you would call a good one.

<sub>~3 min · optional · feeds `directives.git_workflow.branching_strategy`, `directives.git_workflow.commit_message_format`, `directives.git_workflow.commit_message_example`</sub>

**Q58.** How do you write a review comment on a less experienced engineer's component: the tone, how much you explain, what you leave as a suggestion? Paste a real one if you can.

<sub>~3 min · optional · feeds `directives.code_review.mentoring_voice`, `directives.code_review.philosophy`</sub>

## Depth: working with others (optional)

Uncertainty, crises, how the person has changed, focus and frustration.

### R. Working with others

**Q59.** When you are unsure or stuck, how do you say so, and at what point do you escalate or ask for help? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q60.** The day of a launch, part of your users get a blank page. What do you do in the first ten minutes, and how do you talk to people while it is happening?

<sub>~3 min · optional · feeds `directives.meta_cognition.crisis_personality`</sub>

**Q61.** What frontend belief did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q62.** When do you do your best work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q63.** What reliably frustrates you in a codebase or in a team's habits?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
