import fs from 'fs';
import path from 'path';

const SITE_URL = 'https://www.rectg.com';
const dataPath = path.resolve('public/data.json');
const data = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
const items = [];

for (const type of data.types || []) {
  for (const category of type.categories || []) {
    for (const item of category.items || []) {
      items.push({
        ...item,
        typeName: type.name,
        categoryName: category.fullName,
      });
    }
  }
}

const idCounts = new Map();
const urlCounts = new Map();
const invalidItems = [];

for (const item of items) {
  if (!item.id || !item.title || !item.url) invalidItems.push(item);
  idCounts.set(item.id, (idCounts.get(item.id) || 0) + 1);
  urlCounts.set(item.url.toLowerCase(), (urlCounts.get(item.url.toLowerCase()) || 0) + 1);
}

const duplicateIds = [...idCounts.entries()].filter(([, count]) => count > 1);
const duplicateUrls = [...urlCounts.entries()].filter(([, count]) => count > 1);
const sitemapPath = path.resolve('public/sitemap.xml');
const sitemap = fs.readFileSync(sitemapPath, 'utf-8');
const sitemapUrls = [...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map((match) => match[1]);
const categoryUrls = (data.categories || []).map((category) => `${SITE_URL}/category/${encodeURIComponent(category.id)}/`);
const detailUrls = items.map((item) => `${SITE_URL}/p/${encodeURIComponent(item.id)}/`);
const expectedSitemapUrls = [`${SITE_URL}/`, ...categoryUrls, ...detailUrls];
const missingSitemapUrls = expectedSitemapUrls.filter((url) => !sitemapUrls.includes(url));
const llmsPath = path.resolve('public/llms.txt');
const llms = fs.existsSync(llmsPath) ? fs.readFileSync(llmsPath, 'utf-8') : '';
const llmsFailures = [];

if (!llms.includes('rectg')) llmsFailures.push('llms.txt missing rectg summary');
if (!llms.includes('## 分类目录')) llmsFailures.push('llms.txt missing category directory');
if (!llms.includes('提交收录')) llmsFailures.push('llms.txt missing submission link');

function existingHtmlPath(...candidates) {
  const found = candidates.map((candidate) => path.resolve(candidate)).find((candidate) => fs.existsSync(candidate));
  return found || path.resolve(candidates[0]);
}

function parseJsonLdFromHtml(filePath) {
  if (!fs.existsSync(filePath)) return [`Missing built HTML: ${path.relative(process.cwd(), filePath)}`];

  const html = fs.readFileSync(filePath, 'utf-8');
  const matches = [...html.matchAll(/<script[^>]+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)];
  if (!matches.length) return [`No JSON-LD script in ${path.relative(process.cwd(), filePath)}`];

  const failures = [];
  matches.forEach((match, index) => {
    try {
      JSON.parse(match[1]);
    } catch (error) {
      failures.push(`Invalid JSON-LD #${index + 1} in ${path.relative(process.cwd(), filePath)}: ${error.message}`);
    }
  });
  return failures;
}

const jsonLdFailures = [
  existingHtmlPath('dist/index.html'),
  ...(data.categories || []).map((category) => existingHtmlPath(
    `dist/category/${category.id}/index.html`,
    `dist/category/${encodeURIComponent(category.id)}/index.html`,
  )),
  ...items.map((item) => existingHtmlPath(
    `dist/p/${item.id}/index.html`,
    `dist/p/${encodeURIComponent(item.id)}/index.html`,
  )),
].flatMap((filePath) => parseJsonLdFromHtml(filePath));

if (
  invalidItems.length ||
  duplicateIds.length ||
  duplicateUrls.length ||
  sitemapUrls.length !== expectedSitemapUrls.length ||
  missingSitemapUrls.length ||
  llmsFailures.length ||
  jsonLdFailures.length
) {
  console.error(JSON.stringify({
    invalidItems: invalidItems.slice(0, 10),
    duplicateIds,
    duplicateUrls,
    sitemap: {
      actual: sitemapUrls.length,
      expected: expectedSitemapUrls.length,
      missing: missingSitemapUrls.slice(0, 10),
    },
    llmsFailures,
    jsonLdFailures,
  }, null, 2));
  process.exit(1);
}

console.log(`✅ data ok: ${items.length} resources, ${idCounts.size} unique ids`);
console.log(`✅ sitemap ok: ${sitemapUrls.length} urls`);
console.log('✅ llms ok');
console.log('✅ json-ld ok');
