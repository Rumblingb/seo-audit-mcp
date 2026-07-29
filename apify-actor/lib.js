const UA = 'Mozilla/5.0 (compatible; SeoAuditActor/0.1; +https://apify.com)';

export function normaliseUrl(input) {
  let u = String(input ?? '').trim();
  if (!u) return { ok: false, reason: 'Empty input' };
  if (!/^https?:\/\//i.test(u)) u = `https://${u}`;
  try {
    const parsed = new URL(u);
    if (!['http:', 'https:'].includes(parsed.protocol)) return { ok: false, reason: 'Only http and https are supported' };
    if (!parsed.hostname.includes('.')) return { ok: false, reason: 'Hostname has no TLD' };
    return { ok: true, url: parsed.toString() };
  } catch {
    return { ok: false, reason: 'Malformed URL' };
  }
}

export function stripTags(html) {
  return String(html ?? '')
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function extractTitle(html) {
  const m = String(html ?? '').match(/<title\b[^>]*>([\s\S]*?)<\/title>/i);
  return m ? stripTags(m[1]) : null;
}

export function extractMeta(html, name) {
  const src = String(html ?? '');
  // name= and property= both appear in the wild; attribute order varies.
  const patterns = [
    new RegExp(`<meta[^>]+(?:name|property)\\s*=\\s*["']${name}["'][^>]*content\\s*=\\s*["']([^"']*)["']`, 'i'),
    new RegExp(`<meta[^>]+content\\s*=\\s*["']([^"']*)["'][^>]*(?:name|property)\\s*=\\s*["']${name}["']`, 'i'),
  ];
  for (const re of patterns) {
    const m = src.match(re);
    if (m) return m[1].trim();
  }
  return null;
}

export function extractHeadings(html) {
  const src = String(html ?? '');
  const out = { h1: [], h2: [], h3: [] };
  for (const level of ['h1', 'h2', 'h3']) {
    const re = new RegExp(`<${level}\\b[^>]*>([\\s\\S]*?)<\\/${level}>`, 'gi');
    let m;
    while ((m = re.exec(src)) !== null) {
      const t = stripTags(m[1]);
      if (t) out[level].push(t);
    }
  }
  return out;
}

export function extractCanonical(html) {
  const m = String(html ?? '').match(/<link[^>]+rel\s*=\s*["']canonical["'][^>]*href\s*=\s*["']([^"']*)["']/i)
    ?? String(html ?? '').match(/<link[^>]+href\s*=\s*["']([^"']*)["'][^>]*rel\s*=\s*["']canonical["']/i);
  return m ? m[1].trim() : null;
}

export function analyseImages(html) {
  const imgs = String(html ?? '').match(/<img\b[^>]*>/gi) ?? [];
  const missingAlt = imgs.filter((tag) => !/\balt\s*=\s*["'][^"']+["']/i.test(tag)).length;
  return { total: imgs.length, missingAlt };
}

export function analyseLinks(html, baseUrl) {
  const src = String(html ?? '');
  const hrefs = [...src.matchAll(/<a\b[^>]*href\s*=\s*["']([^"']+)["']/gi)].map((m) => m[1]);
  let internal = 0;
  let external = 0;
  let host = null;
  try {
    host = new URL(baseUrl).hostname;
  } catch {
    /* base unusable; treat everything absolute as external */
  }
  for (const h of hrefs) {
    if (/^(mailto:|tel:|javascript:|#)/i.test(h)) continue;
    try {
      const abs = new URL(h, baseUrl);
      if (host && abs.hostname === host) internal += 1;
      else external += 1;
    } catch {
      /* unparseable href */
    }
  }
  return { total: hrefs.length, internal, external };
}

export function countWords(html) {
  const text = stripTags(html);
  if (!text) return 0;
  return text.split(/\s+/).filter(Boolean).length;
}

// Deductions are stated so the score is explainable, not a black box.
export function scorePage(f) {
  const issues = [];
  let score = 100;

  const ded = (points, msg) => {
    score -= points;
    issues.push(msg);
  };

  if (!f.title) ded(15, 'Missing <title>');
  else if (f.titleLength < 30) ded(5, `Title is short (${f.titleLength} chars, aim 30-60)`);
  else if (f.titleLength > 60) ded(5, `Title is long (${f.titleLength} chars, aim 30-60)`);

  if (!f.metaDescription) ded(12, 'Missing meta description');
  else if (f.metaDescriptionLength < 70) ded(4, `Meta description is short (${f.metaDescriptionLength} chars, aim 70-160)`);
  else if (f.metaDescriptionLength > 160) ded(4, `Meta description is long (${f.metaDescriptionLength} chars, aim 70-160)`);

  if (f.h1Count === 0) ded(10, 'No <h1> on the page');
  else if (f.h1Count > 1) ded(5, `${f.h1Count} <h1> tags (expected exactly 1)`);

  if (!f.canonical) ded(5, 'No canonical link');
  if (!f.https) ded(15, 'Page is not served over HTTPS');
  if (!f.viewport) ded(8, 'No viewport meta tag (not mobile friendly)');
  if (!f.langAttr) ded(3, 'No lang attribute on <html>');

  if (f.imagesMissingAlt > 0) {
    ded(Math.min(10, f.imagesMissingAlt), `${f.imagesMissingAlt} image(s) missing alt text`);
  }
  if (f.wordCount < 300) ded(8, `Thin content (${f.wordCount} words, aim 300+)`);
  if (!f.ogTitle && !f.ogDescription) ded(4, 'No Open Graph tags (poor social previews)');
  if (f.statusCode >= 400) ded(30, `HTTP ${f.statusCode}`);
  if (f.responseTimeMs > 3000) ded(6, `Slow response (${f.responseTimeMs}ms)`);
  if (f.noindex) ded(20, 'Page is marked noindex');

  return { score: Math.max(0, Math.min(100, score)), issues };
}

export async function auditUrl(rawUrl, { timeoutMs = 15000, userAgent = UA } = {}) {
  const norm = normaliseUrl(rawUrl);
  if (!norm.ok) {
    return { input: String(rawUrl ?? ''), url: null, ok: false, reason: norm.reason };
  }
  const url = norm.url;

  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  const startedAt = Date.now();

  try {
    const res = await fetch(url, {
      signal: ctl.signal,
      redirect: 'follow',
      headers: { 'user-agent': userAgent, accept: 'text/html,application/xhtml+xml' },
    });
    const responseTimeMs = Date.now() - startedAt;
    const html = await res.text();

    const headings = extractHeadings(html);
    const images = analyseImages(html);
    const links = analyseLinks(html, res.url || url);
    const title = extractTitle(html);
    const metaDescription = extractMeta(html, 'description');
    const robots = extractMeta(html, 'robots');
    const canonical = extractCanonical(html);
    const viewport = extractMeta(html, 'viewport');
    const ogTitle = extractMeta(html, 'og:title');
    const ogDescription = extractMeta(html, 'og:description');
    const langAttr = /<html[^>]+lang\s*=\s*["']([^"']+)["']/i.exec(html)?.[1] ?? null;
    const wordCount = countWords(html);

    const facts = {
      statusCode: res.status,
      https: new URL(res.url || url).protocol === 'https:',
      title,
      titleLength: title?.length ?? 0,
      metaDescription,
      metaDescriptionLength: metaDescription?.length ?? 0,
      h1Count: headings.h1.length,
      canonical,
      viewport,
      langAttr,
      imagesMissingAlt: images.missingAlt,
      wordCount,
      ogTitle,
      ogDescription,
      responseTimeMs,
      noindex: /noindex/i.test(robots ?? ''),
    };

    const { score, issues } = scorePage(facts);

    return {
      input: String(rawUrl ?? ''),
      url: res.url || url,
      ok: true,
      score,
      issueCount: issues.length,
      issues,
      statusCode: res.status,
      redirected: (res.url || url) !== url,
      https: facts.https,
      responseTimeMs,
      title,
      titleLength: facts.titleLength,
      metaDescription,
      metaDescriptionLength: facts.metaDescriptionLength,
      h1: headings.h1.slice(0, 5),
      h1Count: headings.h1.length,
      h2Count: headings.h2.length,
      h3Count: headings.h3.length,
      canonical,
      robots,
      noindex: facts.noindex,
      viewport,
      langAttr,
      ogTitle,
      ogDescription,
      images: images.total,
      imagesMissingAlt: images.missingAlt,
      links: links.total,
      internalLinks: links.internal,
      externalLinks: links.external,
      wordCount,
      contentType: res.headers.get('content-type') ?? null,
      checkedAt: new Date().toISOString(),
    };
  } catch (err) {
    const reason = err.name === 'AbortError' ? `Request timed out after ${timeoutMs}ms` : err.message;
    return { input: String(rawUrl ?? ''), url, ok: false, reason, checkedAt: new Date().toISOString() };
  } finally {
    clearTimeout(timer);
  }
}

export async function mapLimit(items, limit, fn) {
  const out = new Array(items.length);
  let i = 0;
  const workers = new Array(Math.min(limit, items.length)).fill(null).map(async () => {
    while (i < items.length) {
      const idx = i++;
      out[idx] = await fn(items[idx], idx);
    }
  });
  await Promise.all(workers);
  return out;
}
