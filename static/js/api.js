// static/js/api.js

const API_BASE = '/api/v1';

// ============================================================
// Token storage
// ============================================================

function getAccessToken() {
  return localStorage.getItem('access_token');
}

function getRefreshToken() {
  return localStorage.getItem('refresh_token');
}

function setTokens({ access, refresh }) {
  if (access) localStorage.setItem('access_token', access);
  if (refresh) localStorage.setItem('refresh_token', refresh);
}

function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
}

// ============================================================
// Path helpers
// ============================================================

/**
 * Return the segments of the current path, without empty strings.
 *   "/posts/my-post/"  →  ["posts", "my-post"]
 *   "/author/alice/"   →  ["author", "alice"]
 *   "/"                →  []
 */
function getPathParts() {
  return window.location.pathname.split('/').filter(Boolean);
}

/**
 * Return a path segment by index, URL-decoded.
 *   getPathSegment(0) on "/posts/my-post/" → "posts"
 *   getPathSegment(1) on "/posts/my-post/" → "my-post"
 * Returns null if the index is out of range.
 */
function getPathSegment(index) {
  const parts = getPathParts();
  return parts[index] ? decodeURIComponent(parts[index]) : null;
}

// ============================================================
// Refresh
// ============================================================

async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) return false;

  try {
    const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    setTokens({ access: data.access, refresh: data.refresh });
    return true;
  } catch {
    return false;
  }
}

// ============================================================
// Fetch
// ============================================================

/**
 * Fetch JSON from the API.
 *
 * - Attaches the access token if one is stored.
 * - On 401, tries one refresh (only if a refresh token exists).
 *   If refresh fails, clears tokens but does NOT redirect —
 *   the caller decides what to do.
 * - Throws on non-2xx responses with { status, body }.
 */
async function apiFetch(path, options = {}) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;

  const headers = { ...(options.headers || {}) };
  const isFormData = options.body instanceof FormData;
  if (!isFormData && options.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const token = getAccessToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let res = await fetch(url, { ...options, headers });

  if (res.status === 401 && token && getRefreshToken()) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${getAccessToken()}`;
      res = await fetch(url, { ...options, headers });
    } else {
      clearTokens();
    }
  }

  if (!res.ok) {
    let body = null;
    try {
      body = await res.json();
    } catch {
      body = { detail: res.statusText };
    }
    const err = new Error(`API error ${res.status}`);
    err.status = res.status;
    err.body = body;
    throw err;
  }

  if (res.status === 204) return null;
  return res.json();
}

// ============================================================
// Auth helper — is the current visitor logged in?
// ============================================================

function isAuthenticated() {
  return !!getAccessToken();
}

/**
 * Redirect to login, preserving the current path via ?next=
 * so the login page can send the user back after success.
 */
function redirectToLogin() {
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.href = `/login/?next=${next}`;
}
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
