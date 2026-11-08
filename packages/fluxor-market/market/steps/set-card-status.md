# set-card-status: Task Status Update Step

A single step that writes a task's new status back to the task source the flow was started from, with a short note, and changes nothing else.

## What this step does

- Sets the status the flow decided (for example in progress, completed, blocked or failed), using the status values the task source defines.
- When the task is completed, checks off the acceptance criteria the flow verified; when it is blocked or failed, appends a short note that says why (the failing check, or the constraint that could not be met).
- When the task lives in a file in the repository, adds that file to the flow's list of touched paths, so the commit that records the work includes it.

## Contract

- **Input:** the task brief from `read-card`, the new status, the verification verdict, and the note.
- **Output:** the updated task.
- **Capabilities:** `fs.write` (declared in the manifest's `requires`), or the tracker's write access when the task lives outside the repository.

## Rules

- Mark a task completed only when the flow's verification passed and every acceptance criterion is met.
- Change only the status, the criteria checkboxes and the note: never the directive, the criteria text, the priority, or any other task.
- Use only the statuses the task source defines. When it has no value for the outcome (for example no `blocked`), keep the current status, write the note, and report it; never map an outcome silently to another status.

## When it stops

After one update. It stops and reports, without writing, when the task changed since `read-card` read it or when the task source refuses the write.
