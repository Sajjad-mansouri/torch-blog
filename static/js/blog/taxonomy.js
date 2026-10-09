// static/js/taxonomy.js

(function () {
  // ============================================================
  // Detect page from URL
  //   /categories/<slug>/  →  { kind: "categories", slug }
  //   /tags/<slug>/       →  { kind: "tags", slug }
  // ============================================================

  function detectPage() {
    const parts = getPathParts();
    const kind = parts[0];
    const slug = parts[1];

    if ((kind !== 'categories' && kind !== 'tags') || !slug) {
      return null;
    }
    return { kind, slug: decodeURIComponent(slug) };
  }

  const page = detectPage();
  if (!page) return;

  const { escapeHtml, renderCard } = window.TorchUI;

  // ============================================================
  // State
  // ============================================================

  const state = {
    page: 1,
    search: '',
    ordering: 'newest',
  };

  let requestSeq = 0;

  // ============================================================
  // Elements
  // ============================================================

  const els = {
    skeleton: document.getElementById('taxonomy-skeleton'),
    error: document.getElementById('taxonomy-error'),
    errorTitle: document.getElementById('taxonomy-error-title'),
    errorMessage: document.getElementById('taxonomy-error-message'),
    header: document.getElementById('taxonomy-header'),

    title: document.getElementById('taxonomy-title'),
    description: document.getElementById('taxonomy-description'),
    meta: document.getElementById('taxonomy-meta'),
    media: document.getElementById('taxonomy-media'),
    image: document.getElementById('taxonomy-image'),

    controls: document.getElementById('taxonomy-controls'),
    search: document.getElementById('taxonomy-search'),
    ordering: document.getElementById('taxonomy-ordering'),

    grid: document.getElementById('taxonomy-grid'),
    empty: document.getElementById('taxonomy-empty'),
    pagination: document.getElementById('taxonomy-pagination'),

    topbarAuth: document.getElementById('topbar-auth'),
    footerYear: document.getElementById('footer-year'),
  };

  // ============================================================
  // URL <-> state
  // ============================================================

  function readStateFromURL() {
    const p = new URLSearchParams(window.location.search);
    if (p.has('page')) {
      state.page = Math.max(1, parseInt(p.get('page'), 10) || 1);
    }
    if (p.has('search')) state.search = p.get('search');
    if (p.has('ordering')) state.ordering = p.get('ordering');
  }

  function writeStateToURL() {
    const p = new URLSearchParams();
    if (state.page > 1) p.set('page', String(state.page));
    if (state.search) p.set('search', state.search);
    if (state.ordering && state.ordering !== 'newest') {
      p.set('ordering', state.ordering);
    }
    const qs = p.toString();
    const url = window.location.pathname + (qs ? '?' + qs : '');
    window.history.replaceState({}, '', url);
  }

  // ============================================================
  // API calls
  // ============================================================

  async function fetchTaxonomy() {
    return apiFetch(
      `/${page.kind}/${encodeURIComponent(page.slug)}/`
    );
  }

  async function fetchPosts() {
    const p = new URLSearchParams();
    p.set('page', String(state.page));
    if (state.search) p.set('search', state.search);
    if (state.ordering && state.ordering !== 'newest') {
      p.set('ordering', state.ordering);
    }
    return apiFetch(
      `/${page.kind}/${encodeURIComponent(page.slug)}/posts/?${p.toString()}`
    );
  }

  // ============================================================
  // Rendering — header
  // ============================================================

  function renderHeader(data) {
    // data is Category or Tag.
    // Category: name, description, image, parent, order, post_count
    // Tag:      name, usage_count

    const name = data.name || '';
    document.title = `${name} — Torch`;
    els.title.textContent = name;

    // Description — category only
    if (els.description) {
      if (data.description) {
        els.description.textContent = data.description;
        els.description.hidden = false;
      } else {
        els.description.hidden = true;
      }
    }

    // Image — category only
    if (els.media && els.image) {
      if (data.image) {
        els.image.src = data.image;
        els.image.alt = name;
        els.media.hidden = false;
      } else {
        els.media.hidden = true;
      }
    }

    // Meta
    let metaText = '';
    if (page.kind === 'categories' && typeof data.post_count === 'number') {
      metaText = data.post_count === 1 ? '1 post' : `${data.post_count} posts`;
    } else if (page.kind === 'tags' && typeof data.usage_count === 'number') {
      metaText = data.usage_count === 1
        ? '1 post tagged'
        : `${data.usage_count} posts tagged`;
    }
    els.meta.textContent = metaText;

    els.header.hidden = false;
    els.controls.hidden = false;
    els.grid.hidden = false;
  }

  // ============================================================
  // Pagination
  // ============================================================

  function renderPagination(data) {
    const total = data.count || 0;
    const pageSize = inferPageSize(data);
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const current = state.page;

    if (totalPages <= 1) {
      els.pagination.hidden = true;
      els.pagination.innerHTML = '';
      return;
    }
    els.pagination.hidden = false;

    const items = [];
    const push = (p) => {
      const active = p === current;
      items.push(
        `<button type="button" data-page="${p}" ${
          active ? 'class="is-active" aria-current="page"' : ''
        }>${p}</button>`
      );
    };
    const ellipsis = () =>
      items.push('<span class="pagination__ellipsis">…</span>');

    items.push(
      `<button type="button" data-page="${current - 1}" ${
        data.previous ? '' : 'disabled'
      } aria-label="Previous page">‹</button>`
    );

    const pages = new Set([1, totalPages, current - 1, current, current + 1]);
    const sorted = [...pages]
      .filter((n) => n >= 1 && n <= totalPages)
      .sort((a, b) => a - b);

    let last = 0;
    for (const n of sorted) {
      if (n - last > 1) ellipsis();
      push(n);
      last = n;
    }

    items.push(
      `<button type="button" data-page="${current + 1}" ${
        data.next ? '' : 'disabled'
      } aria-label="Next page">›</button>`
    );

    els.pagination.innerHTML = items.join('');
  }

  function inferPageSize(data) {
    // PostPagination sets page_size to 12 by default.
    // We only use this to estimate total pages.
    // If results length is known and count is larger, use results length.
    const results = data.results || [];
    if (results.length && data.count && data.count > results.length) {
      // approximate: if count == results.length, one page anyway
      // otherwise page_size == results.length on a full page
      return Math.max(results.length, 1);
    }
    return 12;
  }

  // ============================================================
  // Load posts
  // ============================================================

  async function loadPosts() {
    const mySeq = ++requestSeq;

    try {
      const data = await fetchPosts();
      if (mySeq !== requestSeq) return;

      const posts = data.results || [];

      if (!posts.length) {
        els.grid.hidden = true;
        els.grid.innerHTML = '';
        els.empty.hidden = false;
        els.pagination.hidden = true;
        return;
      }

      els.empty.hidden = true;
      els.grid.hidden = false;
      els.grid.innerHTML = posts.map((p) => renderCard(p)).join('');

      renderPagination(data);
    } catch (err) {
      if (mySeq !== requestSeq) return;
      console.error(err);
      els.grid.hidden = true;
      els.empty.hidden = true;
      els.pagination.hidden = true;
      showError(
        "Couldn't load posts",
        (err.body && (err.body.detail || err.body.message)) ||
          'Please check your connection and try again.'
      );
    }
  }

  // ============================================================
  // Load — full page
  // ============================================================

  async function load() {
    if ('scrollRestoration' in history) {
      history.scrollRestoration = 'manual';
    }
    window.scrollTo({ top: 0, behavior: 'auto' });

    els.skeleton.hidden = false;
    els.error.hidden = true;
    els.header.hidden = true;
    els.controls.hidden = true;
    els.grid.hidden = true;
    els.empty.hidden = true;
    els.pagination.hidden = true;

    try {
      const taxonomy = await fetchTaxonomy();
      els.skeleton.hidden = true;
      renderHeader(taxonomy);

      await loadPosts();
    } catch (err) {
      console.error(err);
      els.skeleton.hidden = true;

      const label = page.kind === 'categories' ? 'Category' : 'Tag';

      if (err.status === 404) {
        showError(`${label} not found`, `This ${page.kind} does not exist.`);
      } else {
        showError(
          `Couldn't load this ${page.kind}`,
          (err.body && (err.body.detail || err.body.message)) ||
            'Please check your connection and try again.'
        );
      }
    }
  }

  function showError(title, message) {
    els.skeleton.hidden = true;
    els.header.hidden = true;
    els.controls.hidden = true;
    els.grid.hidden = true;
    els.empty.hidden = true;
    els.pagination.hidden = true;
    els.errorTitle.textContent = title;
    els.errorMessage.textContent = message;
    els.error.hidden = false;
    window.scrollTo({ top: 0, behavior: 'auto' });
  }

  // ============================================================
  // Topbar auth
  // ============================================================

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

  // ============================================================
  // Events
  // ============================================================

  let searchTimer = null;
  if (els.search) {
    els.search.addEventListener('input', () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        state.search = els.search.value.trim();
        state.page = 1;
        writeStateToURL();
        loadPosts();
      }, 300);
    });
  }

  if (els.ordering) {
    els.ordering.addEventListener('change', () => {
      state.ordering = els.ordering.value;
      state.page = 1;
      writeStateToURL();
      loadPosts();
    });
  }

  if (els.pagination) {
    els.pagination.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-page]');
      if (!btn || btn.disabled) return;
      const p = parseInt(btn.dataset.page, 10);
      if (!Number.isFinite(p) || p === state.page) return;
      state.page = p;
      writeStateToURL();
      loadPosts();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ============================================================
  // Init
  // ============================================================

  document.addEventListener('DOMContentLoaded', () => {
    if (els.footerYear) {
      els.footerYear.textContent = new Date().getFullYear();
    }

    readStateFromURL();

    if (els.search) els.search.value = state.search;
    if (els.ordering) els.ordering.value = state.ordering;

    renderTopbarAuth();
    load();
  });

  window.addEventListener('popstate', () => {
    readStateFromURL();
    if (els.search) els.search.value = state.search;
    if (els.ordering) els.ordering.value = state.ordering;
    loadPosts();
  });
})();
