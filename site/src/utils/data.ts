import fs from 'fs';
import path from 'path';

export const SITE_URL = 'https://www.rectg.com';

export function absoluteUrl(pathname = '/'): string {
  return new URL(pathname, SITE_URL).href;
}

export function categoryPath(categoryId: string): string {
  return `/category/${encodeURIComponent(categoryId)}/`;
}

export function itemPath(itemId: string): string {
  return `/p/${encodeURIComponent(itemId)}/`;
}

export interface CategoryMeta {
  icon: string;
  name: string;
  fullName: string;
  keywords?: string;
  id: string;
}

export interface RawItem {
  title: string;
  url: string;
  countStr: string;
  desc: string;
  id: string;
}

export interface DirectoryItem extends RawItem {
  typeName: string;
  categoryId: string;
  categoryName: string;
  categoryFullName: string;
  categoryIcon: string;
  categoryKeywords: string;
}

export interface TypeGroup {
  name: string;
  categories: Array<{
    fullName: string;
    items: RawItem[];
  }>;
}

export interface SiteData {
  categories: CategoryMeta[];
  types: TypeGroup[];
}

export interface CategoryGroup {
  meta: CategoryMeta;
  items: DirectoryItem[];
}

export interface DirectoryData {
  data: SiteData;
  categories: CategoryMeta[];
  validSections: CategoryGroup[];
  allItems: DirectoryItem[];
  featuredItems: DirectoryItem[];
  totalItems: number;
  typeStats: Array<{ name: string; count: number }>;
}

export interface DetailLinkItem {
  id: string;
  title: string;
  typeName: string;
  countStr: string;
  categoryName: string;
}

export function loadSiteData(): SiteData {
  const dataPath = path.resolve(process.cwd(), 'public/data.json');
  return JSON.parse(fs.readFileSync(dataPath, 'utf-8')) as SiteData;
}

export function parseCount(countStr?: string): number {
  if (!countStr || countStr === '-') return 0;
  const parsed = Number.parseInt(countStr.replace(/,/g, ''), 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function hashText(value: string): number {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function getFeaturedItems(items: DirectoryItem[], size = 18): DirectoryItem[] {
  return [...items]
    .sort((a, b) => {
      const scoreA = hashText(`${a.id}:${a.title}:featured`);
      const scoreB = hashText(`${b.id}:${b.title}:featured`);
      return Number(b.id === 'fanren4k') - Number(a.id === 'fanren4k') || scoreA - scoreB;
    })
    .slice(0, size);
}

export function buildDirectoryData(data = loadSiteData()): DirectoryData {
  const categoryGroups = new Map<string, CategoryGroup>();

  data.categories.forEach((category) => {
    categoryGroups.set(category.id, { meta: category, items: [] });
  });

  data.types.forEach((typeObj) => {
    typeObj.categories.forEach((catObj) => {
      const catMeta = data.categories.find((category) => category.fullName === catObj.fullName);
      if (!catMeta) return;

      const group = categoryGroups.get(catMeta.id);
      if (!group) return;

      group.items.push(
        ...catObj.items.map((item) => ({
          ...item,
          typeName: typeObj.name,
          categoryId: catMeta.id,
          categoryName: catMeta.name,
          categoryFullName: catMeta.fullName,
          categoryIcon: catMeta.icon,
          categoryKeywords: catMeta.keywords || '',
        })),
      );
    });
  });

  const validSections = [...categoryGroups.values()]
    .filter((group) => group.items.length > 0)
    .map((group) => ({
      ...group,
      items: [...group.items].sort((a, b) => Number(b.id === 'fanren4k') - Number(a.id === 'fanren4k') || parseCount(b.countStr) - parseCount(a.countStr)),
    }));

  const allItems = validSections.flatMap((group) => group.items);
  const typeStats = data.types
    .map((typeObj) => ({
      name: typeObj.name,
      count: typeObj.categories.reduce((sum, category) => sum + category.items.length, 0),
    }))
    .filter((stat) => stat.count > 0);

  return {
    data,
    categories: data.categories,
    validSections,
    allItems,
    featuredItems: getFeaturedItems(allItems),
    totalItems: allItems.length,
    typeStats,
  };
}

export function getItemPaths(data = loadSiteData()) {
  const paths: Array<{
    params: { id: string };
    props: {
      item: DirectoryItem;
      categoryName: string;
      categoryFullName: string;
      typeName: string;
      previousItem: DetailLinkItem | null;
      nextItem: DetailLinkItem | null;
      relatedItems: DetailLinkItem[];
    };
  }> = [];
  const seen = new Set<string>();

  buildDirectoryData(data).validSections.forEach((section) => {
    const compactItem = (candidate?: DirectoryItem): DetailLinkItem | null => {
      if (!candidate) return null;
      return {
        id: candidate.id,
        title: candidate.title,
        typeName: candidate.typeName,
        countStr: candidate.countStr,
        categoryName: candidate.categoryName,
      };
    };

    section.items.forEach((item, index) => {
      if (!item.id || seen.has(item.id)) return;
      seen.add(item.id);
      paths.push({
        params: { id: item.id },
        props: {
          item,
          categoryName: item.categoryName,
          categoryFullName: item.categoryFullName,
          typeName: item.typeName,
          previousItem: compactItem(section.items[index - 1]),
          nextItem: compactItem(section.items[index + 1]),
          relatedItems: section.items
            .filter((candidate) => candidate.id !== item.id)
            .slice(0, 4)
            .map((candidate) => compactItem(candidate))
            .filter((candidate): candidate is DetailLinkItem => Boolean(candidate)),
        },
      });
    });
  });

  return paths;
}

export function getCategoryPaths(data = loadSiteData()) {
  return buildDirectoryData(data).validSections.map((section) => ({
    params: { id: section.meta.id },
    props: {
      section,
      totalItems: section.items.length,
      channelCount: section.items.filter((item) => item.typeName === '频道').length,
      groupCount: section.items.filter((item) => item.typeName === '群组').length,
    },
  }));
}

export function getTelegramUsername(url?: string): string {
  if (!url || !url.includes('t.me/')) return '';
  const parts = url.split('t.me/');
  return parts[1]?.split('/')[0]?.split('?')[0] || '';
}

export function getAvatarColorClass(value?: string): string {
  const source = value || '?';
  return `avatar-color-${hashText(source) % 6}`;
}
