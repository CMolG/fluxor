# Task — Engineering PR review

> CEET cluster: engineering (`ceet-backend-engineer`).

Use this prompt verbatim. Save the model's reply under
`evals/results/<run-id>/engineering-pr-review/<arm>.md` where `<arm>`
is one of `baseline`, `ceet`, or `generic`.

---

Review the following pull request. Comment on what is risky, what is
missing, and what you would change. Be specific about migration safety
and rollback. Do not rewrite the diff — produce only the review.

```
title: Rename users.email to users.primary_email and add unique index
files:
  - migrations/0042_rename_email.sql
  - app/models/user.py

migrations/0042_rename_email.sql
--------------------------------
BEGIN;

ALTER TABLE users RENAME COLUMN email TO primary_email;
UPDATE users SET primary_email = LOWER(primary_email) WHERE primary_email IS NOT NULL;
CREATE UNIQUE INDEX idx_users_primary_email ON users (primary_email);

COMMIT;

app/models/user.py
------------------
- email = Column(String, nullable=False)
+ primary_email = Column(String, nullable=False)

  def __repr__(self):
-     return f"<User {self.email}>"
+     return f"<User {self.primary_email}>"
```

Surrounding context:

- Production has 50M rows in `users`.
- `email` is referenced by 4 services and ~120 call sites.
- Deploy is rolling, no maintenance window.
- The team has a feature-flag system and an error-budget SLO.

Write a complete review in Markdown.
