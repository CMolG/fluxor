# deterministic-tests: Deterministic, Lowest-Level Tests Modifier

When this modifier is active, every test the agent writes gives the same result on every run, sits at the lowest level that proves its behavior, and is never made to pass by waiting, retrying or skipping.

## Rules

1. **The lowest level that proves it.** A unit test where the cause lives, an integration test against a real boundary, an end-to-end test only for a journey nothing lower can prove. Going higher needs a written reason naming what only that level can see.
2. **Control time, randomness and order.** Each test owns its data, so tests pass in parallel and in any order.
3. **No fixed sleeps, retries, skips or raised timeouts.** Browser tests use role-based locators and web-first assertions, never a fixed wait.
4. **Flakiness is fixed at its cause.** Name the cause (async wait, order, shared state, time, network, resources) and fix it where it lives, or quarantine the test with a card that names the cause. Never re-run until green.
5. **Assert behavior, not implementation.** One behavior per test, named as the behavior it proves, so a refactor does not break it.
6. **Choose cases deliberately.** Pick equivalence partitions and boundary values when the plan leaves cases open. A property-based failure keeps its seed and shrunk counterexample as a fixed case.
7. **A testing card changes no production code.** A defect the tests find becomes its own card, and the test is not bent to pass.

## Behavioral Overrides

- Before finishing, the agent runs the new tests more than once, in a different order where the runner allows, and reports the results.
- A test that cannot be made deterministic is reported with its cause instead of being merged.
- Pre-existing flaky tests are reported, not fixed, unless the change already touches them.
