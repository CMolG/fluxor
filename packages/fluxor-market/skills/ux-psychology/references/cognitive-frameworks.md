# Cognitive frameworks: mechanism → design consequence

Each section follows the same outline: **what the mechanism says**, **what it requires of the
interface** and **what it does NOT entitle you to claim**. That last part matters: most abuses of
"neuro" talk in UX consist of turning a correlation into a design mandate.

Contents:

1. [Cognitive load theory](#1-cognitive-load-theory)
2. [The gulfs of execution, evaluation and envisioning](#2-the-gulfs-of-execution-evaluation-and-envisioning)
3. [The Fogg Behavior Model (B=MAP)](#3-the-fogg-behavior-model-bmap)
4. [Aesthetics, reward and the aesthetic-usability effect](#4-aesthetics-reward-and-the-aesthetic-usability-effect)
5. [The ventral and dorsal visual pathways](#5-the-ventral-and-dorsal-visual-pathways)
6. [Processing fluency and trust](#6-processing-fluency-and-trust)
7. [Deferred trust in AI systems](#7-deferred-trust-in-ai-systems)
8. [Dark patterns](#8-dark-patterns)
9. [Desirable difficulties and microboundaries](#9-desirable-difficulties-and-microboundaries)
10. [Cognitive offloading and cognitive debt](#10-cognitive-offloading-and-cognitive-debt)

---

## 1. Cognitive load theory

**Mechanism.** Working memory holds very few elements at once before consolidating them into
long-term schemas. The demand splits into three types that add up:

| Type | What it is | What to do with it |
| :---- | :---- | :---- |
| **Intrinsic** | Difficulty inherent to the task, set by how many concepts must be held *simultaneously* (element interactivity) | It can't be removed: sequence it (progressive disclosure, *chunking*) and adapt it to the user's level |
| **Extraneous** | Effort imposed by the design: visual noise, redundancy, split attention, arbitrary hierarchies | Reduce it to the absolute minimum. It's the only type that is always a defect |
| **Germane** | Productive effort devoted to understanding and building schemas | Maximize it, but it only shows up once extraneous load is already low |

**Design consequences.**
- Put text and images that explain each other in the same visual focus; separating them forces
  split attention and doubles the cost.
- The complexity of the task decides the number of steps, not the "everything on one screen" trend.
- If the user has to remember something from the previous screen, you've turned intrinsic load
  into extraneous load for nothing.
- The symptom of overload isn't a complaint: it's errors, decision paralysis, blindness to elements
  that are right there, and abandonment.

**It does not entitle you to claim** that there's a universal magic number of elements, or that
"less is always more": cutting below what the task requires shifts the work onto the user's memory.

## 2. The gulfs of execution, evaluation and envisioning

**Mechanism.** Interaction is a seven-stage cycle: goal → intention → action specification →
execution → perception of the new state → interpretation → evaluation against the goal. Two gaps
open up:

- **Gulf of execution**: the user knows what they want, but the interface doesn't communicate how to
  do it. It's closed with visible affordances, natural mapping of controls and respect for
  conventions.
- **Gulf of evaluation**: after acting, the user can't tell whether it worked. It's closed with
  immediate feedback, system status that's always visible and messages people can interpret.

Unexpected delays in the screen's response don't just annoy: they degrade feedback-based learning,
because the brain can no longer attribute the result to its own action.

**A third gulf, in LLM interfaces: the gulf of envisioning.** Writing a precise instruction means
translating an abstract intention into language the machine will interpret correctly; the cognitive
cost shifts from mechanical execution to semantic articulation and to negotiating the result. In
practice: offer examples and templates, show how the system interpreted the request, and let people
correct parts of the output instead of rewriting from scratch.

## 3. The Fogg Behavior Model (B=MAP)

**Mechanism.** A behavior happens only when **motivation**, **ability** and a **prompt** converge.
Motivation responds to core motivators (pleasure/pain, hope/fear, social acceptance/rejection);
ability is real simplicity, both cognitive and physical; the prompt is the stimulus that triggers
the action at that moment.

**Mandatory order of intervention:** (1) make sure the prompt is perceived, (2) make the action
trivial, (3) and only then, motivation. Changing motivational drivers is the most expensive option
and the one that most easily degenerates into manipulation. A highly motivated user facing a
demanding interface fails just the same.

**Use in diagnosis.** When "it doesn't convert": is the prompt visible at the moment and in the
place where the user already is? How many steps, fields and decisions separate the intention from
the result? Only once both are solved does it make sense to talk about incentives.

## 4. Aesthetics, reward and the aesthetic-usability effect

**Mechanism.** Users perceive attractive designs as easier to use even when their objective
performance is identical. Aesthetically pleasing stimuli activate reward circuits (ventromedial
prefrontal cortex, medial orbitofrontal cortex, ventral striatum, anterior cingulate), the same ones
that process primary rewards; that hedonic tag transfers by a halo effect to the assessment of
usefulness. Interfaces perceived as chaotic or unpleasant are associated with aversive responses.

Related: the Gestalt **aesthetic "aha"**. Resolving a visual ambiguity or grasping an interface
metaphor produces pleasure and strengthens brand affinity.

**Design consequences.** Invest in visual quality: it buys tolerance, trust and perceived
competence. And don't use it as a metric: in usability tests, always keep reported satisfaction
separate from task success, because the former is contaminated by the halo.

**It does not entitle you to claim** that a beautiful design *is* usable, or that an activation
heat map proves pleasure or frustration (see `audit-and-metrics.md`, reverse inference).

## 5. The ventral and dorsal visual pathways

**Mechanism.** Visual information splits after the occipital cortex:

- **Ventral ("what")**, toward the temporal lobe: conscious recognition of shapes, objects, color,
  text and faces. It's what reads a paragraph or recognizes that an icon means "cart".
- **Dorsal ("where/how")**, toward the parietal cortex: spatial location, motion and real-time motor
  guidance, largely nonconscious. It's what moves your finger to the button without looking at it.

**Design consequences.**
- Ventral fatigue: cryptic unlabeled icons, low contrast, small type, information density that
  forces pixel-by-pixel decoding.
- Dorsal sabotage: menus that move between pages, small controls or controls with no margin,
  unpredictable positions, layout shifts between states. They destroy spatial memory and force users
  to consciously remap the screen on every visit.
- A healthy design splits the work: the dorsal pathway should be able to take the user to the right
  control **without** the ventral pathway having to read anything.

## 6. Processing fluency and trust

**Mechanism.** The brain doesn't just process content (first-order cognition); it also monitors how
much effort processing it takes (metacognition). When processing feels easy, that feeling is tagged
as positive and **mistaken for truth, safety and competence**. It's the most widespread and cheapest
heuristic we use to decide whether to trust something.

Three levels to look after separately:
- **Perceptual**: contrast, legibility, alignment, density, rhythm.
- **Conceptual**: an understandable hierarchy, familiar vocabulary, groupings that match the user's
  mental model.
- **Linguistic**: plain language, short sentences, no internal jargon.

**Text-image congruence** is a critical case: when image and text don't match exactly, it creates
dissonance, and the user reads it as a reason to distrust the provider, even if they can't say why.
In commerce and bookings, lowering cognitive load (progressive disclosure, predictable menus, strict
congruence) moves purchase intent, not just liking.

**The flip side of the risk:** fluency also makes people swallow false content. See the next section.

## 7. Deferred trust in AI systems

**Mechanism.** When people distrust human agents or institutions, they redirect their reliance
toward AI systems that, through highly polished interfaces and fluent language, project competence
and neutrality. Users tend to trust AI for factual decisions and to prefer humans for decisions with
moral or social weight. The danger is overtrust: extreme fluency numbs skepticism and encourages
people to accept wrong or fabricated output.

**Design consequences.**
- Make verification cheap: linked sources, quotable excerpts, "where this comes from".
- Express uncertainty perceptibly and honestly, not as a legal disclaimer in the footer.
- State the system's limits at the point of use, not in the terms and conditions.
- Design editing and correction as the main path, not as the exception.
- Watch for the perverse effect: the better the interface looks, the more vigilance you need to hand
  back to the user.

## 8. Dark patterns

**Mechanism.** Interfaces designed to get the user to do something they didn't intend, by exploiting
biases and fast heuristic processing. Main types:

| Pattern | Mechanism exploited | Antidote |
| :---- | :---- | :---- |
| **Roach motel** | Load asymmetry: getting in is smooth, getting out is a maze | Symmetric entry/exit steps (INV-08) |
| **Visual interference** | Visual hierarchy: the harmful option looks like the only actionable one | Parity of control, size and contrast (INV-09) |
| **False urgency / scarcity** | Loss aversion; it inhibits deliberate evaluation | Only true, verifiable data (INV-10) |
| **Confirmshaming** | Social cost and guilt for saying no | Neutral, symmetrical wording (INV-11) |
| **Preselection and default consent** | Status quo bias, decision fatigue | Explicit opt-in, no pre-checked boxes |
| **Hidden costs** | Escalating commitment (*sunk cost*) | Total cost visible from the first step |

Besides being harmful, it's regulated: see `regulation-and-ethics.md`.

## 9. Desirable difficulties and microboundaries

**Mechanism.** An environment with no effort at all produces shallow processing and poor
consolidation in memory. **Desirable difficulties** are obstacles that hurt immediate performance
and greatly improve long-term retention and transfer: retrieval practice (recalling instead of
rereading), spaced practice, interleaving problem types.

In load terms: an undesirable difficulty is **extraneous** load (a confusing menu); a desirable one
is **germane** load induced on purpose. The difference isn't how much it costs, but whether the cost
builds schemas in the user.

**Microboundaries** are minimal frictions placed right before a critical action: making the user
type the repository's name before deleting it, a pause before sending to the whole list. Their job
is to force the shift from automatic gesture to conscious deliberation. They're also used in digital
wellbeing (breaking compulsive loops) and in financial systems (preventing typos).

**Rule of application.** Desirable friction only if: (a) the goal is learning or mastery, or
(b) it protects the user from irreversible harm. Any other friction serves the business and should
be removed.

## 10. Cognitive offloading and cognitive debt

**Mechanism.** Outsourcing memory, calculation, wayfinding or reasoning to tools reduces effort
today. Over the medium term it interferes with the "use it or lose it" principle of neuroplasticity:
the information never gets consolidated (the Google effect / digital amnesia). With generative
tools, the phenomenon scales up to synthesis and analysis, piling up **cognitive debt**: the erosion
of critical thinking, sustained attention and independent problem solving.

**Design consequence.** Decide explicitly what gets mechanized and what gets protected. Automate
what's repetitive and error-prone; keep the human at the point where judgment is exercised, and make
that comfortable (this isn't "putting up obstacles", it's designing the place where the person
decides). In educational and professional tools, this is a product decision, not a UX detail.
