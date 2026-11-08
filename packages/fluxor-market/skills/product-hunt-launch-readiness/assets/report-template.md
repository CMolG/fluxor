# Product Hunt launch readiness — {{Product}}

**Verdict:** {{🔴 Not ready | 🟡 Ready with fixes | 🟢 Ready | 🏆 Launch-perfect}}{{ — conditional on the items to confirm, when any of them could be a blocker}}
**Audited:** {{repo path and/or URL(s)}} · {{date}} · against Product Hunt's launch guide and featuring guidelines (skill rulebook, {{rulebook date}})
**Open items:** 🔴 {{n}} · 🟠 {{n}} · 🟡 {{n}} · ⚪ {{n}} to confirm

## Summary
{{Three to five sentences, in plain words: what the product is and who it's for, whether it can be featured as it stands, the biggest risks for launch day, and the first thing to do.}}

## 🔴 Blockers — fix before launching
| # | Check | What's wrong (evidence) | Fix |
|---|---|---|---|
| 1 | {{A1 · Usable today}} | {{finding, citing `file:line`, URL, screenshot or field}} | {{concrete fix}} |

## 🟠 Major issues
| # | Check | What's wrong (evidence) | Fix |
|---|---|---|---|

## 🟡 Polish
| # | Check | What's wrong (evidence) | Fix |
|---|---|---|---|

## ⚪ To confirm — can't be verified from the code or site
- [ ] {{H1 · Is the posting account at least a week old?}}

## Scorecard
| Area | Status | Notes |
|---|---|---|
| A · Featuring eligibility | {{🔴/🟠/🟡/🟢/⚪}} | |
| B · Listing assets | | |
| C · First impression | | |
| D · Try-ability & conversion | | |
| E · Launch-day robustness | | |
| F · Trust & polish | | |
| G · Rules & promotion | | |
| H · Account, schedule & team | | |
| I · After the launch | | |
| J · {{product-type add-ons}} | | |

## Featuring potential
Product Hunt's editors feature launches that are strong on at least one or two of these.

| Criterion | Rating | Why |
|---|---|---|
| Useful | {{Strong / Moderate / Weak}} | |
| Novel | | |
| High craft | | |
| Creative | | |

## Launch kit
Full, validated drafts are in `launch-kit.md`. The key lines:

- **Name** ({{n}}/40): {{name}}
- **Tagline** ({{n}}/60): {{recommended tagline}} — alternatives: {{…}}
- **Description** ({{n}}/500): {{description}}
- **Launch tags:** {{up to 3}}
- **Pricing:** {{form option}} · **Promo:** {{offer / code / expiry or "none"}}
- **Gallery plan:** {{1-line storyboard, noting which images already exist}}

## Launch timeline
{{Output of `launch_timeline.py --markdown`, or: "Launch date not given — Product Hunt days start at 12:01 AM PT (= {{local}})."}}

## Changes made
{{Only in fix mode: `file:line` — what changed and why. Otherwise: "No files were changed; say the word and I'll apply the fixes marked as code changes."}}

## Evidence & limits
- {{evidence files: evidence/repo.json, evidence/url.json, evidence/screens/…}}
- {{anything you couldn't check, e.g. "producthunt.com was unreachable, so volatile limits were not re-verified live", "auditing a local server, so HTTPS and capacity were not assessed"}}
