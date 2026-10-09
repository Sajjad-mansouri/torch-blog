// static/js/author.js

const {
  escapeHtml,
  ICONS,
  renderCard,
} = window.TorchUI;

// ============================================================
// Read username from path: /author/<username>/
// ============================================================

function getUsernameFromPath() {
  const parts = getPathParts();
  if (parts[0] === 'author' && parts[1]) {
    return decodeURIComponent(parts[1]);
  }
  return null;
}

// ============================================================
// State
// ============================================================

const state = {
  username: null,
  profile: null,
  postsPage: 1,
  postsTotal: 0,
  postsHasNext: false,
};

// ============================================================
// Elements
// ============================================================

const els = {
  skeleton: document.getElementById('author-skeleton'),
  error: document.getElementById('author-error'),
  errorTitle: document.getElementById('author-error-title'),
  errorMessage: document.getElementById('author-error-message'),
  header: document.getElementById('author-header'),

  avatar: document.getElementById('author-avatar'),
  name: document.getElementById('author-name'),
  handle: document.getElementById('author-handle'),
  bio: document.getElementById('author-bio'),
  links: document.getElementById('author-links'),

  stats: document.getElementById('author-stats'),
  statPosts: document.getElementById('stat-posts'),
  statViews: document.getElementById('stat-views'),
  statLikes: document.getElementById('stat-likes'),
  statComments: document.getElementById('stat-comments'),
  statBookmarks: document.getElementById('stat-bookmarks'),

  recentSection: document.getElementById('recent-section'),
  recentGrid: document.getElementById('recent-grid'),

  allSection: document.getElementById('all-section'),
  allCount: document.getElementById('all-count'),
  allGrid: document.getElementById('all-grid'),
  allMore: document.getElementById('all-more'),
  allLoadMore: document.getElementById('all-load-more'),
  allEmpty: document.getElementById('all-empty'),

  topbarAuth: document.getElementById('topbar-auth'),
  footerYear: document.getElementById('footer-year'),
};

// ============================================================
// API calls
// ============================================================

async function fetchProfile(username) {
  return apiFetch(`/authors/${encodeURIComponent(username)}/`);
}

async function fetchPosts(username, page = 1) {
  const p = new URLSearchParams();
  p.set('page', String(page));
  return apiFetch(
    `/authors/${encodeURIComponent(username)}/posts/?${p.toString()}`
  );
}

// ============================================================
// Helpers
// ============================================================

function formatNumber(n) {
  const value = Number(n) || 0;
  if (value >= 1_000_000) {
    return (value / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  }
  if (value >= 1_000) {
    return (value / 1_000).toFixed(1).replace(/\.0$/, '') + 'k';
  }
  return String(value);
}

function linkIcon() {
  return (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>' +
    '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.72-1.71"/>' +
    '</svg>'
  );
}

// ============================================================
// Rendering — profile
// ============================================================

function renderProfile(profile) {
  const displayName = profile.display_name || profile.username || 'Unknown';
  const username = profile.username || '';

  document.title = `${displayName} — Torch`;

  els.avatar.src = profile.avatar_url || '/static/img/default-avatar.jpg';
  els.avatar.alt = displayName;
  els.name.textContent = displayName;
  els.handle.textContent = username ? `@${username}` : '';

  if (profile.bio) {
    els.bio.textContent = profile.bio;
    els.bio.hidden = false;
  } else {
    els.bio.hidden = true;
  }

  renderLinks(profile);
  renderStats(profile.stats || {});

  els.header.hidden = false;
}

function renderLinks(profile) {
  const links = [];

  if (profile.website) {
    links.push({
      url: profile.website,
      label: 'Website',
    });
  }

  for (const s of profile.social_links || []) {
    if (!s.url) continue;
    links.push({
      url: s.url,
      label: s.platform_display || s.platform,
    });
  }

  if (!links.length) {
    els.links.hidden = true;
    return;
  }

  els.links.innerHTML = links
    .map(
      (l) => `
        <a class="author-header__link" href="${escapeHtml(l.url)}"
           target="_blank" rel="noopener noreferrer">
          ${linkIcon()}
          <span>${escapeHtml(l.label)}</span>
        </a>
      `
    )
    .join('');
  els.links.hidden = false;
}

function renderStats(stats) {
  els.statPosts.textContent = formatNumber(stats.total_posts);
  els.statViews.textContent = formatNumber(stats.total_views);
  els.statLikes.textContent = formatNumber(stats.total_likes);
  els.statComments.textContent = formatNumber(stats.total_comments);
  els.statBookmarks.textContent = formatNumber(stats.total_bookmarks);

  els.stats.hidden = false;
}

// ============================================================
// Rendering — posts
// ============================================================

function renderRecentPosts(posts) {
  if (!posts || !posts.length) {
    els.recentSection.hidden = true;
    return;
  }

  els.recentGrid.innerHTML = posts.map((p) => renderCard(p)).join('');
  els.recentSection.hidden = false;
}

function renderAllPosts(posts, append = false) {
  if (!append) {
    els.allGrid.innerHTML = '';
  }

  if (!posts.length && !append) {
    els.allEmpty.hidden = false;
    els.allMore.hidden = true;
    return;
  }

  els.allEmpty.hidden = true;
  els.allGrid.insertAdjacentHTML(
    'beforeend',
    posts.map((p) => renderCard(p)).join('')
  );
}

function updateAllCount() {
  if (!state.postsTotal) {
    els.allCount.textContent = '';
    return;
  }
  els.allCount.textContent =
    state.postsTotal === 1 ? '1 post' : `${state.postsTotal} posts`;
}

// ============================================================
// Load
// ============================================================

async function loadPosts(page = 1, append = false) {
  const data = await fetchPosts(state.username, page);

  state.postsPage = page;
  state.postsTotal = data.count ?? 0;
  state.postsHasNext = !!data.next;

  renderAllPosts(data.results || [], append);
  updateAllCount();

  els.allMore.hidden = !state.postsHasNext;
  els.allSection.hidden = false;
}

async function load() {
  const username = getUsernameFromPath();
  if (!username) {
    showError('Author not found', 'No author was specified in the URL.');
    return;
  }
  state.username = username;

  if ('scrollRestoration' in history) {
    history.scrollRestoration = 'manual';
  }
  window.scrollTo({ top: 0, behavior: 'auto' });

  try {
    const profile = await fetchProfile(username);
    state.profile = profile;

    renderProfile(profile);
    renderRecentPosts(profile.recent_posts || []);

    els.skeleton.hidden = true;

    await loadPosts(1, false);
  } catch (err) {
    console.error(err);
    if (err.status === 404) {
      showError(
        'Author not found',
        'This author may not exist, or their profile is not public.'
      );
    } else {
      showError(
        "Couldn't load this profile",
        (err.body && (err.body.detail || err.body.message)) ||
          'Please check your connection and try again.'
      );
    }
  }
}

// ============================================================
// State helpers
// ============================================================

function showError(title, message) {
  els.skeleton.hidden = true;
  els.header.hidden = true;
  els.recentSection.hidden = true;
  els.allSection.hidden = true;
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

els.allLoadMore.addEventListener('click', async () => {
  if (!state.postsHasNext) return;
  els.allLoadMore.disabled = true;
  try {
    await loadPosts(state.postsPage + 1, true);
  } catch (err) {
    console.error(err);
  } finally {
    els.allLoadMore.disabled = false;
  }
});

// ============================================================
// Init
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  if (els.footerYear) {
    els.footerYear.textContent = new Date().getFullYear();
  }

  renderTopbarAuth();
  load();
});
