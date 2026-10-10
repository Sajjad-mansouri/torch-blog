// static/js/post-preview.js
//
// Renders the author/editor preview of a post.
//
// Flow:
//   1. Guard: must be authenticated → else redirect to /login/?next=...
//   2. Extract slug from URL: /posts/<slug>/preview/
//   3. GET /api/v1/posts/<slug>/preview/
//   4. Render header, body, tags, SEO footer into #preview-article
//   5. Interactions (like/bookmark/comment) are intentionally
//      DISABLED here — a preview is read-only and does not
//      mutate analytics or counters.

(() => {
  'use strict';

  // ============================================================
  // Config
  // ============================================================

  const API_BASE = '/api/v1';
  const SKELETON_HIDE_DELAY_MS = 120; // small delay to avoid flash on fast loads

  // ============================================================
  // DOM refs
  // ============================================================

  const $ = (id) => document.getElementById(id);

  const els = {
    main:        $('preview-main'),
    skeleton:    $('preview-skeleton'),
    error:       $('preview-error'),
    errorTitle:  $('preview-error-title'),
    errorMsg:    $('preview-error-message'),
    retryBtn:    $('preview-retry-btn'),
    article:     $('preview-article'),

    bannerText:  $('preview-banner-text'),
    statusPill:  $('preview-status-pill'),
    editLink:    $('preview-edit-link'),
    exitBtn:     $('preview-exit-btn'),

    toastHost:   $('toast-host'),
  };

  // ============================================================
  // Utilities
  // ============================================================

  function escapeHTML(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDate(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return '';
    }
  }

  function formatNumber(n) {
    if (n == null) return '0';
    if (n < 1000) return String(n);
    if (n < 1_000_000) return (n / 1000).toFixed(n < 10_000 ? 1 : 0) + 'k';
    return (n / 1_000_000).toFixed(1) + 'M';
  }

  function getInitials(name) {
    if (!name) return '?';
    return name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((p) => p[0] ? p[0].toUpperCase() : '')
      .join('');
  }

  function humanStatus(status) {
    const map = {
      draft: 'Draft',
      pending: 'Pending review',
      changes_requested: 'Changes requested',
      approved: 'Approved',
      scheduled: 'Scheduled',
      published: 'Published',
      rejected: 'Rejected',
      unpublished: 'Unpublished',
      archived: 'Archived',
    };
    return map[status] || (status ? status.replace(/_/g, ' ') : 'Unknown');
  }

  function toast(message, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast toast--${type}`;
    el.textContent = message;
    els.toastHost.appendChild(el);
    setTimeout(() => {
      el.style.transition = 'opacity 0.25s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 260);
    }, 3200);
  }

  // ============================================================
  // Slug extraction
  // ============================================================

function getSlugFromUrl() {
  // Handles:
  //   /posts/<slug>/preview/              → parts: ["posts", "<slug>", "preview"]
  //   /dashboard/posts/<slug>/preview/    → parts: ["dashboard", "posts", "<slug>", "preview"]
  //
  // Strategy: find the "preview" segment, then the segment
  // immediately before it must be the slug, and the one before
  // that must be "posts". This is path-prefix agnostic.
  const parts = window.location.pathname.split('/').filter(Boolean);

  const previewIdx = parts.indexOf('preview');
  if (previewIdx < 2) return null;                 // need at least [..., "posts", "<slug>", "preview"]
  if (parts[previewIdx - 2] !== 'posts') return null;

  const slug = parts[previewIdx - 1];
  return slug ? decodeURIComponent(slug) : null;
}

  // ============================================================
  // Auth guard
  // ============================================================

  function requireAuth() {
    // api.js exposes isAuthenticated() and redirectToLogin()
    if (typeof isAuthenticated === 'function' && !isAuthenticated()) {
      redirectToLogin();
      return false;
    }
    return true;
  }

  // ============================================================
  // State
  // ============================================================

  const state = {
    slug: null,
    post: null,
  };

  // ============================================================
  // Render — banner
  // ============================================================

  function renderBanner(post) {
    els.statusPill.dataset.status = post.status || 'draft';
    els.statusPill.textContent = humanStatus(post.status);

    const title = post.title ? `<strong>${escapeHTML(post.title)}</strong>` : 'Untitled';
    const updated = post.updated_at ? ` · updated ${formatDate(post.updated_at)}` : '';
    els.bannerText.innerHTML = `Viewing preview — ${title}${updated}`;

    // Editor link → dashboard editor
    if (state.slug) {
      els.editLink.href = `/dashboard/posts/${encodeURIComponent(state.slug)}/edit/`;
    } else {
      els.editLink.style.display = 'none';
    }

    // Update the document title too
    document.title = `Preview · ${post.title || 'Untitled'} · Torch`;
  }

  // ============================================================
  // Render — article body
  // ============================================================

  function renderAuthor(author) {
    if (!author) return '';

    const name = author.display_name || author.username || 'Unknown';
    const avatar = author.avatar_url
      ? `<img src="${escapeHTML(author.avatar_url)}" alt="${escapeHTML(name)}">`
      : `<span class="avatar-fallback">${escapeHTML(getInitials(name))}</span>`;

    return `
      <a class="post-article__author" href="/author/${encodeURIComponent(author.username)}/">
        ${avatar}
        <span>
          <span class="post-article__author-name">${escapeHTML(name)}</span>
          <span class="post-article__author-sub">@${escapeHTML(author.username)}</span>
        </span>
      </a>
    `;
  }

  function renderCategory(cat) {
    if (!cat) return '';
    return `<a class="post-article__category" href="/categories/${encodeURIComponent(cat.slug)}/">
      ${escapeHTML(cat.name)}
    </a>`;
  }

  function renderStats(post) {
    const parts = [];
    parts.push(`<span class="post-article__stats" title="Views">👁 ${formatNumber(post.views_count)}</span>`);
    parts.push(`<span class="post-article__stats" title="Likes">♥ ${formatNumber(post.like_count)}</span>`);
    parts.push(`<span class="post-article__stats" title="Comments">💬 ${formatNumber(post.comment_count)}</span>`);
    if (post.reading_time) {
      parts.push(`<span class="post-article__stats" title="Reading time">⏱ ${post.reading_time} min</span>`);
    }
    return parts.join('<span class="post-article__meta-divider">·</span>');
  }

  function renderTags(tags) {
    if (!Array.isArray(tags) || tags.length === 0) return '';
    const pills = tags.map((t) =>
      `<a class="tag-pill" href="/tags/${encodeURIComponent(t.slug)}/">#${escapeHTML(t.name)}</a>`
    ).join('');
    return `<div class="post-article__tags">${pills}</div>`;
  }

  function renderSeoFooter(post) {
    const rows = [];
    if (post.meta_title)       rows.push(`<dt>Meta title</dt><dd>${escapeHTML(post.meta_title)}</dd>`);
    if (post.meta_description) rows.push(`<dt>Meta description</dt><dd>${escapeHTML(post.meta_description)}</dd>`);

    const flags = [];
    if (post.no_index) flags.push('<span class="post-article__seo-flag">noindex</span>');

    if (rows.length === 0 && flags.length === 0) return '';

    return `
      <div class="post-article__seo">
        <dl>${rows.join('')}</dl>
        ${flags.join('')}
      </div>
    `;
  }

  function sanitizeBody(html) {
    // DOMPurify is loaded in the template. Fall back to a very
    // conservative strip if for some reason it isn't available.
    if (window.DOMPurify) {
      return window.DOMPurify.sanitize(html, {
        ADD_ATTR: ['target', 'rel'],
        FORBID_TAGS: ['script', 'style', 'iframe', 'form', 'input', 'button'],
      });
    }
    // Fallback: escape everything (safe but ugly)
    return `<pre>${escapeHTML(html)}</pre>`;
  }

  function renderArticle(post) {
    const publishedOrUpdated = post.published_at
      ? `Published ${formatDate(post.published_at)}`
      : `Created ${formatDate(post.created_at)}`;

    const hero = post.featured_image
      ? `<img class="post-article__hero" src="${escapeHTML(post.featured_image)}" alt="">`
      : '';

    const summary = post.summary
      ? `<p class="post-article__summary">${escapeHTML(post.summary)}</p>`
      : '';

    const bodyHTML = post.body ? sanitizeBody(post.body) : '<p><em>(empty body)</em></p>';

    els.article.innerHTML = `
      <header class="post-article__header">
        ${renderCategory(post.category)}
        <h1 class="post-article__title">${escapeHTML(post.title || 'Untitled')}</h1>
        <div class="post-article__meta">
          ${renderAuthor(post.author)}
          <span class="post-article__meta-divider">·</span>
          <span>${escapeHTML(publishedOrUpdated)}</span>
          <span class="post-article__meta-divider">·</span>
          ${renderStats(post)}
        </div>
      </header>

      ${hero}
      ${summary}

      <div class="post-article__body">
        ${bodyHTML}
      </div>

      ${renderTags(post.tags)}
      ${renderSeoFooter(post)}
    `;

    els.article.hidden = false;

    // Syntax highlighting (best effort)
    if (window.hljs) {
      els.article.querySelectorAll('pre code').forEach((block) => {
        try { window.hljs.highlightElement(block); } catch {}
      });
    }

    // External links → open in a new tab with safe rel
    els.article.querySelectorAll('.post-article__body a[href^="http"]').forEach((a) => {
      a.setAttribute('target', '_blank');
      a.setAttribute('rel', 'noopener noreferrer nofollow');
    });
  }

  // ============================================================
  // View transitions
  // ============================================================

  function showSkeleton() {
    els.main.setAttribute('aria-busy', 'true');
    els.skeleton.hidden = false;
    els.error.hidden = true;
    els.article.hidden = true;
  }

  function showArticle() {
    // Small delay avoids a flash when the request is instant
    setTimeout(() => {
      els.skeleton.hidden = true;
      els.main.setAttribute('aria-busy', 'false');
    }, SKELETON_HIDE_DELAY_MS);
  }

  function showError(title, message) {
    els.main.setAttribute('aria-busy', 'false');
    els.skeleton.hidden = true;
    els.article.hidden = true;
    els.error.hidden = false;
    els.errorTitle.textContent = title || 'Unable to load preview';
    els.errorMsg.textContent = message || '';
  }

  // ============================================================
  // Data fetching
  // ============================================================

  async function loadPreview(slug) {
    showSkeleton();

    try {
      const data = await apiFetch(`/posts/${encodeURIComponent(slug)}/preview/`);
      state.post = data;
      renderBanner(data);
      renderArticle(data);
      showArticle();
    } catch (err) {
      handleLoadError(err);
    }
  }

  function handleLoadError(err) {
    const status = err?.status;
    const body = err?.body || {};

    if (status === 401 || status === 403) {
      showError(
        'Preview not available',
        'You need to be signed in as the author or an editor to view this preview.'
      );
      // Optionally redirect to login after a short delay
      setTimeout(() => {
        if (typeof redirectToLogin === 'function') redirectToLogin();
      }, 1800);
      return;
    }

    if (status === 404) {
      showError(
        'Post not found',
        'This post may have been deleted, or the URL is incorrect.'
      );
      return;
    }

    const detail = body.detail || body.message || err?.message || 'Unexpected error.';
    showError('Unable to load preview', detail);
  }

  // ============================================================
  // Wire up UI
  // ============================================================

  function bindEvents() {
    els.retryBtn.addEventListener('click', () => {
      if (state.slug) loadPreview(state.slug);
    });

    els.exitBtn.addEventListener('click', () => {
      // Prefer dashboard if the user is an author/editor
      window.location.href = '/dashboard/posts/';
    });

    // Keyboard shortcut: Esc → exit preview
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        window.location.href = '/dashboard/posts/';
      }
    });
  }

  // ============================================================
  // Boot
  // ============================================================

  function init() {
    if (!requireAuth()) return;

    const slug = getSlugFromUrl();
    if (!slug) {
      showError('Invalid preview URL', 'Missing post slug in the URL.');
      return;
    }

    state.slug = slug;
    bindEvents();
    loadPreview(slug);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
