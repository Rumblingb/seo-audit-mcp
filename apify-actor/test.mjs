import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  normaliseUrl, stripTags, extractTitle, extractMeta, extractHeadings,
  extractCanonical, analyseImages, analyseLinks, countWords, scorePage, mapLimit,
} from './lib.js';

const PAGE = `
<!doctype html>
<html lang="en">
<head>
  <title>  A Reasonable Page Title For Testing  </title>
  <meta name="description" content="A meta description that is long enough to be sensible and pass the length check comfortably here.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta property="og:title" content="OG Title">
  <link rel="canonical" href="https://example.com/page">
  <style>.x { color: red }</style>
</head>
<body>
  <h1>Only Heading</h1>
  <h2>Sub A</h2><h2>Sub B</h2>
  <h3>Deep</h3>
  <img src="a.png" alt="described">
  <img src="b.png">
  <img src="c.png" alt="">
  <a href="/internal">in</a>
  <a href="https://example.com/also-internal">in2</a>
  <a href="https://other.com/out">out</a>
  <a href="mailto:x@y.com">mail</a>
  <script>var ignored = "text in script";</script>
  <p>Some visible words here.</p>
</body>
</html>`;

test('normaliseUrl assumes https for a bare domain', () => {
  const r = normaliseUrl('example.com');
  assert.equal(r.ok, true);
  assert.ok(r.url.startsWith('https://example.com'));
});

test('normaliseUrl keeps an explicit http scheme', () => {
  assert.ok(normaliseUrl('http://example.com').url.startsWith('http://'));
});

test('normaliseUrl rejects a non-http scheme', () => {
  assert.equal(normaliseUrl('ftp://example.com').ok, false);
});

test('normaliseUrl rejects empty input', () => {
  assert.equal(normaliseUrl('  ').ok, false);
});

test('normaliseUrl rejects a hostname with no TLD', () => {
  assert.equal(normaliseUrl('localhost').ok, false);
});

test('extractTitle trims surrounding whitespace', () => {
  assert.equal(extractTitle(PAGE), 'A Reasonable Page Title For Testing');
});

test('extractTitle returns null when absent', () => {
  assert.equal(extractTitle('<html><head></head></html>'), null);
});

test('extractMeta reads a name= meta tag', () => {
  assert.ok(extractMeta(PAGE, 'description').startsWith('A meta description'));
});

test('extractMeta reads a property= meta tag', () => {
  assert.equal(extractMeta(PAGE, 'og:title'), 'OG Title');
});

test('extractMeta handles content before name in attribute order', () => {
  const html = '<meta content="reversed order" name="description">';
  assert.equal(extractMeta(html, 'description'), 'reversed order');
});

test('extractMeta returns null for a missing tag', () => {
  assert.equal(extractMeta(PAGE, 'twitter:card'), null);
});

test('extractHeadings counts each level', () => {
  const h = extractHeadings(PAGE);
  assert.equal(h.h1.length, 1);
  assert.equal(h.h2.length, 2);
  assert.equal(h.h3.length, 1);
  assert.equal(h.h1[0], 'Only Heading');
});

test('extractCanonical finds the canonical href', () => {
  assert.equal(extractCanonical(PAGE), 'https://example.com/page');
});

test('analyseImages counts images missing alt, treating empty alt as missing', () => {
  const i = analyseImages(PAGE);
  assert.equal(i.total, 3);
  assert.equal(i.missingAlt, 2);
});

test('analyseLinks splits internal from external and skips mailto', () => {
  const l = analyseLinks(PAGE, 'https://example.com/page');
  assert.equal(l.internal, 2);
  assert.equal(l.external, 1);
});

test('stripTags removes script and style content', () => {
  const t = stripTags(PAGE);
  assert.ok(!t.includes('text in script'));
  assert.ok(!t.includes('color: red'));
  assert.ok(t.includes('Some visible words here.'));
});

test('countWords ignores markup', () => {
  assert.ok(countWords('<p>one two three</p>') === 3);
});

test('scorePage returns 100 for a clean page', () => {
  const { score, issues } = scorePage({
    statusCode: 200, https: true, title: 'x'.repeat(45), titleLength: 45,
    metaDescription: 'y'.repeat(120), metaDescriptionLength: 120, h1Count: 1,
    canonical: 'https://example.com', viewport: 'width=device-width', langAttr: 'en',
    imagesMissingAlt: 0, wordCount: 800, ogTitle: 'a', ogDescription: 'b',
    responseTimeMs: 400, noindex: false,
  });
  assert.equal(score, 100);
  assert.equal(issues.length, 0);
});

test('scorePage penalises a missing title and reports why', () => {
  const { score, issues } = scorePage({
    statusCode: 200, https: true, title: null, titleLength: 0,
    metaDescription: 'y'.repeat(120), metaDescriptionLength: 120, h1Count: 1,
    canonical: 'c', viewport: 'v', langAttr: 'en', imagesMissingAlt: 0,
    wordCount: 800, ogTitle: 'a', ogDescription: 'b', responseTimeMs: 400, noindex: false,
  });
  assert.equal(score, 85);
  assert.ok(issues.some((i) => /Missing <title>/.test(i)));
});

test('scorePage never returns below zero', () => {
  const { score } = scorePage({
    statusCode: 500, https: false, title: null, titleLength: 0,
    metaDescription: null, metaDescriptionLength: 0, h1Count: 0,
    canonical: null, viewport: null, langAttr: null, imagesMissingAlt: 50,
    wordCount: 10, ogTitle: null, ogDescription: null, responseTimeMs: 9000, noindex: true,
  });
  assert.ok(score >= 0, `score was ${score}`);
});

test('scorePage flags multiple h1 tags', () => {
  const { issues } = scorePage({
    statusCode: 200, https: true, title: 'x'.repeat(45), titleLength: 45,
    metaDescription: 'y'.repeat(120), metaDescriptionLength: 120, h1Count: 3,
    canonical: 'c', viewport: 'v', langAttr: 'en', imagesMissingAlt: 0,
    wordCount: 800, ogTitle: 'a', ogDescription: 'b', responseTimeMs: 400, noindex: false,
  });
  assert.ok(issues.some((i) => /3 <h1> tags/.test(i)));
});

test('mapLimit preserves order', async () => {
  const out = await mapLimit([40, 5, 20], 2, async (d, i) => {
    await new Promise((r) => setTimeout(r, d));
    return i;
  });
  assert.deepEqual(out, [0, 1, 2]);
});
