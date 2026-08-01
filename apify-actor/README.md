# SEO Audit — bulk on-page checks with a scored report

Audit any list of URLs for on-page SEO and get back a **0–100 score plus the exact issues
behind it**. Not a black box: every deduction is named, so you can hand the output straight
to a client or a developer.

No API keys. No external services. No per-result vendor cost.

## What it checks

| Area | Checks |
|---|---|
| **Title** | Present, length against the 30–60 character target |
| **Meta description** | Present, length against the 70–160 character target |
| **Headings** | H1 present and unique, H2/H3 counts |
| **Indexability** | `noindex` in robots meta, canonical link present |
| **Mobile** | Viewport meta tag |
| **Accessibility** | Images missing `alt` text |
| **Social** | Open Graph title and description |
| **Content** | Word count against a 300-word thin-content threshold |
| **Technical** | HTTP status, HTTPS, redirects, response time, `lang` attribute |
| **Links** | Total, internal and external counts |

## Input

```json
{
  "urls": ["https://example.com", "example.com/pricing"],
  "maxConcurrency": 5,
  "timeoutMs": 15000
}
```

A bare domain is accepted — `https://` is assumed. Wire `urls` to the output of a crawler
Actor to audit an entire site.

| Field | Default | Notes |
|---|---|---|
| `urls` | — | Required. List of pages to audit. |
| `maxConcurrency` | 5 | Lower this when auditing many pages on one host. |
| `timeoutMs` | 15000 | Slow pages are recorded as failed rather than stalling the run. |
| `userAgent` | *(see input)* | Some sites serve different markup to unknown agents. |

## Output

One dataset item per URL:

```json
{
  "url": "https://example.com/",
  "ok": true,
  "score": 66,
  "issueCount": 5,
  "issues": [
    "Title is short (14 chars, aim 30-60)",
    "Missing meta description",
    "No canonical link",
    "Thin content (21 words, aim 300+)",
    "No Open Graph tags (poor social previews)"
  ],
  "statusCode": 200,
  "https": true,
  "title": "Example Domain",
  "titleLength": 14,
  "metaDescriptionLength": 0,
  "h1Count": 1,
  "h2Count": 0,
  "canonical": null,
  "noindex": false,
  "images": 0,
  "imagesMissingAlt": 0,
  "internalLinks": 0,
  "externalLinks": 1,
  "wordCount": 21,
  "responseTimeMs": 214
}
```

A `SUMMARY` record is written to the key-value store with run-level totals: average score,
how many pages are missing a title, meta description or H1, how many are `noindex`, and how
many are thin.

## How the score works

Every page starts at 100 and loses points per issue. The heaviest deductions are the ones
that actually stop a page ranking:

| Deduction | Issue |
|---:|---|
| −30 | HTTP 4xx/5xx |
| −20 | Marked `noindex` |
| −15 | Missing title, or not served over HTTPS |
| −12 | Missing meta description |
| −10 | No H1 |
| −8 | No viewport, or thin content |
| −5 | Multiple H1s, no canonical, title/meta length off target |

The score is clamped to 0–100. Because deductions are listed in `issues`, you can always
reconstruct exactly how a page got its number.

## Typical uses

- **Agency site audits** — run a client's sitemap, sort by score ascending, fix the worst first
- **Pre-launch QA** — catch missing meta and `noindex` before a release goes out
- **Competitor benchmarking** — audit competitor pages alongside your own
- **Regression monitoring** — schedule weekly and alert when a score drops
- **Lead generation** — audit prospect sites and lead with the specific problems you found

## Notes and limits

Pages are fetched as static HTML. Content injected by client-side JavaScript after load is
**not** evaluated — for heavily client-rendered sites, put a rendering Actor upstream and
feed this one the rendered HTML's URL.

`robots.txt` is not consulted; this reads the pages you supply.
