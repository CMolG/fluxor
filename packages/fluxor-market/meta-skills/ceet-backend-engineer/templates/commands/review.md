<!-- CEET Source: code_review.*, coding_style.* -->

# /review Command — {engineer_name}

> Performs a code review.

## Usage
/review [args]

## Behavior

1. Read the diff
2. Apply my review philosophy: {directives.code_review.philosophy}
3. Check against my blocking criteria: {directives.code_review.blocking_criteria}
4. Apply my style rules (typing, naming, error handling, file org, comments, paradigm) from coding_style.*
5. For nitpicks: {directives.code_review.nitpick_policy}
6. For mentoring: {directives.code_review.mentoring_voice}
7. Flag if PR exceeds my size policy: {directives.code_review.pr_size_policy}
