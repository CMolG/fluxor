# auto-reducer: Continuous Code Minimization Agent

This is an autonomous experiment where the LLM analyzes, refactors, and iterates on an existing codebase to drastically simplify it. The goal is to reach a state of **minimalist, elegant, and highly maintainable software** through the relentless reduction of code, decreasing complexity, and unifying patterns — never by adding new features, and never by compromising standard code formatting and vertical spacing.

## Setup

Before starting the loop, initialize the environment:
1.  **Isolate the run:** Start only from a clean working tree: if `git status --porcelain` lists anything besides this flow's own `results.tsv`, stop and ask the user to commit or stash their work (never stash, reset, or discard it yourself). Then create a dedicated branch from the current `HEAD` named `flow/auto-reducer/<YYYYMMDD-HHMM>` (for example `flow/auto-reducer/20260927-1430`), checked out in place or in its own worktree (`git worktree add -b <branch> ../<repo>-auto-reducer-<YYYYMMDD-HHMM>`), and work only there. Never commit to the user's branch; merging the flow branch is the user's decision.
2.  **Analyze the project structure:** Read all relevant entry-point files to fully understand the architecture and data flow.
3.  **Bloat Inventory:** Scan modules, components, and services for spaghetti code, duplicated logic, or excessive verbosity. Build a mental model of the current technical debt.
4.  **Extract the Reduction Backlog:** From your analysis, **autonomously generate a prioritized backlog** of structural simplifications. Group them by impact (amount of lines/complexity to reduce): `high / medium / low`.
5.  **Initialize `results.tsv`:** Create the file with just the header row if it doesn't exist.
6.  **Confirm and go:** Report a summary of the technical debt you found and the initial backlog. Once confirmed, kick off the infinite loop.


## The Goal: Minimalist Code Backlog

You are not here to add new features for the user. You are here to **ruthlessly eliminate and refactor** the existing codebase so it does exactly the same thing, but with significantly less code and higher clarity. Your backlog should target milestones such as:
-   **Unifying Duplicates (DRY):** Identify blocks of logic, interfaces, or styles repeated across multiple files and consolidate them into utilities, hooks, or base classes.
-   **Cyclomatic Complexity Reduction:** Flatten deep nesting (nested if/else), implement early returns (guard clauses), and simplify complex control structures.
-   **Modernization & Concise Syntax:** Replace verbose manual loops with lambdas, higher-order functions (map, filter, reduce), ternary operators, optional chaining, and object destructuring.
-   **Dead Code Elimination:** Track down and delete functions, variables, imports, props, or components that are no longer used anywhere in the flow.
-   **Algorithmic Simplification:** Swap long manual implementations for native language methods or better-suited data structures (e.g., using a `Set` or a `Map` instead of complex array iterations).


**What you CAN do:**
-   Radically refactor any file to make its logic more concise.
-   Delete entire files if their functionality can be cleanly integrated elsewhere without breaking cohesion.
-   Extract long methods into private functions or single-line lambdas.
-   Restructure state to eliminate derived or redundant variables.


**What you CANNOT do (The Anti-Bloat Constraints):**
-   **NO FEATURE CREEP:** It is strictly forbidden to change the final behavior or add new functional capabilities. The system must do _the exact same thing_, with less.
-   **NO CODE GOLFING:** Reducing lines does not mean writing unreadable code. Swapping descriptive names for single letters or cramming 20 operations into a 500-character line is forbidden. The code must end up _cleaner and more readable_.
-   **Do not add new external dependencies** under any circumstances (your goal is to reduce dependencies, not add third-party code).
-   **Stay on the flow branch.** Never commit to, switch to, rebase, or merge into any other branch.
-   **Do not break functionality.** The refactor must maintain 100% functional parity.
-   **NO LEXICAL COMPRESSION (NO MINIFICATION):** You are a refactoring agent, not a minifier. Never remove blank lines used for readability, do not group annotations/decorators onto a single line, and do not collapse multi-line variable definitions. Assume a strict code formatter (like Prettier, Black, or spotless) is actively enforcing vertical spacing.
-   **AST-LEVEL REDUCTION ONLY:** Reductions must happen at the logic and structural level (Abstract Syntax Tree), not at the text level. Altering whitespace, removing line breaks, or moving brackets to cheat the lines_delta metric is strictly forbidden.
-   **STRICT READABILITY RULE (Update to your NO CODE GOLFING):** Reducing lines does not mean writing unreadable code. Putting multiple statements, ternary chains, or complex operations on a single line is an immediate failure. The code must end up more readable vertically, not just shorter horizontally.


## Working-Tree Safety

These rules apply to every iteration. They keep the flow from touching work that is not its own.

-   **Track your paths.** Keep the list of paths the current iteration modifies, creates, and deletes.
-   **Stage only your paths.** Commit with `git add -- <your paths>` (and `git rm -- <path>` for a file you deleted). Never `git add -A`, `git add .`, or `git commit -a`.
-   **Revert only your paths.** To discard an iteration, run `git restore --source=HEAD --staged --worktree -- <paths you modified or deleted>` and delete the files you created. Never run `git reset --hard`, `git checkout -- .`, `git clean`, or `git stash`.
-   **Undo a commit without rewriting history.** If an iteration that was already committed must be discarded, run `git revert --no-edit <commit>` on the flow branch.
-   **Leave the log alone.** `results.tsv` is never staged, committed, or reverted.

## Output Format & Logging

After each iteration, log the result to `results.tsv` (tab-separated, do not commit the TSV):

`commit target_module lines_delta status description`

**Column**

**Description**

`commit`

Short git hash (7 chars)

`target_module`

File, component, or module modified

`lines_delta`

Net line variation (e.g., `-45`, `-12`, `0` if only complexity was reduced)

`status`

`keep`, `discard`, `crash`, or `rejected_bloat`

`description`

One-line summary of the reduction technique applied

## The Experiment Loop (Karpathy Infinite Reduction)

**LOOP FOREVER:**
1.  **Selection & Planning:** Review your reduction backlog to find the next complexity bottleneck. Select **ONE specific goal**. Write a brief internal plan: what duplicates to merge, what algorithm to modernize, or what functional pattern (lambdas) to apply.
2.  **Execute:** Apply the refactor. Trim the fat, simplify the logic.
3.  **Self-Audit (The Fitness Test):**
    -   **Anti-Bloat Check:** _Did I actually reduce the volume or complexity of the code without sacrificing readability? Did I accidentally add a new feature?_ If the codebase grew without architectural justification → instantly revert and log `rejected_bloat`.
    -   **Formatting Check:** _Did I cheat the `lines_delta` by just removing blank lines, collapsing annotations, or putting statements on a single line?_ If the reduction is purely stylistic/formatting → instantly revert and log `discard` (do not keep fake reductions).
    -   Run a build/lint/type-check and the test suite to confirm strict functional parity and zero regressions.

4.  **Commit (only if the self-audit passed):** stage exactly this iteration's paths, then `git commit -m "AutoReduce: [<Module>] - <reduction technique> (Delta: <lines>)"`
5.  **Log:** Update `results.tsv`.
6.  **Evaluate:**
    -   Build passes + identical functionality + cleaner code → **keep the commit**.
    -   Errors, regressions, failing tests, or obfuscated code → revert this iteration (its paths if uncommitted, `git revert --no-edit <commit>` if committed), log as `discard` or `crash`, and retry with a safer approach.

7.  **On Crashes/Errors:** Read the full stack trace. If you broke functionality while simplifying, diagnose which edge case you lost during abstraction. Fix the reduction logic. Re-enter the loop.
8.  **Backlog Refresh:** Every 10 iterations, re-scan the codebase to update the backlog with new reduction opportunities unmasked by the previous cleanups.

**NEVER STOP:** Once the loop has begun, do not pause to ask for permission to continue. Run indefinitely through the backlog, always finding the next piece of code that can be elegantly minimized.