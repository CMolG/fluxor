# Audit and metrics

Order of preference: **observed behavior > structured self-report > physiological signal**.
Physiological signals are expensive, fragile and easy to overinterpret; bring them in only when
behavior isn't enough to tell two hypotheses apart, and always triangulated.

## 1. Behavioral proxies (what you can measure without lab equipment)

These come from conventional product analytics. Each one has a likely interpretation, not a certain
one: treat it as a signal of where to look.

| Signal | Calculated as | Usually indicates |
| :---- | :---- | :---- |
| **Time to first meaningful action** | From the moment the view is interactive to the first non-exploratory event | Gulf of execution: people can't see how to start |
| **Hesitation before clicking** | Time between the first *hover*/focus on a control and its activation | An ambiguous label, fear of the consequence |
| **Backtracking** | Going back or closing before completing the step | A broken mental model: it wasn't what it promised |
| **Undo or correction rate** | Reverted actions / total actions | Too little friction on irreversible actions, or a misleading label |
| **Errors per field** | Failed validations per field and per attempt | A poorly communicated format, memory dependency |
| **Drop-off per field** | The last field with focus before leaving | The exact point where load outweighed motivation |
| **Search after navigating** | Search use within N seconds of entering a section | A taxonomy that doesn't match the mental model |
| **Rereading / visual back-and-forth** | Going back and forth between two areas | Split attention: information that should be together |
| **Repeated data** | The same value entered twice in the flow | INV-02 broken |
| **Novice vs. expert** | The same metrics segmented by tenure | The real size of the learning curve |

Useful, cheap self-report complements: **SEQ** (a single difficulty question right after the task,
while the memory is fresh), **SUS** for comparing versions, **NASA-TLX** for perceived workload.
Remember that self-report is contaminated by the aesthetic halo: ask about task difficulty, not
whether they "liked it".

**Method rule.** Set the threshold *before* touching anything: "if drop-off at step 3 doesn't fall
from 18% to 12%, the hypothesis was false". Without a prior threshold, any result can be
rationalized.

## 2. Physiological signals: what they contribute and what they don't

### Eye tracking and pupillary response (TEPR)

Task-evoked pupil dilation is one of the cleanest noninvasive indices of momentary mental effort and
working-memory use: it grows almost linearly with cognitive demand and distinguishes complexity
levels within the same task. It lets you pinpoint the exact sub-segment of an interface that
demands too much, even when performance looks flawless. Novices show larger responses than experts
on the same correctly completed task: it can measure a product's real learning curve.

**Conditions for it to be worth anything:** strictly controlled ambient lighting (the pupil responds
to light before it responds to cognition), a per-subject baseline, a time-bounded task. Outside the
lab, it's almost always noise.

### EEG: frequency bands and the theta-alpha ratio (TAR)

The bands and their usual functional reading: **delta** (0.1–4 Hz) drowsiness and extreme fatigue;
**theta** (4–8 Hz) sustained concentration and task difficulty, especially frontal; **alpha**
(8–13 Hz) cortical relaxation, and its parietal suppression indicates active attention;
**beta/gamma** (>13 Hz) alertness, analytical processing and affective engagement with aesthetics.

The most robust index of mental workload is the **theta-alpha ratio (TAR)**: frontal theta power
(Fz) divided by parietal alpha power (Pz). Faced with poor design or ambiguous instructions, theta
rises and alpha falls: the TAR spikes. It's the basis of **adaptive interfaces**, which, on detecting
imminent overload, reduce visual density, slow the task down or tone down notifications. That makes
sense in air traffic control, surgical simulation or immersive training, and rarely on a commercial
website.

### Event-related potentials (ERPs)

- **N200** (200–300 ms): novelty, conflict between stimuli, the need to inhibit a response already
  prepared. In UI it shows up in response to the unexpected and to whatever contradicts convention.
- **P300** (300–500 ms): conscious evaluation and updating of context in working memory. Its
  attenuation beforehand predicts that the user is about to make an error through an attentional
  lapse.
- **ERN** (error-related negativity): a pulse generated in the anterior cingulate within milliseconds
  when the system behaves differently than expected or the user makes a mistake, **before** they
  are aware of the error. It's the objective signature of "this isn't what I thought was going to
  happen".

Legitimate product use: comparing two variants in the lab to locate the exact instant expectations
break. Illegitimate use: presenting an activation as proof of an emotion.

### fNIRS

It measures cortical oxygenation with fewer immobility constraints than MRI; combined with eye
tracking, it offers ecological validity in natural tasks, 3D environments and reading. It's still
lab equipment.

## 3. The reverse inference fallacy

The reasoning "the insula activates when there's frustration; the insula activated in our test;
therefore the interface is frustrating" is **structurally invalid**: it's affirming the consequent.
The brain is pleiotropic: the insula takes part in disgust, pain, complex language processing,
interoception and general autonomic arousal. No region equals a mental state.

For a physiological inference to carry predictive weight, you need: correction for the **base rate**
of activation of that region (Neurosynth-style meta-analyses), multivariate decoding of patterns
instead of "hot spots", and mandatory triangulation with behavior and self-report.

**In practice, within this skill:** neurocognitive mechanisms serve to **generate hypotheses and
set priorities**, never as proof. If you remove the word "cortex" from an argument and it no longer
holds up, it wasn't an argument (INV-13).

## 4. Neuroprivacy

Neurodata and attentional biometrics aren't retrospective traces of voluntary behavior: they expose
subconscious attention flows and intentions before the person decides to express them, and they make
it possible to profile traits nobody has agreed to reveal. Under the GDPR they usually fall into a
special category (Art. 9), with explicit consent and a solid legal basis as preconditions.

If a project captures gaze, pupil, EEG or emotional inferences:

- A declared, bounded purpose, with explicit, informed and revocable consent.
- Real minimization: the bare minimum signal, aggregated whenever possible, short retention.
- No opaque algorithms: what is inferred, how, and with what margin of error; auditable logs.
- No profiling of traits, psychological states or health from these signals.
- *Ethics-by-design* documented before the first capture, not after the first incident.

## 5. Minimum user-testing protocol

1. Real tasks phrased as goals ("get an invoice for March"), never in interface terms ("click the
   billing menu").
2. 5–8 participants per profile catch most of the serious problems; segment novice/expert, because
   they measure different things.
3. Measure **task success, time and errors** before asking for opinions.
4. Ask about perceived difficulty right after each task, not at the end of the session.
5. Always keep reported satisfaction separate from observed performance; when they diverge,
   performance wins, and suspect the aesthetic halo.
6. Write the hypotheses and thresholds down before the session.
