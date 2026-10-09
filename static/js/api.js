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
