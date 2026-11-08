# Cross-cutting techniques: T1 to T5

Applied with the P0 protocol (`../SKILL.md`). These are the ones that pay off most, and the two
best ones, T3 and T4, save **zero lines**. That is not a paradox: what this campaign optimizes is
what the agent has to discover, and lines are only a proxy for it.

The examples are illustrative: they come from one real codebase, told without its names, and
they are here because they explain why a rule exists.

---

## T1: One schema-first contract

**Detect:** every data shape that exists twice, once in the backend and once in the frontend. A
Java `record` and a hand-written TypeScript `interface` in an app describing the same payload.

**Replace with:** a versioned contract from which both sides are generated at build time, so they
cannot drift in silence.

**Measure the thing that actually hurts**, and put it in the analysis file: not how many
duplicated types disappear, but **how many tasks today force you to read both stacks to change one
field**. That number is the argument; the LOC saving is a side effect.

**Find out where the contract lives today.** It may be emitted by the backend framework, written
by hand, or, as in one codebase, assembled at request time from a catalog while the framework's
own OpenAPI endpoint is blocked because it also describes the private surface. The generation
direction (backend to frontend, contract to both, or frontend to backend) is a **decision for the
user, not for the agent**. It usually adds a build step and a code generator, which is a new
dependency (`../SKILL.md` § Hard rules).

**Blocker to write down:** whatever is chosen must not become a second source of truth next to an
existing one. **Derive, don't describe.**

---

## T2: Deleting dead code

**Detect:** code with no incoming references; feature flags already resolved, plus both of their
branches; endpoints with no traffic; components nobody imports; tests for code that was deleted;
unused dependencies. A dedicated tool (for example `knip` or `ts-prune` for TypeScript, or the
IDE's unused-declaration inspection for Java) beats a regex; if the project already has one
configured, use it.

**Replace with:** nothing. It gets deleted. This is reduction **by elimination**: it removes lines
and concepts at the same time, so it has no break-even point and always applies.

**Runs first**, before every other technique: migrating code that is about to die is the one way
to pay for a refactor twice.

**The gate that is not optional:** before deleting an **endpoint or a screen**, list the candidates
and get them confirmed **one by one**, not in bulk. A public API may have callers outside the
repository, and a published deprecation policy promises them notice, not a surprise.

**Use traffic when the project has it.** Access logs or analytics are evidence: an endpoint with
zero traffic across the retained window is a candidate. "I could not find a caller in the
repository" is not evidence for a public surface.

**Careful with:** `git log` is the archive. Code kept "just in case we need it again" is
contamination (`../SKILL.md` § Hard rules).

---

## T3: Predictable location

**Detect:** what makes finding things fail. Packages or folders with generic names (`common`,
`utils`, `core`, `misc`, `shared`), and one domain scattered across several packages. Those are
real findings, and they are also the input to J10.

**Replace with:** a location rule the agent can follow without searching, **derived from the code
rather than written by hand**. A hand-written map of the tree starts going stale the day it is
written.

- If the `topology` skill is installed, `reduction.py route` already gives a map derived from the
  build files and the real imports. Then T3 is closed as "write a tree file", and belongs in
  `decided`. What is left is the workflow rule below.
- If not, the deliverable is the list of generic-named packages and scattered domains, and a
  proposal for how the project could derive its map.

> If you have not located the spot within two hops, that is **not your failure: it is a bug in
> the routing**, and it gets fixed in the same batch. Either the concept gets its own type in the
> module that owns it, or the routing heuristic needs a tweak.

**Saving in LOC: zero.** It is the technique that most reduces the agent's searching, which is why
it runs in the first group.

---

## T4: Conventions enforced by tooling

**Detect:** conventions that today live only in someone's head or in prose.

**Replace with:** a check that fails: a linter rule, an architecture test, a hook, a verifier
script. Prose dilutes as context grows; a failing build does not.

**Two conditions, both non-negotiable, and both learned by breaking them:**

- **Only what is NOT a judgment call gets wired in.** A check enforcing a preference gets disabled
  by hand, and takes down whatever it was actually protecting with it. Debatable guidance stays in
  written rules, where the agent reading them is the judge.
- **Only what starts GREEN gets wired in.** A rule added while broken leaves a permanently red
  check, and a check that is always red stops being looked at. **Measure before writing the
  rule.** If it comes back red, what gets opened is a work item, not a guardrail.

**Deliverable, before implementing anything:** the list of proposed rules, each with the count of
current violations. A rule with violations does not become a check; it becomes a work item, and it
becomes a check the day that item closes. For example, one project had a purely mechanical
interface rule that stayed prose for a while, because as a hook it would have started red with
over a dozen violations.

**Where a new check goes:** an existing check or hook, not a new one, whenever one fits. If the
project uses agent hooks, keep their roles apart: preparation before the prompt, invariants
before a tool call, closing cycles after the work. **A hook without a test bench rots**: the first
false positive gets it disabled by hand. Add the new case to the hook's cases, and run its tests.

---

## T5: Domain modularization

**Detect:** classes that participate in more than one domain, and dependencies between domains
that do not go through a public edge.

**Replace with:** boundaries the build enforces. **Module boundaries beat package boundaries**: a
package boundary is a naming convention, while a module boundary (a Maven or Gradle module, a
workspace package) is a build failure. Architecture tests (ArchUnit or similar) cover what
modules cannot, such as "the domain is framework-free" or "no context reaches into another's
internals".

**Often mostly done already.** In one codebase every bounded context was already split into
domain / application / infrastructure modules, with a handful of architecture tests on top. T5
was then not a migration. It was the residue:

1. **Declared gaps**, for example a second deployable whose classes are not on the classpath of
   the architecture tests, so the tests never see it. Closing that is small, bounded work.
2. **Real couplings.** If architecture tests exist, any real coupling makes them red, so **check
   the tests before claiming there are any**.

**Do not move packages on your own initiative.** If the project has already declared its
deviations with their reasons, reopening them without an explicit request from the user reopens a
closed decision. If the analysis finds a genuine coupling, deliver the map and the couplings and
stop there.
