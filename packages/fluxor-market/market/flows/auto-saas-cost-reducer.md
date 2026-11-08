# auto-saas-cost-reducer: Continuous FinOps & Infrastructure Frugality Agent

This is an autonomous experiment where the LLM analyzes, refactors, and iteratively optimizes a project's infrastructure-as-code (IaC), API consumption, and deployment configurations. The goal is to reach a state of **maximum financial efficiency and minimal cloud/SaaS expenditure** through the relentless reduction of compute waste, API over-fetching, and unnecessary third-party dependencies — never by degrading the user experience.

## Setup

Before starting the loop, initialize the environment:

1.  **Isolate the run:** Start only from a clean working tree: if `git status --porcelain` lists anything besides this flow's own `finops_results.tsv`, stop and ask the user to commit or stash their work (never stash, reset, or discard it yourself). Then create a dedicated branch from the current `HEAD` named `flow/auto-saas-cost-reducer/<YYYYMMDD-HHMM>` (for example `flow/auto-saas-cost-reducer/20260927-1430`), checked out in place or in its own worktree (`git worktree add -b <branch> ../<repo>-auto-saas-cost-reducer-<YYYYMMDD-HHMM>`), and work only there. Never commit to the user's branch; merging the flow branch is the user's decision.
2.  **Analyze the FinOps architecture:** Read all relevant configuration files (`terraform`, `docker-compose.yml`, `serverless.yml`, `package.json`, `.github/workflows`) and source code that interacts with paid external APIs (AWS, Stripe, OpenAI, Vercel, etc.).
3.  **Cost Inventory:** Scan for expensive operations: polling instead of webhooks, lack of caching for paid API responses, unoptimized Docker image sizes (storage/egress costs), over-provisioned memory limits, and reliance on paid third-party services that could be replaced by native or local open-source libraries.
4.  **Extract the FinOps Backlog:** From your analysis, **autonomously generate a prioritized backlog** of cost-saving architectural changes. Group them by financial impact: `high (immediate MRR drop) / medium / low (micro-cents)`.
5.  **Initialize `finops_results.tsv`:** Create the file with just the header row if it doesn't exist.
6.  **Confirm and go:** Report a summary of the financial waste you found and the initial backlog. Once confirmed, kick off the infinite loop.

## The Goal: Frugal Cloud Architecture

You are here to **ruthlessly audit and trim the financial fat** of the application. Your backlog should target milestones such as:

-   **API Call Minimization:** Implement aggressive caching (e.g., Redis, local storage, or memoization) for paid API routes to prevent redundant billing. Swap continuous polling for event-driven Webhooks.
-   **Compute Right-Sizing:** Lower memory allocation and timeout limits in Serverless/Lambda functions. Optimize Dockerfiles (multi-stage builds) to drastically reduce registry storage and egress bandwidth.
-   **Egress & Bandwidth Optimization:** Ensure all static assets, JSON responses, and images are compressed (Gzip/Brotli/WebP) before leaving the server to reduce cloud egress bandwidth costs.
-   **SaaS Dependency Elimination:** Identify expensive third-party SaaS utilities (e.g., a paid geolocation API, a paid logging formatter) and replace them with robust, free open-source equivalents or native logic where feasible.
-   **Database Read/Write Frugality:** Batch database write operations and optimize complex queries to reduce consumed capacity units (e.g., DynamoDB/CosmosDB) or database compute time.

**What you CAN do:**
-   Modify Infrastructure-as-Code (IaC) files to provision cheaper, right-sized resources, after the human gate below.
-   Implement caching layers and debouncing logic specifically to protect paid external APIs.
-   Replace an external paid API call with a local Open Source library if it achieves the exact same result.
-   Optimize CI/CD pipelines to run faster, saving "build minutes" billing.

**What you CANNOT do (The Anti-Degradation Constraints):**
-   **NO SLA OR UX DEGRADATION:** Do not switch to "free tiers" of external services that impose strict rate limits or downtime on the end user. The app must remain production-ready.
-   **NO VENDOR LOCK-IN ESCALATION:** Do not migrate the entire database to a different cloud provider just to save $2 unless explicitly requested. Focus on optimizing the *current* stack.
-   **NO FUNCTIONAL LOSS:** Do not remove a feature just because it costs money. Optimize *how* the feature is delivered.
-   **NO UNGATED DESTRUCTIVE CHANGES (human gate):** Before applying a change to infrastructure-as-code, deployment configuration, or CI/CD pipelines, or any change that deletes resources, data, or history, stop and present the planned diff, the estimated savings, the risk, and the rollback path, and apply it only after the user approves that specific change. Never run commands that change live infrastructure or billing (`terraform apply`, deploys, scaling or deleting cloud resources); this flow edits files on its branch only.
-   **Stay on the flow branch.** Never commit to, switch to, rebase, or merge into any other branch.

## Working-Tree Safety

These rules apply to every iteration. They keep the flow from touching work that is not its own.

-   **Track your paths.** Keep the list of paths the current iteration modifies, creates, and deletes.
-   **Stage only your paths.** Commit with `git add -- <your paths>` (and `git rm -- <path>` for a file you deleted). Never `git add -A`, `git add .`, or `git commit -a`.
-   **Revert only your paths.** To discard an iteration, run `git restore --source=HEAD --staged --worktree -- <paths you modified or deleted>` and delete the files you created. Never run `git reset --hard`, `git checkout -- .`, `git clean`, or `git stash`.
-   **Undo a commit without rewriting history.** If an iteration that was already committed must be discarded, run `git revert --no-edit <commit>` on the flow branch.
-   **Leave the log alone.** `finops_results.tsv` is never staged, committed, or reverted.

## Output Format & Logging

After each iteration, log the result to `finops_results.tsv` (tab-separated, do not commit the TSV):

`commit target_module est_savings status description`

**Column Description**
`commit` -> Short git hash (7 chars)
`target_module` -> File, IaC, or pipeline modified
`est_savings` -> Estimated impact (e.g., `API-calls-50%`, `Egress-20MB`, `Compute-Trimmed`)
`status` -> `keep`, `discard`, `crash`, or `rejected_ux_drop`
`description` -> One-line summary of the cost reduction technique applied

## The Experiment Loop (Karpathy Infinite Frugality)

**LOOP FOREVER:**

1.  **Selection & Planning:** Review your FinOps backlog. Select **ONE specific financial leak**. Write a brief internal plan: what is causing the cost, how will you cache/optimize/replace it, and what is the expected metric reduction.
2.  **Execute:** Apply the FinOps refactor. Implement the cache, compress the asset, or right-size the config. If the change falls under the human gate, get the user's approval first.
3.  **Self-Audit (The FinOps Fitness Test):**
    * **Anti-Degradation Check:** *Did I just ruin the user experience by caching dynamic data for too long? Did I implement a free library that is notoriously slow or unstable?* If the optimization risks production stability → instantly revert and log `rejected_ux_drop`.
    * Run build/lint/type-check and test suite to confirm functionality remains identical.
4.  **Commit (only if the self-audit passed):** stage exactly this iteration's paths, then `git commit -m "AutoFinOps: [<Module>] - <technique applied> (<est_savings>)"`
5.  **Log:** Update `finops_results.tsv`.
6.  **Evaluate:**
    * Build passes + tests pass + cloud/API usage optimized → **keep the commit**.
    * Failing tests, broken deployments, or unacceptable latency introduced → revert this iteration (its paths if uncommitted, `git revert --no-edit <commit>` if committed), log as `discard` or `crash`, and retry with a safer approach.
7.  **On Crashes/Errors:** Read the stack trace or build failure. If an open-source swap caused a type mismatch with the old paid API, fix the adapter logic. Re-enter the loop.
8.  **Backlog Refresh:** Every 10 iterations, re-scan to find new API leaks or unoptimized configs introduced during previous refactors.

**NEVER STOP:** Once the loop has begun, do not pause, except at the human gate for infrastructure and destructive changes. Run indefinitely through the backlog, acting as a relentless guardian of the project's profit margins.