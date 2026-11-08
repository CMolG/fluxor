# read-card: Task Intake Step

A single step that reads one task from the task source the flow was started from and turns it into the brief the rest of the flow works from. It changes nothing.

## What this step does

- Reads the task the flow was started with. When the flow consumes a queue and names no task, it selects the highest-priority open task assigned to this flow, in the order the task source defines.
- Extracts the fields the flow needs: the task id, its current status, its target (the module, files or area it names), the directive, and the acceptance criteria.
- Reads the code the target names only far enough to confirm that it exists; analysis belongs to the next step.

## Contract

- **Input:** the task source the flow was started from (a backlog file in the repository, an issue in a tracker, or a task handed to the flow directly) and, optionally, a task id.
- **Output:** a task brief: id, status, target, directive, acceptance criteria, and where the task lives, so that `set-card-status` can update it later.
- **Capabilities:** `fs.read` (declared in the manifest's `requires`), or the tracker's read access when the task lives outside the repository.

## Rules

- Take the task as written: do not widen the directive, add criteria, or fill a missing field with a guess.
- Keep the task source's own format and field names; do not rewrite or normalize the task.
- Do not pick up a task that is closed (done, blocked or failed) or assigned to another flow.

## When it stops

After one brief. It stops and reports instead when the task cannot be found or read, when it has no directive or no acceptance criteria, or when it is not open for this flow; in a queue with no eligible task, it reports that the queue is empty.
