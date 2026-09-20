const SAVED_KEY = 'rectg:saved';
let toastTimer;
const copyTimers = new WeakMap();

export function readStorage(key, fallback = null) {
  try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
}

export function writeStorage(key, value) {
  try { localStorage.setItem(key, value); return true; } catch { return false; }
}

export function getSavedIds() {
  try {
    const value = JSON.parse(readStorage(SAVED_KEY, '[]'));
    return new Set(Array.isArray(value) ? value.filter(id => typeof id === 'string') : []);
  } catch { return new Set(); }
}

export function showToast(message) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2400);
}

export function syncBookmarks() {
  const saved = getSavedIds();
  document.querySelectorAll('[data-bookmark]').forEach(button => {
    const selected = saved.has(button.dataset.bookmark);
    const title = button.dataset.title || button.closest('.card')?.querySelector('.card-title')?.textContent || '';
    button.setAttribute('aria-pressed', String(selected));
    button.setAttribute('aria-label', `${selected ? '取消收藏' : '收藏'} ${title}`.trim());
    button.title = selected ? '取消收藏' : '收藏';
    const label = button.querySelector('.bookmark-label');
    if (label) label.textContent = selected ? '已收藏' : '收藏';
  });
  document.querySelectorAll('[data-saved-count]').forEach(el => { el.textContent = String(saved.size); });
}

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    try { await navigator.clipboard.writeText(value); return true; } catch { /* Use the fallback below. */ }
  }
  const previousFocus = document.activeElement;
  const input = document.createElement('textarea');
  input.value = value;
  input.className = 'clipboard-fallback';
  input.setAttribute('readonly', '');
  document.body.append(input);
  input.select();
  try { return document.execCommand('copy'); } finally {
    input.remove();
    if (previousFocus instanceof HTMLElement) previousFocus.focus({ preventScroll: true });
  }
}

function init() {
  const toggle = document.getElementById('theme-toggle');
  const syncTheme = () => {
    const dark = document.body.classList.contains('dark');
    document.getElementById('theme-color-meta')?.setAttribute('content', dark ? '#171c19' : '#f8f9f6');
    const label = dark ? '切换到浅色主题' : '切换到深色主题';
    toggle?.setAttribute('aria-pressed', String(dark));
    toggle?.setAttribute('aria-label', label);
    toggle?.setAttribute('title', label);
  };
  syncTheme();
  toggle?.addEventListener('click', () => {
    document.body.classList.toggle('dark');
    writeStorage('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
    syncTheme();
  });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
    if (!readStorage('theme')) { document.body.classList.toggle('dark', event.matches); syncTheme(); }
  });
  syncBookmarks();
  window.addEventListener('pageshow', syncBookmarks);
  window.addEventListener('storage', event => {
    if (event.key === SAVED_KEY || event.key === null) {
      syncBookmarks();
      document.dispatchEvent(new CustomEvent('rectg:saved'));
    }
  });
  document.addEventListener('click', async event => {
    if (!(event.target instanceof Element)) return;
    const bookmark = event.target.closest('[data-bookmark]');
    if (bookmark) {
      const saved = getSavedIds();
      const id = bookmark.dataset.bookmark;
      if (!id) return;
      const removing = saved.has(id);
      if (removing) saved.delete(id); else saved.add(id);
      if (!writeStorage(SAVED_KEY, JSON.stringify([...saved]))) {
        showToast('浏览器未允许保存收藏，请检查存储设置');
        return;
      }
      syncBookmarks();
      document.dispatchEvent(new CustomEvent('rectg:saved', { detail: { id, removing } }));
      showToast(removing ? '已取消收藏' : '已收藏');
      return;
    }
    const copy = event.target.closest('[data-copy-url]');
    if (copy) {
      try {
        if (!await copyText(copy.dataset.copyUrl)) throw new Error('Copy failed');
        copy.classList.add('copied');
        copy.title = '已复制';
        clearTimeout(copyTimers.get(copy));
        copyTimers.set(copy, setTimeout(() => { copy.classList.remove('copied'); copy.title = '复制链接'; }, 2000));
        showToast('链接已复制');
        window.rectgTrack?.('copy_link', { resource_id: copy.closest('[data-id]')?.dataset.id || '' });
      } catch { showToast('复制失败，请长按或右键复制链接'); }
      return;
    }
    const direct = event.target.closest('.card-action-primary, .action-primary');
    const detail = event.target.closest('.card-title');
    if (direct || detail) window.rectgTrack?.(direct ? 'telegram_click' : 'resource_detail', {
      resource_id: event.target.closest('[data-id]')?.dataset.id || '',
      type: event.target.closest('[data-type]')?.dataset.type || '',
    });
  });
  try {
    const returnPath = sessionStorage.getItem('rectg:directory-return');
    const url = returnPath && new URL(returnPath, location.origin);
    if (url && url.origin === location.origin && (url.pathname === '/' || url.pathname.startsWith('/category/'))) {
      document.querySelectorAll('[data-back-directory]').forEach(link => { link.href = url.pathname + url.search; });
    }
  } catch { /* The category link remains a useful fallback. */ }
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
else init();
