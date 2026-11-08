# rule-enforcer: Review Against the Project's Written Rules

When this modifier is active, a review is judged against the project's written rules, not only against the diff and its tests. Every role of the review phase runs with it. Green checks are evidence about the tests; they are not a verdict on the rules.

## Rules

1. **Build the rule set before reading the diff.** List the rules that apply to this change:
   - the project's invariants and its always-on rules;
   - every rule whose scope matches a file the change touches (its path patterns, or the "read it when" table of the project's rule index);
   - the card category's contract and the card's own acceptance criteria.

   Read each one in full. A rule you only remember is not a rule you checked.
2. **Walk every rule against the change, with evidence.** Evidence is a `file:line`, a command and its output, or a capture of the rendered screen. A rule you could not check is **not verified**, never **pass**, and you say why it could not be checked.
3. **A violated rule is a send-back.** Name the rule, and its quality-rule id where the board has one. It is never an approval with a note, and never "fix it in a later card" unless the rule itself allows that.
4. **What the change made stale counts.** A document, a rule text, a baseline or a contract that describes what this change altered, left unchanged, is a violation wherever the project requires docs to change with the code.
5. **Interface rules are judged on the screen.** When the change touches what a person sees, the rules about layout, states, units, motion, contrast and copy are checked on captures at a laptop and a phone viewport, not by reading class names.
6. **The verdict carries the checklist.** The review comment includes a table with one row per rule: the rule, its verdict (`pass`, `violated`, `not verified`, `not applicable`) and the evidence. No table, no approval.

## Behavioral Overrides

- A rule outranks the reviewer's taste and the author's explanation. Disagreeing with a rule is a card that proposes changing it, never an exception granted in review.
- A violation is not softened because the rest of the change is good.
- `not applicable` needs one line of why. A rule marked `not applicable` because it was inconvenient is a violation of this mod.
