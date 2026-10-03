import PinyinMatchModule from 'pinyin-match';
import { getSavedIds, readStorage, writeStorage, syncBookmarks } from './shared';

const PinyinMatch = PinyinMatchModule?.default || PinyinMatchModule;
const $ = selector => document.querySelector(selector);
const payload = JSON.parse($('#directory-data').textContent);
const sections = payload.sections;
const allItems = sections.flatMap(section => section.items);
const itemsById = new Map(allItems.map(item => [item.id, item]));
const featured = payload.featuredIds.map(id => itemsById.get(id)).filter(Boolean);
const pageSize = 24;
let visibleCount = pageSize;
let searchTimer;
let composing = false;
let state = readLocation();
let view = readStorage('rectg:view') === 'list' ? 'list' : 'grid';
let filteredItems = [];
let matchesById = new Map();
const grid = $('#active-grid');
const search = $('#search-input');
const mobile = matchMedia('(max-width: 800px)');
const sidebar = $('#sidebar');
let previousFocus;

function readLocation() {
  const params = new URLSearchParams(location.search);
  let routeCategory = '';
  try { routeCategory = decodeURIComponent(location.pathname.match(/^\/category\/([^/]+)/)?.[1] || ''); } catch { /* Fall back to the directory. */ }
  const requested = routeCategory || params.get('c') || 'featured';
  return {
    section: ['featured', 'all', 'saved'].includes(requested) || sections.some(section => section.id === requested) ? requested : 'featured',
    q: (params.get('q') || '').trim(),
    type: ['频道', '群组'].includes(params.get('type')) ? params.get('type') : 'all',
    sort: ['members', 'name'].includes(params.get('sort')) ? params.get('sort') : 'default',
  };
}

function updateLocation(replace = false) {
  const url = new URL(location.href);
  const isCategory = sections.some(section => section.id === state.section);
  url.pathname = isCategory ? `/category/${encodeURIComponent(state.section)}/` : '/';
  url.hash = '';
  for (const key of ['c', 'q', 'type', 'sort']) url.searchParams.delete(key);
  if (!isCategory && state.section !== 'featured') url.searchParams.set('c', state.section);
  if (state.q) url.searchParams.set('q', state.q);
  if (state.type !== 'all') url.searchParams.set('type', state.type);
  if (state.sort !== 'default') url.searchParams.set('sort', state.sort);
  if (url.href !== location.href) history[replace ? 'replaceState' : 'pushState']({}, '', url);
}

function highlight(element, value, range) {
  element.textContent = '';
  if (!range) { element.textContent = value; return; }
  const start = Math.max(0, range[0]);
  const end = Math.min(value.length, range[1] + 1);
  const mark = document.createElement('mark');
  mark.textContent = value.slice(start, end);
  element.append(value.slice(0, start), mark, value.slice(end));
}

function matchItem(item, rawQuery) {
  const query = rawQuery.toLowerCase().replace(/^@/, '');
  if (!query) return { score: 0 };
  const find = value => {
    const position = value.toLowerCase().indexOf(query);
    return position >= 0 ? [position, position + query.length - 1] : PinyinMatch.match(value, query) || null;
  };
  const title = find(item.title || '');
  const desc = find(item.desc || '');
  const url = item.url.toLowerCase().includes(query);
  const category = `${item.categoryName} ${item.categoryKeywords}`.toLowerCase().includes(query);
  if (!title && !desc && !url && !category) return null;
  return { title, desc, score: title ? (title[0] === 0 ? 0 : 1) : url ? 2 : category ? 3 : 4 };
}

function numericCount(item) { return Number.parseInt((item.countStr || '').replaceAll(',', ''), 10) || 0; }

function createCard(item) {
  const card = $('#card-template').content.firstElementChild.cloneNode(true);
  const match = matchesById.get(item.id);
  card.dataset.id = item.id;
  card.dataset.type = item.typeName;
  const title = card.querySelector('.card-title');
  title.href = `/p/${encodeURIComponent(item.id)}/`;
  title.title = item.title;
  highlight(title, item.title, match?.title);
  card.querySelector('.card-type').textContent = item.typeName;
  card.querySelector('.card-category').textContent = item.categoryName;
  highlight(card.querySelector('.card-desc'), item.desc || '暂无简介，前往 Telegram 了解更多。', match?.desc);
  card.querySelector('.resource-count strong').textContent = item.countStr || '—';
  card.querySelector('.resource-count span').textContent = item.typeName === '群组' ? '成员' : '订阅';
  const copy = card.querySelector('[data-copy-url]');
  copy.dataset.copyUrl = item.url;
  copy.setAttribute('aria-label', `复制 ${item.title} 的链接`);
  const direct = card.querySelector('.card-action-primary');
  direct.href = item.url;
  direct.setAttribute('aria-label', `在 Telegram 打开 ${item.title}`);
  const bookmark = card.querySelector('[data-bookmark]');
  bookmark.dataset.bookmark = item.id;
  const firstLetter = Array.from(item.title || '?')[0].toUpperCase();
  let hash = 2166136261;
  for (let i = 0; i < firstLetter.length; i++) { hash ^= firstLetter.charCodeAt(i); hash = Math.imul(hash, 16777619); }
  const avatar = card.querySelector('.card-icon');
  avatar.className = `card-icon avatar-color-${(hash >>> 0) % 6}`;
  card.querySelector('.avatar-letter').textContent = firstLetter;
  const username = item.url.match(/^https?:\/\/t\.me\/([a-zA-Z0-9_]+)(?:[/?#]|$)/)?.[1];
  if (username && !['joinchat', 'c'].includes(username)) {
    const image = document.createElement('img');
    Object.assign(image, { src: `https://unavatar.io/telegram/${username}`, alt: '', loading: 'lazy', decoding: 'async', width: 42, height: 42 });
    image.addEventListener('error', () => { image.hidden = true; }, { once: true });
    avatar.append(image);
  }
  return card;
}

function renderCards(appendFrom = 0) {
  const fragment = document.createDocumentFragment();
  filteredItems.slice(appendFrom, visibleCount).forEach(item => fragment.append(createCard(item)));
  if (appendFrom) grid.append(fragment); else grid.replaceChildren(fragment);
  syncBookmarks();
  $('#load-more-wrap').hidden = filteredItems.length <= visibleCount;
  $('#page-count').textContent = `已显示 ${Math.min(visibleCount, filteredItems.length)} / ${filteredItems.length} 个资源`;
  $('#load-more').firstChild.textContent = `再显示 ${Math.min(pageSize, Math.max(0, filteredItems.length - visibleCount))} 个 `;
  $('#results-end').hidden = !filteredItems.length || filteredItems.length > visibleCount;
  $('#results-end').textContent = `共 ${filteredItems.length} 个收录 · 人数仅供参考`;
  $('#results-announcement').textContent = `找到 ${filteredItems.length} 个资源，已显示 ${Math.min(visibleCount, filteredItems.length)} 个`;
}

function render() {
  const section = sections.find(section => section.id === state.section);
  const saved = getSavedIds();
  const source = section?.items || (state.section === 'saved' ? allItems.filter(item => saved.has(item.id)) : state.section === 'all' || state.q ? allItems : featured);
  matchesById = new Map();
  const matching = state.q ? source.filter(item => {
    const match = matchItem(item, state.q);
    if (match) matchesById.set(item.id, match);
    return Boolean(match);
  }) : source;
  filteredItems = matching.filter(item => state.type === 'all' || item.typeName === state.type);
  if (state.sort === 'name') filteredItems.sort((a, b) => a.title.localeCompare(b.title, 'zh-CN'));
  else if (state.sort === 'members') filteredItems.sort((a, b) => numericCount(b) - numericCount(a));
  else if (state.q) filteredItems.sort((a, b) => (matchesById.get(a.id)?.score || 0) - (matchesById.get(b.id)?.score || 0) || numericCount(b) - numericCount(a));

  const name = section?.name || ({ featured: '目录摘选', all: '全部收录', saved: '我的收藏' })[state.section];
  const searchScope = section?.name || (state.section === 'saved' ? '我的收藏' : '全部收录');
  $('#active-section-title').textContent = state.q ? '搜索结果' : name;
  $('#active-section-meta').textContent = filteredItems.length;
  $('#active-section-desc').textContent = state.q ? `在「${searchScope}」中搜索“${state.q}”` : section ? `浏览${section.name}相关的频道与群组。` : state.section === 'saved' ? '留住感兴趣的频道。收藏保存在当前浏览器中。' : state.section === 'all' ? `${allItems.length} 个公开频道与群组，按兴趣慢慢找。` : '换个方向逛逛，也许会有新发现。';
  $('#directory-intro').hidden = state.section !== 'featured' || Boolean(state.q);
  $('.category-title').setAttribute('aria-level', $('#directory-intro').hidden ? '1' : '2');
  $('#section-eyebrow').hidden = state.section === 'featured' && !state.q;
  $('#section-eyebrow').textContent = state.q ? '搜索目录' : section ? '主题目录' : '你的目录';
  $('#browse-all').hidden = state.section !== 'featured' || Boolean(state.q);
  $('#directory-about').hidden = state.section !== 'featured' || Boolean(state.q);
  $('#active-section').dataset.currentId = state.section;
  $('#sort-select').value = state.sort;
  search.placeholder = section ? `在${section.name}中搜索…` : state.section === 'saved' ? '在收藏中搜索…' : '搜索名称、简介或 t.me 地址';
  $('#clear-search-btn').hidden = !search.value;
  $('#search-shortcut').hidden = Boolean(search.value);
  document.title = state.q ? `搜索 ${state.q} - rectg` : `${section ? `${section.name} Telegram 频道和群组` : state.section === 'featured' ? 'Telegram 中文目录' : name} - rectg`;
  const canonical = document.querySelector('link[rel="canonical"]');
  if (canonical) canonical.href = `https://www.rectg.com${section ? `/category/${encodeURIComponent(section.id)}/` : '/'}`;
  document.querySelectorAll('[data-section]').forEach(link => {
    const selected = link.dataset.section === state.section;
    link.classList.toggle('active', selected);
    if (selected) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
  });
  document.querySelectorAll('[data-type]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.type === state.type)));
  document.querySelectorAll('[data-type-count]').forEach(count => {
    count.textContent = matching.filter(item => count.dataset.typeCount === 'all' || item.typeName === count.dataset.typeCount).length;
  });
  const hasConditions = Boolean(state.q) || state.type !== 'all' || state.sort !== 'default';
  $('#result-status').hidden = !hasConditions;
  $('#result-status-text').textContent = `${filteredItems.length} 个结果${state.type === 'all' ? '' : ` · 仅${state.type}`}`;
  $('#search-all-btn').hidden = !state.q || (!section && state.section !== 'saved');
  $('#empty-state').hidden = filteredItems.length > 0;
  const noSaved = state.section === 'saved' && !source.length;
  $('#empty-state h3').textContent = noSaved ? '把喜欢的频道留在这里' : '暂时没有找到';
  $('#empty-state p').textContent = noSaved ? '点击资源右上角的书签，下次就能在这里找到它。' : state.q ? '试试更短的关键词、拼音或 t.me 用户名。' : '这个分类暂无该类型的资源，试试其他筛选。';
  $('#empty-reset').textContent = noSaved ? '去发现频道' : '清除筛选';
  renderCards();
}

function syncView() {
  grid.classList.toggle('list-view', view === 'list');
  document.querySelectorAll('[data-view]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.view === view)));
}

function changeState(next, { replace = false, scroll = false, syncInput = true } = {}) {
  clearTimeout(searchTimer);
  state = { ...state, ...next };
  if (syncInput && search.value !== state.q) search.value = state.q;
  visibleCount = pageSize;
  updateLocation(replace);
  render();
  if (scroll) window.scrollTo({ top: 0, behavior: 'instant' });
}

function syncSidebar(open = false) {
  const expanded = mobile.matches && open;
  const exposed = !mobile.matches || expanded;
  sidebar.classList.toggle('open', expanded);
  sidebar.setAttribute('aria-hidden', String(!exposed));
  sidebar.inert = !exposed;
  $('#sidebar-overlay').classList.toggle('open', expanded);
  $('#menu-btn').setAttribute('aria-expanded', String(expanded));
  $('#main-content').inert = expanded;
  document.body.classList.toggle('menu-open', expanded);
  if (expanded) { sidebar.setAttribute('role', 'dialog'); sidebar.setAttribute('aria-modal', 'true'); }
  else { sidebar.removeAttribute('role'); sidebar.removeAttribute('aria-modal'); }
}

function closeSidebar() {
  const wasOpen = sidebar.classList.contains('open');
  syncSidebar(false);
  if (wasOpen && previousFocus instanceof HTMLElement) previousFocus.focus({ preventScroll: true });
}

$('#menu-btn').addEventListener('click', () => {
  previousFocus = document.activeElement;
  syncSidebar(true);
  $('#close-sidebar-btn').focus();
});
$('#close-sidebar-btn').addEventListener('click', closeSidebar);
$('#sidebar-overlay').addEventListener('click', closeSidebar);
mobile.addEventListener('change', () => {
  if (mobile.matches && sidebar.contains(document.activeElement)) $('#menu-btn').focus();
  syncSidebar(false);
});
syncSidebar(false);

function commitSearch() {
  if (composing) return;
  const hadQuery = Boolean(state.q);
  changeState({ q: search.value.trim() }, { replace: hadQuery, syncInput: false });
}
search.addEventListener('input', () => {
  clearTimeout(searchTimer);
  $('#clear-search-btn').hidden = !search.value;
  $('#search-shortcut').hidden = Boolean(search.value);
  if (!composing) searchTimer = setTimeout(commitSearch, 150);
});
search.addEventListener('compositionstart', () => { composing = true; clearTimeout(searchTimer); });
search.addEventListener('compositionend', () => { composing = false; clearTimeout(searchTimer); searchTimer = setTimeout(commitSearch, 150); });
$('.search-box').addEventListener('submit', event => { event.preventDefault(); clearTimeout(searchTimer); commitSearch(); });
$('#clear-search-btn').addEventListener('click', () => { changeState({ q: '' }); search.focus(); });
$('#result-clear-btn').addEventListener('click', () => { changeState({ q: '', type: 'all', sort: 'default' }); search.focus(); });
$('#search-all-btn').addEventListener('click', () => changeState({ section: 'all' }));
$('#empty-reset').addEventListener('click', () => {
  const goDiscover = state.section === 'saved' && !getSavedIds().size;
  changeState({ section: goDiscover ? 'featured' : state.section, q: '', type: 'all', sort: 'default' }, { scroll: goDiscover });
  search.focus({ preventScroll: goDiscover });
});
$('#sort-select').addEventListener('change', event => changeState({ sort: event.target.value }));
$('#load-more').addEventListener('click', event => {
  const previousCount = visibleCount;
  visibleCount += pageSize;
  renderCards(previousCount);
  if (event.detail === 0) grid.children[previousCount]?.querySelector('.card-title')?.focus();
});

document.addEventListener('click', event => {
  if (!(event.target instanceof Element)) return;
  const nav = event.target.closest('[data-section]');
  if (nav && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey && event.button === 0) {
    event.preventDefault();
    closeSidebar();
    changeState({ section: nav.dataset.section, q: '', type: 'all', sort: 'default' }, { scroll: true });
    document.querySelector('.mobile-category-item.active')?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }
  const type = event.target.closest('[data-type]');
  if (type?.tagName === 'BUTTON') changeState({ type: type.dataset.type });
  const display = event.target.closest('[data-view]');
  if (display) { view = display.dataset.view; writeStorage('rectg:view', view); syncView(); }
  if (event.target.closest('.card-title')) rememberPosition();
});

document.addEventListener('keydown', event => {
  if (event.isComposing) return;
  if (sidebar.classList.contains('open')) {
    if (event.key === 'Escape') { event.preventDefault(); closeSidebar(); }
    if (event.key === 'Tab') {
      const controls = [...sidebar.querySelectorAll('a[href], button')].filter(element => element.getClientRects().length);
      const first = controls[0];
      const last = controls.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    return;
  }
  const editable = document.activeElement?.matches('input, textarea, select, [contenteditable="true"]');
  if ((event.key === '/' && !editable) || (event.key.toLowerCase() === 'k' && (event.metaKey || event.ctrlKey))) {
    event.preventDefault(); search.focus(); search.select();
  }
  if (event.key === 'Escape' && document.activeElement === search) { changeState({ q: '' }); search.focus(); }
});

document.addEventListener('rectg:saved', event => {
  if (state.section !== 'saved') return;
  const index = [...grid.children].findIndex(card => card.dataset.id === event.detail?.id);
  const focusInGrid = grid.contains(document.activeElement);
  render();
  if (focusInGrid) (grid.children[Math.max(0, Math.min(index, grid.children.length - 1))]?.querySelector('[data-bookmark]') || $('#empty-reset')).focus();
});

function rememberPosition() {
  try {
    sessionStorage.setItem('rectg:directory-return', location.pathname + location.search);
    sessionStorage.setItem('rectg:directory-position', JSON.stringify({ url: location.pathname + location.search, count: visibleCount, y: scrollY }));
  } catch { /* Browsing still works when storage is unavailable. */ }
}
window.addEventListener('pagehide', rememberPosition);
window.addEventListener('pageshow', event => {
  // A detail page can change a bookmark while this page is in the back/forward cache.
  if (event.persisted && state.section === 'saved') render();
});
window.addEventListener('popstate', () => { clearTimeout(searchTimer); state = readLocation(); search.value = state.q; visibleCount = pageSize; render(); });
window.addEventListener('scroll', () => { $('#back-to-top').hidden = scrollY < 700; }, { passive: true });
$('#back-to-top').addEventListener('click', () => window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }));

let restoreY = 0;
try {
  const savedPosition = JSON.parse(sessionStorage.getItem('rectg:directory-position') || 'null');
  const navigationType = performance.getEntriesByType('navigation')[0]?.type;
  const fromDetail = document.referrer && new URL(document.referrer).origin === location.origin && new URL(document.referrer).pathname.startsWith('/p/');
  if (savedPosition?.url === location.pathname + location.search && (fromDetail || navigationType === 'back_forward' || navigationType === 'reload')) {
    visibleCount = Math.max(pageSize, Math.min(allItems.length, Number(savedPosition.count) || pageSize));
    restoreY = Number(savedPosition.y) || 0;
  }
} catch { /* Start at the top if there is no saved position. */ }
search.value = state.q;
syncView();
render();
if (restoreY) requestAnimationFrame(() => window.scrollTo({ top: restoreY, behavior: 'instant' }));
