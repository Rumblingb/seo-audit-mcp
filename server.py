"""
SEO Audit MCP Server
Provides AI agents with the ability to audit any URL's on-page SEO.

Usage:
  python3 server.py                    # Free tier (50 calls/instance)
  python3 server.py --pro-key PROL_XXX  # Pro tier (unlimited)

Tools:
- seo_analyze_url: Full on-page SEO audit
- seo_check_headers: HTTP headers audit
- seo_suggest_keywords: Extract keywords from page content
- seo_analyze_speed_factors: Page weight and resource analysis

Pricing: $19/mo — https://buy.stripe.com/dRm6oJ4Hd2Jugek0wz1oI0m
"""

import json
import re
import ssl as ssl_module
import sys
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl

server = Server("seo-audit-mcp")

# ─── Rate Limiting & Pro Key ───────────────────────────────────────────
FREE_LIMIT = 50
PRO_KEYS = {"PROL_AGENTPAY_DEMO": "demo"}  # Demo key for testing

# Parse --pro-key from command line
PRO_KEY = None
for i, arg in enumerate(sys.argv):
    if arg == "--pro-key" and i + 1 < len(sys.argv):
        PRO_KEY = sys.argv[i + 1]
        break

IS_PRO = PRO_KEY in PRO_KEYS
call_counter = 0

STRIPE_LINK = "https://buy.stripe.com/dRm6oJ4Hd2Jugek0wz1oI0m"  # $19/mo

def check_rate_limit():
    """Check if free tier has exceeded limit. Returns error dict or None."""
    global call_counter
    if IS_PRO:
        return None
    call_counter += 1
    if call_counter > FREE_LIMIT:
        remaining = call_counter - FREE_LIMIT
        return {
            "error": f"Free tier limit reached ({FREE_LIMIT} calls). Upgrade to Pro for unlimited access.",
            "isError": True,
            "next_steps": [
                f"Purchase Pro at {STRIPE_LINK} ($19/mo, unlimited)",
                "Restart the server to reset the free counter",
                "Use --pro-key PROL_XXX to run in Pro mode"
            ],
            "calls_used": call_counter,
            "limit": FREE_LIMIT,
            "over_by": remaining
        }
    return None


# ─── Helpers ───────────────────────────────────────────────────────────────

def fetch_url(url: str, follow_redirects: bool = True) -> httpx.Response:
    """Fetch a URL with sensible defaults. Raises on network errors."""
    with httpx.Client(
        follow_redirects=follow_redirects,
        timeout=30.0,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; SEOAuditBot/1.0; "
                "+https://seo-audit-mcp.example.com)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        },
    ) as client:
        return client.get(url)


def extract_tag(html: str, tag: str) -> list[str]:
    """Extract full <tag ...>content</tag> from HTML using regex."""
    pattern = re.compile(
        rf'<{tag}[^>]*>(.*?)</{tag}>', re.IGNORECASE | re.DOTALL
    )
    return pattern.findall(html)


def extract_attr(html: str, tag: str, attr: str) -> list[str]:
    """Extract attribute values from specific tags."""
    pattern = re.compile(
        rf'<{tag}[^>]*\s{attr}\s*=\s*["\']([^"\']*)["\']',
        re.IGNORECASE | re.DOTALL,
    )
    return pattern.findall(html)


def extract_meta_content(html: str, name_or_prop: str) -> Optional[str]:
    """Extract content from a <meta> tag by name or property."""
    # Try property first (Open Graph)
    pattern = re.compile(
        rf'<meta[^>]*(?:property|name)\s*=\s*["\']{re.escape(name_or_prop)}["\'][^>]*'
        rf'\s+content\s*=\s*["\']([^"\']*)["\']',
        re.IGNORECASE,
    )
    m = pattern.search(html)
    if m:
        return m.group(1)
    # Try reversed attribute order
    pattern2 = re.compile(
        rf'<meta[^>]*\s+content\s*=\s*["\']([^"\']*)["\'][^>]*'
        rf'(?:property|name)\s*=\s*["\']{re.escape(name_or_prop)}["\']',
        re.IGNORECASE,
    )
    m2 = pattern2.search(html)
    if m2:
        return m2.group(1)
    return None


def extract_all_meta(html: str) -> dict[str, str]:
    """Extract all meta tags into a dict keyed by name/property."""
    metas: dict[str, str] = {}
    pattern = re.compile(
        r'<meta[^>]*(?:name|property)\s*=\s*["\']([^"\']*)["\']'
        r'[^>]*\s+content\s*=\s*["\']([^"\']*)["\']',
        re.IGNORECASE,
    )
    for m in pattern.finditer(html):
        metas[m.group(1).strip()] = m.group(2).strip()
    # reversed order
    pattern2 = re.compile(
        r'<meta[^>]*\s+content\s*=\s*["\']([^"\']*)["\']'
        r'[^>]*(?:name|property)\s*=\s*["\']([^"\']*)["\']',
        re.IGNORECASE,
    )
    for m in pattern2.finditer(html):
        metas[m.group(2).strip()] = m.group(1).strip()
    return metas


def strip_html(html: str) -> str:
    """Remove all HTML tags, returning only visible text."""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def check_ssl(url: str) -> dict[str, Any]:
    """Check SSL certificate validity for a URL."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    port = parsed.port or 443
    result: dict[str, Any] = {"valid": False, "issuer": None, "error": None}
    try:
        ctx = ssl_module.create_default_context()
        with ctx.wrap_socket(
            ssl_module.SSLSocket(socket=None, family=0, type=0, proto=0),  # type: ignore
            server_hostname=hostname,
        ) as sock:
            pass
    except Exception as e:
        # Try a simpler check via httpx
        try:
            with httpx.Client(verify=True, timeout=10.0) as client:
                resp = client.get(f"https://{hostname}:{port}", headers={"User-Agent": "SEOAuditBot/1.0"})
                result["valid"] = True
                result["issuer"] = "verified (via httpx)"
        except Exception as e2:
            result["valid"] = False
            result["error"] = str(e2)
    return result


def status_for_length(length: int, min_val: int, max_val: int) -> str:
    """Return 'good', 'fair', or 'poor' based on length bounds."""
    if min_val <= length <= max_val:
        return "good"
    if length == 0:
        return "poor"
    return "fair"


def compute_score(issues: list[str]) -> int:
    """Compute an SEO score out of 100 based on issues list."""
    penalties = {
        "Missing title tag": 20,
        "Title tag too short": 10,
        "Title tag too long": 10,
        "Missing meta description": 20,
        "Meta description too short": 5,
        "Meta description too long": 5,
        "No H1 heading": 15,
        "Multiple H1 headings": 10,
        "H1 too long": 5,
        "Missing alt text on images": 5,
        "No Open Graph title": 5,
        "No Open Graph description": 3,
        "No Open Graph image": 3,
        "No viewport meta tag": 10,
        "No canonical URL": 5,
        "No structured data": 5,
        "SSL certificate issue": 15,
    }
    score = 100
    for issue in issues:
        penalty = penalties.get(issue, 2)
        score -= penalty
    return max(0, min(100, score))


# ─── Parse helpers ─────────────────────────────────────────────────────────

def parse_headings(html: str) -> dict[str, Any]:
    """Analyze heading structure (H1-H6)."""
    result: dict[str, Any] = {
        "h1_count": 0, "h2_count": 0, "h3_count": 0,
        "h4_count": 0, "h5_count": 0, "h6_count": 0,
        "h1_contents": [], "issues": [],
    }
    for level in range(1, 7):
        tag = f"h{level}"
        contents = extract_tag(html, tag)
        result[f"h{level}_count"] = len(contents)
        if level == 1:
            result["h1_contents"] = [strip_html(c)[:100] for c in contents]

    # H1 issues
    if result["h1_count"] == 0:
        result["issues"].append("No H1 heading")
    elif result["h1_count"] > 1:
        result["issues"].append("Multiple H1 headings")
    if result["h1_contents"]:
        for h1 in result["h1_contents"]:
            if len(h1) > 70:
                result["issues"].append("H1 too long")
                break
    return result


def parse_images(html: str) -> dict[str, Any]:
    """Analyze image tags for alt text coverage."""
    img_tags = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
    total = len(img_tags)
    missing_alt = 0
    for img in img_tags:
        if not re.search(r'\salt\s*=\s*["\']', img, re.IGNORECASE):
            missing_alt += 1
    return {"total": total, "missing_alt": missing_alt}


def parse_open_graph(html: str) -> dict[str, bool]:
    """Check for Open Graph meta tags."""
    og_title = extract_meta_content(html, "og:title") is not None
    og_description = extract_meta_content(html, "og:description") is not None
    og_image = extract_meta_content(html, "og:image") is not None
    og_url = extract_meta_content(html, "og:url") is not None
    og_type = extract_meta_content(html, "og:type") is not None
    return {
        "og_title": og_title,
        "og_description": og_description,
        "og_image": og_image,
        "og_url": og_url,
        "og_type": og_type,
    }


def parse_title(html: str) -> dict[str, Any]:
    """Extract and analyze the <title> tag."""
    titles = extract_tag(html, "title")
    if not titles:
        return {"content": "", "length": 0, "status": "poor"}
    content = strip_html(titles[0])
    length = len(content)
    if length == 0:
        return {"content": "", "length": 0, "status": "poor"}
    status = status_for_length(length, 30, 60)
    return {"content": content, "length": length, "status": status}


def parse_meta_description(html: str) -> dict[str, Any]:
    """Extract and analyze the meta description."""
    content = extract_meta_content(html, "description")
    if not content:
        return {"content": "", "length": 0, "status": "poor"}
    length = len(content)
    status = status_for_length(length, 120, 158)
    return {"content": content, "length": length, "status": status}


def parse_structured_data(html: str) -> dict[str, Any]:
    """Detect structured data (JSON-LD, Microdata, RDFa)."""
    # JSON-LD
    jsonld = bool(re.search(
        r'<script[^>]*type\s*=\s*["\']application/ld\+json["\']',
        html, re.IGNORECASE,
    ))
    # Microdata (itemscope/itemprop)
    microdata = bool(re.search(r'\bitemscope\b', html, re.IGNORECASE))
    # RDFa
    rdfa = bool(re.search(r'\btypeof\s*=\s*["\']', html, re.IGNORECASE))
    return {
        "json_ld": jsonld,
        "microdata": microdata,
        "rdfa": rdfa,
        "present": jsonld or microdata or rdfa,
    }


def parse_hreflang(html: str) -> list[dict[str, str]]:
    """Extract hreflang tags."""
    tags = []
    pattern = re.compile(
        r'<link[^>]*\brel\s*=\s*["\']alternate["\'][^>]*\bhreflang\s*=\s*["\']([^"\']*)["\']',
        re.IGNORECASE,
    )
    for m in pattern.finditer(html):
        link_tag = m.group(0)
        href_m = re.search(r'\bhref\s*=\s*["\']([^"\']*)["\']', link_tag, re.IGNORECASE)
        href = href_m.group(1) if href_m else ""
        tags.append({"hreflang": m.group(1), "href": href})
    return tags


# ─── MCP Tools ─────────────────────────────────────────────────────────────

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="seo_analyze_url",
            description=(
                "Full on-page SEO audit of any URL. Analyzes title tag, meta "
                "description, headings (H1-H6), image alt texts, word count, "
                "SSL status, mobile-friendly viewport tag, Open Graph tags, "
                "canonical URL, hreflang tags, robots meta, and structured "
                "data presence. Returns a comprehensive JSON report with an "
                "SEO score out of 100."
            ),
            inputSchema={
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to audit (e.g., https://example.com)",
                    }
                },
            },
        ),
        types.Tool(
            name="seo_check_headers",
            description=(
                "HTTP headers audit of a URL. Checks status code, content-type, "
                "x-robots-tag, link rel=canonical, cache-control, server, "
                "last-modified headers."
            ),
            inputSchema={
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to check headers for",
                    }
                },
            },
        ),
        types.Tool(
            name="seo_suggest_keywords",
            description=(
                "Extract keyword suggestions from page content. Analyzes most "
                "frequent words, words in headings, and words in the title. "
                "Suggests primary and secondary keywords."
            ),
            inputSchema={
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to extract keywords from",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of keyword suggestions (default: 10)",
                        "default": 10,
                    },
                },
            },
        ),
        types.Tool(
            name="seo_analyze_speed_factors",
            description=(
                "Analyze page weight and resource loading. Measures total HTML "
                "size, number of resources (scripts, stylesheets, images), "
                "compression (gzip/brotli), and keep-alive connection status."
            ),
            inputSchema={
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to analyze speed factors for",
                    }
                },
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    if arguments is None:
        arguments = {}

    # Rate limit check
    limit_check = check_rate_limit()
    if limit_check:
        return [types.TextContent(type="text", text=json.dumps(limit_check, indent=2))]

    url = arguments.get("url", "")

    if name == "seo_analyze_url":
        return [types.TextContent(type="text", text=json.dumps(
            await seo_analyze_url(url), indent=2
        ))]
    elif name == "seo_check_headers":
        return [types.TextContent(type="text", text=json.dumps(
            await seo_check_headers(url), indent=2
        ))]
    elif name == "seo_suggest_keywords":
        count = arguments.get("count", 10)
        return [types.TextContent(type="text", text=json.dumps(
            await seo_suggest_keywords(url, count), indent=2
        ))]
    elif name == "seo_analyze_speed_factors":
        return [types.TextContent(type="text", text=json.dumps(
            await seo_analyze_speed_factors(url), indent=2
        ))]
    else:
        raise ValueError(f"Unknown tool: {name}")


async def seo_analyze_url(url: str) -> dict[str, Any]:
    """Full on-page SEO audit."""
    try:
        response = fetch_url(url)
        html = response.text
    except Exception as e:
        return {"url": url, "error": f"Failed to fetch URL: {str(e)}", "score": 0}

    issues: list[str] = []

    # Title
    title_info = parse_title(html)
    if title_info["status"] == "poor" and title_info["length"] == 0:
        issues.append("Missing title tag")
    elif title_info["status"] == "poor":
        issues.append("Title tag too short")
    elif title_info["status"] == "fair":
        issues.append("Title tag too long" if title_info["length"] > 60 else "Title tag too short")

    # Meta description
    meta_desc = parse_meta_description(html)
    if meta_desc["status"] == "poor" and meta_desc["length"] == 0:
        issues.append("Missing meta description")
    elif meta_desc["status"] == "poor":
        issues.append("Meta description too short")
    elif meta_desc["status"] == "fair":
        issues.append("Meta description too long" if meta_desc["length"] > 158 else "Meta description too short")

    # Headings
    headings_info = parse_headings(html)
    issues.extend(headings_info.get("issues", []))

    # Images
    images_info = parse_images(html)
    if images_info["missing_alt"] > 0:
        issues.append(f"Missing alt text on images ({images_info['missing_alt']} of {images_info['total']})")

    # SSL
    ssl_info = check_ssl(url)
    if not ssl_info["valid"]:
        issues.append("SSL certificate issue")

    # Viewport (mobile-friendly)
    viewport = extract_meta_content(html, "viewport")
    if not viewport:
        issues.append("No viewport meta tag")

    # Open Graph
    og_info = parse_open_graph(html)
    if not og_info["og_title"]:
        issues.append("No Open Graph title")
    if not og_info["og_description"]:
        issues.append("No Open Graph description")
    if not og_info["og_image"]:
        issues.append("No Open Graph image")

    # Canonical URL
    canonical = extract_attr(html, "link", "href") if 'rel="canonical"' in html.lower() or "rel='canonical'" in html.lower() else None
    # Actually, let's properly extract canonical
    canonical_href = None
    link_pattern = re.compile(
        r'<link[^>]*\brel\s*=\s*["\']canonical["\'][^>]*>',
        re.IGNORECASE,
    )
    for link_tag in link_pattern.finditer(html):
        href_m = re.search(r'\bhref\s*=\s*["\']([^"\']*)["\']', link_tag.group(0), re.IGNORECASE)
        if href_m:
            canonical_href = href_m.group(1)
            break
    if not canonical_href:
        issues.append("No canonical URL")

    # Hreflang
    hreflang_tags = parse_hreflang(html)

    # Robots meta
    robots = extract_meta_content(html, "robots")

    # Structured data
    sd_info = parse_structured_data(html)
    if not sd_info["present"]:
        issues.append("No structured data")

    # Word count
    body_text = ""
    body_m = re.search(r'<body[^>]*>(.*)</body>', html, re.IGNORECASE | re.DOTALL)
    if body_m:
        body_text = strip_html(body_m.group(1))
    else:
        body_text = strip_html(html)
    word_count = len(body_text.split())

    # Score
    score = compute_score(issues)

    return {
        "url": url,
        "title": title_info,
        "meta_description": meta_desc,
        "headings": headings_info,
        "images": images_info,
        "ssl": ssl_info,
        "viewport": viewport if viewport else None,
        "open_graph": og_info,
        "canonical_url": canonical_href,
        "hreflang_tags": hreflang_tags,
        "robots_meta": robots,
        "structured_data": sd_info,
        "word_count": word_count,
        "issues": issues,
        "score": score,
    }


async def seo_check_headers(url: str) -> dict[str, Any]:
    """HTTP headers audit."""
    try:
        # Don't follow redirects to capture the first response
        response = fetch_url(url, follow_redirects=False)
    except Exception as e:
        return {"url": url, "error": f"Failed to fetch URL: {str(e)}"}

    headers = response.headers
    # Extract link header for canonical
    link_header = headers.get("link", "")
    canonical_from_link = None
    if link_header:
        cm = re.search(r'<([^>]+)>\s*;\s*rel\s*=\s*["\']?canonical["\']?', link_header, re.IGNORECASE)
        if cm:
            canonical_from_link = cm.group(1)

    return {
        "url": str(response.url),
        "status_code": response.status_code,
        "content_type": headers.get("content-type"),
        "x_robots_tag": headers.get("x-robots-tag"),
        "link_canonical": canonical_from_link,
        "cache_control": headers.get("cache-control"),
        "server": headers.get("server"),
        "last_modified": headers.get("last-modified"),
        "content_length": headers.get("content-length"),
        "all_headers": dict(headers),
    }


async def seo_suggest_keywords(url: str, count: int = 10) -> dict[str, Any]:
    """Extract keyword suggestions from page content."""
    try:
        response = fetch_url(url)
        html = response.text
    except Exception as e:
        return {"url": url, "error": f"Failed to fetch URL: {str(e)}"}

    # Extract text
    body_m = re.search(r'<body[^>]*>(.*)</body>', html, re.IGNORECASE | re.DOTALL)
    body_html = body_m.group(1) if body_m else html
    body_text = strip_html(body_html)

    # Title text
    title_text = ""
    titles = extract_tag(html, "title")
    if titles:
        title_text = strip_html(titles[0])

    # Heading texts
    heading_text = ""
    for level in range(1, 7):
        for h in extract_tag(html, f"h{level}"):
            heading_text += " " + strip_html(h)

    # Tokenize (simple: lowercase, keep alphabetic words >= 3 chars)
    def tokenize(text: str) -> list[str]:
        words = re.findall(r'[a-zA-Z]{3,}', text.lower())
        # Filter common stop words
        stop_words = {
            "the", "and", "for", "are", "but", "not", "you", "all", "can",
            "had", "her", "was", "one", "our", "out", "has", "have", "been",
            "some", "same", "also", "just", "than", "that", "this", "with",
            "from", "they", "their", "them", "would", "could", "should",
            "about", "into", "over", "after", "what", "when", "where", "which",
            "will", "been", "were", "being", "does", "more", "most", "other",
            "such", "here", "there", "each", "like", "very", "your",
        }
        return [w for w in words if w not in stop_words]

    body_words = tokenize(body_text)
    title_words = tokenize(title_text)
    heading_words = tokenize(heading_text)

    # Count frequencies
    from collections import Counter
    body_freq = Counter(body_words)
    heading_freq = Counter(heading_words)
    title_freq = Counter(title_words)

    # Suggest primary keywords (top from headings + title)
    primary_candidates: list[str] = []
    seen: set[str] = set()
    for word, _ in heading_freq.most_common(20):
        if word not in seen:
            primary_candidates.append(word)
            seen.add(word)
    for word, _ in title_freq.most_common(20):
        if word not in seen:
            primary_candidates.append(word)
            seen.add(word)

    # Secondary keywords (top from body minus already seen)
    secondary_candidates: list[str] = []
    for word, _ in body_freq.most_common(50):
        if word not in seen:
            secondary_candidates.append(word)
            seen.add(word)

    # Bigrams as additional suggestions (for secondary)
    bigrams = re.findall(r'(?=(\b[a-zA-Z]{3,}\s+[a-zA-Z]{3,}\b))', body_text.lower())
    bigram_freq = Counter(bigrams)
    bigram_suggestions = [bg for bg, _ in bigram_freq.most_common(count) if bg not in seen]

    return {
        "url": url,
        "word_count": len(body_words),
        "primary_keywords": primary_candidates[:max(5, count // 2)],
        "secondary_keywords": secondary_candidates[:count],
        "title_words": title_freq.most_common(10),
        "heading_words": heading_freq.most_common(15),
        "top_body_words": body_freq.most_common(30),
        "bigram_suggestions": bigram_suggestions[:5],
    }


async def seo_analyze_speed_factors(url: str) -> dict[str, Any]:
    """Analyze page weight and resource loading."""
    try:
        response = fetch_url(url, follow_redirects=True)
        html = response.text
    except Exception as e:
        return {"url": url, "error": f"Failed to fetch URL: {str(e)}"}

    headers = response.headers
    html_size_bytes = len(html)
    html_size_kb = round(html_size_bytes / 1024, 2)

    # Count resources
    scripts = len(re.findall(r'<script[^>]*src\s*=', html, re.IGNORECASE))
    stylesheets = len(re.findall(
        r'<link[^>]*\brel\s*=\s*["\']stylesheet["\']', html, re.IGNORECASE
    ))
    images = len(re.findall(r'<img[^>]*src\s*=', html, re.IGNORECASE))
    inline_scripts = len(re.findall(
        r'<script[^>]*>(?!.*src=)(.*?)</script>', html, re.IGNORECASE | re.DOTALL
    ))
    inline_styles = len(re.findall(r'<style[^>]*>(.*?)</style>', html, re.IGNORECASE | re.DOTALL))
    fonts = len(re.findall(r'<link[^>]*\brel\s*=\s*["\']font["\']', html, re.IGNORECASE))

    # Compression
    content_encoding = headers.get("content-encoding", "none")
    transfer_encoding = headers.get("transfer-encoding", "")
    connection = headers.get("connection", "")
    keep_alive = headers.get("keep-alive", "")

    # Check if keep-alive is indicated
    is_keep_alive = False
    if keep_alive:
        is_keep_alive = True
    elif connection and connection.lower() == "keep-alive":
        is_keep_alive = True

    # HTTP version (httpx doesn't expose this directly, but we can infer)
    http_version = response.http_version if hasattr(response, 'http_version') else "unknown"

    return {
        "url": url,
        "html_size_bytes": html_size_bytes,
        "html_size_kb": html_size_kb,
        "resources": {
            "scripts_external": scripts,
            "scripts_inline": inline_scripts,
            "stylesheets_external": stylesheets,
            "stylesheets_inline": inline_styles,
            "images": images,
            "fonts": fonts,
            "total_resources": scripts + stylesheets + images + fonts,
        },
        "compression": {
            "content_encoding": content_encoding if content_encoding != "none" else None,
            "is_compressed": content_encoding != "none",
        },
        "connection": {
            "keep_alive": is_keep_alive,
            "connection_header": connection if connection else None,
            "keep_alive_header": keep_alive if keep_alive else None,
        },
        "http_version": http_version,
        "response_headers": {
            "content_type": headers.get("content-type"),
            "content_length": headers.get("content-length"),
        },
    }


# ─── Main entry point ─────────────────────────────────────────────────────

async def main():
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="seo-audit-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
