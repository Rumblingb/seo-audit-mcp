import { Actor, log } from 'apify';
import { auditUrl, mapLimit } from './lib.js';

await Actor.init();

const input = (await Actor.getInput()) ?? {};
const {
  urls = [],
  timeoutMs = 15000,
  maxConcurrency = 5,
  userAgent = 'Mozilla/5.0 (compatible; SeoAuditActor/0.1; +https://apify.com)',
} = input;

const list = (Array.isArray(urls) ? urls : [urls])
  .map((u) => String(u ?? '').trim())
  .filter((u) => u.length > 0);

if (list.length === 0) {
  await Actor.fail('No URLs supplied. Provide a "urls" array with at least one entry.');
}

log.info(`Auditing ${list.length} URL(s) | concurrency=${maxConcurrency} timeout=${timeoutMs}ms`);

let done = 0;
const results = await mapLimit(list, Math.max(1, maxConcurrency), async (url) => {
  const result = await auditUrl(url, { timeoutMs, userAgent });
  await Actor.pushData(result);

  // Pay-per-event. No-ops when the Actor is not on a PPE pricing model.
  try {
    await Actor.charge({ eventName: 'page-audited' });
  } catch (err) {
    log.debug(`charge skipped: ${err.message}`);
  }

  done += 1;
  if (done % 25 === 0) log.info(`  ${done}/${list.length} audited`);
  return result;
});

const ok = results.filter((r) => r.ok);
const scores = ok.map((r) => r.score);
const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null;

const summary = {
  total: list.length,
  audited: ok.length,
  failed: results.length - ok.length,
  averageScore: avg,
  missingTitle: ok.filter((r) => !r.title).length,
  missingMetaDescription: ok.filter((r) => !r.metaDescription).length,
  missingH1: ok.filter((r) => r.h1Count === 0).length,
  notHttps: ok.filter((r) => !r.https).length,
  noindex: ok.filter((r) => r.noindex).length,
  thinContent: ok.filter((r) => r.wordCount < 300).length,
  finishedAt: new Date().toISOString(),
};

log.info(
  `Done. ${summary.audited}/${summary.total} audited | avg score ${summary.averageScore} | ` +
    `${summary.missingTitle} no title | ${summary.missingMetaDescription} no meta desc | ${summary.missingH1} no H1 | ${summary.noindex} noindex`,
);

await Actor.setValue('SUMMARY', summary);
await Actor.exit();
