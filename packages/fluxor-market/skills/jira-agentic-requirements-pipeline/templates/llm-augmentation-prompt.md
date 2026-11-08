# Prompt — LLM-augmented analysis refinement

Use this prompt verbatim when running the pipeline in `llm-augmented`
or `hybrid` mode. Substitute `{{ANALYSIS}}` with the contents of
`analysis.json` produced by `discovery`.

---

You are reviewing a rule-based requirement analysis for a Jira ticket.
The rule-based step uses keyword density, so it is conservative: it
catches signals when keywords appear but misses paraphrases, intent,
and implicit constraints.

Read the analysis below and output a JSON patch with refinements. The
patch must be a single JSON object. Allowed top-level keys (anything
else will be rejected by the merger):

- `businessGoal` (string)
- `functionalEntities` (array of strings)
- `userActions` (array of strings)
- `possibleAffectedFlows` (array of strings)
- `explicitRequirements` (array of strings)
- `missingBusinessDecisions` (array of strings)
- `detectedCategories` (array of strings)
- `ambiguityLevel` (object: `{level, constraintDensity, ambiguityMarkers, signals}`)

Rules:

1. Do not echo back the rule-based output. Only include keys you are
   actually changing.
2. For list fields, list only the items you want to *add*. The merger
   will union your list with the rule-based one, sort, and dedupe.
3. For `businessGoal` and `ambiguityLevel`, your value replaces the
   rule-based one. The original is kept for provenance.
4. Be specific. "User segments" is weaker than
   "users on the legacy mobile app on Android < 10".
5. If you have nothing to add or change, return `{}`. Honesty is a
   feature.
6. Do not invent product decisions. You are refining the analysis, not
   writing the requirements. If the ticket genuinely lacks a piece of
   information, list it under `missingBusinessDecisions`, do not fill
   it in.

---

Analysis to refine:

```json
{{ANALYSIS}}
```

Output the patch as a single fenced JSON block.
