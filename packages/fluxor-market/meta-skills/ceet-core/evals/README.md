# Smoke test

A deterministic regression check for the CEET packs. It has no model dependency and never calls a
model: whoever runs it pastes each arm's reply into a results folder, and the scripts score the
text. It lives in `ceet-core` and is not installed with the skill (`install.exclude`); paths below
are relative to the `ceet-core` folder, and its tests are in `../tests/`.

**What it is not.** Phrase and section coverage measure whether an output uses a task's vocabulary
and structure, not whether it decides the way the person would: the required phrases of these tasks
are the vocabulary a pack cultivates, so coverage is circular as evidence of fidelity. Fidelity is
measured per person, against held-out decisions and the person's own consistency, with
`scripts/fidelity.py` ([`references/fidelity.md`](../references/fidelity.md)). No number from
hand-written outputs is published; the old seed run is now only a test fixture.

## Layout

```
evals/
├── README.md                  # this file
├── tasks/<task>/              # prompt.md, criteria.json, voice-corpus.txt
│   ├── engineering-pr-review/ # ceet-backend-engineer
│   ├── product-prd-draft/     # ceet-product-manager
│   └── copy-headlines/        # ceet-copywriter
└── scripts/
    ├── scoring.py             # structure, whole-word phrases, planted defects, forbidden phrases, voice
    └── run.py                 # runner; writes report.{json,md} next to the outputs
```

## Arms

| Arm | The model gets |
| --- | --- |
| `baseline` | The prompt alone. |
| `generic` | The prompt and "You are a senior <role>." |
| `raw` | The prompt, the person's raw answers and about ten of their real decisions. No synthesis. |
| `ceet` | The prompt and the rendered pack (`core.md` plus the matching artifact and examples). |

## How to run

1. Pick a results folder **outside the repository** and a run id.
2. For each task and arm, save the model's reply as `<results>/<run-id>/<task>/<arm>.md`.
3. Score:

   ```bash
   python3 evals/scripts/run.py --run-id <run-id> --results-dir <results>
   python3 evals/scripts/run.py --run-id <run-id> --results-dir <results> --check   # exit 1 on a regression of the ceet arm
   ```

`--check` fails when the `ceet` arm's output is out of the task's length bounds, misses a required
section, or uses a forbidden phrase. Planted-defect recall is reported, not gated: detection by phrase
is too crude to fail on; read the misses by hand.

## Metrics

- `wordCount`, `lengthWithinBounds` — against `minWords` / `maxWords`.
- `sectionCoverage` — `requiredSections` found in the Markdown headings.
- `phraseCoverage` — `requiredPhrases` found as **whole words** (`lock` does not match `block`; a space
  also matches a hyphen).
- `defectRecall` — the share of `seededDefects` (known flaws planted in the task) whose `detect`
  phrases appear: task quality, separate from any fidelity claim.
- `forbiddenHits` — `forbiddenPhrases` the output used.
- `voiceAlignment` — term-frequency cosine against the task's `voice-corpus.txt`. Vocabulary overlap,
  confounded by topic: a diagnostic only.
