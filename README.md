# SEO Audit MCP Server

> **AI-native SEO auditing for content marketers and SEO professionals.**

Give any AI agent the power to audit on-page SEO in seconds. No dashboards, no logins — just pure, actionable SEO intelligence delivered directly into your AI workflows.

---

## 🚀 Features

| Tool | Description |
|------|-------------|
| **`seo_analyze_url`** | Full on-page SEO audit — title, meta, headings, images, SSL, Open Graph, canonical, hreflang, structured data, and more. Returns a comprehensive JSON report with an SEO score out of 100. |
| **`seo_check_headers`** | HTTP headers audit — status code, content-type, X-Robots-Tag, Link canonical, Cache-Control, Server, Last-Modified. |
| **`seo_suggest_keywords`** | Extract keyword suggestions from page content — most frequent words, heading words, title words. Suggests primary and secondary keywords + bigram suggestions. |
| **`seo_analyze_speed_factors`** | Page weight analysis — HTML size, resource counts (scripts, stylesheets, images, fonts), compression status, keep-alive. |

## 📦 Installation

```bash
# Clone the repo
git clone https://github.com/nousresearch/seo-audit-mcp.git
cd seo-audit-mcp

# Install dependencies
pip install -r requirements.txt

# Run the server
python server.py
```

### Requirements

- Python 3.10+
- `mcp>=1.0.0`
- `httpx>=0.27.0`

## 🔧 Configuration

### Smithery (Recommended)

Deploy in one click on [Smithery](https://smithery.ai):

```yaml
startCommand:
  type: stdio
  configSchema:
    type: object
    properties: {}
  commandFunction: |-
    (config) => ({ command: 'python', args: ['server.py'] })
```

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "seo-audit": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

### Cursor / Windsurf / Continue

Point to the `server.py` file as a custom MCP tool.

## 📋 Example Output

```json
{
  "url": "https://example.com",
  "title": { "content": "Example Domain", "length": 14, "status": "poor" },
  "meta_description": { "content": "...", "length": 0, "status": "poor" },
  "headings": { "h1_count": 1, "h2_count": 0, "issues": [] },
  "images": { "total": 0, "missing_alt": 0 },
  "ssl": { "valid": true, "issuer": "verified (via httpx)" },
  "open_graph": { "og_title": false, "og_description": false, "og_image": false },
  "word_count": 42,
  "issues": [
    "Missing title tag",
    "Missing meta description",
    "No Open Graph title",
    "No Open Graph description",
    "No Open Graph image",
    "No viewport meta tag",
    "No canonical URL",
    "No structured data"
  ],
  "score": 32
}
```

## 💰 Pricing

**$19/month** — flat rate, unlimited audits.

- ✅ Unlimited URL audits
- ✅ All 4 tools included
- ✅ No rate limits
- ✅ Priority support
- ✅ Cancel anytime

[Subscribe Now — $19/mo](https://buy.stripe.com/dRm6oJ4Hd2Jugek0wz1oI0m)

### Enterprise

Need custom integrations, white-labeling, or on-premise deployment? Contact us for enterprise pricing.

## 🏗 Architecture

This MCP server uses:

- **[MCP (Model Context Protocol)](https://modelcontextprotocol.io)** — The open standard for connecting AI models to tools and data.
- **`httpx`** — Modern Python HTTP client with async support.
- **`re` (regex)** — Lightweight HTML parsing with zero heavy dependencies.

No Selenium, no headless browser, no bloated dependencies. Pure Python, fast execution.

## 🔍 Tool Reference

### `seo_analyze_url(url)`

Full-page SEO audit analyzing:

- `<title>` tag content, length, and quality
- `<meta name="description">` content, length, and quality
- Heading structure (H1–H6) with count and content
- Image alt text coverage
- SSL certificate validity
- Viewport meta tag (mobile-friendliness)
- Open Graph tags (`og:title`, `og:description`, `og:image`, `og:url`, `og:type`)
- Canonical URL detection
- Hreflang tag extraction
- Robots meta tag value
- Structured data detection (JSON-LD, Microdata, RDFa)
- Total word count
- SEO score (0-100) with actionable issues list

### `seo_check_headers(url)`

HTTP response header audit:

- Status code
- Content-Type
- X-Robots-Tag
- Link header canonical
- Cache-Control
- Server
- Last-Modified
- Content-Length

### `seo_suggest_keywords(url, count=10)`

Keyword intelligence:

- Primary keywords (from headings + title)
- Secondary keywords (from body content)
- Top title words with frequencies
- Top heading words with frequencies
- Top body words with frequencies
- Bigram (two-word phrase) suggestions

### `seo_analyze_speed_factors(url)`

Performance analysis:

- Total HTML size (bytes and KB)
- External/inline scripts, stylesheets, images, fonts
- Compression status (gzip/brotli)
- Keep-alive connection status
- HTTP version

## 🤝 Contributing

PRs welcome! Please ensure:

1. All regex parsing handles edge cases (self-closing tags, malformed HTML)
2. Network timeouts and error handling are robust
3. Tests pass with `pytest`

## 📄 License

MIT — free to use, modify, and distribute.

---

Made by [Nous Research](https://nousresearch.com) — building the future of AI-agent tooling.
