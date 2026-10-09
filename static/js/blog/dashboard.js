// static/js/blog/dashboard.js

(function () {
  const root = document.getElementById('dashboard-root');
  const gate = document.getElementById('dashboard-gate');
  if (!root || !gate) return;

  const { escapeHtml, formatDate, formatDateTime, renderCard } =
    window.TorchUI;

  // ============================================================
  // State
  // ============================================================

  const state = {
    user: null,
    activeTab: 'overview',
    loadedTabs: {},
    caches: {
      bookmarks:     { items: null, page: 1, total: 0, hasNext: false },
      likes:         { items: null, page: 1, total: 0, hasNext: false },
      notifications: { items: null, page: 1, total: 0, hasNext: false },
      posts:         { items: null, page: 1, total: 0, hasNext: false, status: '' },
      analytics:     { data: null },
    },
  };

  // ============================================================
  // Elements
  // ============================================================

  const els = {
    user: document.getElementById('dashboard-user'),
    avatar: document.getElementById('dashboard-avatar'),
    userName: document.getElementById('dashboard-user-name'),
    userRole: document.getElementById('dashboard-user-role'),

    tabs: document.getElementById('dashboard-tabs'),
    panels: root.querySelectorAll('.dashboard__panel'),

    notifBadge: document.getElementById('notif-badge'),

    overviewGreeting: document.getElementById('overview-greeting'),
    statBookmarks: document.getElementById('stat-bookmarks'),
    statLikes: document.getElementById('stat-likes'),
    statNotifications: document.getElementById('stat-notifications'),
    overviewBookmarks: document.getElementById('overview-bookmarks'),
    overviewBookmarksEmpty: document.getElementById('overview-bookmarks-empty'),

    bookmarksGrid: document.getElementById('bookmarks-grid'),
    bookmarksSkeleton: document.getElementById('bookmarks-skeleton'),
    bookmarksEmpty: document.getElementById('bookmarks-empty'),
    bookmarksPagination: document.getElementById('bookmarks-pagination'),
    bookmarksCount: document.getElementById('bookmarks-count'),

    likesGrid: document.getElementById('likes-grid'),
    likesSkeleton: document.getElementById('likes-skeleton'),
    likesEmpty: document.getElementById('likes-empty'),
    likesPagination: document.getElementById('likes-pagination'),
    likesCount: document.getElementById('likes-count'),

    notificationsList: document.getElementById('notifications-list'),
    notificationsSkeleton: document.getElementById('notifications-skeleton'),
    notificationsEmpty: document.getElementById('notifications-empty'),
    notificationsPagination: document.getElementById('notifications-pagination'),
    notificationsCount: document.getElementById('notifications-count'),
    notificationsReadAll: document.getElementById('notifications-read-all'),

    avatarPreview: document.getElementById('profile-avatar-preview'),
    avatarInput: document.getElementById('profile-avatar-input'),
    avatarSubmit: document.getElementById('profile-avatar-submit'),
    avatarForm: document.getElementById('avatar-form'),

    profileForm: document.getElementById('profile-form'),
    profileFirstName: document.getElementById('profile-first-name'),
    profileLastName: document.getElementById('profile-last-name'),
    profileEmail: document.getElementById('profile-email'),
    profileEmailError: document.getElementById('profile-email-error'),
    profileBio: document.getElementById('profile-bio'),
    profileBioCount: document.getElementById('profile-bio-count'),
    profileWebsite: document.getElementById('profile-website'),
    profileWebsiteError: document.getElementById('profile-website-error'),
    profileError: document.getElementById('profile-error'),
    profileSubmit: document.getElementById('profile-submit'),
    profileSaved: document.getElementById('profile-saved'),

    passwordForm: document.getElementById('password-form'),
    passwordCurrent: document.getElementById('password-current'),
    passwordCurrentError: document.getElementById('password-current-error'),
    passwordNew: document.getElementById('password-new'),
    passwordNewError: document.getElementById('password-new-error'),
    passwordConfirm: document.getElementById('password-confirm'),
    passwordConfirmError: document.getElementById('password-confirm-error'),
    passwordFormError: document.getElementById('password-form-error'),
    passwordSubmit: document.getElementById('password-submit'),

    postsTableWrap: document.getElementById('posts-table-wrap'),
    postsTableBody: document.getElementById('posts-table-body'),
    postsSkeleton: document.getElementById('posts-skeleton'),
    postsEmpty: document.getElementById('posts-empty'),
    postsPagination: document.getElementById('posts-pagination'),
    postsCount: document.getElementById('posts-count'),
    postsStatusFilter: document.getElementById('posts-status-filter'),

    analyticsPosts: document.getElementById('analytics-posts'),
    analyticsViews: document.getElementById('analytics-views'),
    analyticsLikes: document.getElementById('analytics-likes'),
    analyticsComments: document.getElementById('analytics-comments'),
    analyticsBookmarks: document.getElementById('analytics-bookmarks'),
    analyticsTopPosts: document.getElementById('analytics-top-posts'),
    analyticsTopPostsEmpty: document.getElementById('analytics-top-posts-empty'),
    analyticsSkeleton: document.getElementById('analytics-skeleton'),

    byStatusDraft: document.getElementById('by-status-draft'),
    byStatusPending: document.getElementById('by-status-pending'),
    byStatusChangesRequested: document.getElementById('by-status-changes_requested'),
    byStatusPublished: document.getElementById('by-status-published'),
    byStatusRejected: document.getElementById('by-status-rejected'),
    byStatusUnpublished: document.getElementById('by-status-unpublished'),
    byStatusArchived: document.getElementById('by-status-archived'),
  };

  // ============================================================
  // Utilities
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

  const STATUS_LABELS = {
    draft: 'Draft',
    pending: 'In review',
    changes_requested: 'Changes requested',
    approved: 'Approved',
    scheduled: 'Scheduled',
    published: 'Published',
    rejected: 'Rejected',
    unpublished: 'Unpublished',
    archived: 'Archived',
  };

  // ============================================================
  // Auth gate
  // ============================================================

  async function init() {
    if ('scrollRestoration' in history) {
      history.scrollRestoration = 'manual';
    }

    if (!getAccessToken()) {
      redirectToLogin();
      return;
    }

    try {
      const user = await apiFetch('/auth/me/');
      state.user = user;

      renderUser(user);
      renderTabsAvailability(user);

      gate.hidden = true;
      root.hidden = false;

      const params = new URLSearchParams(window.location.search);
      const initialTab = params.get('tab') || 'overview';
      switchTab(initialTab);
    } catch (err) {
      console.error(err);
      clearTokens();
      redirectToLogin();
    }
  }

  function renderUser(user) {
    const display = user.display_name || user.username;
    els.avatar.src = user.avatar_url || '/static/img/default-avatar.jpg';
    els.avatar.alt = display;
    els.userName.textContent = display;
    els.userRole.textContent = user.role_display || user.role || '';
    els.user.hidden = false;

    els.profileFirstName.value = user.first_name || '';
    els.profileLastName.value = user.last_name || '';
    els.profileEmail.value = user.email || '';
    els.profileBio.value = user.bio || '';
    els.profileWebsite.value = user.website || '';
    els.avatarPreview.src = user.avatar_url || '/static/img/default-avatar.jpg';

    updateBioCount();
  }

  function renderTabsAvailability(user) {
    const isWriter = user.role === 'author' || user.role === 'editor';

    for (const el of document.querySelectorAll('[data-role="author"]')) {
      el.hidden = !isWriter;
    }
  }

  // ============================================================
  // Tabs
  // ============================================================

  const VALID_TABS = [
    'overview',
    'bookmarks',
    'likes',
    'notifications',
    'profile',
    'posts',
    'analytics',
  ];

  function switchTab(name) {
    if (!VALID_TABS.includes(name)) name = 'overview';

    const tabButton = document.querySelector(
      `.dashboard__tab[data-tab="${name}"]`
    );
    if (tabButton && tabButton.hidden) {
      name = 'overview';
    }

    state.activeTab = name;

    for (const btn of els.tabs.querySelectorAll('.dashboard__tab')) {
      const isActive = btn.dataset.tab === name;
      btn.classList.toggle('is-active', isActive);
      btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    }

    for (const panel of els.panels) {
      const isActive = panel.dataset.panel === name;
      panel.hidden = !isActive;
      panel.classList.toggle('is-active', isActive);
    }

    const params = new URLSearchParams(window.location.search);
    if (name === 'overview') params.delete('tab');
    else params.set('tab', name);
    const qs = params.toString();
    window.history.replaceState(
      {},
      '',
      window.location.pathname + (qs ? '?' + qs : '')
    );

    window.scrollTo({ top: 0, behavior: 'auto' });

    if (!state.loadedTabs[name]) {
      state.loadedTabs[name] = true;
      loadTab(name);
    }
  }

  function loadTab(name) {
    if (name === 'overview') return loadOverview();
    if (name === 'bookmarks') return loadBookmarks(1, false);
    if (name === 'likes') return loadLikes(1, false);
    if (name === 'notifications') return loadNotifications(1, false);
    if (name === 'profile') return Promise.resolve();
    if (name === 'posts') return loadMyPosts(1, false);
    if (name === 'analytics') return loadAnalytics();
    return Promise.resolve();
  }

  // ============================================================
  // Overview
  // ============================================================

  async function loadOverview() {
    const name = state.user?.display_name || state.user?.username || '';
    els.overviewGreeting.textContent = `Welcome back, ${name}.`;

    try {
      const [b, l, n] = await Promise.all([
        apiFetch('/me/bookmarks/?page_size=1'),
        apiFetch('/me/likes/?page_size=1'),
        apiFetch('/notifications/unread-count/'),
      ]);

      els.statBookmarks.textContent = b.count ?? 0;
      els.statLikes.textContent = l.count ?? 0;
      els.statNotifications.textContent = n.unread ?? 0;
    } catch (err) {
      console.error('Failed to load overview stats:', err);
      els.statBookmarks.textContent = '—';
      els.statLikes.textContent = '—';
      els.statNotifications.textContent = '—';
    }

    try {
      const b = await apiFetch('/me/bookmarks/?page_size=3');
      const items = b.results || [];

      if (!items.length) {
        els.overviewBookmarksEmpty.hidden = false;
        els.overviewBookmarks.innerHTML = '';
        return;
      }
      els.overviewBookmarksEmpty.hidden = true;
      els.overviewBookmarks.innerHTML = items.map((p) => renderCard(p)).join('');
    } catch (err) {
      console.error('Failed to load recent bookmarks:', err);
      els.overviewBookmarksEmpty.hidden = false;
    }
  }

  // ============================================================
  // Skeletons
  // ============================================================

  function renderSkeletons(container, count) {
    container.innerHTML = Array.from({ length: count })
      .map(() => `
        <div class="skeleton-card" aria-hidden="true">
          <div class="sk-media"></div>
          <div class="sk-body">
            <div class="sk-line sk-line--sm"></div>
            <div class="sk-line sk-line--lg"></div>
            <div class="sk-line sk-line--md"></div>
            <div class="sk-line sk-line--sm"></div>
          </div>
        </div>
      `)
      .join('');
  }

  // ============================================================
  // Bookmarks
  // ============================================================

  async function loadBookmarks(page, append) {
    const cache = state.caches.bookmarks;

    if (!append) {
      els.bookmarksGrid.hidden = true;
      els.bookmarksEmpty.hidden = true;
      els.bookmarksPagination.hidden = true;
      els.bookmarksSkeleton.hidden = false;
      renderSkeletons(els.bookmarksSkeleton, 6);
    }

    try {
      const data = await apiFetch(`/me/bookmarks/?page=${page}&page_size=12`);
      cache.page = page;
      cache.total = data.count ?? 0;
      cache.hasNext = !!data.next;

      els.bookmarksSkeleton.hidden = true;

      const items = data.results || [];
      if (!append) cache.items = items;
      else cache.items = (cache.items || []).concat(items);

      if (!items.length && !append) {
        els.bookmarksGrid.hidden = true;
        els.bookmarksGrid.innerHTML = '';
        els.bookmarksEmpty.hidden = false;
        els.bookmarksPagination.hidden = true;
        els.bookmarksCount.textContent = '';
        return;
      }

      els.bookmarksEmpty.hidden = true;
      els.bookmarksGrid.hidden = false;
      els.bookmarksGrid.innerHTML = cache.items.map((p) => renderCard(p)).join('');

      els.bookmarksCount.textContent =
        cache.total === 1 ? '1 bookmarked post' : `${cache.total} bookmarked posts`;

      renderPagination(
        els.bookmarksPagination,
        cache,
        (p) => loadBookmarks(p, false),
        { pageSize: 12 }
      );
    } catch (err) {
      console.error(err);
      els.bookmarksSkeleton.hidden = true;
      els.bookmarksEmpty.hidden = false;
      els.bookmarksEmpty.innerHTML =
        '<p>Could not load your bookmarks. Please try again.</p>';
    }
  }

  // ============================================================
  // Likes
  // ============================================================

  async function loadLikes(page, append) {
    const cache = state.caches.likes;

    if (!append) {
      els.likesGrid.hidden = true;
      els.likesEmpty.hidden = true;
      els.likesPagination.hidden = true;
      els.likesSkeleton.hidden = false;
      renderSkeletons(els.likesSkeleton, 6);
    }

    try {
      const data = await apiFetch(`/me/likes/?page=${page}&page_size=12`);
      cache.page = page;
      cache.total = data.count ?? 0;
      cache.hasNext = !!data.next;

      els.likesSkeleton.hidden = true;

      const items = data.results || [];
      if (!append) cache.items = items;
      else cache.items = (cache.items || []).concat(items);

      if (!items.length && !append) {
        els.likesGrid.hidden = true;
        els.likesGrid.innerHTML = '';
        els.likesEmpty.hidden = false;
        els.likesPagination.hidden = true;
        els.likesCount.textContent = '';
        return;
      }

      els.likesEmpty.hidden = true;
      els.likesGrid.hidden = false;
      els.likesGrid.innerHTML = cache.items.map((p) => renderCard(p)).join('');

      els.likesCount.textContent =
        cache.total === 1 ? '1 liked post' : `${cache.total} liked posts`;

      renderPagination(
        els.likesPagination,
        cache,
        (p) => loadLikes(p, false),
        { pageSize: 12 }
      );
    } catch (err) {
      console.error(err);
      els.likesSkeleton.hidden = true;
      els.likesEmpty.hidden = false;
      els.likesEmpty.innerHTML =
        '<p>Could not load your liked posts. Please try again.</p>';
    }
  }

  // ============================================================
  // Notifications
  // ============================================================

  async function loadNotifications(page, append) {
    const cache = state.caches.notifications;

    if (!append) {
      els.notificationsList.hidden = true;
      els.notificationsEmpty.hidden = true;
      els.notificationsPagination.hidden = true;
      els.notificationsSkeleton.hidden = false;
    }

    try {
      const data = await apiFetch(`/notifications/?page=${page}&page_size=20`);
      cache.page = page;
      cache.total = data.count ?? 0;
      cache.hasNext = !!data.next;

      els.notificationsSkeleton.hidden = true;

      const items = data.results || [];
      if (!append) cache.items = items;
      else cache.items = (cache.items || []).concat(items);

      if (!items.length && !append) {
        els.notificationsList.hidden = true;
        els.notificationsList.innerHTML = '';
        els.notificationsEmpty.hidden = false;
        els.notificationsPagination.hidden = true;
        els.notificationsCount.textContent = '';
        updateUnreadBadge(0);
        return;
      }

      els.notificationsEmpty.hidden = true;
      els.notificationsList.hidden = false;
      els.notificationsList.innerHTML = cache.items
        .map((n) => renderNotification(n))
        .join('');

      els.notificationsCount.textContent =
        cache.total === 1 ? '1 notification' : `${cache.total} notifications`;

      renderPagination(
        els.notificationsPagination,
        cache,
        (p) => loadNotifications(p, false),
        { pageSize: 20 }
      );

      const unread = cache.items.filter((n) => !n.is_read).length;
      updateUnreadBadge(unread);
    } catch (err) {
      console.error(err);
      els.notificationsSkeleton.hidden = true;
      els.notificationsEmpty.hidden = false;
      els.notificationsEmpty.innerHTML =
        '<p>Could not load your notifications. Please try again.</p>';
    }
  }

  function renderNotification(n) {
    const actor = n.actor || {};
    const name = actor.display_name || actor.username || 'Someone';
    const avatar = actor.avatar_url || '/static/img/default-avatar.jpg';

    const text = n.message || n.verb_display || 'New activity';
    const url = n.url || '#';
    const unread = !n.is_read;

    return `
      <a class="notification ${unread ? 'notification--unread' : 'notification--read'}"
         href="${escapeHtml(url)}"
         data-notification-id="${n.id}">
        <img class="notification__avatar" src="${escapeHtml(avatar)}" alt="">
        <div class="notification__body">
          <p class="notification__text">
            <strong>${escapeHtml(name)}</strong> — ${escapeHtml(text)}
          </p>
          <span class="notification__time">${formatDateTime(n.created_at)}</span>
        </div>
        <span class="notification__mark" aria-hidden="true"></span>
      </a>
    `;
  }

  function updateUnreadBadge(count) {
    if (!els.notifBadge) return;
    if (count > 0) {
      els.notifBadge.textContent = count > 99 ? '99+' : count;
      els.notifBadge.hidden = false;
    } else {
      els.notifBadge.hidden = true;
    }
  }

  async function onNotificationClick(e) {
    const link = e.target.closest('.notification');
    if (!link) return;

    const id = link.dataset.notificationId;
    if (!id) return;

    if (link.classList.contains('notification--unread')) {
      link.classList.remove('notification--unread');
      link.classList.add('notification--read');
      const current = parseInt(els.notifBadge.textContent || '0', 10) || 0;
      updateUnreadBadge(Math.max(0, current - 1));
    }

    try {
      await apiFetch(`/notifications/${id}/read/`, { method: 'POST' });
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
    }
  }

  async function markAllRead() {
    if (!els.notificationsReadAll) return;
    els.notificationsReadAll.disabled = true;
    try {
      await apiFetch('/notifications/read-all/', { method: 'POST' });
      for (const el of els.notificationsList.querySelectorAll('.notification')) {
        el.classList.remove('notification--unread');
        el.classList.add('notification--read');
      }
      updateUnreadBadge(0);
    } catch (err) {
      console.error(err);
    } finally {
      els.notificationsReadAll.disabled = false;
    }
  }

  // ============================================================
  // Pagination
  // ============================================================

  function renderPagination(container, cache, onPageChange, options = {}) {
    const pageSize = options.pageSize || 12;
    const totalPages = Math.max(1, Math.ceil(cache.total / pageSize));
    const current = cache.page;

    if (totalPages <= 1) {
      container.hidden = true;
      container.innerHTML = '';
      return;
    }
    container.hidden = false;

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
        current > 1 ? '' : 'disabled'
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
        current < totalPages ? '' : 'disabled'
      } aria-label="Next page">›</button>`
    );

    container.innerHTML = items.join('');

    container.onclick = (e) => {
      const btn = e.target.closest('button[data-page]');
      if (!btn || btn.disabled) return;
      const p = parseInt(btn.dataset.page, 10);
      if (!Number.isFinite(p) || p === current) return;
      onPageChange(p);
    };
  }

  // ============================================================
  // Profile
  // ============================================================

  function updateBioCount() {
    const len = (els.profileBio.value || '').length;
    els.profileBioCount.textContent = String(len);
  }

  els.profileBio.addEventListener('input', updateBioCount);

  function clearProfileErrors() {
    els.profileEmail.classList.remove('is-invalid');
    els.profileWebsite.classList.remove('is-invalid');
    els.profileEmailError.textContent = '';
    els.profileWebsiteError.textContent = '';
    els.profileError.hidden = true;
    els.profileError.textContent = '';
    els.profileSaved.hidden = true;
  }

  els.profileForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearProfileErrors();

    const payload = {
      first_name: els.profileFirstName.value.trim(),
      last_name: els.profileLastName.value.trim(),
      email: els.profileEmail.value.trim(),
      bio: els.profileBio.value.trim(),
      website: els.profileWebsite.value.trim(),
    };

    els.profileSubmit.disabled = true;
    els.profileSubmit.textContent = 'Saving…';

    try {
      const updated = await apiFetch('/auth/me/', {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });

      state.user = updated;
      renderUser(updated);
      els.profileSaved.hidden = false;
      setTimeout(() => (els.profileSaved.hidden = true), 2500);
    } catch (err) {
      console.error(err);
      const body = err.body || {};

      if (body.email) {
        els.profileEmail.classList.add('is-invalid');
        els.profileEmailError.textContent = Array.isArray(body.email)
          ? body.email[0]
          : String(body.email);
      }
      if (body.website) {
        els.profileWebsite.classList.add('is-invalid');
        els.profileWebsiteError.textContent = Array.isArray(body.website)
          ? body.website[0]
          : String(body.website);
      }
      if (!body.email && !body.website) {
        els.profileError.textContent =
          body.detail || 'Could not save changes. Please try again.';
        els.profileError.hidden = false;
      }
    } finally {
      els.profileSubmit.disabled = false;
      els.profileSubmit.textContent = 'Save changes';
    }
  });

  // ============================================================
  // Avatar
  // ============================================================

  els.avatarInput.addEventListener('change', () => {
    const file = els.avatarInput.files[0];
    els.avatarSubmit.disabled = !file;
    if (file) {
      const url = URL.createObjectURL(file);
      els.avatarPreview.src = url;
    }
  });

  els.avatarForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const file = els.avatarInput.files[0];
    if (!file) return;

    els.avatarSubmit.disabled = true;
    els.avatarSubmit.textContent = 'Uploading…';

    try {
      const formData = new FormData();
      formData.append('avatar', file);

      const updated = await apiFetch('/auth/me/avatar/', {
        method: 'POST',
        body: formData,
      });

      state.user = updated;
      els.avatarPreview.src = updated.avatar_url || '';
      els.avatar.src = updated.avatar_url || '';
      els.avatarInput.value = '';
      els.avatarSubmit.disabled = true;
    } catch (err) {
      console.error(err);
      alert('Could not upload the image. Please try again.');
    } finally {
      els.avatarSubmit.textContent = 'Upload';
    }
  });

  // ============================================================
  // Password
  // ============================================================

  function clearPasswordErrors() {
    for (const [input, errorEl] of [
      [els.passwordCurrent, els.passwordCurrentError],
      [els.passwordNew, els.passwordNewError],
      [els.passwordConfirm, els.passwordConfirmError],
    ]) {
      input.classList.remove('is-invalid');
      errorEl.textContent = '';
    }
    els.passwordFormError.hidden = true;
    els.passwordFormError.textContent = '';
  }

  els.passwordCurrent.addEventListener('input', () => {
    els.passwordCurrent.classList.remove('is-invalid');
    els.passwordCurrentError.textContent = '';
  });
  els.passwordNew.addEventListener('input', () => {
    els.passwordNew.classList.remove('is-invalid');
    els.passwordNewError.textContent = '';
  });
  els.passwordConfirm.addEventListener('input', () => {
    els.passwordConfirm.classList.remove('is-invalid');
    els.passwordConfirmError.textContent = '';
  });

  els.passwordForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearPasswordErrors();

    const oldPw = els.passwordCurrent.value;
    const newPw = els.passwordNew.value;
    const confirmPw = els.passwordConfirm.value;

    let hasError = false;
    if (!oldPw) {
      els.passwordCurrent.classList.add('is-invalid');
      els.passwordCurrentError.textContent = 'Current password is required.';
      hasError = true;
    }
    if (!newPw) {
      els.passwordNew.classList.add('is-invalid');
      els.passwordNewError.textContent = 'New password is required.';
      hasError = true;
    } else if (newPw.length < 8) {
      els.passwordNew.classList.add('is-invalid');
      els.passwordNewError.textContent =
        'Password must be at least 8 characters.';
      hasError = true;
    }
    if (newPw !== confirmPw) {
      els.passwordConfirm.classList.add('is-invalid');
      els.passwordConfirmError.textContent = 'Passwords do not match.';
      hasError = true;
    }
    if (hasError) return;

    els.passwordSubmit.disabled = true;
    els.passwordSubmit.textContent = 'Changing…';

    try {
      await apiFetch('/auth/me/change-password/', {
        method: 'POST',
        body: JSON.stringify({
          old_password: oldPw,
          new_password: newPw,
          new_password_confirm: confirmPw,
        }),
      });

      els.passwordForm.reset();
      alert('Password changed.');
    } catch (err) {
      console.error(err);
      const body = err.body || {};

      if (body.old_password) {
        els.passwordCurrent.classList.add('is-invalid');
        els.passwordCurrentError.textContent = Array.isArray(body.old_password)
          ? body.old_password[0]
          : String(body.old_password);
      }
      if (body.new_password) {
        els.passwordNew.classList.add('is-invalid');
        els.passwordNewError.textContent = Array.isArray(body.new_password)
          ? body.new_password[0]
          : String(body.new_password);
      }
      if (body.new_password_confirm) {
        els.passwordConfirm.classList.add('is-invalid');
        els.passwordConfirmError.textContent =
          Array.isArray(body.new_password_confirm)
            ? body.new_password_confirm[0]
            : String(body.new_password_confirm);
      }
      if (
        !body.old_password &&
        !body.new_password &&
        !body.new_password_confirm
      ) {
        els.passwordFormError.textContent =
          body.detail || 'Could not change the password. Please try again.';
        els.passwordFormError.hidden = false;
      }
    } finally {
      els.passwordSubmit.disabled = false;
      els.passwordSubmit.textContent = 'Change password';
    }
  });

  for (const btn of document.querySelectorAll('.dash-input-toggle')) {
    btn.addEventListener('click', () => {
      const targetId = btn.dataset.toggleTarget;
      const input = document.getElementById(targetId);
      if (!input) return;
      const showing = btn.getAttribute('aria-pressed') === 'true';
      const next = !showing;
      btn.setAttribute('aria-pressed', next ? 'true' : 'false');
      btn.setAttribute('aria-label', next ? 'Hide password' : 'Show password');
      input.type = next ? 'text' : 'password';
    });
  }

  // ============================================================
  // My Posts
  // ============================================================

  async function loadMyPosts(page, append) {
    const cache = state.caches.posts;

    if (!append) {
      els.postsTableWrap.hidden = true;
      els.postsEmpty.hidden = true;
      els.postsPagination.hidden = true;
      els.postsSkeleton.hidden = false;
    }

    const params = new URLSearchParams();
    params.set('page', String(page));
    params.set('page_size', '20');
    if (cache.status) params.set('status', cache.status);

    try {
      const data = await apiFetch(`/me/posts/?${params.toString()}`);

      cache.page = page;
      cache.total = data.count ?? 0;
      cache.hasNext = !!data.next;

      els.postsSkeleton.hidden = true;

      const items = data.results || [];
      if (!append) cache.items = items;
      else cache.items = (cache.items || []).concat(items);

      if (!items.length && !append) {
        els.postsTableWrap.hidden = true;
        els.postsEmpty.hidden = false;
        els.postsPagination.hidden = true;
        els.postsCount.textContent = '';

        if (cache.status) {
          els.postsEmpty.innerHTML = `
            <p>No posts with status “${escapeHtml(
              STATUS_LABELS[cache.status] || cache.status
            )}”.</p>
          `;
        } else {
          els.postsEmpty.innerHTML = `
            <p>You haven't written any posts yet.</p>
            <a href="/dashboard/posts/new/" class="btn btn--primary">
              Write your first post
            </a>
          `;
        }
        return;
      }

      els.postsEmpty.hidden = true;
      els.postsTableWrap.hidden = false;
      els.postsTableBody.innerHTML = cache.items.map(renderPostRow).join('');

      els.postsCount.textContent =
        cache.total === 1 ? '1 post' : `${cache.total} posts`;

      renderPagination(
        els.postsPagination,
        cache,
        (p) => loadMyPosts(p, false),
        { pageSize: 20 }
      );
    } catch (err) {
      console.error(err);
      els.postsSkeleton.hidden = true;
      els.postsEmpty.hidden = false;
      els.postsEmpty.innerHTML =
        '<p>Could not load your posts. Please try again.</p>';
    }
  }

  function renderPostRow(post) {
    const status = post.status || 'draft';
    const statusLabel = STATUS_LABELS[status] || status;
    const updated = post.updated_at || post.created_at;
    const slug = post.slug || '';

    // Reason button — only for rejected and changes_requested
    let reasonButton = '';
    if (status === 'rejected' && post.rejection_reason) {
      reasonButton = `
        <button type="button"
                class="posts-table__reason-btn"
                data-post-reason="rejected"
                data-slug="${escapeHtml(slug)}"
                aria-label="View rejection reason"
                title="View rejection reason">!</button>
      `;
    } else if (
      status === 'changes_requested' &&
      post.changes_requested_note
    ) {
      reasonButton = `
        <button type="button"
                class="posts-table__reason-btn posts-table__reason-btn--changes"
                data-post-reason="changes_requested"
                data-slug="${escapeHtml(slug)}"
                aria-label="View change request"
                title="View change request">!</button>
      `;
    }

    const actions = post.allowed_actions || {};
    const hasAnyAction =
      actions.can_edit ||
      actions.can_delete ||
      actions.can_submit ||
      actions.can_preview ||
      actions.can_view_public;

    return `
      <tr data-slug="${escapeHtml(slug)}">
        <td>
          <a class="posts-table__title"
             href="/dashboard/posts/${encodeURIComponent(slug)}/edit/">
            ${escapeHtml(post.title || 'Untitled')}
          </a>
        </td>
        <td>
          <span class="posts-table__status posts-table__status--${escapeHtml(status)}">
            ${escapeHtml(statusLabel)}
          </span>
          ${reasonButton}
        </td>
        <td class="posts-table__col-num">${post.views_count ?? 0}</td>
        <td class="posts-table__col-num">${post.like_count ?? 0}</td>
        <td class="posts-table__col-num">${post.comment_count ?? 0}</td>
        <td class="posts-table__col-date">${formatDate(updated)}</td>
        <td class="posts-table__col-actions">
          ${
            hasAnyAction
              ? `
                <div class="posts-table__actions" data-row-actions>
                  <button
                    type="button"
                    class="posts-table__actions-btn"
                    data-post-menu-btn
                    data-slug="${escapeHtml(slug)}"
                    aria-haspopup="true"
                    aria-expanded="false"
                    aria-label="Post actions"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                         stroke-width="2" stroke-linecap="round" aria-hidden="true">
                      <circle cx="12" cy="12" r="1"/>
                      <circle cx="19" cy="12" r="1"/>
                      <circle cx="5" cy="12" r="1"/>
                    </svg>
                  </button>
                </div>
              `
              : ''
          }
        </td>
      </tr>
    `;
  }

  if (els.postsStatusFilter) {
    els.postsStatusFilter.addEventListener('click', (e) => {
      const btn = e.target.closest('.status-filter__btn');
      if (!btn) return;

      for (const other of els.postsStatusFilter.querySelectorAll(
        '.status-filter__btn'
      )) {
        other.classList.toggle('is-active', other === btn);
      }

      state.caches.posts.status = btn.dataset.status || '';
      state.caches.posts.page = 1;
      loadMyPosts(1, false);
    });
  }

  // ============================================================
  // Table click handling
  //   - Clicks inside the table (menu button, reason button)
  //     are caught here.
  //   - Clicks on menu items are caught by the document-level
  //     listener below, because the menu lives on document.body.
  // ============================================================

  if (els.postsTableBody) {
    els.postsTableBody.addEventListener('click', onPostsTableClick);
  }

  function onPostsTableClick(e) {
    // Menu open button — inside the table
    const menuBtn = e.target.closest('[data-post-menu-btn]');
    if (menuBtn) {
      e.stopPropagation();
      toggleActionsMenu(menuBtn);
      return;
    }

    // Reason popover trigger — inside the table
    const reasonBtn = e.target.closest('[data-post-reason]');
    if (reasonBtn) {
      e.stopPropagation();
      toggleReasonPopover(reasonBtn);
      return;
    }
  }

  // ============================================================
  // Menu item clicks — caught at the document level
  // ============================================================

  document.addEventListener('click', onDocumentMenuClick);

  function onDocumentMenuClick(e) {
    const menuItem = e.target.closest('[data-post-menu-item]');
    if (!menuItem) return;

    // Links navigate normally. Buttons need default prevented.
    if (menuItem.tagName !== 'A') {
      e.preventDefault();
    }

    // Stop the click from being seen by the outside-click handler
    // that closes the menu. We close it explicitly here.
    e.stopPropagation();

    const action = menuItem.dataset.postMenuItem;
    const slug = menuItem.dataset.slug;

    closeAllActionMenus();

    // Links handle navigation via their href.
    // Buttons run their action here.
    if (menuItem.tagName !== 'A') {
      handleRowAction(action, slug);
    }
  }

  // ============================================================
  // Row actions menu (positioned with fixed coordinates)
  // ============================================================

  function toggleActionsMenu(button) {
    const isOpen = button.getAttribute('aria-expanded') === 'true';

    closeAllActionMenus();

    if (isOpen) return;

    const slug = button.dataset.slug;
    const post = (state.caches.posts.items || []).find(
      (p) => p.slug === slug
    );
    if (!post) return;

    const actions = post.allowed_actions || {};
    const items = [];

    if (actions.can_edit) {
      items.push(`
        <a class="posts-table__menu-item"
           href="/dashboard/posts/${encodeURIComponent(slug)}/edit/"
           data-post-menu-item="edit"
           data-slug="${escapeHtml(slug)}"
           role="menuitem">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
               aria-hidden="true">
            <path d="M12 20h9"/>
            <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"/>
          </svg>
          Edit
        </a>
      `);
    }

    if (actions.can_preview) {
      items.push(`
        <a class="posts-table__menu-item"
           href="/dashboard/posts/${encodeURIComponent(slug)}/preview/"
           target="_blank"
           rel="noopener"
           data-post-menu-item="preview"
           data-slug="${escapeHtml(slug)}"
           role="menuitem">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
               aria-hidden="true">
            <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
          Preview
        </a>
      `);
    }

    if (actions.can_view_public) {
      items.push(`
        <a class="posts-table__menu-item"
           href="/posts/${encodeURIComponent(slug)}/"
           target="_blank"
           rel="noopener"
           data-post-menu-item="view"
           data-slug="${escapeHtml(slug)}"
           role="menuitem">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
               aria-hidden="true">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
            <polyline points="15 3 21 3 21 9"/>
            <line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
          View on site
        </a>
      `);
    }

    if (actions.can_submit) {
      if (items.length) {
        items.push('<div class="posts-table__menu-divider" role="separator"></div>');
      }
      items.push(`
        <button type="button"
                class="posts-table__menu-item"
                data-post-menu-item="submit"
                data-slug="${escapeHtml(slug)}"
                role="menuitem">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
               aria-hidden="true">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
          Submit for review
        </button>
      `);
    }

    if (actions.can_delete) {
      if (items.length) {
        items.push('<div class="posts-table__menu-divider" role="separator"></div>');
      }
      items.push(`
        <button type="button"
                class="posts-table__menu-item posts-table__menu-item--danger"
                data-post-menu-item="delete"
                data-slug="${escapeHtml(slug)}"
                role="menuitem">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
               aria-hidden="true">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
            <path d="M10 11v6M14 11v6"/>
            <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
          </svg>
          Delete
        </button>
      `);
    }

    const menu = document.createElement('div');
    menu.className = 'posts-table__menu';
    menu.setAttribute('role', 'menu');
    menu.innerHTML = items.join('');

    // Position with fixed coordinates so the table never needs
    // to scroll to make room.
    const rect = button.getBoundingClientRect();
    const MENU_GAP = 6;
    const VIEWPORT_PAD = 8;

    menu.style.position = 'fixed';
    menu.style.top = '0px';
    menu.style.left = '0px';
    menu.style.visibility = 'hidden';
    document.body.appendChild(menu);

    const menuRect = menu.getBoundingClientRect();
    let top = rect.bottom + MENU_GAP;
    let left = rect.left + rect.width - menuRect.width;

    if (top + menuRect.height > window.innerHeight - VIEWPORT_PAD) {
      const above = rect.top - menuRect.height - MENU_GAP;
      top = above >= VIEWPORT_PAD
        ? above
        : Math.max(
            VIEWPORT_PAD,
            window.innerHeight - menuRect.height - VIEWPORT_PAD
          );
    }
    if (left < VIEWPORT_PAD) left = VIEWPORT_PAD;
    if (left + menuRect.width > window.innerWidth - VIEWPORT_PAD) {
      left = window.innerWidth - menuRect.width - VIEWPORT_PAD;
    }

    menu.style.top = `${Math.round(top)}px`;
    menu.style.left = `${Math.round(left)}px`;
    menu.style.visibility = '';

    button.setAttribute('aria-expanded', 'true');

    setTimeout(() => {
      document.addEventListener('click', closeMenusOnOutsideClick);
      document.addEventListener('keydown', closeMenusOnEscape);
      window.addEventListener('scroll', closeAllActionMenus, { passive: true });
      window.addEventListener('resize', closeAllActionMenus);
    }, 0);
  }

  function closeAllActionMenus() {
    for (const menu of document.querySelectorAll('.posts-table__menu')) {
      menu.remove();
    }
    for (const btn of document.querySelectorAll('[data-post-menu-btn]')) {
      btn.setAttribute('aria-expanded', 'false');
    }
    document.removeEventListener('click', closeMenusOnOutsideClick);
    document.removeEventListener('keydown', closeMenusOnEscape);
    window.removeEventListener('scroll', closeAllActionMenus);
    window.removeEventListener('resize', closeAllActionMenus);
  }

  function closeMenusOnOutsideClick(e) {
    if (e.target.closest('.posts-table__menu')) return;
    if (e.target.closest('[data-post-menu-btn]')) return;
    closeAllActionMenus();
  }

  function closeMenusOnEscape(e) {
    if (e.key === 'Escape') closeAllActionMenus();
  }

  async function handleRowAction(action, slug) {
    if (action === 'submit') {
      if (!confirm('Submit this post for review?')) return;

      try {
        await apiFetch(`/dashboard/posts/${encodeURIComponent(slug)}/submit/`, {
          method: 'POST',
        });
        await refreshMyPosts();
      } catch (err) {
        console.error(err);
        alert(
          (err.body && (err.body.detail || err.body.message)) ||
            'Could not submit the post.'
        );
      }
      return;
    }

    if (action === 'delete') {
      if (
        !confirm(
          'Delete this post? It will be moved out of your active list.'
        )
      ) {
        return;
      }

      try {
        await apiFetch(`/dashboard/posts/${encodeURIComponent(slug)}/`, {
          method: 'DELETE',
        });
        await refreshMyPosts();
      } catch (err) {
        console.error(err);
        alert(
          (err.body && (err.body.detail || err.body.message)) ||
            'Could not delete the post.'
        );
      }
      return;
    }
  }

  async function refreshMyPosts() {
    const cache = state.caches.posts;
    cache.items = null;
    await loadMyPosts(cache.page || 1, false);
  }

  // ============================================================
  // Reason popover
  // ============================================================

  function toggleReasonPopover(button) {
    const isOpen = button.getAttribute('aria-expanded') === 'true';

    closeAllReasonPopovers();

    if (isOpen) return;

    const slug = button.dataset.slug;
    const kind = button.dataset.postReason;
    const post = (state.caches.posts.items || []).find(
      (p) => p.slug === slug
    );
    if (!post) return;

    const isRejected = kind === 'rejected';
    const text = isRejected
      ? post.rejection_reason || ''
      : post.changes_requested_note || '';

    const popover = document.createElement('div');
    popover.className = 'posts-table__reason-popover';
    popover.setAttribute('role', 'dialog');
    popover.innerHTML = `
      <div class="posts-table__reason-title">
        ${isRejected ? 'Rejection reason' : 'Changes requested'}
      </div>
      <div class="posts-table__reason-body">${escapeHtml(text)}</div>
    `;

    const rect = button.getBoundingClientRect();
    const MENU_GAP = 6;
    const VIEWPORT_PAD = 8;

    popover.style.position = 'fixed';
    popover.style.top = '0px';
    popover.style.left = '0px';
    popover.style.visibility = 'hidden';
    document.body.appendChild(popover);

    const popRect = popover.getBoundingClientRect();
    let top = rect.bottom + MENU_GAP;
    let left = rect.left;

    if (top + popRect.height > window.innerHeight - VIEWPORT_PAD) {
      top = Math.max(
        VIEWPORT_PAD,
        rect.top - popRect.height - MENU_GAP
      );
    }
    if (left + popRect.width > window.innerWidth - VIEWPORT_PAD) {
      left = window.innerWidth - popRect.width - VIEWPORT_PAD;
    }
    if (left < VIEWPORT_PAD) left = VIEWPORT_PAD;

    popover.style.top = `${Math.round(top)}px`;
    popover.style.left = `${Math.round(left)}px`;
    popover.style.visibility = '';

    button.setAttribute('aria-expanded', 'true');

    setTimeout(() => {
      document.addEventListener('click', closeReasonOnOutsideClick);
      document.addEventListener('keydown', closeReasonOnEscape);
      window.addEventListener('scroll', closeAllReasonPopovers, { passive: true });
      window.addEventListener('resize', closeAllReasonPopovers);
    }, 0);
  }

  function closeAllReasonPopovers() {
    for (const pop of document.querySelectorAll(
      '.posts-table__reason-popover'
    )) {
      pop.remove();
    }
    for (const btn of document.querySelectorAll('[data-post-reason]')) {
      btn.setAttribute('aria-expanded', 'false');
    }
    document.removeEventListener('click', closeReasonOnOutsideClick);
    document.removeEventListener('keydown', closeReasonOnEscape);
    window.removeEventListener('scroll', closeAllReasonPopovers);
    window.removeEventListener('resize', closeAllReasonPopovers);
  }

  function closeReasonOnOutsideClick(e) {
    if (e.target.closest('.posts-table__reason-popover')) return;
    if (e.target.closest('[data-post-reason]')) return;
    closeAllReasonPopovers();
  }

  function closeReasonOnEscape(e) {
    if (e.key === 'Escape') closeAllReasonPopovers();
  }

  // ============================================================
  // Analytics
  // ============================================================

  async function loadAnalytics() {
    if (state.caches.analytics.data) {
      renderAnalytics(state.caches.analytics.data);
      return;
    }

    els.analyticsSkeleton.hidden = false;

    try {
      const data = await apiFetch('/me/posts/analytics/');
      state.caches.analytics.data = data;
      els.analyticsSkeleton.hidden = true;
      renderAnalytics(data);
    } catch (err) {
      console.error(err);
      els.analyticsSkeleton.hidden = true;
    }
  }

  function renderAnalytics(data) {
    const totals = data.totals || {};
    const byStatus = data.by_status || {};
    const topPosts = data.top_posts || [];

    els.analyticsPosts.textContent = formatNumber(totals.posts);
    els.analyticsViews.textContent = formatNumber(totals.views);
    els.analyticsLikes.textContent = formatNumber(totals.likes);
    els.analyticsComments.textContent = formatNumber(totals.comments);
    els.analyticsBookmarks.textContent = formatNumber(totals.bookmarks);

    els.byStatusDraft.textContent = formatNumber(byStatus.draft);
    els.byStatusPending.textContent = formatNumber(byStatus.pending);
    els.byStatusChangesRequested.textContent = formatNumber(
      byStatus.changes_requested
    );
    els.byStatusPublished.textContent = formatNumber(byStatus.published);
    els.byStatusRejected.textContent = formatNumber(byStatus.rejected);
    els.byStatusUnpublished.textContent = formatNumber(byStatus.unpublished);
    els.byStatusArchived.textContent = formatNumber(byStatus.archived);

    if (topPosts.length) {
      els.analyticsTopPostsEmpty.hidden = true;
      els.analyticsTopPosts.hidden = false;
      els.analyticsTopPosts.innerHTML = topPosts
        .map((p) => renderCard(p))
        .join('');
    } else {
      els.analyticsTopPosts.hidden = true;
      els.analyticsTopPostsEmpty.hidden = false;
    }
  }

  // ============================================================
  // Global events
  // ============================================================

  els.tabs.addEventListener('click', (e) => {
    const tab = e.target.closest('.dashboard__tab');
    if (!tab) return;
    switchTab(tab.dataset.tab);
  });

  document.addEventListener('click', (e) => {
    const link = e.target.closest('[data-goto-tab]');
    if (!link) return;
    e.preventDefault();
    switchTab(link.dataset.gotoTab);
  });

  if (els.notificationsList) {
    els.notificationsList.addEventListener('click', onNotificationClick);
  }

  if (els.notificationsReadAll) {
    els.notificationsReadAll.addEventListener('click', markAllRead);
  }

  // ============================================================
  // Kick off
  // ============================================================

  document.addEventListener('DOMContentLoaded', init);
})();
