import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const README_PATH = path.resolve(__dirname, '../README.md');
const OUT_DIR = path.resolve(__dirname, 'public');
const OUT_FILE = path.resolve(OUT_DIR, 'data.json');
const SITE_URL = 'https://www.rectg.com';

function main() {
    const content = fs.readFileSync(README_PATH, 'utf-8');
    const maintenancePath = path.join(OUT_DIR, 'maintenance.json');
    const maintenance = fs.existsSync(maintenancePath) ? JSON.parse(fs.readFileSync(maintenancePath, 'utf-8')).resources : {};
    const lines = content.split('\n');

    const data = {
        categories: [],
        types: []
    };

    let currentType = null;
    let currentCategory = null;
    let currentItem = null;
    let currentItemProps = [];
    const categorySet = new Set();
    const categoriesList = [];
    const typeMap = {};

    function cleanMarkdownText(text) {
        return text
            .replace(/\\([\[\]])/g, '$1')
            .trim();
    }

    function extractDesc(descCell) {
        return cleanMarkdownText(descCell.replace(/<!--.*?-->/g, '').trim());
    }

    function getTelegramParts(url) {
        const trimmed = (url || '').trim();
        const match = trimmed.match(/^(https?:\/\/)(?:www\.)?(t\.me|telegram\.me)\/([^?#]+)([?#].*)?$/i);
        if (!match) return null;

        const pathParts = match[3].split('/').filter(Boolean);
        if (!pathParts.length) return null;

        const firstPart = pathParts[0];
        const firstPartLower = firstPart.toLowerCase();
        const isJoinchat = firstPartLower === 'joinchat';
        const isPrivateChannel = firstPartLower === 'c';
        const isInvite = isJoinchat || firstPart.startsWith('+') || isPrivateChannel;
        const canonicalParts = [...pathParts];
        let idPart = firstPart;

        if (isJoinchat && pathParts[1]) {
            idPart = `joinchat-${pathParts[1]}`;
        } else if (isPrivateChannel && pathParts[1]) {
            idPart = `c-${pathParts[1]}`;
        } else if (!isInvite) {
            canonicalParts[0] = firstPart.toLowerCase();
            idPart = canonicalParts[0];
        }

        return {
            id: idPart.replace(/[^a-zA-Z0-9_\-]/g, '').toLowerCase(),
            url: `https://t.me/${canonicalParts.join('/')}${match[4] || ''}`,
        };
    }

    function getItemId(title, url) {
        const telegram = getTelegramParts(url);
        if (telegram?.id) return telegram.id;
        return title.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '').toLowerCase();
    }

    function normalizeItem(item) {
        if (!item) return item;
        const telegram = getTelegramParts(item.url);
        return {
            ...item,
            countCheckedAt: maintenance?.[telegram?.id || item.id]?.countCheckedAt || null,
            countStale: maintenance?.[telegram?.id || item.id]?.countStale === true,
            reviewPending: maintenance?.[telegram?.id || item.id]?.reviewPending !== false,
            listConflict: maintenance?.[telegram?.id || item.id]?.listConflict === true,
            url: telegram?.url || item.url,
            id: telegram?.id || item.id || getItemId(item.title || '', item.url || ''),
        };
    }

    function siteUrl(pathname = '/') {
        return new URL(pathname, SITE_URL).href;
    }

    function categoryUrl(categoryId) {
        return siteUrl(`/category/${encodeURIComponent(categoryId)}/`);
    }

    function itemUrl(itemId) {
        return siteUrl(`/p/${encodeURIComponent(itemId)}/`);
    }

    function escapeXml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&apos;');
    }

    function parseTableRow(rawLine) {
        const trimmed = rawLine.trim();
        if (
            !trimmed.startsWith('|') ||
            trimmed === '| --- | --- | ---: | --- |' ||
            trimmed === '| --- | ---: | --- |' ||
            trimmed === '| 名称 | 链接 | 订阅数 | 简介 |' ||
            trimmed === '| 名称 | 链接 | 人数 | 简介 |' ||
            trimmed === '| 资源 | 人数 | 简介 |'
        ) {
            return null;
        }

        const parts = trimmed
            .split('|')
            .slice(1, -1)
            .map(part => part.trim());

        if (parts.length < 3) {
            return null;
        }

        let title;
        let url;
        let countStr;
        let desc;

        if (parts.length >= 4) {
            const [titleCell, linkCell, countCell, descCell] = parts;
            const urlMatch = linkCell.match(/\[(.*?)\]\((.*?)\)/);
            if (!urlMatch) {
                return null;
            }
            title = cleanMarkdownText(titleCell);
            url = urlMatch[2];
            countStr = countCell;
            desc = descCell;
        } else {
            const [resourceCell, countCell, descCell] = parts;
            const resourceMatch = resourceCell.match(/\[(.*?)\]\((.*?)\)/);
            if (!resourceMatch) {
                return null;
            }
            title = cleanMarkdownText(resourceMatch[1]);
            url = resourceMatch[2];
            countStr = countCell;
            desc = descCell;
        }

        const parsedDesc = extractDesc(desc);

        return normalizeItem({
            title,
            url,
            countStr,
            desc: parsedDesc === '-' ? '' : parsedDesc,
            id: getItemId(title, url)
        });
    }

    function pushCurrentItem() {
        if (currentItem && currentType && currentCategory) {
            typeMap[currentType][currentCategory].push(normalizeItem(currentItem));
            currentItem = null;
        }
    }

    const seoKeywords = {
        "新闻快讯": "吃瓜播报 一手资讯 热点追踪 国际新闻",
        "加密货币": "区块链资讯 Web3 新闻 市场动态",
        "影视剧集": "影视资讯 剧集推荐 观影讨论"
    };

    for (const rawLine of lines) {
        if (!rawLine.trim()) {
            pushCurrentItem();
            continue;
        }

        if (rawLine.startsWith('## ') && !rawLine.startsWith('### ') && ['## 频道', '## 群组', '## 机器人'].includes(rawLine.trim())) {
            currentType = rawLine.substring(3).trim();
            if (!typeMap[currentType]) typeMap[currentType] = {};
            currentCategory = null;
            currentItem = null;
        } else if (rawLine.startsWith('### ')) {
            const fullCat = rawLine.substring(4).trim();
            currentCategory = fullCat;
            if (currentType && !typeMap[currentType][currentCategory]) {
                typeMap[currentType][currentCategory] = [];
            }
            if (!categorySet.has(fullCat)) {
                categorySet.add(fullCat);
                // Extract icon and name (e.g. "📰 新闻快讯" -> icon: "📰", name: "新闻快讯")
                // Use a simpler regex that splits by the first whitespace to safely handle compound ZWJ emojis
                const match = fullCat.match(/^(\S+)\s+(.*)$/);
                if (match) {
                    const catName = match[2].trim();
                    categoriesList.push({
                        icon: match[1],
                        name: catName,
                        fullName: fullCat,
                        keywords: seoKeywords[catName] || "",
                        id: catName.toLowerCase()
                    });
                } else {
                    categoriesList.push({ icon: '📌', name: fullCat, fullName: fullCat, keywords: seoKeywords[fullCat.trim()] || "", id: fullCat.trim() });
                }
            }
            currentItem = null;
        } else if (rawLine.startsWith('| ') && currentType && currentCategory) {
            const tableItem = parseTableRow(rawLine);
            if (tableItem) {
                typeMap[currentType][currentCategory].push(tableItem);
            }
        } else if (rawLine.startsWith('- ')) {
            pushCurrentItem();
            const title = rawLine.substring(2).trim();
            currentItem = { title, desc: '' };
            currentItem.id = getItemId(title, '');
            currentItemProps = [];
        } else if (rawLine.startsWith('  - ') && currentItem) {
            currentItemProps.push(rawLine.substring(4).trim());
            if (currentItemProps.length === 1) {
                currentItem.typeLabel = currentItemProps[0];
            } else if (currentItemProps.length === 2) {
                const urlMatch = currentItemProps[1].match(/\[.*?\]\((.*?)\)/);
                currentItem.url = urlMatch ? urlMatch[1] : '';
                currentItem.id = getItemId(currentItem.title, currentItem.url);
            } else if (currentItemProps.length === 3) {
                currentItem.countStr = currentItemProps[2];
            } else if (currentItemProps.length === 4) {
                currentItem.desc = currentItemProps[3];
            }
        }
    }
    pushCurrentItem();

    data.categories = categoriesList;

    const seenItems = new Set();
    let duplicateCount = 0;

    Object.keys(typeMap).forEach(type => {
        Object.keys(typeMap[type]).forEach(catFullName => {
            typeMap[type][catFullName] = typeMap[type][catFullName].filter(item => {
                const normalized = normalizeItem(item);
                const key = normalized.id || `${normalized.title}:${normalized.url}`;
                if (seenItems.has(key)) {
                    duplicateCount += 1;
                    return false;
                }
                seenItems.add(key);
                Object.assign(item, normalized);
                return true;
            });
        });
    });

    // Sort categories list based on existing sequence, or just leave as is (it matches README)
    // Flatten types map
    data.types = Object.keys(typeMap).map(type => {
        return {
            name: type,
            categories: Object.keys(typeMap[type]).map(catFullName => {
                return {
                    fullName: catFullName,
                    items: typeMap[type][catFullName]
                };
            }).filter(c => c.items.length > 0)
        };
    }).filter(t => t.categories.length > 0);

    if (!fs.existsSync(OUT_DIR)) {
        fs.mkdirSync(OUT_DIR, { recursive: true });
    }
    fs.writeFileSync(OUT_FILE, JSON.stringify(data, null, 2));
    console.log(`✅ Generated data.json with ${data.categories.length} categories.`);
    if (duplicateCount > 0) {
        console.log(`ℹ️ Removed ${duplicateCount} duplicate Telegram resources.`);
    }

    const sourceLastmod = fs.statSync(README_PATH).mtime.toISOString().slice(0, 10);
    const sitemapEntries = [
        {
            loc: siteUrl('/'),
            changefreq: 'daily',
            priority: '1.0',
        },
        ...data.categories.map(category => ({
            loc: categoryUrl(category.id),
            changefreq: 'weekly',
            priority: '0.9',
        })),
    ];

    data.types.forEach(t => {
        t.categories.forEach(c => {
            c.items.forEach(item => {
                if (item.id) {
                    sitemapEntries.push({
                        loc: itemUrl(item.id),
                        changefreq: 'weekly',
                        priority: '0.8',
                    });
                }
            });
        });
    });

    const sitemapUrls = sitemapEntries.map(entry => `  <url>
    <loc>${escapeXml(entry.loc)}</loc>
    <lastmod>${sourceLastmod}</lastmod>
    <changefreq>${entry.changefreq}</changefreq>
    <priority>${entry.priority}</priority>
  </url>`).join('\n');

    const sitemapContent = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${sitemapUrls}
</urlset>`;
    const sitemapPath = path.resolve(OUT_DIR, 'sitemap.xml');
    fs.writeFileSync(sitemapPath, sitemapContent, 'utf-8');
    console.log(`✅ Generated sitemap.xml at ${sitemapPath}`);

    // Generate Robots.txt
    const robotsContent = `User-agent: *
Allow: /

Sitemap: https://www.rectg.com/sitemap.xml`;
    const robotsPath = path.resolve(OUT_DIR, 'robots.txt');
    fs.writeFileSync(robotsPath, robotsContent, 'utf-8');
    console.log(`✅ Generated robots.txt at ${robotsPath}`);

    const categoryCounts = new Map();
    data.types.forEach(type => {
        type.categories.forEach(category => {
            const previous = categoryCounts.get(category.fullName) || { count: 0, types: [] };
            categoryCounts.set(category.fullName, {
                count: previous.count + category.items.length,
                types: [
                    ...previous.types,
                    `${type.name} ${category.items.length}`,
                ],
            });
        });
    });

    const llmsCategories = data.categories.map(category => {
        const stats = categoryCounts.get(category.fullName);
        const typeText = stats?.types?.length ? `，${stats.types.join('，')}` : '';
        return `- ${category.fullName}: ${categoryUrl(category.id)}，共 ${stats?.count || 0} 个资源${typeText}`;
    }).join('\n');

    const llmsContent = `# rectg

rectg 是一个中文 Telegram 频道、群组和机器人资源索引站，整理公开可访问的 Telegram 资源，方便用户按主题浏览、关键词搜索并跳转到 Telegram。

## 主要入口

- 首页: ${siteUrl('/')}
- 分类目录: ${siteUrl('/')} 和各分类静态页面
- 提交收录: https://github.com/jackvale/rectg/issues/new?template=channel-submission.md
- GitHub: https://github.com/jackvale/rectg
- 数据文件: ${siteUrl('/data.json')}
- Sitemap: ${siteUrl('/sitemap.xml')}

## 分类目录

${llmsCategories}

## 数据说明

- 当前公开目录共 ${data.types.reduce((sum, type) => sum + type.categories.reduce((inner, category) => inner + category.items.length, 0), 0)} 个资源。
- 每个资源通常包含名称、Telegram 链接、订阅数或成员数、简介、类型和分类。
- 订阅数或成员数仅作浏览参考，可能随 Telegram 实际数据变化。
- 目录数据来自 README 生成流程，站点不手工维护 public/data.json。

## 收录原则与免责声明

rectg 只整理公开信息，优先收录有明确主题、简介和稳定链接的资源。广告刷量、违法内容和成人内容不作为推荐方向。用户应自行判断资源风险，并遵守所在地区法律法规。
`;
    const llmsPath = path.resolve(OUT_DIR, 'llms.txt');
    fs.writeFileSync(llmsPath, llmsContent, 'utf-8');
    console.log(`✅ Generated llms.txt at ${llmsPath}`);
}

main();
