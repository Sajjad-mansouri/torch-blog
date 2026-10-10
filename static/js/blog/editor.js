// static/js/blog/editor.js
//
// Editor dashboard — tabs for review queue, all posts, featured,
// comments, users, taxonomy, settings, and activity log.

(() => {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  // ============================================================
  // Utilities
  // ============================================================

  const escapeHTML = (s) => s == null ? '' : String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

  const formatDate = (iso) => {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleDateString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
      });
    } catch { return ''; }
  };

  const formatDateTime = (iso) => {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch { return ''; }
  };

  const formatNumber = (n) => {
    if (n == null) return '0';
    if (n < 1000) return String(n);
    if (n < 1_000_000) return (n / 1000).toFixed(n < 10_000 ? 1 : 0) + 'k';
    return (n / 1_000_000).toFixed(1) + 'M';
  };

  const getInitials = (name) => {
    if (!name) return '?';
    return name.trim().split(/\s+/).slice(0, 2)
      .map((p) => p[0]?.toUpperCase() || '').join('');
  };

  const humanStatus = (s) => ({
    draft: 'Draft', pending: 'Pending', changes_requested: 'Changes requested',
    approved: 'Approved', scheduled: 'Scheduled', published: 'Published',
    rejected: 'Rejected', unpublished: 'Unpublished', archived: 'Archived',
  }[s] || s);

  const humanAction = (a) => ({
    post_created: 'Post created', post_edited: 'Post edited',
    post_submitted: 'Post submitted', post_published: 'Post published',
    post_rejected: 'Post rejected', post_unpublished: 'Post unpublished',
    post_deleted: 'Post deleted', post_restored: 'Post restored',
    comment_deleted: 'Comment deleted', user_role_changed: 'User role changed',
    user_banned: 'User banned', settings_updated: 'Settings updated',
  }[a] || a);

  function toast(message, type = 'info') {
    const host = $('#toast-host');
    if (!host) return;
    const el = document.createElement('div');
    el.className = `toast toast--${type}`;
    el.textContent = message;
    host.appendChild(el);
    setTimeout(() => {
      el.style.transition = 'opacity 0.25s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 260);
    }, 3200);
  }

  // ============================================================
  // State
  // ============================================================

  const state = {
    activeTab: 'review-queue',
    queuePage: 1,
    postsPage: 1,
    featuredCandidatesPage: 1,
    commentsPage: 1,
    usersPage: 1,
    activityPage: 1,
    postsFilters: { status: '', search: '' },
    commentsFilters: { status: 'pending', search: '' },
    usersFilters: { role: '', search: '' },
    activityFilters: { action: '' },
    featuredSearch: '',
    featuredPosts: [],
    queueCache: [],
    postsCache: [],
    categories: [],
    tags: [],
  };

  // ============================================================
  // Tabs
  // ============================================================

  function activateTab(name) {
    state.activeTab = name;

    $$('.editor-tab').forEach((btn) => {
      const active = btn.dataset.tab === name;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-selected', active ? 'true' : 'false');
    });

    $$('.editor-panel').forEach((panel) => {
      const active = panel.dataset.panel === name;
      panel.classList.toggle('is-active', active);
      panel.hidden = !active;
    });

    if (name === 'review-queue') loadReviewQueue();
    else if (name === 'posts') loadPosts();
    else if (name === 'featured') loadFeatured();
    else if (name === 'comments') loadComments();
    else if (name === 'users') loadUsers();
    else if (name === 'taxonomy') loadTaxonomy();
    else if (name === 'settings') loadSettings();
    else if (name === 'activity') loadActivity();
  }

  // ============================================================
  // Pagination
  // ============================================================

  function renderPagination(container, page, numPages, onGo) {
    container.innerHTML = '';
    if (!numPages || numPages <= 1) return;

    const btn = (label, target, opts = {}) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = label;
      if (opts.active) b.classList.add('is-active');
      if (opts.disabled) b.disabled = true;
      b.addEventListener('click', () => !opts.disabled && onGo(target));
      return b;
    };

    container.appendChild(btn('‹', page - 1, { disabled: page <= 1 }));

    const pages = new Set([1, numPages, page, page - 1, page + 1]);
    const ordered = [...pages].filter((p) => p >= 1 && p <= numPages).sort((a, b) => a - b);

    let prev = 0;
    for (const p of ordered) {
      if (p - prev > 1) {
        const s = document.createElement('span');
        s.className = 'editor-pagination__ellipsis';
        s.textContent = '…';
        container.appendChild(s);
      }
      container.appendChild(btn(String(p), p, { active: p === page }));
      prev = p;
    }

    container.appendChild(btn('›', page + 1, { disabled: page >= numPages }));
  }

  // ============================================================
  // Shared row builders
  // ============================================================

  function statusPill(status) {
    return `<span class="status-pill" data-status="${escapeHTML(status || 'draft')}">
      ${escapeHTML(humanStatus(status || 'draft'))}
    </span>`;
  }

  function authorChip(author) {
    if (!author) return '';
    const name = author.display_name || author.username || 'Unknown';
    return `
      <a href="/author/${encodeURIComponent(author.username)}/" style="display:inline-flex;align-items:center;gap:0.4rem">
        <span style="width:20px;height:20px;border-radius:50%;overflow:hidden;display:inline-block;background:#e5e7eb">
          ${author.avatar_url ? `<img src="${escapeHTML(author.avatar_url)}" style="width:100%;height:100%;object-fit:cover" alt="">` : ''}
        </span>
        <span>${escapeHTML(name)}</span>
      </a>`;
  }

  function reviewContextBlock(post) {
    const status = post.status;
    const reason = post.rejection_reason || post.changes_requested_note || '';
    if (!reason) return '';
    if (status !== 'rejected' && status !== 'changes_requested') return '';

    const isReject = status === 'rejected';
    const label = isReject ? 'Rejection reason' : 'Changes requested';
    const by = post.reviewed_by?.display_name || post.reviewed_by?.username || '';
    const when = post.reviewed_at ? formatDateTime(post.reviewed_at) : '';
    const meta = [by ? `by ${by}` : '', when].filter(Boolean).join(' · ');

    return `
      <div class="review-context ${isReject ? 'review-context--reject' : 'review-context--changes'}">
        <div class="review-context__head">
          <span class="review-context__label">${escapeHTML(label)}</span>
          ${meta ? `<span class="review-context__meta">${escapeHTML(meta)}</span>` : ''}
        </div>
        <p class="review-context__body">${escapeHTML(reason)}</p>
      </div>
    `;
  }

  function findPostBySlug(slug) {
    return (
      state.queueCache.find((p) => p.slug === slug) ||
      state.postsCache.find((p) => p.slug === slug) ||
      state.featuredPosts.find((p) => p.slug === slug) ||
      null
    );
  }

  // ============================================================
  // Review Queue
  // ============================================================

  async function loadReviewQueue(page = state.queuePage) {
    state.queuePage = page;
    const list = $('#queue-list');
    list.innerHTML = '<div class="editor-loading">Loading…</div>';

    try {
      const data = await apiFetch(`/editor/review-queue/?page=${page}`);
      const items = data.results || [];
      state.queueCache = items;

      $('#queue-count').textContent = `${data.count ?? items.length} pending`;
      $('#tab-badge-queue').hidden = !data.count;
      $('#tab-badge-queue').textContent = data.count ?? 0;

      if (!items.length) {
        list.innerHTML = '<div class="editor-empty">No pending posts. Review queue is empty.</div>';
        $('#queue-pagination').innerHTML = '';
        return;
      }

      list.innerHTML = items.map(renderQueueRow).join('');
      renderPagination(
        $('#queue-pagination'),
        page,
        data.num_pages || Math.ceil((data.count || 0) / (data.page_size || 12)),
        (p) => loadReviewQueue(p)
      );
    } catch (err) {
      list.innerHTML = `<div class="editor-empty">Failed to load queue: ${escapeHTML(err?.body?.detail || err.message)}</div>`;
    }
  }

  function renderQueueRow(post) {
    const actions = [
      `<a href="/dashboard/posts/${encodeURIComponent(post.slug)}/preview/"
          target="_blank" rel="noopener" class="btn btn--ghost btn--sm">Preview</a>`,
    ];

    if (post.status === 'rejected' || post.status === 'changes_requested') {
      actions.push(`<button class="btn btn--primary btn--sm" data-action="reconsider" data-slug="${escapeHTML(post.slug)}">Reconsider</button>`);
    }

    actions.push(`<button class="btn btn--primary btn--sm" data-action="approve" data-slug="${escapeHTML(post.slug)}">Approve</button>`);
    actions.push(`<button class="btn btn--ghost btn--sm" data-action="request-changes" data-slug="${escapeHTML(post.slug)}">Request changes</button>`);
    actions.push(`<button class="btn btn--danger btn--sm" data-action="reject" data-slug="${escapeHTML(post.slug)}">Reject</button>`);

    return `
      <div class="editor-row" data-slug="${escapeHTML(post.slug)}">
        <div class="editor-row__main">
          <div class="editor-row__meta">
            ${statusPill(post.status)}
            <span>${authorChip(post.author)}</span>
            <span>·</span>
            <span>submitted ${escapeHTML(formatDateTime(post.updated_at))}</span>
          </div>
          <h3 class="editor-row__title">
            <a href="/dashboard/posts/${encodeURIComponent(post.slug)}/preview/"
               target="_blank" rel="noopener">
              ${escapeHTML(post.title)}
            </a>
          </h3>
          ${reviewContextBlock(post)}
          ${post.summary ? `<p class="editor-row__summary">${escapeHTML(post.summary)}</p>` : ''}
          <div class="editor-row__stats">
            <span>👁 ${formatNumber(post.views_count || 0)}</span>
            <span>♥ ${formatNumber(post.like_count || 0)}</span>
            <span>💬 ${formatNumber(post.comment_count || 0)}</span>
          </div>
        </div>
        <div class="editor-row__actions">${actions.join('')}</div>
      </div>
    `;
  }

  // ============================================================
  // All Posts
  // ============================================================

  async function loadPosts(page = state.postsPage) {
    state.postsPage = page;
    const list = $('#posts-list');
    list.innerHTML = '<div class="editor-loading">Loading…</div>';

    const qs = new URLSearchParams();
    qs.set('page', page);
    if (state.postsFilters.status) qs.set('status', state.postsFilters.status);
    if (state.postsFilters.search) qs.set('search', state.postsFilters.search);

    try {
      const data = await apiFetch(`/editor/posts-list/?${qs.toString()}`);
      const items = data.results || [];
      state.postsCache = items;

      $('#posts-count').textContent = `${data.count ?? items.length} posts`;

      if (!items.length) {
        list.innerHTML = '<div class="editor-empty">No posts match the current filters.</div>';
        $('#posts-pagination').innerHTML = '';
        return;
      }

      list.innerHTML = items.map(renderPostRow).join('');
      renderPagination(
        $('#posts-pagination'),
        page,
        data.num_pages || Math.ceil((data.count || 0) / (data.page_size || 12)),
        (p) => loadPosts(p)
      );
    } catch (err) {
      list.innerHTML = `<div class="editor-empty">Failed to load posts: ${escapeHTML(err?.body?.detail || err.message)}</div>`;
    }
  }

  function renderPostRow(post) {
    const actions = [];

    if (post.status === 'pending') {
      actions.push(`<button class="btn btn--primary btn--sm" data-action="approve" data-slug="${escapeHTML(post.slug)}">Approve</button>`);
      actions.push(`<button class="btn btn--ghost btn--sm" data-action="request-changes" data-slug="${escapeHTML(post.slug)}">Changes</button>`);
      actions.push(`<button class="btn btn--danger btn--sm" data-action="reject" data-slug="${escapeHTML(post.slug)}">Reject</button>`);
    } else if (post.status === 'rejected' || post.status === 'changes_requested') {
      actions.push(`<a href="/dashboard/posts/${encodeURIComponent(post.slug)}/preview/" target="_blank" class="btn btn--ghost btn--sm">Preview</a>`);
      actions.push(`<button class="btn btn--primary btn--sm" data-action="reconsider" data-slug="${escapeHTML(post.slug)}">Reconsider</button>`);
      actions.push(`<button class="btn btn--ghost btn--sm" data-action="approve" data-slug="${escapeHTML(post.slug)}">Approve</button>`);
      actions.push(`<button class="btn btn--danger btn--sm" data-action="reject" data-slug="${escapeHTML(post.slug)}">Reject</button>`);
    } else if (post.status === 'published') {
      actions.push(`<a href="/posts/${encodeURIComponent(post.slug)}/" target="_blank" class="btn btn--ghost btn--sm">View</a>`);
      actions.push(`<button class="btn btn--danger btn--sm" data-action="unpublish" data-slug="${escapeHTML(post.slug)}">Unpublish</button>`);
    } else {
      actions.push(`<a href="/dashboard/posts/${encodeURIComponent(post.slug)}/preview/" target="_blank" class="btn btn--ghost btn--sm">Preview</a>`);
    }

    return `
      <div class="editor-row" data-slug="${escapeHTML(post.slug)}">
        <div class="editor-row__main">
          <div class="editor-row__meta">
            ${statusPill(post.status)}
            <span>${authorChip(post.author)}</span>
            <span>·</span>
            <span>updated ${escapeHTML(formatDate(post.updated_at))}</span>
          </div>
          <h3 class="editor-row__title">${escapeHTML(post.title)}</h3>
          ${reviewContextBlock(post)}
          ${post.summary ? `<p class="editor-row__summary">${escapeHTML(post.summary)}</p>` : ''}
          <div class="editor-row__stats">
            <span>👁 ${formatNumber(post.views_count || 0)}</span>
            <span>♥ ${formatNumber(post.like_count || 0)}</span>
            <span>💬 ${formatNumber(post.comment_count || 0)}</span>
          </div>
        </div>
        <div class="editor-row__actions">${actions.join('')}</div>
      </div>
    `;
  }

  // ============================================================
  // Featured
  // ============================================================

  async function loadFeatured() {
    const list = $('#featured-list');
    list.innerHTML = '<div class="editor-loading">Loading…</div>';

    try {
      const data = await apiFetch('/editor/featured/');
      const items = Array.isArray(data) ? data : (data.results || []);
      state.featuredPosts = items;

      $('#featured-count').textContent = `${items.length} featured`;
      $('#tab-badge-featured').hidden = !items.length;
      $('#tab-badge-featured').textContent = items.length;

      if (!items.length) {
        list.innerHTML = '<div class="editor-empty">No featured posts yet. Click “Add post”.</div>';
        return;
      }

      list.innerHTML = items.map((p, i) => renderFeaturedRow(p, i)).join('');
      enableDragReorder(list);
    } catch (err) {
      list.innerHTML = `<div class="editor-empty">Failed to load featured: ${escapeHTML(err?.body?.detail || err.message)}</div>`;
    }
  }

  function renderFeaturedRow(post, index) {
    return `
      <div class="editor-row" data-id="${post.id}" data-slug="${escapeHTML(post.slug)}" draggable="true">
        <span class="editor-row__handle" aria-hidden="true">⋮⋮</span>
        <div class="editor-row__main">
          <div class="editor-row__meta">
            <span class="editor-row__order">${index + 1}</span>
            ${statusPill(post.status)}
            <span>${authorChip(post.author)}</span>
            <span>·</span>
            <span>published ${escapeHTML(formatDate(post.published_at))}</span>
          </div>
          <h3 class="editor-row__title">
            <a href="/posts/${encodeURIComponent(post.slug)}/" target="_blank" rel="noopener">
              ${escapeHTML(post.title)}
            </a>
          </h3>
          ${post.summary ? `<p class="editor-row__summary">${escapeHTML(post.summary)}</p>` : ''}
        </div>
        <div class="editor-row__actions">
          <button class="btn btn--danger btn--sm" data-action="featured-remove" data-slug="${escapeHTML(post.slug)}" data-title="${escapeHTML(post.title)}">
            Remove
          </button>
        </div>
      </div>
    `;
  }

  function enableDragReorder(list) {
    let dragging = null;

    list.addEventListener('dragstart', (e) => {
      const row = e.target.closest('.editor-row');
      if (!row || !row.draggable) return;
      dragging = row;
      row.classList.add('is-dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', row.dataset.id || '');
    });

    list.addEventListener('dragover', (e) => {
      if (!dragging) return;
      e.preventDefault();
      const target = e.target.closest('.editor-row');
      if (!target || target === dragging) return;

      list.querySelectorAll('.is-drop-target')
        .forEach((el) => el.classList.remove('is-drop-target'));
      target.classList.add('is-drop-target');
    });

    list.addEventListener('dragleave', (e) => {
      const target = e.target.closest('.editor-row');
      if (target) target.classList.remove('is-drop-target');
    });

    list.addEventListener('drop', async (e) => {
      if (!dragging) return;
      e.preventDefault();
      const target = e.target.closest('.editor-row');
      if (!target || target === dragging) return;

      const rect = target.getBoundingClientRect();
      const after = e.clientY > rect.top + rect.height / 2;

      if (after) target.after(dragging);
      else target.before(dragging);

      target.classList.remove('is-drop-target');
      dragging.classList.remove('is-dragging');

      [...list.querySelectorAll('.editor-row')].forEach((row, i) => {
        const badge = row.querySelector('.editor-row__order');
        if (badge) badge.textContent = String(i + 1);
      });

      await saveFeaturedOrder(list);
    });

    list.addEventListener('dragend', () => {
      if (dragging) dragging.classList.remove('is-dragging');
      list.querySelectorAll('.is-drop-target')
        .forEach((el) => el.classList.remove('is-drop-target'));
      dragging = null;
    });
  }

  async function saveFeaturedOrder(list) {
    const rows = [...list.querySelectorAll('.editor-row')];
    const items = rows.map((row, i) => ({
      id: Number(row.dataset.id),
      order: i,
    }));

    try {
      await apiFetch('/editor/featured/reorder/', {
        method: 'PATCH',
        body: JSON.stringify({ items }),
      });
      toast('Order saved.', 'ok');
    } catch (err) {
      toast('Could not save order: ' + (err?.body?.detail || err.message), 'error');
      loadFeatured();
    }
  }

  async function openFeaturedAddModal() {
    $('#featured-add-modal').hidden = false;
    $('#featured-search').value = '';
    state.featuredCandidatesPage = 1;
    state.featuredSearch = '';
    await loadFeaturedCandidates();
    $('#featured-search').focus();
  }

  function closeFeaturedAddModal() {
    $('#featured-add-modal').hidden = true;
  }

  async function loadFeaturedCandidates(page = 1) {
    state.featuredCandidatesPage = page;
    const list = $('#featured-candidates');
    list.innerHTML = '<div class="editor-loading">Loading…</div>';

    const qs = new URLSearchParams();
    qs.set('page', page);
    if (state.featuredSearch) qs.set('search', state.featuredSearch);

    try {
      const data = await apiFetch(`/editor/featured/candidates/?${qs.toString()}`);
      const items = data.results || [];

      if (!items.length) {
        list.innerHTML = '<div class="editor-empty">No posts available to feature.</div>';
        $('#featured-candidates-pagination').innerHTML = '';
        return;
      }

      list.innerHTML = items.map((p) => `
        <div class="editor-row" data-slug="${escapeHTML(p.slug)}">
          <div class="editor-row__main">
            <div class="editor-row__meta">
              ${statusPill(p.status)}
              <span>${authorChip(p.author)}</span>
              <span>·</span>
              <span>published ${escapeHTML(formatDate(p.published_at))}</span>
            </div>
            <h3 class="editor-row__title">${escapeHTML(p.title)}</h3>
          </div>
          <div class="editor-row__actions">
            <button class="btn btn--primary btn--sm" data-action="featured-add" data-slug="${escapeHTML(p.slug)}">Add</button>
          </div>
        </div>
      `).join('');

      renderPagination(
        $('#featured-candidates-pagination'),
        page,
        data.num_pages || Math.ceil((data.count || 0) / (data.page_size || 12)),
        (p) => loadFeaturedCandidates(p)
      );
    } catch (err) {
      list.innerHTML = `<div class="editor-empty">Failed: ${escapeHTML(err?.body?.detail || err.message)}</div>`;
    }
  }

  // ============================================================
  // Comments
  // ============================================================

  async function loadComments(page = state.commentsPage) {
    state.commentsPage = page;
    const list = $('#comments-list');
    list.innerHTML = '<div class="editor-loading">Loading…</div>';

    const qs = new URLSearchParams();
    qs.set('page', page);
    if (state.commentsFilters.status) qs.set('status', state.commentsFilters.status);
    if (state.commentsFilters.search) qs.set('search', state.commentsFilters.search);

    try {
      const data = await apiFetch(`/editor/comments-list/?${qs.toString()}`);
      const items = data.results || [];
      $('#comments-count').textContent = `${data.count ?? items.length} comments`;

      if (state.commentsFilters.status === 'pending') {
        $('#tab-badge-comments').hidden = !data.count;
        $('#tab-badge-comments').textContent = data.count ?? 0;
      }

      if (!items.length) {
        list.innerHTML = '<div class="editor-empty">No comments match the current filters.</div>';
        $('#comments-pagination').innerHTML = '';
        return;
      }

      list.innerHTML = items.map(renderCommentRow).join('');
      renderPagination(
        $('#comments-pagination'),
        page,
        data.num_pages || Math.ceil((data.count || 0) / (data.page_size || 12)),
        (p) => loadComments(p)
      );
    } catch (err) {
      list.innerHTML = `<div class="editor-empty">Failed to load comments: ${escapeHTML(err?.body?.detail || err.message)}</div>`;
    }
  }

  function renderCommentRow(comment) {
    return `
      <div class="editor-row" data-id="${comment.id}">
        <div class="editor-row__main">
          <div class="editor-row__meta">
            <span class="status-pill" data-status="${escapeHTML(comment.status || 'pending')}">
              ${escapeHTML(comment.status || 'pending')}
            </span>
            <span>${escapeHTML(comment.author?.username || comment.author_username || 'Unknown')}</span>
            <span>·</span>
            <span>on <a href="/posts/${encodeURIComponent(comment.post_slug || '')}/" target="_blank">${escapeHTML(comment.post_title || comment.post || '')}</a></span>
            <span>·</span>
            <span>${escapeHTML(formatDateTime(comment.created_at))}</span>
          </div>
          <p class="editor-row__body">${escapeHTML(comment.body)}</p>
        </div>
        <div class="editor-row__actions">
          <button class="btn btn--primary btn--sm" data-action="comment-approve" data-id="${comment.id}">Approve</button>
          <button class="btn btn--ghost btn--sm" data-action="comment-reject" data-id="${comment.id}">Reject</button>
          <button class="btn btn--ghost btn--sm" data-action="comment-spam" data-id="${comment.id}">Spam</button>
          <button class="btn btn--danger btn--sm" data-action="comment-delete" data-id="${comment.id}">Delete</button>
        </div>
      </div>
    `;
  }

  // ============================================================
  // Users
  // ============================================================

  async function loadUsers(page = state.usersPage) {
    state.usersPage = page;
    const list = $('#users-list');
    list.innerHTML = '<div class="editor-loading">Loading…</div>';

    const qs = new URLSearchParams();
    qs.set('page', page);
    if (state.usersFilters.role) qs.set('role', state.usersFilters.role);
    if (state.usersFilters.search) qs.set('search', state.usersFilters.search);

    try {
      const data = await apiFetch(`/editor/users-list/?${qs.toString()}`);
      const items = data.results || [];
      $('#users-count').textContent = `${data.count ?? items.length} users`;

      if (!items.length) {
        list.innerHTML = '<div class="editor-empty">No users match the current filters.</div>';
        $('#users-pagination').innerHTML = '';
        return;
      }

      list.innerHTML = items.map(renderUserRow).join('');
      renderPagination(
        $('#users-pagination'),
        page,
        data.num_pages || Math.ceil((data.count || 0) / (data.page_size || 12)),
        (p) => loadUsers(p)
      );
    } catch (err) {
      list.innerHTML = `<div class="editor-empty">Failed to load users: ${escapeHTML(err?.body?.detail || err.message)}</div>`;
    }
  }

  function renderUserRow(user) {
    const name = user.display_name || user.username;
    const avatar = user.avatar_url
      ? `<img class="editor-row__avatar" src="${escapeHTML(user.avatar_url)}" alt="">`
      : `<span class="editor-row__avatar" style="display:inline-flex;align-items:center;justify-content:center;font-weight:700;color:var(--text-muted)">${escapeHTML(getInitials(name))}</span>`;

    return `
      <div class="editor-row" data-id="${user.id}">
        ${avatar}
        <div class="editor-row__main">
          <div class="editor-row__meta">
            <span class="status-pill" data-status="approved">${escapeHTML(user.role || 'reader')}</span>
            <strong>${escapeHTML(name)}</strong>
            <span>@${escapeHTML(user.username)}</span>
          </div>
        </div>
        <div class="editor-row__actions">
          <button class="btn btn--ghost btn--sm" data-action="change-role" data-id="${user.id}" data-username="${escapeHTML(user.username)}" data-role="${escapeHTML(user.role || 'reader')}">Change role</button>
          <button class="btn btn--danger btn--sm" data-action="ban-user" data-id="${user.id}" data-username="${escapeHTML(user.username)}">Ban</button>
          <button class="btn btn--ghost btn--sm" data-action="unban-user" data-id="${user.id}" data-username="${escapeHTML(user.username)}">Unban</button>
        </div>
      </div>
    `;
  }

  // ============================================================
  // Taxonomy
  // ============================================================

  async function loadTaxonomy() {
    const catList = $('#categories-list');
    const tagList = $('#tags-list');
    catList.innerHTML = '<div class="editor-loading">Loading…</div>';
    tagList.innerHTML = '<div class="editor-loading">Loading…</div>';

    try {
      const [categories, tags] = await Promise.all([
        apiFetch('/editor/categories/'),
        apiFetch('/editor/tags/'),
      ]);

      state.categories = Array.isArray(categories) ? categories : (categories.results || []);
      state.tags = Array.isArray(tags) ? tags : (tags.results || []);

      catList.innerHTML = state.categories.length
        ? state.categories.map(renderCategoryRow).join('')
        : '<div class="editor-empty">No categories yet.</div>';

      tagList.innerHTML = state.tags.length
        ? state.tags.map(renderTagRow).join('')
        : '<div class="editor-empty">No tags yet.</div>';
    } catch (err) {
      catList.innerHTML = `<div class="editor-empty">Failed: ${escapeHTML(err?.body?.detail || err.message)}</div>`;
      tagList.innerHTML = '';
    }
  }

  function renderCategoryRow(c) {
    return `
      <div class="editor-row" data-slug="${escapeHTML(c.slug)}">
        <div class="editor-row__main">
          <div class="editor-row__title">${escapeHTML(c.name)}</div>
          <div class="editor-row__meta">
            <code>${escapeHTML(c.slug)}</code>
            <span>·</span>
            <span>${c.post_count ?? 0} posts</span>
          </div>
        </div>
        <div class="editor-row__actions">
          <button class="btn btn--ghost btn--sm" data-action="edit-category" data-slug="${escapeHTML(c.slug)}">Edit</button>
          <button class="btn btn--danger btn--sm" data-action="delete-category" data-slug="${escapeHTML(c.slug)}" data-name="${escapeHTML(c.name)}">Delete</button>
        </div>
      </div>
    `;
  }

  function renderTagRow(t) {
    return `
      <div class="editor-row" data-slug="${escapeHTML(t.slug)}">
        <div class="editor-row__main">
          <div class="editor-row__title">${escapeHTML(t.name)}</div>
          <div class="editor-row__meta">
            <code>${escapeHTML(t.slug)}</code>
            <span>·</span>
            <span>${t.usage_count ?? 0} posts</span>
          </div>
        </div>
        <div class="editor-row__actions">
          <button class="btn btn--ghost btn--sm" data-action="edit-tag" data-slug="${escapeHTML(t.slug)}">Edit</button>
          <button class="btn btn--danger btn--sm" data-action="delete-tag" data-slug="${escapeHTML(t.slug)}" data-name="${escapeHTML(t.name)}">Delete</button>
        </div>
      </div>
    `;
  }

  // ============================================================
  // Settings
  // ============================================================

  async function loadSettings() {
    const form = $('#settings-form');
    try {
      const data = await apiFetch('/editor/settings/');
      const fields = ['site_title', 'tagline', 'hero_text', 'hero_cta_text',
                      'hero_cta_link', 'posts_per_page', 'featured_count', 'footer_text'];
      for (const name of fields) {
        const input = form.elements[name];
        if (!input) continue;
        if (input.type === 'checkbox') input.checked = !!data[name];
        else input.value = data[name] ?? '';
      }
    } catch (err) {
      toast('Failed to load settings: ' + (err?.body?.detail || err.message), 'error');
    }
  }

  async function saveSettings() {
    const form = $('#settings-form');
    const payload = new FormData(form);
    try {
      await apiFetch('/editor/settings/', {
        method: 'PATCH',
        body: payload,
      });
      toast('Settings saved.', 'ok');
    } catch (err) {
      toast('Save failed: ' + (err?.body?.detail || err.message), 'error');
    }
  }

  // ============================================================
  // Activity Log
  // ============================================================

  async function loadActivity(page = state.activityPage) {
    state.activityPage = page;
    const list = $('#activity-list');
    list.innerHTML = '<div class="editor-loading">Loading…</div>';

    const qs = new URLSearchParams();
    qs.set('page', page);
    if (state.activityFilters.action) qs.set('action', state.activityFilters.action);

    try {
      const data = await apiFetch(`/editor/activity-log/?${qs.toString()}`);
      const items = data.results || [];
      $('#activity-count').textContent = `${data.count ?? items.length} entries`;

      if (!items.length) {
        list.innerHTML = '<div class="editor-empty">No activity yet.</div>';
        $('#activity-pagination').innerHTML = '';
        return;
      }

      list.innerHTML = items.map(renderActivityRow).join('');
      renderPagination(
        $('#activity-pagination'),
        page,
        data.num_pages || Math.ceil((data.count || 0) / (data.page_size || 12)),
        (p) => loadActivity(p)
      );
    } catch (err) {
      list.innerHTML = `<div class="editor-empty">Failed to load activity: ${escapeHTML(err?.body?.detail || err.message)}</div>`;
    }
  }

  function renderActivityRow(entry) {
    const who = entry.user?.display_name || entry.user?.username || 'System';
    return `
      <div class="editor-row">
        <div class="editor-row__main">
          <div class="editor-row__meta">
            <strong>${escapeHTML(who)}</strong>
            <span>·</span>
            <span>${escapeHTML(entry.action_display || humanAction(entry.action))}</span>
            ${entry.target_type ? `<span>·</span><span>${escapeHTML(entry.target_type)} #${entry.target_id ?? ''}</span>` : ''}
            <span>·</span>
            <span>${escapeHTML(formatDateTime(entry.created_at))}</span>
          </div>
          ${entry.description ? `<p class="editor-row__body">${escapeHTML(entry.description)}</p>` : ''}
        </div>
      </div>
    `;
  }

  // ============================================================
  // Modals
  // ============================================================

  let confirmResolver = null;

  function openConfirm({ title, message, confirmLabel = 'Delete', danger = true }) {
    return new Promise((resolve) => {
      confirmResolver = resolve;
      $('#confirm-title').textContent = title;
      $('#confirm-message').textContent = message;
      const ok = $('#confirm-ok');
      ok.textContent = confirmLabel;
      ok.className = danger ? 'btn btn--danger' : 'btn btn--primary';
      $('#confirm-modal').hidden = false;
    });
  }

  function closeConfirm(result) {
    $('#confirm-modal').hidden = true;
    if (confirmResolver) {
      confirmResolver(result);
      confirmResolver = null;
    }
  }

  let pendingPostAction = null;

  function openPostDecision({ slug, action, title, message, needsNote, existingNote = '', existingBy = '' }) {
    pendingPostAction = { slug, action };
    $('#post-decision-title').textContent = title;
    $('#post-decision-message').textContent = message;

    const note = $('#post-decision-note');
    note.value = existingNote || '';
    note.hidden = !needsNote;

    const meta = $('#post-decision-existing-meta');
    meta.textContent = existingBy ? `Previous note by ${existingBy}` : '';
    meta.hidden = !existingBy;

    $('#post-decision-confirm').textContent = title;
    $('#post-decision-modal').hidden = false;
    if (needsNote) note.focus();
  }

  function closePostDecision() {
    $('#post-decision-modal').hidden = true;
    pendingPostAction = null;
  }

  async function submitPostDecision() {
    if (!pendingPostAction) return;
    const { slug, action } = pendingPostAction;
    const note = $('#post-decision-note').value.trim();

    const urls = {
      approve: `/editor/posts/${encodeURIComponent(slug)}/approve/`,
      reject: `/editor/posts/${encodeURIComponent(slug)}/reject/`,
      'request-changes': `/editor/posts/${encodeURIComponent(slug)}/request-changes/`,
      unpublish: `/editor/posts/${encodeURIComponent(slug)}/unpublish/`,
    };
    const bodies = {
      approve: {},
      reject: { reason: note },
      'request-changes': { note },
      unpublish: { reason: note },
    };

    try {
      await apiFetch(urls[action], {
        method: 'POST',
        body: JSON.stringify(bodies[action]),
      });
      toast('Action completed.', 'ok');
      closePostDecision();
      if (state.activeTab === 'review-queue') loadReviewQueue();
      else if (state.activeTab === 'posts') loadPosts();
    } catch (err) {
      toast(err?.body?.detail || 'Action failed.', 'error');
    }
  }

  let taxonomyMode = null;

  function openTaxonomyModal({ type, existing }) {
    taxonomyMode = { type, slug: existing?.slug || null };
    const isCategory = type === 'category';

    $('#taxonomy-modal-title').textContent =
      (existing ? 'Edit ' : 'New ') + (isCategory ? 'category' : 'tag');

    $('#tax-description-field').hidden = !isCategory;
    $('#tax-parent-field').hidden = !isCategory;
    $('#tax-order-field').hidden = !isCategory;
    $('#tax-active-field').hidden = !isCategory;

    $('#tax-name').value = existing?.name || '';
    $('#tax-slug').value = existing?.slug || '';
    $('#tax-description').value = existing?.description || '';
    $('#tax-order').value = existing?.order ?? 0;
    $('#tax-active').checked = existing ? !!existing.is_active : true;

    if (isCategory) {
      const parentSelect = $('#tax-parent');
      parentSelect.innerHTML = '<option value="">— None —</option>';
      for (const c of state.categories) {
        if (existing && c.slug === existing.slug) continue;
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.name;
        parentSelect.appendChild(opt);
      }
      parentSelect.value = existing?.parent?.id ?? existing?.parent ?? '';
    }

    $('#taxonomy-modal').hidden = false;
    $('#tax-name').focus();
  }

  function closeTaxonomyModal() {
    $('#taxonomy-modal').hidden = true;
    taxonomyMode = null;
  }

  async function submitTaxonomyForm(e) {
    e.preventDefault();
    if (!taxonomyMode) return;
    const { type, slug } = taxonomyMode;
    const isCategory = type === 'category';

    const payload = new FormData();
    payload.append('name', $('#tax-name').value.trim());
    const slugVal = $('#tax-slug').value.trim();
    if (slugVal) payload.append('slug', slugVal);

    if (isCategory) {
      payload.append('description', $('#tax-description').value.trim());
      const parent = $('#tax-parent').value;
      if (parent) payload.append('parent', parent);
      payload.append('order', $('#tax-order').value || '0');
      payload.append('is_active', $('#tax-active').checked ? 'true' : 'false');
    }

    const base = isCategory ? '/editor/categories/' : '/editor/tags/';
    const url = slug ? `${base}${encodeURIComponent(slug)}/` : base;
    const method = slug ? 'PATCH' : 'POST';

    try {
      await apiFetch(url, { method, body: payload });
      toast(`${isCategory ? 'Category' : 'Tag'} saved.`, 'ok');
      closeTaxonomyModal();
      loadTaxonomy();
    } catch (err) {
      toast(err?.body?.detail || JSON.stringify(err?.body) || 'Save failed.', 'error');
    }
  }

  let userAction = null;

  function openUserModal({ id, username, role }) {
    userAction = { id, username, mode: 'role' };
    $('#user-modal-title').textContent = `Change role · ${username}`;
    $('#user-modal-message').textContent = 'Select a new role for this user.';
    $('#user-modal-body').innerHTML = `
      <div class="user-role-select">
        ${['reader', 'author', 'editor'].map((r) => `
          <label class="user-role-option ${role === r ? 'is-active' : ''}">
            <input type="radio" name="user-role" value="${r}" ${role === r ? 'checked' : ''}>
            <span>${r[0].toUpperCase() + r.slice(1)}</span>
          </label>
        `).join('')}
      </div>
    `;
    $('#user-modal-confirm').textContent = 'Save role';
    $('#user-modal').hidden = false;
  }

  function closeUserModal() {
    $('#user-modal').hidden = true;
    userAction = null;
  }

  async function submitUserModal() {
    if (!userAction) return;
    const radio = document.querySelector('input[name="user-role"]:checked');
    if (!radio) return;
    try {
      await apiFetch(`/editor/users/${userAction.id}/role/`, {
        method: 'PATCH',
        body: JSON.stringify({ role: radio.value }),
      });
      toast('Role updated.', 'ok');
      closeUserModal();
      loadUsers();
    } catch (err) {
      toast(err?.body?.detail || 'Role update failed.', 'error');
    }
  }

  // ============================================================
  // Click delegation
  // ============================================================

  async function handleActionClick(e) {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;

    const { action } = btn.dataset;

    if (action === 'approve') {
      openPostDecision({
        slug: btn.dataset.slug,
        action: 'approve',
        title: 'Approve',
        message: 'Publish this post now?',
        needsNote: false,
      });
    } else if (action === 'reject') {
      const post = findPostBySlug(btn.dataset.slug);
      openPostDecision({
        slug: btn.dataset.slug,
        action: 'reject',
        title: 'Reject',
        message: 'Reject this post with a reason:',
        needsNote: true,
        existingNote: post?.rejection_reason || '',
        existingBy: post?.reviewed_by?.display_name || post?.reviewed_by?.username || '',
      });
    } else if (action === 'request-changes') {
      const post = findPostBySlug(btn.dataset.slug);
      openPostDecision({
        slug: btn.dataset.slug,
        action: 'request-changes',
        title: 'Request changes',
        message: 'Explain what the author should change:',
        needsNote: true,
        existingNote: post?.changes_requested_note || '',
        existingBy: post?.reviewed_by?.display_name || post?.reviewed_by?.username || '',
      });
    } else if (action === 'unpublish') {
      const post = findPostBySlug(btn.dataset.slug);
      openPostDecision({
        slug: btn.dataset.slug,
        action: 'unpublish',
        title: 'Unpublish',
        message: 'Unpublish this post. Optionally add a reason:',
        needsNote: true,
        existingNote: post?.rejection_reason || '',
        existingBy: post?.reviewed_by?.display_name || post?.reviewed_by?.username || '',
      });
    } else if (action === 'reconsider') {
      const post = findPostBySlug(btn.dataset.slug);
      const reason = post?.rejection_reason || post?.changes_requested_note || '';
      const shortReason = reason.length > 120 ? reason.slice(0, 120) + '…' : reason;

      const ok = await openConfirm({
        title: 'Reconsider this post?',
        message: reason
          ? `The post will return to the review queue. The previous decision note ("${shortReason}") will be cleared.`
          : 'The post will return to the review queue. The previous decision will be cleared.',
        confirmLabel: 'Reconsider',
        danger: false,
      });
      if (!ok) return;

      try {
        await apiFetch(`/editor/posts/${encodeURIComponent(btn.dataset.slug)}/reconsider/`, {
          method: 'POST',
          body: JSON.stringify({}),
        });
        toast('Post returned to the review queue.', 'ok');
        if (state.activeTab === 'review-queue') loadReviewQueue();
        else if (state.activeTab === 'posts') loadPosts();
      } catch (err) {
        toast(err?.body?.detail || 'Reconsider failed.', 'error');
      }
    }

    else if (action === 'comment-approve' || action === 'comment-reject' || action === 'comment-spam') {
      const endpoint = {
        'comment-approve': 'approve',
        'comment-reject': 'reject',
        'comment-spam': 'spam',
      }[action];
      try {
        await apiFetch(`/editor/comments/${btn.dataset.id}/${endpoint}/`, { method: 'POST' });
        toast('Comment ' + endpoint + '.', 'ok');
        loadComments();
      } catch (err) {
        toast(err?.body?.detail || 'Action failed.', 'error');
      }
    } else if (action === 'comment-delete') {
      const ok = await openConfirm({
        title: 'Delete comment?',
        message: 'This action cannot be undone.',
      });
      if (!ok) return;
      try {
        await apiFetch(`/editor/comments/${btn.dataset.id}/delete/`, { method: 'DELETE' });
        toast('Comment deleted.', 'ok');
        loadComments();
      } catch (err) {
        toast(err?.body?.detail || 'Delete failed.', 'error');
      }
    }

    else if (action === 'change-role') {
      openUserModal({
        id: btn.dataset.id,
        username: btn.dataset.username,
        role: btn.dataset.role,
      });
    } else if (action === 'ban-user') {
      const ok = await openConfirm({
        title: `Ban ${btn.dataset.username}?`,
        message: 'This user will no longer be able to sign in.',
        confirmLabel: 'Ban',
      });
      if (!ok) return;
      try {
        await apiFetch(`/editor/users/${btn.dataset.id}/ban/`, {
          method: 'POST',
          body: JSON.stringify({ reason: '' }),
        });
        toast('User banned.', 'ok');
        loadUsers();
      } catch (err) {
        toast(err?.body?.detail || 'Ban failed.', 'error');
      }
    } else if (action === 'unban-user') {
      try {
        await apiFetch(`/editor/users/${btn.dataset.id}/unban/`, { method: 'POST' });
        toast('User unbanned.', 'ok');
        loadUsers();
      } catch (err) {
        toast(err?.body?.detail || 'Unban failed.', 'error');
      }
    }

    else if (action === 'edit-category') {
      const existing = state.categories.find((c) => c.slug === btn.dataset.slug);
      openTaxonomyModal({ type: 'category', existing });
    } else if (action === 'delete-category') {
      const ok = await openConfirm({
        title: `Delete category "${btn.dataset.name}"?`,
        message: 'Categories with posts cannot be deleted.',
      });
      if (!ok) return;
      try {
        await apiFetch(`/editor/categories/${encodeURIComponent(btn.dataset.slug)}/`, { method: 'DELETE' });
        toast('Category deleted.', 'ok');
        loadTaxonomy();
      } catch (err) {
        toast(err?.body?.detail || 'Delete failed.', 'error');
      }
    } else if (action === 'edit-tag') {
      const existing = state.tags.find((t) => t.slug === btn.dataset.slug);
      openTaxonomyModal({ type: 'tag', existing });
    } else if (action === 'delete-tag') {
      const ok = await openConfirm({
        title: `Delete tag "${btn.dataset.name}"?`,
        message: 'Tags with usage cannot be deleted.',
      });
      if (!ok) return;
      try {
        await apiFetch(`/editor/tags/${encodeURIComponent(btn.dataset.slug)}/`, { method: 'DELETE' });
        toast('Tag deleted.', 'ok');
        loadTaxonomy();
      } catch (err) {
        toast(err?.body?.detail || 'Delete failed.', 'error');
      }
    }

    else if (action === 'featured-remove') {
      const ok = await openConfirm({
        title: `Remove "${btn.dataset.title}" from featured?`,
        message: 'The post stays published. It only loses its hero slot.',
        confirmLabel: 'Remove',
      });
      if (!ok) return;
      try {
        await apiFetch(`/editor/featured/${encodeURIComponent(btn.dataset.slug)}/remove/`, {
          method: 'DELETE',
        });
        toast('Removed from featured.', 'ok');
        loadFeatured();
      } catch (err) {
        toast(err?.body?.detail || 'Remove failed.', 'error');
      }
    } else if (action === 'featured-add') {
      try {
        await apiFetch(`/editor/featured/${encodeURIComponent(btn.dataset.slug)}/add/`, {
          method: 'POST',
        });
        toast('Added to featured.', 'ok');
        loadFeatured();
        loadFeaturedCandidates(state.featuredCandidatesPage);
      } catch (err) {
        toast(err?.body?.detail || 'Add failed.', 'error');
      }
    }
  }

  // ============================================================
  // Bind
  // ============================================================

  function bind() {
    document.addEventListener('click', (e) => {
      const tab = e.target.closest('.editor-tab');
      if (tab) {
        e.preventDefault();
        activateTab(tab.dataset.tab);
      }
    });

    document.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-refresh]');
      if (!btn) return;
      const which = btn.dataset.refresh;
      if (which === 'review-queue') loadReviewQueue(1);
      else if (which === 'posts') loadPosts(1);
      else if (which === 'featured') loadFeatured();
      else if (which === 'comments') loadComments(1);
      else if (which === 'users') loadUsers(1);
      else if (which === 'activity') loadActivity(1);
    });

    document.addEventListener('click', handleActionClick);

    $('#posts-status-filter')?.addEventListener('change', (e) => {
      state.postsFilters.status = e.target.value;
      loadPosts(1);
    });
    let postsSearchT;
    $('#posts-search')?.addEventListener('input', (e) => {
      clearTimeout(postsSearchT);
      postsSearchT = setTimeout(() => {
        state.postsFilters.search = e.target.value.trim();
        loadPosts(1);
      }, 300);
    });

    $('#comments-status-filter')?.addEventListener('change', (e) => {
      state.commentsFilters.status = e.target.value;
      loadComments(1);
    });
    let commentsSearchT;
    $('#comments-search')?.addEventListener('input', (e) => {
      clearTimeout(commentsSearchT);
      commentsSearchT = setTimeout(() => {
        state.commentsFilters.search = e.target.value.trim();
        loadComments(1);
      }, 300);
    });

    $('#users-role-filter')?.addEventListener('change', (e) => {
      state.usersFilters.role = e.target.value;
      loadUsers(1);
    });
    let usersSearchT;
    $('#users-search')?.addEventListener('input', (e) => {
      clearTimeout(usersSearchT);
      usersSearchT = setTimeout(() => {
        state.usersFilters.search = e.target.value.trim();
        loadUsers(1);
      }, 300);
    });

    $('#activity-action-filter')?.addEventListener('change', (e) => {
      state.activityFilters.action = e.target.value;
      loadActivity(1);
    });

    $('#save-settings-btn')?.addEventListener('click', (e) => {
      e.preventDefault();
      saveSettings();
    });

    $('#new-category-btn')?.addEventListener('click', () => {
      openTaxonomyModal({ type: 'category' });
    });
    $('#new-tag-btn')?.addEventListener('click', () => {
      openTaxonomyModal({ type: 'tag' });
    });
    $('#taxonomy-form')?.addEventListener('submit', submitTaxonomyForm);
    $('#taxonomy-cancel')?.addEventListener('click', closeTaxonomyModal);

    $('#post-decision-cancel')?.addEventListener('click', closePostDecision);
    $('#post-decision-confirm')?.addEventListener('click', submitPostDecision);
    $('#post-decision-modal')?.addEventListener('click', (e) => {
      if (e.target === $('#post-decision-modal')) closePostDecision();
    });

    $('#user-modal-cancel')?.addEventListener('click', closeUserModal);
    $('#user-modal-confirm')?.addEventListener('click', submitUserModal);
    $('#user-modal')?.addEventListener('click', (e) => {
      if (e.target === $('#user-modal')) closeUserModal();
    });
    document.addEventListener('change', (e) => {
      if (e.target.matches('input[name="user-role"]')) {
        $$('.user-role-option').forEach((el) => {
          el.classList.toggle('is-active', el.querySelector('input').checked);
        });
      }
    });

    $('#confirm-cancel')?.addEventListener('click', () => closeConfirm(false));
    $('#confirm-ok')?.addEventListener('click', () => closeConfirm(true));
    $('#confirm-modal')?.addEventListener('click', (e) => {
      if (e.target === $('#confirm-modal')) closeConfirm(false);
    });

    $('#featured-add-btn')?.addEventListener('click', openFeaturedAddModal);
    $('#featured-add-cancel')?.addEventListener('click', closeFeaturedAddModal);
    $('#featured-add-modal')?.addEventListener('click', (e) => {
      if (e.target === $('#featured-add-modal')) closeFeaturedAddModal();
    });

    let featuredSearchT;
    $('#featured-search')?.addEventListener('input', (e) => {
      clearTimeout(featuredSearchT);
      featuredSearchT = setTimeout(() => {
        state.featuredSearch = e.target.value.trim();
        loadFeaturedCandidates(1);
      }, 300);
    });

    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      if (!$('#confirm-modal').hidden) closeConfirm(false);
      if (!$('#post-decision-modal').hidden) closePostDecision();
      if (!$('#taxonomy-modal').hidden) closeTaxonomyModal();
      if (!$('#user-modal').hidden) closeUserModal();
      if (!$('#featured-add-modal').hidden) closeFeaturedAddModal();
    });
  }

  // ============================================================
  // Boot
  // ============================================================

  async function init() {
    if (typeof isAuthenticated === 'function' && !isAuthenticated()) {
      redirectToLogin();
      return;
    }

    bind();
    activateTab('review-queue');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
