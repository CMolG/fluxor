# ds-house: In-House Design System Modifier

When this modifier is active, all UI is pinned to the project's OWN design system: a shared UI
package the project maintains, built on some substrate (shadcn/Radix, Tailwind, a headless
library, plain CSS). The substrate is what the house system is BUILT ON; the design language is
the project's. A piece that could belong to any product built on the same substrate does not
belong to this one.

> **Exclusive group: `design-system`.** Only one design-system mod may be active at a time. Inside
> a project that has a house system, enable this one instead of `ds-shadcn` / `ds-tailwind`: those
> describe its substrate, not its identity, and their rules (the substrate's CLI, its default
> file layout, its stock tokens) would pull the work back toward the template look.

## Where the project declares its system

If the harness has `.harness/config/ds-house.json` (the per-skill config seam of the harness
convention), read it first. Every key is optional:

- `uiPackage`: the shared UI package or directory primitives come from (e.g. `@acme/ui`).
- `brandColorSource`: the one function, token or file brand color is read from.
- `tokenPrefix`: the prefix of the house's CSS custom properties / design tokens (e.g. `--acme-`).
- `contracts`: a list of paths (relative to the project root), or URIs the harness can resolve
  (a `doc://` page read through the project's docs tool), to the documents that define the system,
  typically the art-direction contract, the token reference and the admission test. When two of
  them state the same visual value differently, the one that declares precedence wins; with none
  declared, the agent reports the conflict instead of choosing.

A `$`-prefixed key (for example `"$comment"`) is a comment. A complete example (illustrative
names; the schema is `ds-house.config.schema.json` next to this file):

```json
{
  "$comment": "The in-house design system, for the ds-house mod. Illustrative names.",
  "uiPackage": "@acme/ui",
  "brandColorSource": "packages/ui/src/theme/brand.ts",
  "tokenPrefix": "--acme-",
  "contracts": [
    ".harness/contracts/art-direction.md",
    ".harness/contracts/design-tokens.md",
    ".harness/contracts/admission-test.md"
  ]
}
```

With no config, discover the same facts from the code: the workspace package every app imports
its button/card/dialog from, the token file those primitives read, and any design-system or
art-direction document in the harness (`contracts/`, `rules/`) or the package's own README. If
the project has no shared UI package at all, this mod does not apply: say so and fall back to
the substrate's mod.

## Rules

1. **Primitives come from the house UI package, never re-implemented locally.** A button, card,
   input, badge or dialog rewritten inside an app is how a design system dies: each copy drifts,
   and dozens of near-identical versions are the usual end state. Reach for the import first.
2. **Brand color has ONE source.** Read it from the declared source (a function, a token, a
   theme file). No brand hex in tokens, catalog entries or components; no parallel palettes.
3. **Semantic and ink tokens over hand-written alphas.** Muted/faint/subtle text and border
   tokens are precomputed to pass contrast (WCAG AA) on their surface. Writing an alpha by hand
   silently skips that calculation; use the token, or add one to the system.
4. **The house visual signature beats the substrate's template look.** Apply the traits the
   project declares in its art-direction / design-system contract (delimiters, radius policy,
   type roles for metadata and values, accent marks, fill density). When no contract exists,
   follow what the house primitives already do rather than the substrate's defaults. Form should
   say something about the data when it can.
5. **New visible pieces pass the project's admission test**, if it has one (the checklist in its
   art-direction contract, a showcase or preview route where every piece must be mounted).
   No test declared: the piece must at least use house tokens only and appear alongside its
   siblings in whatever catalog the package keeps.
6. **Consuming the system is not reskinning.** Tokens and primitives are infrastructure: adopt
   them first, with behavior unchanged. Any visual "flavor" for a specific surface comes after
   adoption is complete, never before and never as a substitute for it.

## Behavioral Overrides

- If a needed piece does not exist in the house UI package, the agent proposes adding it THERE,
  with a real consumer in the same change, never a local copy.
- The agent does not run the substrate's generators (e.g. a component CLI) into an app; if the
  substrate provides the primitive, it gets wrapped once, inside the house package.
- Stacks cleanly with `cognitive-ux`, `error-ux` and `a11y-enforcer` at its AA floor: those govern
  what is shown and how it behaves; this mod governs where the pieces come from and what they look
  like. If the project declares AAA, the ink tokens are recomputed for it in the house system first;
  until then the agent reports the conflict instead of hand-writing alphas.
