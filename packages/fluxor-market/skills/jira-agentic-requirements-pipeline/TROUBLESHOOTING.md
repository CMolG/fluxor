# Troubleshooting

Common errors when running the pipeline against a real Jira instance,
plus the fix for each.

## `Missing Jira environment variables`

```
Missing Jira environment variables: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
```

Set the three required environment variables before invoking the CLI:

```bash
export JIRA_BASE_URL="https://example.atlassian.net"
export JIRA_EMAIL="you@example.com"
export JIRA_API_TOKEN="<token-from-id.atlassian.com/manage-profile/security/api-tokens>"
```

`JIRA_BASE_URL` may end in `/` — the CLI strips trailing slashes. The
hostname is your Atlassian Cloud subdomain or the URL of your
self-hosted Jira (e.g. `https://jira.example.com`).

## `Jira HTTP 401`

Atlassian Cloud requires Basic auth with **email + API token** (not the
password). Common mistakes:

- Using your Atlassian password instead of an API token.
- Using a token created for a different account than `JIRA_EMAIL`.
- Server (Data Center) installs that require Bearer tokens — Basic auth
  with email/password may also work depending on your admin's
  configuration.

Fix: regenerate the token at
`https://id.atlassian.com/manage-profile/security/api-tokens` and re-set
`JIRA_API_TOKEN`.

## `Jira HTTP 404` on `fetch-issue`

The issue key is wrong, or your account does not have permission to
view it. Verify by opening
`$JIRA_BASE_URL/browse/<ISSUE_KEY>` in a browser while logged in as
`$JIRA_EMAIL`. If the issue exists but you cannot see it, ask your Jira
admin to add your account to the project's Browse permission scheme.

## Epic field is empty even though the ticket has an epic link

The CLI reads the epic via `customfield_10011`, which is the default
field id on Atlassian Cloud's classic projects. Newer team-managed
projects, on-prem installs, or any heavily customized scheme expose the
epic link under a different field id.

Fix: open the issue in Jira, append `?fields=*all` to the URL of the
REST endpoint, and find the correct `customfieldXXXX`. Patch the
`fetch_issue` request in
`scripts/jira_pipeline_cli.py`.

## Comments are truncated on a long ticket

You should see a warning to stderr:

```
warning: comment cap reached (1000 of 1483); increase --max-comments to fetch all
```

Rerun with a larger cap:

```bash
python3 "$CLI" fetch-issue DEMO-1 --output issue.json --max-comments 5000
```

The pipeline pages through `/rest/api/3/issue/<key>/comment` 100 at a
time, so increasing the cap simply means more API calls — there is no
silent truncation once the cap fits the ticket size.

## Stale session lock for a different ticket

`collect-input` keeps state in `.jira_requirement_state.json` at the project root
(`$CLAUDE_PROJECT_DIR`, else the git top level, else the current directory), keyed by
`issueKey`. If you run `collect-input` for `DEMO-1` and then for
`DEMO-2` against the same state file, the second run starts from a
fresh state because the keys do not match. Either pass a different
`--state-file` per ticket or delete the existing state file:

```bash
rm "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}/.jira_requirement_state.json"
```

## `Cannot resolve contract. Missing required answers: Q3, Q5`

`resolve-contract` refuses to emit a `FunctionalContract` until every
required question has an answer. Run `collect-input` again — it resumes
from the missing entries — or pass the missing answers programmatically
into the state file.

## Snapshot tests fail after I change the inference logic

That is expected: the snapshot files under `tests/snapshots/` are
the contract. After an intentional change, run from this skill's directory
in the source repository (tests are not installed with the skill):

```bash
SNAPSHOT_UPDATE=1 python3 -m unittest discover -s tests -t tests -p test_pipeline_snapshots.py
```

Then review the diff before committing. If the diff is wider than you
expected, that is also a signal worth investigating.
