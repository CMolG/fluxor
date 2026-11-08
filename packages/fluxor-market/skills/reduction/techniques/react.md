# React techniques: R1 to R6

Applied with the P0 protocol (`../SKILL.md`). Scope: the roots in `sources.react`
(`reduction.py config`). "The shared UI package" below means the package named by the config's
`uiPackage` key; if there is none, R3 and R4 *propose* creating one instead of using it.

The examples are illustrative: they come from one real workspace, told without its names, and
they are here because they explain why a rule exists.

## Read this before analyzing any of them

**Several of these techniques need a dependency the workspace may not have**: a form library for
R2, a table library for R5, a query library for R6, a contract code generator for R1. Check the
workspace's `package.json` files and lockfile first, and write down what is and is not there.

Adding one is not something the agent does on its own initiative. A new dependency is the last
option, it can land in many projects and the root lockfile at once, and it is a decision for the
user: **stop and present two or three options with their trade-offs**, then record the choice
where the project records technology decisions (a harness keeps them in
`PREFERRED_TECHNOLOGIES.csv`). If the project has a hook that blocks adding a dependency to a
`package.json` by hand, it applies here too.

So when the dependency is missing, the honest phase-1 deliverable for R1, R2, R5 and R6 is:
**the measured surface, the saving it would buy, and the dependency question**, not an
application plan. R3 and R4 need nothing new when a shared UI package exists.

Look for what already exists before proposing anything, because it changes the shape of the
work:

- **A shared SDK or types package** that already holds hand-written interfaces for backend
  payloads and is already consumed by the apps. R1 grows that package; it does not create one.
- **A schema library already in the tree** (for example `zod`, used for API request and response
  schemas). For R2 that is the difference between "add two dependencies" and "add one, or none".

---

## R1: Generated API client and types

**Detect:** hand-written TypeScript interfaces that replicate backend shapes, and repeated
`fetch`/`axios` wrappers per endpoint.

**Replace with:** types and a client generated at build time from the backend contract, consumed
by every app from a shared package.

**Find where the contract really comes from.** Generating from a contract needs a contract that
exists at build time. In one workspace the public OpenAPI document was assembled *at request
time* from a live catalog, and the framework's own OpenAPI endpoint was deliberately blocked
because it also described the private surface. So "generate from the contract" first needed a
build-time source. That is a design question, and it belongs to T1: do not answer it inside R1.

**Report** how many duplicated types disappear **and** how many past changes required touching the
backend and the frontend by hand for one field (`git log` on the duplicated type files tells you).
The second number is what justifies the dependency.

---

## R2: Schema-driven forms

**Detect:** forms with `useState` per field, hand-written validation, manual `errors`/`touched`
bookkeeping. A first measure: `reduction.py surface 'useState\(' --lang react`, then narrow to
files that also have `onChange` and a `<form` or submit handler.

**Replace with:** one validation schema per form plus shared field components.

**State the dependency question precisely.** The options to put in front of the user are usually:
reuse a schema library the tree already has with native form submission and no new dependency, or
a schema library plus a form library. Measure both before asking. The answer depends on how many
of the matches are genuinely multi-field forms and how many are a single controlled input, and
that is a count, not an opinion.

**Careful with:** forms on a conversion surface (sign-up, checkout, a landing page). If the
project has rules for interface states (mandatory loading/error/empty states, errors that say how
to get out, disabled controls with the reason visible), any change goes through them. This is a
refactor, so **the visible behavior must not change**.

---

## R3: Shared design system across apps

**Detect:** components with the same purpose duplicated across apps. **Compare by structure, not
by name**: a name match is the easy half and the smaller half.

**Replace with:** a single version in the shared UI package (config: `uiPackage`), with the
differences expressed as props.

**Check whether this is already a rule.** Some projects make the shared UI package mandatory and
block new primitives outside it with a hook. Then R3 is not a proposal: it is finding the
remaining copies. Why it matters, from one workspace: before the package became mandatory it had
accumulated dozens of reimplementations of button, card, input, badge and dialog, three radius
scales, and three contradicting sources of brand color.

**State the counting method.** In that same workspace, two careful counts of the remaining
primitives outside the package disagreed by one, depending on whether an inline local `Card`
inside a larger component counted. A percentage computed from an undefined denominator is
theater.

**Deliverable before moving anything:** the table of duplicated components and how many copies of
each exist.

---

## R4: Variants instead of cloned components

**Detect:** `ButtonPrimary` / `ButtonSecondary` / `ButtonDanger` and their equivalents; style
classes copied between sibling components.

**Replace with:** one component with declared variants, built on the design tokens.

**Limit:** more than five variants usually means it is two components, not one. Say so in the
analysis instead of adding the sixth.

**Respect the floor the design system already sets**: its tokens, its mandatory states, and any
admission test it has for new pieces. **Contrast comes from a token, never from an alpha value
written by hand**: tokens can be chosen once to pass WCAG AA, and every hand-written alpha is a
place where contrast can silently fail.

---

## R5: Declarative tables

**Detect:** hand-written `<thead>`/`<tbody>`, with sorting, filtering and pagination reimplemented
per screen (`reduction.py surface '<thead' --lang react`).

**Replace with:** one table component that takes its columns as data.

**Do the arithmetic before proposing a library.** If there is no table library in the tree, this
technique means adding one for the number of call sites you measured. In one workspace that was
about a dozen, several of them static presentation tables with no sorting or pagination at all.
Count how many actually need sort, filter or paginate. If it is a handful, the answer is a shared
component in the shared UI package, with **no new dependency**.

---

## R6: One data-fetching layer

**Detect:** `useEffect` with `fetch` inside, and `loading`/`error`/`data` state declared by hand in
each component.

**Replace with:** one query layer with conventional cache keys, and loading/error states resolved
by shared components.

**A declared but unused dependency is not a precedent.** In one workspace a fetching library was
declared in an app's `package.json` with zero imports in its source. That is an unused dependency
(T2 territory), not evidence that the library was chosen. Either it gets removed or it gets
adopted deliberately, and both are decisions for the user.

**Careful with the session.** If login is shared across apps and must survive navigation between
them, a fetching refactor that re-authenticates, or that loses the session between apps, has
broken that guarantee no matter how many lines it removed. Check the project's invariants for it
before touching auth-bearing requests.
