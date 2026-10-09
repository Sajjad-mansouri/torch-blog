// static/js/posts.js

// ============================================================
// Shared UI helpers — exposed on window.TorchUI
// ============================================================

window.TorchUI = (function () {
  function escapeHtml(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  function formatDateTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  const ICONS = {
    eye:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    heart:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21.2l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>',
    heartFilled:
      '<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21.2l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>',
    chat:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    bookmark:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>',
    bookmarkFilled:
      '<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>',
    share:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.6" y1="10.7" x2="15.4" y2="6.3"/><line x1="8.6" y1="13.3" x2="15.4" y2="17.7"/></svg>',
    reply:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 17 4 12 9 7"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/></svg>',
  };

  /**
   * Build the URL to a post detail page.
   *   /posts/<slug>/
   */
  function postUrl(slug) {
    return `/posts/${encodeURIComponent(slug)}/`;
  }

  /**
   * Build the URL to an author profile page.
   *   /author/<username>/
   */
  function authorUrl(username) {
    return `/author/${encodeURIComponent(username)}/`;
  }

  /**
   * Build the URL to the posts list with a category filter.
   */
  function categoryUrl(slug) {
    return `/posts/?category=${encodeURIComponent(slug)}`;
  }

  /**
   * Build the URL to the posts list with a tag filter.
   */
  function tagUrl(slug) {
    return `/posts/?tag=${encodeURIComponent(slug)}`;
  }

  /**
   * Render a PostCard. Used on the list page, related posts, etc.
   */
  function renderCard(post, hrefBase) {
    const base = hrefBase || '/posts/';
    const url = base.endsWith('/') && base !== '/posts/'
      ? base + encodeURIComponent(post.slug) + '/'
      : postUrl(post.slug);

    const author = post.author || {};
    const category = post.category || {};

    const image = post.featured_image
      ? `<img src="${escapeHtml(post.featured_image)}" alt="" loading="lazy">`
      : '';

    const categoryHtml = category.slug
      ? `<a class="card__category" href="${categoryUrl(category.slug)}">${escapeHtml(category.name)}</a>`
      : '';

    const authorName = author.display_name || author.username || 'Unknown';
    const avatar = author.avatar_url || '/static/img/default-avatar.jpg';
    const published = formatDate(post.published_at);
    const reading = post.reading_time ? `${post.reading_time} min read` : '';

    return `
      <article class="card">
        <a class="card__media" href="${url}">${image}</a>
        <div class="card__body">
          ${categoryHtml}
          <h3 class="card__title"><a href="${url}">${escapeHtml(post.title)}</a></h3>
          ${post.summary ? `<p class="card__summary">${escapeHtml(post.summary)}</p>` : ''}
          <div class="card__meta">
            <img class="card__avatar" src="${escapeHtml(avatar)}" alt="">
            <span class="card__author">${escapeHtml(authorName)}</span>
            ${
              published
                ? `<span class="card__dot">·</span><time datetime="${escapeHtml(post.published_at)}">${published}</time>`
                : ''
            }
            ${reading ? `<span class="card__dot">·</span><span>${reading}</span>` : ''}
          </div>
          <div class="card__stats">
            <span>${ICONS.eye}${post.views_count ?? 0}</span>
            <span>${ICONS.heart}${post.like_count ?? 0}</span>
            <span>${ICONS.chat}${post.comment_count ?? 0}</span>
            <span>${ICONS.bookmark}${post.bookmark_count ?? 0}</span>
          </div>
        </div>
      </article>
    `;
  }

  return {
    escapeHtml,
    formatDate,
    formatDateTime,
    ICONS,
    renderCard,
    postUrl,
    authorUrl,
    categoryUrl,
    tagUrl,
  };
})();

// ============================================================
// Post LIST page — runs only when #post-grid exists
// ============================================================

(function () {
  const grid = document.getElementById('post-grid');
  if (!grid) return;

  const { escapeHtml, renderCard } = window.TorchUI;

  // ------------------------------------------------------------
  // State — mirrors the URL query string
  // ------------------------------------------------------------

  const state = {
    page: 1,
    page_size: 12,
    search: '',
    category: '',
    tag: '',
    ordering: 'newest',
  };

  let requestSeq = 0;

  // ------------------------------------------------------------
  // Elements
  // ------------------------------------------------------------

  const els = {
    grid,
    skeleton: document.getElementById('skeleton'),
    empty: document.getElementById('state-empty'),
    error: document.getElementById('state-error'),
    errorMessage: document.getElementById('state-error-message'),
    errorRetry: document.getElementById('state-error-retry'),
    pagination: document.getElementById('pagination'),
    resultCount: document.getElementById('result-count'),

    search: document.getElementById('filter-search'),
    category: document.getElementById('filter-category'),
    tag: document.getElementById('filter-tag'),
    ordering: document.getElementById('filter-ordering'),
    pageSize: document.getElementById('filter-pagesize'),
    clear: document.getElementById('filters-clear'),

    topbarAuth: document.getElementById('topbar-auth'),
    footerYear: document.getElementById('footer-year'),
  };

  // ------------------------------------------------------------
  // URL <-> state
  // ------------------------------------------------------------

  function readStateFromURL() {
    const p = new URLSearchParams(window.location.search);
    if (p.has('page')) {
      state.page = Math.max(1, parseInt(p.get('page'), 10) || 1);
    }
    if (p.has('page_size')) {
      state.page_size = Math.max(
        1,
        Math.min(50, parseInt(p.get('page_size'), 10) || 12)
      );
    }
    if (p.has('search')) state.search = p.get('search');
    if (p.has('category')) state.category = p.get('category');
    if (p.has('tag')) state.tag = p.get('tag');
    if (p.has('ordering')) state.ordering = p.get('ordering');
  }

  function writeStateToURL() {
    const p = new URLSearchParams();
    if (state.page > 1) p.set('page', state.page);
    if (state.page_size !== 12) p.set('page_size', state.page_size);
    if (state.search) p.set('search', state.search);
    if (state.category) p.set('category', state.category);
    if (state.tag) p.set('tag', state.tag);
    if (state.ordering !== 'newest') p.set('ordering', state.ordering);

    const qs = p.toString();
    const url = window.location.pathname + (qs ? '?' + qs : '');
    window.history.replaceState({}, '', url);
  }

  // ------------------------------------------------------------
  // API calls
  // ------------------------------------------------------------

  function buildPostsQuery() {
    const p = new URLSearchParams();
    p.set('page', String(state.page));
    p.set('page_size', String(state.page_size));
    if (state.search) p.set('search', state.search);
    if (state.category) p.set('category', state.category);
    if (state.tag) p.set('tag', state.tag);
    if (state.ordering) p.set('ordering', state.ordering);
    return p.toString();
  }

  async function fetchPosts() {
    return apiFetch(`/posts/?${buildPostsQuery()}`);
  }

  async function fetchCategories() {
    return apiFetch('/categories/');
  }

  async function fetchTags() {
    return apiFetch('/tags/');
  }

  // ------------------------------------------------------------
  // Skeletons
  // ------------------------------------------------------------

  function renderSkeletons(count) {
    els.skeleton.innerHTML = Array.from({ length: count })
      .map(
        () => `
        <div class="skeleton-card" aria-hidden="true">
          <div class="sk-media"></div>
          <div class="sk-body">
            <div class="sk-line sk-line--sm"></div>
            <div class="sk-line sk-line--lg"></div>
            <div class="sk-line sk-line--md"></div>
            <div class="sk-line sk-line--sm"></div>
          </div>
        </div>
      `
      )
      .join('');
  }

  // ------------------------------------------------------------
  // Pagination
  // ------------------------------------------------------------

  function renderPagination({ count, next, previous }) {
    const totalPages = Math.max(1, Math.ceil(count / state.page_size));
    const current = state.page;

    if (totalPages <= 1) {
      els.pagination.hidden = true;
      els.pagination.innerHTML = '';
      return;
    }
    els.pagination.hidden = false;

    const items = [];
    const push = (page) => {
      const isActive = page === current;
      items.push(
        `<button type="button" data-page="${page}" ${
          isActive ? 'class="is-active" aria-current="page"' : ''
        }>${page}</button>`
      );
    };
    const pushEllipsis = () =>
      items.push('<span class="pagination__ellipsis">…</span>');

    items.push(
      `<button type="button" data-page="${current - 1}" ${
        previous ? '' : 'disabled'
      } aria-label="Previous page">‹</button>`
    );

    const pages = new Set([1, totalPages, current - 1, current, current + 1]);
    const sorted = [...pages]
      .filter((n) => n >= 1 && n <= totalPages)
      .sort((a, b) => a - b);

    let last = 0;
    for (const n of sorted) {
      if (n - last > 1) pushEllipsis();
      push(n);
      last = n;
    }

    items.push(
      `<button type="button" data-page="${current + 1}" ${
        next ? '' : 'disabled'
      } aria-label="Next page">›</button>`
    );

    els.pagination.innerHTML = items.join('');
  }

  // ------------------------------------------------------------
  // UI state helpers
  // ------------------------------------------------------------

  function showSkeleton() {
    els.grid.innerHTML = '';
    els.grid.hidden = true;
    els.empty.hidden = true;
    els.error.hidden = true;
    els.pagination.hidden = true;
    els.skeleton.hidden = false;
    renderSkeletons(Math.min(state.page_size, 8));
  }

  function showContent() {
    els.skeleton.hidden = true;
    els.grid.hidden = false;
    els.empty.hidden = true;
    els.error.hidden = true;
  }

  function showEmpty() {
    els.skeleton.hidden = true;
    els.grid.hidden = true;
    els.empty.hidden = false;
    els.error.hidden = true;
    els.pagination.hidden = true;
  }

  function showError(message) {
    els.skeleton.hidden = true;
    els.grid.hidden = true;
    els.empty.hidden = true;
    els.pagination.hidden = true;
    els.errorMessage.textContent = message;
    els.error.hidden = false;
  }

  function updateResultCount(count) {
    if (!count) {
      els.resultCount.textContent = 'No posts found';
      return;
    }
    els.resultCount.textContent = count === 1 ? '1 post' : `${count} posts`;
  }

  // ------------------------------------------------------------
  // Load
  // ------------------------------------------------------------

  async function load() {
    const mySeq = ++requestSeq;
    showSkeleton();
    writeStateToURL();

    try {
      const data = await fetchPosts();
      if (mySeq !== requestSeq) return;

      showContent();
      updateResultCount(data.count);

      if (!data.results || data.results.length === 0) {
        showEmpty();
        return;
      }

      els.grid.innerHTML = data.results.map((p) => renderCard(p)).join('');
      renderPagination(data);

      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      if (mySeq !== requestSeq) return;
      console.error(err);
      const msg =
        (err.body && (err.body.detail || err.body.message)) ||
        'Please check your connection and try again.';
      showError(msg);
    }
  }

  // ------------------------------------------------------------
  // Filters
  // ------------------------------------------------------------

  function syncFiltersFromState() {
    if (els.search) els.search.value = state.search;
    if (els.category) els.category.value = state.category;
    if (els.tag) els.tag.value = state.tag;
    if (els.ordering) els.ordering.value = state.ordering;
    if (els.pageSize) els.pageSize.value = String(state.page_size);
  }

  function applyFilters() {
    state.search = els.search ? els.search.value.trim() : '';
    state.category = els.category ? els.category.value : '';
    state.tag = els.tag ? els.tag.value : '';
    state.ordering = els.ordering ? els.ordering.value : 'newest';
    state.page = 1;
    load();
  }

  let searchDebounce;
  if (els.search) {
    els.search.addEventListener('input', () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(applyFilters, 300);
    });
  }

  if (els.category) els.category.addEventListener('change', applyFilters);
  if (els.tag) els.tag.addEventListener('change', applyFilters);
  if (els.ordering) els.ordering.addEventListener('change', applyFilters);

  if (els.pageSize) {
    els.pageSize.addEventListener('change', () => {
      state.page_size = parseInt(els.pageSize.value, 10) || 12;
      state.page = 1;
      load();
    });
  }

  if (els.clear) {
    els.clear.addEventListener('click', () => {
      state.search = '';
      state.category = '';
      state.tag = '';
      state.ordering = 'newest';
      state.page = 1;
      syncFiltersFromState();
      load();
    });
  }

  document.querySelectorAll('[data-clear]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (els.clear) els.clear.click();
    });
  });

  if (els.errorRetry) els.errorRetry.addEventListener('click', load);

  // ------------------------------------------------------------
  // Pagination clicks
  // ------------------------------------------------------------

  if (els.pagination) {
    els.pagination.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-page]');
      if (!btn || btn.disabled) return;
      const page = parseInt(btn.dataset.page, 10);
      if (!Number.isFinite(page) || page === state.page) return;
      state.page = page;
      load();
    });
  }

  // ------------------------------------------------------------
  // Populate filters
  // ------------------------------------------------------------

  async function populateFilters() {
    const [categories, tags] = await Promise.allSettled([
      fetchCategories(),
      fetchTags(),
    ]);

    if (
      els.category &&
      categories.status === 'fulfilled' &&
      Array.isArray(categories.value)
    ) {
      for (const c of categories.value) {
        const opt = document.createElement('option');
        opt.value = c.slug;
        opt.textContent = c.name;
        els.category.appendChild(opt);
      }
    }

    if (
      els.tag &&
      tags.status === 'fulfilled' &&
      Array.isArray(tags.value)
    ) {
      const sorted = [...tags.value].sort(
        (a, b) => (b.usage_count || 0) - (a.usage_count || 0)
      );
      for (const t of sorted) {
        const opt = document.createElement('option');
        opt.value = t.slug;
        opt.textContent = t.name;
        els.tag.appendChild(opt);
      }
    }
  }

  // ------------------------------------------------------------
  // Topbar auth
  // ------------------------------------------------------------

  async function renderTopbarAuth() {
    if (!els.topbarAuth) return;

    const token = getAccessToken();
    if (!token) {
      els.topbarAuth.innerHTML = `<a href="/login/" class="btn btn--ghost">Login</a>`;
      return;
    }

    try {
      const user = await apiFetch('/auth/me/');
      const name = user.display_name || user.username;
      const avatar = user.avatar_url || '/static/img/default-avatar.jpg';
      els.topbarAuth.innerHTML = `
        <span class="topbar__user">
          <img class="topbar__avatar" src="${escapeHtml(avatar)}" alt="">
          <span>${escapeHtml(name)}</span>
        </span>
      `;
    } catch {
      clearTokens();
      els.topbarAuth.innerHTML = `<a href="/login/" class="btn btn--ghost">Login</a>`;
    }
  }

  // ------------------------------------------------------------
  // Init
  // ------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', () => {
    if (els.footerYear) {
      els.footerYear.textContent = new Date().getFullYear();
    }

    readStateFromURL();
    syncFiltersFromState();

    renderTopbarAuth();
    populateFilters().then(load);
  });
})();
