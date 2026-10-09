// static/js/posts.js

// ============================================================
// State — mirrors the URL query string
// ============================================================

const state = {
  page: 1,
  page_size: 12,
  search: '',
  category: '',
  tag: '',
  ordering: 'newest',
};

// Guards against out-of-order responses when filters change rapidly
let requestSeq = 0;

// ============================================================
// Elements
// ============================================================

const els = {
  grid:            document.getElementById('post-grid'),
  skeleton:        document.getElementById('skeleton'),
  empty:           document.getElementById('state-empty'),
  error:           document.getElementById('state-error'),
  errorMessage:    document.getElementById('state-error-message'),
  errorRetry:      document.getElementById('state-error-retry'),
  pagination:      document.getElementById('pagination'),
  resultCount:     document.getElementById('result-count'),

  search:          document.getElementById('filter-search'),
  category:        document.getElementById('filter-category'),
  tag:             document.getElementById('filter-tag'),
  ordering:        document.getElementById('filter-ordering'),
  pageSize:        document.getElementById('filter-pagesize'),
  clear:           document.getElementById('filters-clear'),

  topbarAuth:      document.getElementById('topbar-auth'),
  footerYear:      document.getElementById('footer-year'),
};

// ============================================================
// URL <-> state
// ============================================================

function readStateFromURL() {
  const p = new URLSearchParams(window.location.search);
  if (p.has('page'))      state.page      = Math.max(1, parseInt(p.get('page'), 10) || 1);
  if (p.has('page_size')) state.page_size = Math.max(1, Math.min(50, parseInt(p.get('page_size'), 10) || 12));
  if (p.has('search'))    state.search    = p.get('search');
  if (p.has('category'))  state.category  = p.get('category');
  if (p.has('tag'))       state.tag       = p.get('tag');
  if (p.has('ordering'))  state.ordering  = p.get('ordering');
}

function writeStateToURL() {
  const p = new URLSearchParams();
  if (state.page > 1)              p.set('page', state.page);
  if (state.page_size !== 12)      p.set('page_size', state.page_size);
  if (state.search)                p.set('search', state.search);
  if (state.category)              p.set('category', state.category);
  if (state.tag)                   p.set('tag', state.tag);
  if (state.ordering !== 'newest') p.set('ordering', state.ordering);

  const qs = p.toString();
  const url = window.location.pathname + (qs ? '?' + qs : '');
  window.history.replaceState({}, '', url);
}

// ============================================================
// API calls — paths from the actual OpenAPI schema
// ============================================================

function buildPostsQuery() {
  const p = new URLSearchParams();
  p.set('page', String(state.page));
  p.set('page_size', String(state.page_size));
  if (state.search)   p.set('search', state.search);
  if (state.category) p.set('category', state.category);
  if (state.tag)      p.set('tag', state.tag);
  if (state.ordering) p.set('ordering', state.ordering);
  return p.toString();
}

async function fetchPosts() {
  return apiFetch(`/posts/?${buildPostsQuery()}`);
}

async function fetchCategories() {
  // Returns a plain array (no pagination)
  return apiFetch('/categories/');
}

async function fetchTags() {
  return apiFetch('/tags/');
}

// ============================================================
// Utilities
// ============================================================

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
    year: 'numeric', month: 'short', day: 'numeric',
  });
}

// ============================================================
// Icons (inline SVG)
// ============================================================

const ICONS = {
  eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
  heart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21.2l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>',
  chat:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
  bookmark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>',
};

// ============================================================
// Rendering
// ============================================================

function renderCard(post) {
  const author = post.author || {};
  const category = post.category || {};
  const image = post.featured_image
    ? `<img src="${escapeHtml(post.featured_image)}" alt="" loading="lazy">`
    : '';
  const categoryHtml = category.slug
    ? `<a class="card__category" href="/posts.html?category=${encodeURIComponent(category.slug)}">${escapeHtml(category.name)}</a>`
    : '';
  const authorName = author.display_name || author.username || 'Unknown';
  const avatar = author.avatar_url || '/static/img/default-avatar.jpg';
  const published = formatDate(post.published_at);
  const reading = post.reading_time ? `${post.reading_time} min read` : '';

  return `
    <article class="card">
      <a class="card__media" href="/post.html?slug=${encodeURIComponent(post.slug)}">
        ${image}
      </a>
      <div class="card__body">
        ${categoryHtml}
        <h2 class="card__title">
          <a href="/post.html?slug=${encodeURIComponent(post.slug)}">${escapeHtml(post.title)}</a>
        </h2>
        ${post.summary ? `<p class="card__summary">${escapeHtml(post.summary)}</p>` : ''}
        <div class="card__meta">
          <img class="card__avatar" src="${escapeHtml(avatar)}" alt="">
          <span class="card__author">${escapeHtml(authorName)}</span>
          ${published ? `<span class="card__dot">·</span><time datetime="${escapeHtml(post.published_at)}">${published}</time>` : ''}
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

function renderSkeletons(count) {
  els.skeleton.innerHTML = Array.from({ length: count }).map(() => `
    <div class="skeleton-card" aria-hidden="true">
      <div class="sk-media"></div>
      <div class="sk-body">
        <div class="sk-line sk-line--sm"></div>
        <div class="sk-line sk-line--lg"></div>
        <div class="sk-line sk-line--md"></div>
        <div class="sk-line sk-line--sm"></div>
      </div>
    </div>
  `).join('');
}

// ============================================================
// Pagination — DRF gives next/previous URLs and count only
// ============================================================

function parsePageFromURL(url, fallback) {
  if (!url) return null;
  try {
    const u = new URL(url);
    const n = parseInt(u.searchParams.get('page'), 10);
    return Number.isFinite(n) ? n : fallback;
  } catch {
    return fallback;
  }
}

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
      `<button type="button" data-page="${page}" ${isActive ? 'class="is-active" aria-current="page"' : ''}>${page}</button>`
    );
  };
  const pushEllipsis = () => items.push('<span class="pagination__ellipsis">…</span>');

  items.push(
    `<button type="button" data-page="${current - 1}" ${previous ? '' : 'disabled'} aria-label="Previous page">‹</button>`
  );

  // Window: 1, current-1..current+1, last, with ellipses
  const pages = new Set([1, totalPages, current - 1, current, current + 1]);
  const sorted = [...pages].filter((n) => n >= 1 && n <= totalPages).sort((a, b) => a - b);

  let last = 0;
  for (const n of sorted) {
    if (n - last > 1) pushEllipsis();
    push(n);
    last = n;
  }

  items.push(
    `<button type="button" data-page="${current + 1}" ${next ? '' : 'disabled'} aria-label="Next page">›</button>`
  );

  els.pagination.innerHTML = items.join('');
}

// ============================================================
// UI state helpers
// ============================================================

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

// ============================================================
// Load
// ============================================================

async function load() {
  const mySeq = ++requestSeq;
  showSkeleton();
  writeStateToURL();

  try {
    const data = await fetchPosts();
    if (mySeq !== requestSeq) return; // stale

    showContent();
    updateResultCount(data.count);

    if (!data.results || data.results.length === 0) {
      showEmpty();
      return;
    }

    els.grid.innerHTML = data.results.map(renderCard).join('');
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

// ============================================================
// Filters
// ============================================================

function syncFiltersFromState() {
  els.search.value = state.search;
  els.category.value = state.category;
  els.tag.value = state.tag;
  els.ordering.value = state.ordering;
  els.pageSize.value = String(state.page_size);
}

function applyFilters() {
  state.search = els.search.value.trim();
  state.category = els.category.value;
  state.tag = els.tag.value;
  state.ordering = els.ordering.value;
  state.page = 1;
  load();
}

let searchDebounce;
els.search.addEventListener('input', () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(applyFilters, 300);
});

els.category.addEventListener('change', applyFilters);
els.tag.addEventListener('change', applyFilters);
els.ordering.addEventListener('change', applyFilters);

els.pageSize.addEventListener('change', () => {
  state.page_size = parseInt(els.pageSize.value, 10) || 12;
  state.page = 1;
  load();
});

els.clear.addEventListener('click', () => {
  state.search = '';
  state.category = '';
  state.tag = '';
  state.ordering = 'newest';
  state.page = 1;
  syncFiltersFromState();
  load();
});

document.querySelectorAll('[data-clear]').forEach((btn) => {
  btn.addEventListener('click', () => els.clear.click());
});

els.errorRetry.addEventListener('click', load);

// ============================================================
// Pagination clicks
// ============================================================

els.pagination.addEventListener('click', (e) => {
  const btn = e.target.closest('button[data-page]');
  if (!btn || btn.disabled) return;
  const page = parseInt(btn.dataset.page, 10);
  if (!Number.isFinite(page) || page === state.page) return;
  state.page = page;
  load();
});

// ============================================================
// Populate filters
// ============================================================

async function populateFilters() {
  const [categories, tags] = await Promise.allSettled([
    fetchCategories(),
    fetchTags(),
  ]);

  if (categories.status === 'fulfilled' && Array.isArray(categories.value)) {
    for (const c of categories.value) {
      const opt = document.createElement('option');
      opt.value = c.slug;
      opt.textContent = c.name;
      els.category.appendChild(opt);
    }
  }

  if (tags.status === 'fulfilled' && Array.isArray(tags.value)) {
    // Sort tags by usage_count desc as a friendly default
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

// ============================================================
// Topbar auth (read-only; no redirects)
// ============================================================

async function renderTopbarAuth() {
  const token = getAccessToken();
  if (!token) {
    els.topbarAuth.innerHTML = `<a href="/login.html" class="btn btn--ghost">Login</a>`;
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
    // Token expired or invalid — show Login. Do NOT redirect.
    clearTokens();
    els.topbarAuth.innerHTML = `<a href="/login.html" class="btn btn--ghost">Login</a>`;
  }
}

// ============================================================
// Init
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
  els.footerYear.textContent = new Date().getFullYear();

  readStateFromURL();
  syncFiltersFromState();

  // Run in parallel; only the posts list blocks rendering
  renderTopbarAuth();
  populateFilters().then(load);
});
