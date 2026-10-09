// static/js/search-page.js

(function () {
  if (!document.getElementById('search-tabs')) return;

  const { escapeHtml, renderCard } = window.TorchUI;

  const state = {
    q: '',
    type: 'all',      // 'all' | 'post' | 'author' | 'tag'
    page: 1,
  };

  const els = {
    title: document.getElementById('search-title'),
    subtitle: document.getElementById('search-subtitle'),
    tabs: document.getElementById('search-tabs'),

    loading: document.getElementById('search-loading'),
    empty: document.getElementById('search-empty'),
    emptyHint: document.getElementById('search-empty-hint'),
    error: document.getElementById('search-error'),
    errorMessage: document.getElementById('search-error-message'),

    mixed: document.getElementById('search-mixed'),
    typed: document.getElementById('search-typed'),

    postsGroup: document.getElementById('search-posts-group'),
    postsGrid: document.getElementById('search-posts-grid'),
    postsMore: document.getElementById('search-posts-more'),

    authorsGroup: document.getElementById('search-authors-group'),
    authorsList: document.getElementById('search-authors-list'),
    authorsMore: document.getElementById('search-authors-more'),

    tagsGroup: document.getElementById('search-tags-group'),
    tagsCloud: document.getElementById('search-tags-cloud'),
    tagsMore: document.getElementById('search-tags-more'),

    typedPosts: document.getElementById('search-typed-posts'),
    typedAuthors: document.getElementById('search-typed-authors'),
    typedTags: document.getElementById('search-typed-tags'),

    pagination: document.getElementById('search-pagination'),
    footerYear: document.getElementById('footer-year'),
  };

  // ============================================================
  // URL <-> state
  // ============================================================

  /**
   * Read the URL query string into state.
   * Call this ONLY on initial page load (or on real navigations
   * like back/forward), never from within load().
   */
  function readStateFromURL() {
    const p = new URLSearchParams(window.location.search);
    state.q = (p.get('q') || '').trim();
    state.type = p.get('type') || 'all';
    state.page = Math.max(1, parseInt(p.get('page'), 10) || 1);
  }

  /**
   * Reflect the current state into the URL without reloading.
   * Call this after every state change.
   */
  function writeStateToURL() {
    const p = new URLSearchParams();
    if (state.q) p.set('q', state.q);
    if (state.type !== 'all') p.set('type', state.type);
    if (state.page > 1) p.set('page', String(state.page));
    const qs = p.toString();
    const url = window.location.pathname + (qs ? '?' + qs : '');
    window.history.replaceState({}, '', url);
  }

  // ============================================================
  // Rendering
  // ============================================================

  function renderTabs() {
    for (const tab of els.tabs.querySelectorAll('.search-tab')) {
      const type = tab.dataset.type;
      tab.classList.toggle('is-active', type === state.type);
    }
  }

  function renderAuthorCard(author) {
    const url = `/author/${encodeURIComponent(author.username)}/`;
    const avatar = author.avatar_url || '/static/img/default-avatar.jpg';
    const name = author.display_name || author.username;
    return `
      <a class="author-card-mini" href="${url}">
        <img class="author-card-mini__avatar" src="${escapeHtml(avatar)}" alt="">
        <div class="author-card-mini__meta">
          <div class="author-card-mini__name">${escapeHtml(name)}</div>
          <div class="author-card-mini__handle">@${escapeHtml(author.username)}</div>
        </div>
      </a>
    `;
  }

  function renderTagChip(tag) {
    const url = `/posts/?tag=${encodeURIComponent(tag.slug)}`;
    return `
      <a class="tag-chip" href="${url}">
        #${escapeHtml(tag.name)}
        <span class="tag-chip__count">${tag.usage_count ?? 0}</span>
      </a>
    `;
  }

  function renderMixed(data) {
    els.mixed.hidden = false;
    els.typed.hidden = true;
    els.pagination.hidden = true;

    const posts = data.posts || { results: [], count: 0 };
    const authors = data.authors || { results: [], count: 0 };
    const tags = data.tags || { results: [], count: 0 };

    // Posts
    if (posts.results && posts.results.length) {
      els.postsGrid.innerHTML = posts.results.map((p) => renderCard(p)).join('');
      els.postsGroup.hidden = false;
      els.postsMore.href = `?q=${encodeURIComponent(state.q)}&type=post`;
    } else {
      els.postsGroup.hidden = true;
    }

    // Authors
    if (authors.results && authors.results.length) {
      els.authorsList.innerHTML = authors.results.map(renderAuthorCard).join('');
      els.authorsGroup.hidden = false;
      els.authorsMore.href = `?q=${encodeURIComponent(state.q)}&type=author`;
    } else {
      els.authorsGroup.hidden = true;
    }

    // Tags
    if (tags.results && tags.results.length) {
      els.tagsCloud.innerHTML = tags.results.map(renderTagChip).join('');
      els.tagsGroup.hidden = false;
      els.tagsMore.href = `?q=${encodeURIComponent(state.q)}&type=tag`;
    } else {
      els.tagsGroup.hidden = true;
    }

    const total = (posts.count || 0) + (authors.count || 0) + (tags.count || 0);

    if (total === 0) {
      showEmpty();
    } else {
      els.subtitle.textContent = `${total} result${total === 1 ? '' : 's'}`;
    }
  }

  function renderTyped(data) {
    els.mixed.hidden = true;
    els.typed.hidden = false;

    els.typedPosts.innerHTML = '';
    els.typedAuthors.innerHTML = '';
    els.typedTags.innerHTML = '';

    const results = data.results || [];

    if (state.type === 'post') {
      els.typedPosts.innerHTML = results.map((p) => renderCard(p)).join('');
    } else if (state.type === 'author') {
      els.typedAuthors.innerHTML = results.map(renderAuthorCard).join('');
    } else if (state.type === 'tag') {
      els.typedTags.innerHTML = results.map(renderTagChip).join('');
    }

    if (!results.length) {
      showEmpty();
      return;
    }

    const count = data.count || results.length;
    els.subtitle.textContent = `${count} result${count === 1 ? '' : 's'}`;

    renderPagination(data);
  }

  function renderPagination(data) {
    const count = data.count || 0;
    const pageSize = 12;
    const totalPages = Math.max(1, Math.ceil(count / pageSize));
    const current = state.page;

    if (totalPages <= 1 || state.type === 'all') {
      els.pagination.hidden = true;
      return;
    }
    els.pagination.hidden = false;

    const items = [];
    const push = (p) => {
      const active = p === current;
      items.push(
        `<button type="button" data-page="${p}" ${active ? 'class="is-active"' : ''}>${p}</button>`
      );
    };
    const ellipsis = () =>
      items.push('<span class="pagination__ellipsis">…</span>');

    items.push(
      `<button type="button" data-page="${current - 1}" ${data.previous ? '' : 'disabled'}>‹</button>`
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
      `<button type="button" data-page="${current + 1}" ${data.next ? '' : 'disabled'}>›</button>`
    );

    els.pagination.innerHTML = items.join('');
  }

  // ============================================================
  // States
  // ============================================================

  function showLoading() {
    els.loading.hidden = false;
    els.empty.hidden = true;
    els.error.hidden = true;
    els.mixed.hidden = true;
    els.typed.hidden = true;
    els.pagination.hidden = true;
  }

  function showEmpty() {
    els.loading.hidden = true;
    els.error.hidden = true;
    els.mixed.hidden = true;
    els.typed.hidden = true;
    els.pagination.hidden = true;
    els.emptyHint.textContent = `No results for "${state.q}".`;
    els.empty.hidden = false;
  }

  function showError(message) {
    els.loading.hidden = true;
    els.empty.hidden = true;
    els.mixed.hidden = true;
    els.typed.hidden = true;
    els.pagination.hidden = true;
    els.errorMessage.textContent = message;
    els.error.hidden = false;
  }

  function hideStates() {
    els.loading.hidden = true;
    els.empty.hidden = true;
    els.error.hidden = true;
  }

  // ============================================================
  // Fetch
  // ============================================================

  async function fetchMixed() {
    const p = new URLSearchParams();
    p.set('q', state.q);
    return apiFetch(`/search/?${p.toString()}`);
  }

  async function fetchTyped() {
    const p = new URLSearchParams();
    p.set('q', state.q);
    p.set('type', state.type);
    p.set('page', String(state.page));
    return apiFetch(`/search/?${p.toString()}`);
  }

  // ============================================================
  // Load — reads from state, never from the URL
  // ============================================================

  async function load() {
    writeStateToURL();
    renderTabs();

    if (!state.q || state.q.length < 2) {
      els.title.textContent = 'Search';
      els.subtitle.textContent = 'Type at least 2 characters to search.';
      els.loading.hidden = true;
      els.empty.hidden = true;
      els.error.hidden = true;
      els.mixed.hidden = true;
      els.typed.hidden = true;
      els.pagination.hidden = true;
      return;
    }

    els.title.textContent = `Search: "${state.q}"`;
    els.subtitle.textContent = '';

    showLoading();

    try {
      const data =
        state.type === 'all'
          ? await fetchMixed()
          : await fetchTyped();

      hideStates();

      if (state.type === 'all') {
        renderMixed(data);
      } else {
        renderTyped(data);
      }
    } catch (err) {
      console.error(err);
      showError(
        (err.body && (err.body.detail || err.body.message)) ||
          'Could not complete the search. Please try again.'
      );
    }
  }

  // ============================================================
  // Events
  // ============================================================

  els.tabs.addEventListener('click', (e) => {
    const tab = e.target.closest('.search-tab');
    if (!tab) return;
    e.preventDefault();

    const newType = tab.dataset.type;

    // No-op if already on this tab
    if (newType === state.type) return;

    state.type = newType;
    state.page = 1;
    load();
  });

  els.pagination.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-page]');
    if (!btn || btn.disabled) return;
    const page = parseInt(btn.dataset.page, 10);
    if (!Number.isFinite(page) || page === state.page) return;
    state.page = page;
    load();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // ============================================================
  // Init — read URL once, then load
  // ============================================================

  document.addEventListener('DOMContentLoaded', () => {
    if (els.footerYear) {
      els.footerYear.textContent = document.body.dataset.year || new Date().getFullYear();
    }

    readStateFromURL();
    load();
  });
})();
