# Task — Copy headlines

> CEET cluster: copy (`ceet-copywriter`).

Use this prompt verbatim. Save the model's reply under
`evals/results/<run-id>/copy-headlines/<arm>.md`.

---

Write three landing-page headlines for an observability product
targeting Site Reliability Engineers at mid-sized SaaS companies.

Constraints:

- Each headline must be its own line under a `## Headline 1`,
  `## Headline 2`, `## Headline 3` heading.
- Each headline must be 12 words or fewer.
- After each headline, write one supporting sentence (the
  subheadline) that names the audience, the pain, or the outcome.
- Do not use exclamation marks.
- Do not use generic phrases like "next-generation", "revolutionary",
  "AI-powered" unless the product is genuinely AI-led.
- The product is *not* AI-led. It is a tracing-and-logs product.
