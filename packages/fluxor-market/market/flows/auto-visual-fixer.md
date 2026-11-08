# auto-visual-fixer: Continuous Accessibility & UI Refinement Agent

This is an autonomous experiment where the LLM analyzes, refactors, and iterates on existing UI components and stylesheets to drastically improve accessibility and visual ergonomics. The goal is to reach a state of **flawless accessibility, readable typography, and perfectly sized interactions** based on Google Play and Material Design standards — never by changing the underlying functionality or destroying the core brand identity.

## Setup

Before starting the loop, initialize the environment:
1.  **Isolate the run:** Start only from a clean working tree: if `git status --porcelain` lists anything besides this flow's own `a11y_results.tsv`, stop and ask the user to commit or stash their work (never stash, reset, or discard it yourself). Then create a dedicated branch from the current `HEAD` named `flow/auto-visual-fixer/<YYYYMMDD-HHMM>` (for example `flow/auto-visual-fixer/20260927-1430`), checked out in place or in its own worktree (`git worktree add -b <branch> ../<repo>-auto-visual-fixer-<YYYYMMDD-HHMM>`), and work only there. Never commit to the user's branch; merging the flow branch is the user's decision.
2.  **Analyze the UI architecture:** Read all relevant component files (React, Vue, HTML, etc.) and stylesheets (CSS, Tailwind, SCSS) to fully understand the design system and styling approach.
3.  **Visual & A11y Inventory:** Scan for low-contrast text, undersized touch targets, illegible font sizes, and missing interaction states. Build a mental model of the current visual technical debt.
4.  **Extract the Fix Backlog:** From your analysis, **autonomously generate a prioritized backlog** of UI/UX corrections. Group them by standard violation: `contrast / touch-target / legibility / interaction`.
5.  **Initialize `a11y_results.tsv`:** Create the file with just the header row if it doesn't exist.
6.  **Confirm and go:** Report a summary of the visual debt you found and the initial backlog. Once confirmed, kick off the infinite loop.

## The Goal: Flawless Visual Ergonomics

You are not here to redesign the app or change its layout structure. You are here to **ruthlessly audit and adjust** styling properties so the interface meets strict accessibility standards. Your backlog should target milestones such as:
-   **Contrast Ratio Compliance (WCAG 2.1):** Ensure all normal text has a minimum contrast ratio of 4.5:1 against its background, and large text has at least 3:1. Shift colors intelligently (lighten or darken) without losing the original hue/brand intent.
-   **Touch Target Optimization:** Enforce the Google Play/Material Design standard touch target size of **at least 48x48 dp/px** for all clickable elements (buttons, links, icons). Achieve this via padding, margins, or explicit sizing without breaking the visual flow.
-   **Legibility & Typography:** Ensure minimum font sizes are readable (typically no smaller than 12px/sp, prioritizing 14px-16px for body text) and that line height provides adequate breathing room.
-   **Interaction State Clarity:** Guarantee that all interactive elements have distinct, visible `hover`, `focus`, `active`, and `disabled` states.

**What you CAN do:**
-   Adjust hex codes, RGB, or HSL values slightly to pass contrast checks.
-   Increase padding, margins, or min-height/min-width to expand touch areas.
-   Adjust font-size, font-weight, or line-height properties for legibility.
-   Add missing standard CSS pseudo-classes (`:focus-visible`, `:hover`) or basic ARIA attributes if strictly related to the visual interaction.

**What you CANNOT do (The Anti-Destruction Constraints):**
-   **NO BRAND MUTATION:** Do not change a button from red to blue. If a red button fails contrast against a white background, darken the red; do not change the core color identity.
-   **NO LAYOUT BREAKING:** Adjusting touch targets or font sizes must not cause text overflow, push elements off-screen, or break CSS Grid/Flexbox alignments. Use padding over hardcoded heights whenever possible.
-   **NO FEATURE CREEP OR REDESIGN:** Do not add new UI elements, icons, or animations. Do not change the layout from vertical to horizontal. Fix the existing UI; do not reinvent it.
-   **NO STYLISTIC REGRESSIONS:** Do not remove existing responsive breakpoints or media queries to "simplify" the CSS.

## Working-Tree Safety

These rules apply to every iteration. They keep the flow from touching work that is not its own.

-   **Track your paths.** Keep the list of paths the current iteration modifies, creates, and deletes.
-   **Stage only your paths.** Commit with `git add -- <your paths>` (and `git rm -- <path>` for a file you deleted). Never `git add -A`, `git add .`, or `git commit -a`.
-   **Revert only your paths.** To discard an iteration, run `git restore --source=HEAD --staged --worktree -- <paths you modified or deleted>` and delete the files you created. Never run `git reset --hard`, `git checkout -- .`, `git clean`, or `git stash`.
-   **Undo a commit without rewriting history.** If an iteration that was already committed must be discarded, run `git revert --no-edit <commit>` on the flow branch.
-   **Leave the log alone.** `a11y_results.tsv` is never staged, committed, or reverted.

## Output Format & Logging

After each iteration, log the result to `a11y_results.tsv` (tab-separated, do not commit the TSV):

`commit target_module metric_fixed status description`

**Column Description**
`commit` -> Short git hash (7 chars)
`target_module` -> Component or stylesheet modified
`metric_fixed` -> e.g., `contrast-ratio`, `touch-target`, `font-size`
`status` -> `keep`, `discard`, `crash`, or `rejected_layout_break`
`description` -> One-line summary (e.g., "Darkened #FF5555 to #CC0000 for 4.5:1 contrast on white bg")

## The Experiment Loop (Autonomous Refinement)

**LOOP FOREVER:**
1.  **Selection & Planning:** Review your fix backlog. Select **ONE specific visual goal** (e.g., fixing the touch targets on the navigation bar). Write a brief internal plan.
2.  **Execute:** Apply the CSS/Styling adjustments.
3.  **Self-Audit (The UI/UX Fitness Test):**
    * **Metric Check:** *Did this change actually hit the >4.5:1 contrast ratio or the 48x48px target?* * **Layout Check:** *Did increasing this padding break the flex container or cause wrapping? Did I respect the existing design system variables?* If the layout breaks or the color changes too drastically → instantly revert and log `rejected_layout_break`.
    * Run build/linter to ensure valid syntax.
4.  **Commit (only if the self-audit passed):** stage exactly this iteration's paths, then `git commit -m "AutoVisualFix: [<Module>] - <metric_fixed> - <brief description>"`
5.  **Log:** Update `a11y_results.tsv`.
6.  **Evaluate:**
    * Valid syntax + met accessibility metric + layout intact → **keep the commit**.
    * Broken layout, extreme color shifts, or invalid CSS → revert this iteration (its paths if uncommitted, `git revert --no-edit <commit>` if committed), log as `discard`, and retry with a more subtle approach.
7.  **On Errors:** Read the linter/build output. If a test fails due to a changed class name or dimension, fix the alignment. Re-enter the loop.
8.  **Backlog Refresh:** Every 10 iterations, re-scan the UI architecture to find new issues that may have surfaced or been missed.

**NEVER STOP:** Once the loop has begun, do not pause to ask for permission to continue. Run indefinitely through the backlog, always finding the next pixel or hex code that needs alignment.