# Measuring fidelity

A pack claims to **decide like the person**, not to give better answers. This page is how that
claim is earned, per person, and why the smoke test in `evals/` is not evidence for it.

## What the evidence says

- Agreement between a clone and a person means little until it is divided by the person's
  agreement with themselves: people are inconsistent (software professionals re-estimating the same
  tasks differed by 71% on average), and interview-based agents of 1,052 people were judged against
  each participant's own two-week test-retest accuracy.
- Even the best published "digital twins" capture relative differences between people better than one
  person's unique judgments; one mega-study found them no more accurate than demographics-only
  personas on many outcomes. The bar a pack must clear is therefore concrete and can fail.
- Word overlap correlates weakly with human judgment, style similarity is confounded by topic, and
  LLM judges show position, verbosity and self-preference biases. Vocabulary coverage is no evidence
  of person-specific judgment.

Sources: Park et al., "Generative Agent Simulations of 1,000 People" (arXiv:2411.10109); Toubia et
al., "Twin-2K-500" (arXiv:2505.17479); Peng et al., "A Mega-Study of Digital Twins" (arXiv:2509.19088);
Grimstad and Jørgensen, J. Systems and Software, 2007; Liu et al., "How NOT To Evaluate Your Dialogue
System" (EMNLP 2016); Zheng et al., "Judging LLM-as-a-Judge" (NeurIPS 2023); Miller, "Adding Error
Bars to Evals" (arXiv:2411.00640).

## The protocol

1. **Held-out decisions, before the interview.** 20–40 of the person's real past decisions, each with
   the situation, two or more options and what they chose, stored with
   `python3 scripts/fidelity.py add --pack-id <id> --situation "..." --option "..." --option "..." --choice <n>`
   in `.harness/fidelity/<pack-id>/heldout.json` (`../schemas/heldout.schema.json`). They live outside
   the pack, so nothing that loads the pack sees them; never show them to the synthesis.
2. **The ceiling, two weeks later.** `fidelity.py retest-sheet` prints a subset without the answers;
   the person redoes it blind, and `fidelity.py retest --answer H3=1 ...` records it. The share of
   items where they chose the same again is the ceiling.
3. **Identical inputs for every arm.** `fidelity.py prompts --pack <pack> --out <dir>` writes one
   prompt per item and arm:

   | Arm | Context |
   | --- | --- |
   | `base` | The situation alone. |
   | `persona` | "You are a senior <role>." |
   | `context` | The persona plus what the person said about their context (the form's first section). |
   | `raw` | The person's raw answers, verbatim, plus about ten of their real decisions. **No synthesis.** |
   | `pack` | The pack's `core.md` plus its five decisions closest to the item. |

   Run every prompt in the model the person will use, several samples each when you can, and save the
   replies as `<dir>/<arm>/<item>.txt` or `<item>.<n>.txt`. The first line of a reply is the chosen
   option's number.
4. **Score.** `fidelity.py score --pack-id <id> --responses <dir>` reports each arm's agreement, its
   fidelity (agreement ÷ ceiling), and each arm against the `raw` baseline with a paired bootstrap that
   resamples items, so several samples of one item never count as independent evidence.
5. **Read it honestly.** If `pack` does not beat `raw`, synthesis adds nothing measurable over the
   answers themselves: change the rendering (shorter core, more examples, different directives)
   before claiming anything. If no arm beats `persona`, the interview did not capture what matters for
   these decisions.
6. **Blind judgment by the person.** `fidelity.py pairwise-sheet --a <dir>/pack --b <dir>/raw` builds
   position-randomized pairs; the person picks the reply they would likelier have written;
   `fidelity.py pairwise-score` gives the preference rate with its interval. A "which one is real?"
   test with a colleague follows the same pattern. An LLM judge is only ever a secondary rater,
   calibrated against these human labels.
7. **Task quality apart.** Fidelity is not correctness. Items with a planted defect (a bug in a pull
   request, a claim without proof) carry a `defect` field and are left out of agreement; label whether
   each reply found it and pass the labels to `score --defects` for recall per arm. The smoke test's
   `seededDefects` do the same for its fixed tasks.

## What is published

Numbers from a real person's held-out set, with the ceiling, the number of items, and the intervals.
Never numbers from hand-written outputs, and never the smoke test's coverage as a quality claim.
