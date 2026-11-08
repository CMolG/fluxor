# Java techniques: J1 to J10

Applied with the P0 protocol (`../SKILL.md`). Scope: the roots in `sources.java`
(`reduction.py config`). If the project has a pattern catalog, every one of these instantiates an
existing pattern; **none of them introduces a new one**.

Any figure you write down comes from a command you ran in phase 1. `reduction.py surface` gives a
regex count, which is a starting point, not a compiler-exact result. When the two differ, **say
which method you used**. The examples below are illustrative: they are what these techniques
turned up in one real codebase, told without its names, and they are here because they explain
why a rule exists.

---

## J1: Records and sealed interfaces in the model

**Detect:** classes whose body is only private fields with getters/setters, `equals`, `hashCode`,
`toString` or builders; and closed hierarchies of subtypes.

**Replace with:** `record` for DTOs, value objects, commands and events; a `sealed interface` plus
records for closed hierarchies, consumed with pattern-matching `switch`. Needs Java 16+ for
records and 17+ for sealed types: check the project's language level first.

**Do not touch:** JPA entities, or classes that genuinely need mutability.

**Check what is already the default.** In a codebase where records are already the house style,
the real surface is the residue, not the whole model. Two things to look for:

- **Lombok.** If the project treats it as legacy (not extended, not migrated in bulk), J1 does
  not sweep it. It converts a Lombok class only when a batch is already touching that file for
  another reason.
- **The valuable half is modeling so illegal state cannot be represented.** Validating in the
  compact constructor is the one move that removes lines *and* raises quality, because it deletes
  the defensive branch from every caller. That overlaps J5: read them together.

---

## J2: Single-implementation interfaces

**Detect:** every interface with exactly one `implements` in the codebase. A regex cannot tell
you "exactly one" reliably across generics and nested types; count with the compiler, an IDE
inspection, or a per-interface search, and state the method.

**Replace with:** the concrete class, deleting the interface and giving the implementation the
clean name (no `Impl` suffix).

**What it must never touch:** a **domain port** (in a hexagonal or ports-and-adapters design, the
port is single-implementation *by design*: it keeps the domain free of the framework, and
architecture tests usually rest on it), anything the framework proxies, and anything a test
double depends on.

**Read the names before counting the yield.** In one codebase the raw count was over a hundred,
almost all of them under the ports folder. Of the dozen or so left elsewhere, nearly every one
was a port or an SPI that simply did not sit in a folder literally named `ports`. **The expected
yield was very small, and that was the finding.** Do not force it: deleting a port because it has
one adapter today is how dependency injection wiring and the architecture boundary both break at
once. Before proposing any single removal, verify that transactions and interceptors still work
on the concrete class.

---

## J3: Generic persistence, service and resource

**Detect:** repositories, services or REST resources that repeat the same CRUD shape per entity.

**Replace with:** a parameterized base type or a framework's derived-query repository.

**Check the prerequisites before measuring anything.** The technique needs derived-by-name
queries, which means an ORM layer (Panache, Hibernate ORM, Spring Data or similar). If the
project forbids ORMs (for example, persistence is plain JDBC over `DataSource` by decision), J3 is
`DISCARD` before the analysis, and it belongs in the config's `decided`.

A parameterized base type is also a new pattern. If the project's pattern catalog is closed, or
only admits a shape the codebase already repeats, this cannot come in through J3.

**If the repetition genuinely hurts** without an ORM, that is a different proposal with a
different name, for example a small shared row-mapping helper. Argue it on its own merits against
the break-even arithmetic in `../SKILL.md` § Hard rules, and take it to the user as a decision,
not through J3's back door.

---

## J4: Central exception mapping

**Detect:** `try/catch` blocks that only log and rewrap, or that hand-build the HTTP error
response, repeated per endpoint; and the error mappers themselves (JAX-RS `ExceptionMapper`,
Spring `@ControllerAdvice` / `@ExceptionHandler`).

**Replace with:** one place per ownership boundary that turns exceptions into responses.

**Measure where the repetition really is.** In one codebase it was not in the endpoints (only a
handful of catch blocks hand-built a response, and none was pure log-and-rethrow). It was in
about twenty per-context mappers, each re-deciding the JSON body of an error. **Centralizing
those into one mapper would have been the wrong move**: a single mapper must know every context's
exception types, and per-context mappers keep a context's errors owned by that context. The
smaller, safer version was a shared error-shape helper used by every mapper, plus folding the
few hand-built responses into their context's existing mapper.

**Do not touch:** catches that implement real recovery logic.

**Hand off, do not fix here:** catch blocks that only log, with no rethrow and no response, are
errors swallowed silently. That is a correctness problem, not reduction. It gets a work item of
its own and does not get bundled into a refactor that promises zero behavior change.

---

## J5: Declarative validation

Often the largest Java opportunity.

**Detect:** blocks of `if`s at the top of methods checking nulls, ranges, formats or emptiness and
throwing. A first measure:
`reduction.py surface 'throw new (IllegalArgumentException|IllegalStateException|NullPointerException)' --lang java`,
against the count of Bean Validation constraints
(`reduction.py surface '@(NotNull|NotBlank|NotEmpty|Size|Min|Max|Positive|Pattern|Email|Valid)\b' --lang java`).

**Apply this ladder, in this order.** This is the part a generic version of the technique gets
wrong:

1. **Can the type stop holding the illegal value?** A `record` that validates in its compact
   constructor erases the guard from *every* caller, not just this one. It is the only step that
   reduces lines and raises quality at once. Before writing a validation by hand, check whether
   the type already prevents it.
2. **Otherwise, Bean Validation at the edge**: annotations on the input type. A constraint that
   repeats becomes one well-named custom annotation.
3. **A hand-written guard is what is left over**, not the default.

**Check before estimating:** which modules already declare the validation dependency
(`hibernate-validator`, `quarkus-hibernate-validator`, `spring-boot-starter-validation`). In one
codebase exactly one module had it, so every other module needed the dependency added. If the
technology is already approved in the project, that is not the "stop and ask" path, but it is a
real per-module cost that belongs in the migration-cost line.

**Do not touch:** business rules that query state. Those are not validation, and moving them to
an annotation hides them.

---

## J6: Strategy registry

**Detect:** `if/else` chains or `switch` over an enum or type string, **repeating the same
branches in more than one place**.

**Replace with:** a handler interface, one implementation per branch, and a map injected by the
container.

**Limit: three or more branches AND more than one decision point.** Below that, the registry
costs more than it saves (`../SKILL.md` § Hard rules).

**Measure both answers.** In one codebase exactly one case qualified: the same switch over an
artifact kind, duplicated between a domain class and an infrastructure class. With a single
duplication, a full registry may still lose; a method owned by the `enum` or `sealed` type that
both call is often cheaper. Put both in the analysis and say which one wins, instead of reaching
for the pattern because the technique is named after it.

---

## J7: Mapping layer

**Detect:** `toDto` / `toEntity` / `from` methods written field by field, usually in `*Mapper`
classes in the adapters.

**What is allowed:** exposing the domain type at the edge when the DTO is a **1:1 copy** of it.
That deletes the mapper outright, which is reduction by elimination.

**Check the project's decision on generated mapping** (MapStruct or similar) before proposing it.
A new dependency for a dozen mappers often does not pay for itself, and some projects forbid it
explicitly; in that case J7 is `PARTIAL` by decision and belongs in `decided`.

**Never, under any circumstance:** runtime reflection-based mapping (see the reflection rule in
`../SKILL.md` § Hard rules).

**Careful with:** "1:1 today" is not "1:1 forever". Exposing a domain type at an HTTP boundary
couples the public contract to the domain shape. If the API publishes a deprecation policy, the
mapper may be the seam that lets the domain change without breaking callers. **Then it is earning
its lines**: say so and leave it.

---

## J8: Cross-cutting concerns via interceptors

**Runs last, and only if the analysis clears it.**

**Detect:** entry/exit logging, timing, auditing and transaction handling written by hand inside
business methods.

**Replace with:** an interceptor bound to an annotation with a semantic name that says what it
does, not how.

**The warning is the whole point of the technique:** this **hides behavior**. If phase 1 shows
context per unit going up (you now have to open the interceptor to know what a method does), mark
it `PARTIAL` and confine it to auditing and tracing, the two cases where the behavior being
invisible is exactly what you want.

Relevant to the estimate: if the project already keeps scheduled jobs and endpoints thin (their
whole body delegates to a service), the surface is smaller than in a codebase that does not.

---

## J9: Parametrized tests and a test data factory

**Detect:** copied tests that differ only in input and expected values; the same test object
built over and over. Measure with `--tests`:
`reduction.py surface '@Test\b' --lang java --tests` against `'@ParameterizedTest\b'`, then look
for clusters of near-identical methods in the top files.

**Replace with:** one `@ParameterizedTest` per data source, and a single test-data factory with
defaults and overrides.

**The rule:** parametrize when the cases differ **only in data**; keep them separate when they
differ in the arrange. If the project's testing guideline already says this, J9 applies it, it
does not re-decide it.

**Check the depth of the clusters, not just the ratio.** In one codebase the ratio of plain to
parametrized tests looked dramatic, but the worst copy-paste cluster was four methods. Merging
four methods into one saves single-digit lines, so the honest verdict was low yield; the value,
if any, was uniformity rather than volume.

**The guard:** merging tests is exactly where a weakened suite hides. If the project has mutation
testing, run it. If not, the merged test must fail when you revert the code under test: **prove
it once, by reverting**, and say in the report that this is what was done instead of a mutation
score.

---

## J10: Home-grown utilities vs the framework's library

**Detect:** `Utils` / `Util` / `Helper` / `Common` classes, and hand-written date, string,
collection, retry, cache or JSON functions.
`reduction.py surface '\bclass \w+(Utils?|Helpers?|Common)\b' --lang java --tests` is a first
pass.

**Zero is a real result.** If the scan finds nothing, write it down as `DISCARD` with "no
surface", so nobody spends another batch looking. What remains in scope is hand-rolled
retry/cache/date logic living under a *domain* name rather than a utility one; chasing that is a
targeted search, not a sweep.

**If something is found:** replace it with the framework's equivalent or a library **already
present** in the build. A new dependency is a decision for the user (`../SKILL.md` § Hard rules).
If the project has a hook or check that blocks adding dependencies by hand, it applies here too.
