# Interview — Copywriter

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 27 | ~36 | ~64 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: microcopy, brand and heuristics | 11 | — | ~23 | optional |
| Depth: working with others | 5 | — | ~13 | optional |

## Core interview

Who the person is and how they reason about writing: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What kind of writing do you do (marketing pages, email, UX / microcopy, long-form, ads, all of the above)?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

**Q2.** What brands / products / audiences have you written for? What's current?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q3.** Who reviews your work? What feedback loop do you run on?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

### B. Voice through contrast

**Q4.** Three sentences you'd write without hesitation.

<sub>~3 min · feeds `directives.voice.principles`, `directives.voice.sentence_rhythm`</sub>

**Q5.** Three sentences you'd never let ship, even if a stakeholder asked.

<sub>~3 min · feeds `directives.voice.principles`, `identity.core_values`</sub>

**Q6.** Put your voice on axes: serious↔playful, formal↔casual, reverent↔irreverent, sparse↔rich. Where's home?

<sub>~2 min · feeds `directives.voice.axes`, `directives.voice.contractions_stance`</sub>

- Probe: Where do contractions sit on that line for you: always, never, or depending on the channel?

### C. Heroes

**Q7.** Three writers, copywriters, or brands whose voice you measure against. Why each?

<sub>~3 min · feeds `directives.heroes.writers_admired`, `directives.heroes.brands_admired`</sub>

**Q8.** Three pieces of your own work you're proud of. What makes them work?

<sub>~3 min · optional · feeds `directives.heroes.work_proud_of`, `directives.personality.quality_calibration`</sub>

### D. Structure

**Q10.** How do you open a landing page? An email? An ad?

<sub>~3 min · feeds `directives.structure.landing_page_open`, `directives.structure.email_open`, `directives.structure.ad_open`</sub>

**Q11.** Do you write headline-first, body-first, CTA-first, or outline-first? Why?

<sub>~2 min · feeds `directives.structure.headline_body_cta_order`</sub>

**Q12.** AIDA, PAS, story-arc, reverse pyramid — which frameworks do you actually use, and which do you mock?

<sub>~2 min · optional · feeds `directives.structure.headline_body_cta_order`, `identity.decision_framework`</sub>

### E. Audience

**Q13.** When you sit to write, who are you picturing? In what state (distracted, skeptical, hopeful, pissed)?

<sub>~3 min · feeds `directives.audience.reader_state`</sub>

**Q14.** What's a reader assumption you make that others don't?

<sub>~2 min · optional · feeds `directives.audience.attention_assumptions`</sub>

**Q15.** Reading level — what's your target? What's too dumbed-down?

<sub>~2 min · feeds `directives.audience.reading_level`</sub>

- Probe: What number would you put on it?

### F. Persuasion

**Q16.** Proof, story, benefit, provocation, social proof, urgency — rank them by your default reach.

<sub>~3 min · feeds `directives.persuasion.proof_vs_story`, `directives.persuasion.social_proof_use`</sub>

**Q17.** Where do you refuse to push (manipulative urgency, false scarcity)?

<sub>~2 min · feeds `directives.persuasion.refused_tactics`, `directives.persuasion.urgency_stance`</sub>

- Probe: When does that rule break, and when does it never break?

**Q18.** What's a persuasion move that works but you won't do?

<sub>~2 min · optional · feeds `directives.persuasion.refused_tactics`, `identity.core_values`</sub>

### G. Editing

**Q19.** Your editing procedure — read aloud, cut half, tighten verbs, kill adjectives? What specifically?

<sub>~3 min · feeds `directives.editing.procedure`</sub>

- Probe: Give me a recent, concrete example.

**Q20.** What's your rule for sentence length and variance?

<sub>~2 min · optional · feeds `directives.editing.sentence_length_rule`, `directives.voice.sentence_rhythm`</sub>

- Probe: What number would you put on it?

**Q21.** What punctuation do you love (em-dash, semicolon)? Avoid?

<sub>~2 min · optional · feeds `directives.editing.punctuation_rules`</sub>

**Q22.** Oxford comma stance?

<sub>~1 min · optional · feeds `directives.editing.oxford_comma`</sub>

### H. Banned words & preferred words

**Q23.** List your banned words and phrases. ("Leverage", "seamless", "revolutionary", "delight", etc.)

<sub>~3 min · feeds `directives.banned_preferred.banned_words`, `identity.communication_voice`</sub>

**Q24.** List words you reach for constantly. What do they do for you?

<sub>~2 min · optional · feeds `directives.banned_preferred.reach_for_words`, `identity.communication_voice`</sub>

**Q25.** How do you handle buzzwords when stakeholders insist?

<sub>~2 min · optional · feeds `directives.banned_preferred.buzzword_handling`</sub>

- Probe: Give me a recent, concrete example.

### J. CTAs & conversion

**Q29.** CTA philosophy — literal vs. evocative? Short vs. long?

<sub>~2 min · feeds `directives.conversion.cta_philosophy`</sub>

**Q30.** How do you think about urgency, scarcity, and social proof honestly?

<sub>~3 min · optional · feeds `directives.conversion.urgency_framing`, `directives.conversion.scarcity_stance`, `directives.persuasion.social_proof_use`</sub>

**Q31.** What's a conversion win you're proud of? A loss?

<sub>~3 min · optional · feeds `directives.conversion.cta_philosophy`, `directives.conversion.urgency_framing`</sub>

- Probe: Give me a recent, concrete example.

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### O. Real decisions

**Q41.** Pick a hard copy decision from the last few months, one where reasonable writers would have disagreed: a headline, a claim, the tone of a sensitive message, a fight with a stakeholder over a word. Walk me through it from the first signal: what you noticed, the options you had, what you chose, and what made the difference.

<sub>~8 min · incident · captures decisions · feeds `identity.decision_framework`, `directives.voice.principles`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q9.** One piece you look back at and would rewrite. What was wrong?

<sub>~6 min · incident · captures decisions · feeds `directives.meta_cognition.knowledge_evolution`, `directives.personality.quality_calibration`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q42.** Think of a landing page or email draft a capable junior writer hands you. What would they miss that you would catch before it ships? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.editing.procedure`, `directives.audience.attention_assumptions`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q40.** Show me three before/after edits. Narrate why you changed each.

<sub>~8 min · simulation · captures decisions · feeds `directives.editing.procedure`, `directives.voice.sentence_rhythm`</sub>

- Probe: Why that cut and not another?
- Probe: What would a stakeholder have pushed back on, and would you give way?

**Q43.** Think of two headlines for the same page, one you shipped and one you killed (or write the pair now for a product you know). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.voice.principles`, `directives.persuasion.proof_vs_story`</sub>

- Probe: Which word would flip your verdict?

**Q44.** Here is all you get: the variant with a countdown timer and "only 3 left" converts 22% better in the test, the stock is not actually limited, and the growth lead wants it live tomorrow. What do you do, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.conversion.scarcity_stance`, `directives.conversion.urgency_framing`, `directives.persuasion.refused_tactics`</sub>

- Probe: Why that piece of information and not another?
- Probe: What would make you ship it anyway?

## Depth: microcopy, brand and heuristics (optional)

Interface copy, working with design and brand, the person's rules of thumb and what they outgrew.

### I. Microcopy

**Q26.** What makes a great button label to you? A great error message? A great empty state?

<sub>~3 min · optional · feeds `directives.conversion.cta_philosophy`, `directives.voice.principles`</sub>

**Q27.** What's a microcopy pattern you always push back on?

<sub>~2 min · optional · feeds `directives.voice.principles`</sub>

**Q28.** Do you believe in "conversational" UI copy, or is it overused?

<sub>~2 min · optional · feeds `directives.voice.axes`</sub>

### K. Working with design & brand

**Q32.** How do you collaborate with design — headline-first or layout-first?

<sub>~2 min · optional · feeds `directives.structure.headline_body_cta_order`</sub>

**Q33.** Where do you defer to brand guidelines? Where do you push?

<sub>~2 min · optional · feeds `identity.decision_framework`</sub>

**Q34.** How do you handle voice drift across channels (email vs. landing vs. in-product)?

<sub>~2 min · optional · feeds `directives.voice.principles`</sub>

### L. Heuristics

**Q35.** "If I can't read it aloud without stumbling, {X}."

<sub>~2 min · optional · feeds `directives.editing.procedure`</sub>

**Q36.** "When I'm stuck on a headline, I {X}."

<sub>~2 min · optional · feeds `identity.decision_framework`</sub>

**Q37.** "I know a draft is done when {X}."

<sub>~2 min · optional · feeds `directives.personality.quality_calibration`</sub>

### M. Anti-patterns

**Q38.** Copy trends you refuse to follow.

<sub>~2 min · optional · feeds `identity.core_values`</sub>

**Q39.** A mode of writing you outgrew.

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

## Depth: working with others (optional)

Uncertainty, crises, how the person has changed, focus and frustration.

### P. Working with others

**Q45.** When you are unsure about a call, how do you say so, and at what point do you escalate a decision instead of making it yourself? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q46.** A message goes out wrong: a typo in a subject line sent to a million people, a joke that lands as offensive, a price stated wrong. What do you do in the first hour, and how do you talk to people while it is happening?

<sub>~3 min · optional · feeds `directives.meta_cognition.crisis_personality`</sub>

**Q47.** What writing belief did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q48.** When do you do your best work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q49.** What reliably frustrates you in how teams brief, review or approve copy?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
