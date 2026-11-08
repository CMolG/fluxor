# Regulation and ethics

Design guidance, **not legal advice**. Every flow with regulatory exposure (consent, subscriptions,
pricing, personal data, biometrics, minors) must go through human legal review before it ships.

## 1. Dark patterns: from bad practice to noncompliance

In the European Union, the **Digital Services Act (DSA, Regulation (EU) 2022/2065)** explicitly
prohibits designing, organizing or operating interfaces that deceive, manipulate or materially
distort users' ability to make free and informed decisions. Fines can reach 6% of annual global
turnover, and the framework expressly covers cancellation friction that isn't technically justified
and manipulative confirmation sequences. Other consumer-protection and data-protection rules overlap
depending on the case.

The practical consequence: **interface design is no longer just aesthetics or conversion; it's
compliance**. Invariants INV-08 to INV-11 are the operational translation of this.

**Hot zones** (mandatory review before shipping):

- Consent banners and preference centers.
- Subscription sign-up and cancellation, auto-renewals, free trials that convert to paid.
- Prices, fees and costs added during checkout.
- Pre-checked boxes, extras selected by default, added insurance and donations.
- Countdowns, scarcity indicators, "X people are looking at this".
- Interfaces aimed at minors or with a mostly underage audience.

**Quick contrast test.** For every relevant choice, ask: if the user fully understood what was
happening, would they choose the same thing? If the answer depends on them **not** understanding it,
it's a dark pattern by definition, regardless of what it's called internally.

## 2. Cognitive accessibility: COGA and WCAG 2.2

The W3C's Cognitive and Learning Disabilities Accessibility Task Force (COGA) shaped much of the
evolution toward WCAG 2.1 and 2.2, with success criteria designed to offload executive function and
working memory. Mapping cognitive goals to criteria:

| Cognitive goal | WCAG 2.2 criteria (selection) | Why, in this skill's terms |
| :---- | :---- | :---- |
| Understand structure and interaction | 1.3.1 Info and Relationships · 1.3.5 Identify Input Purpose | Standard icons, descriptive labels and a logical order avoid overloading the ventral pathway with heuristic recognition (INV-04, INV-07) |
| Don't rely on memory | 3.3.7 Redundant Entry · 3.3.8 Accessible Authentication | Removes manual transcription between screens and memorized passwords: direct working-memory bottlenecks (INV-02) |
| Reduce distraction and protect focus | 2.2.x Enough Time · 2.4.6 Headings and Labels | Intrusive notifications, automatic animations and aggressive timers hijack involuntary attentional orienting (INV-03) |
| Recover from errors | 3.3.1 Error Identification · 3.3.3 Error Suggestion | Closes the gulf of evaluation: cause and way out, not just a failure signal (INV-05) |
| Reach the controls | 2.5.8 Target Size · 2.4.11 Focus Not Obscured | Supports the dorsal pathway and guided motor control (INV-06) |

Level AA is the floor, not the goal. And cognitive accessibility isn't a minority case: fatigue,
noise, hurry and multitasking temporarily put anyone in that profile.

## 3. Data, biometrics and neurodata

- A legal basis and a declared purpose before collecting any signal; explicit, informed and
  revocable consent where applicable.
- Gaze, pupillometry, EEG and emotional inferences usually fall into a special category (GDPR
  Art. 9); see `audit-and-metrics.md` §4.
- Aggressive minimization: the minimum signal, aggregated whenever possible, with short retention.
- Transparency about inferences: what is deduced, by what method and with what margin of error.
- Profiling personality traits, psychological states or health from signals captured for another
  purpose is forbidden.
- *Ethics-by-design*: the decision is documented before the first capture, with auditable logs.

## 4. Responsibility for cognitive debt

Removing all friction isn't neutral. Systematically outsourcing memory, calculation and, above all,
synthesis and judgment erodes a person's abilities over the medium term (see
`cognitive-frameworks.md` §10). Designers decide what gets mechanized and what gets protected, and
that decision should be explicit and documented, especially in education, health, finance and
professional tools.

Questions to answer in writing for any product that automates intellectual tasks:

1. What user ability atrophies if they use this every day for a year?
2. Where is the point at which the person exercises judgment, and is it designed to be comfortable?
3. Does the product make it easy to verify, or easy to trust without verifying?
4. What happens if the system gets it wrong and nobody notices? Who detects it, and how?

## 5. Hard limit

No business metric justifies breaking INV-08 to INV-11 or INV-14. If a product requirement demands
the opposite, the right response is to say so clearly, explain the legal and reputational exposure,
and propose the legitimate alternative that pursues the same business goal: improve the prompt,
reduce the friction of the desired action and make the value more obvious (PRO-06), instead of
making it harder to leave.
