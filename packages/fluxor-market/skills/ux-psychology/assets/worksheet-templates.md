# Output templates

Copy the one that fits and fill it in. Sections are never omitted: if something doesn't apply,
write "not applicable" and why. An empty section usually signals an incomplete analysis, not a
trivial case.

---

## A. Analysis worksheet

```markdown
# Psych-UX analysis — [component or flow]

## Framing
- User's task: [in their terms, not in interface terms]
- Profile: [novice / returning / expert] · frequency: [...] · device: [...]
- Context of use: [hurry, fatigue, multitasking, noise, supervision...]
- Success = [observable criterion]
- Material analyzed: [code, screenshot, prototype, recorded session]

## Action cycle
| Stage | What happens today | Gap |
| :---- | :---- | :---- |
| Goal → intention | | |
| Intention → action | | Gulf of execution: [yes/no + where] |
| Action → perception | | |
| Perception → evaluation | | Gulf of evaluation: [yes/no + where] |

## Load inventory
| Element | Type (intrinsic/extraneous/germane) | On critical path | Decision |
| :---- | :---- | :---- | :---- |

## Invariant sweep
| ID | Verdict | Evidence |
| :---- | :---- | :---- |
| INV-01 Extraneous load ≈ 0 | ✅ / ⚠️ / ❌ | |
| INV-02 No memory dependency | | |
| INV-03 Nothing hijacks attention | | |
| INV-04 Cognitive accessibility floor | | |
| INV-05 No gulf of evaluation | | |
| INV-06 Spatial stability | | |
| INV-07 Text–action–result congruence | | |
| INV-08 Entry/exit symmetry | | |
| INV-09 Visual parity of options | | |
| INV-10 True urgency and scarcity | | |
| INV-11 No confirmshaming | | |
| INV-12 Microboundary / undo | | |
| INV-13 No reverse inference | | |
| INV-14 Neurodata with consent | | |

## Friction classification
| Friction point | Extraneous / Desirable / Dark | Justification | Action |
| :---- | :---- | :---- | :---- |

## Findings
### [F-01] Title — [Blocking / High / Medium / Low]
- Where:
- What I observe: [verifiable fact, no interpretation]
- Mechanism: [INV/PRO + the cognitive framework that explains it]
- Cost to the user: [steps, errors, memory, trust]
- Proposed change:
- How we verify it: [metric + threshold defined in advance]

## Plan
1. [Blocking items, in order]
2. [High]
3. [The rest]

## Risks and open questions
- [What can't be asserted with the material available]
- [What requires human legal review]
```

---

## B. Component design worksheet

```markdown
# Psych-UX design — [component]

## Purpose
- Task it solves:
- Catalog archetype: [see references/component-catalog.md]
- Who uses it and how often:

## Cognitive budget
| Parameter | Target | Actual |
| :---- | :---- | :---- |
| Elements held at once | ≤4 | |
| Decisions per screen | 1 | |
| Required fields | justified minimum | |
| Time to first feedback | ≤100 ms | |
| Steps to complete | | |
| Steps to undo | ≤ steps to do | |

## Friction decision
- Reversible action: [yes/no]
- Friction included: [none / undo / microboundary: which one]
- Justification: [protects the user / learning / none → removed]

## States
| State | What it shows | What the user can do |
| :---- | :---- | :---- |
| Initial | | |
| Empty | | |
| Loading | | |
| Success | | |
| Error | | |
| Partial / offline | | |
| Disabled | | [visible reason] |

## Copy
| Element | Text | Check |
| :---- | :---- | :---- |
| Primary action | | Same verb in the result |
| Secondary action | | Parity and neutrality |
| Main error | | Cause + way out |
| Empty state | | Teaches the first action |

## Applicable invariants
- [List of the ones this component must meet and how it meets them]

## Acceptance criteria
- [ ] ...

## Instrumentation
| Event | To answer |
| :---- | :---- |
```

---

## C. Ruling worksheet (a one-off decision about friction)

```markdown
# Decision — [what is being decided]

- Action affected:
- Irreversible or costly? [yes/no + why]
- Learning goal? [yes/no]
- Who does this friction protect? [user / business]
- **Decision:** [no friction / undo / microboundary: which one / remove the existing friction]
- Reason in one sentence:
- What we'd observe if the decision were wrong: [metric + threshold]
```
