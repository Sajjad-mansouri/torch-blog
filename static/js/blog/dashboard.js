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
    loadedTabs: {},          // tabName → true once its data is loaded
    caches: {
      bookmarks: { items: null, page: 1, total: 0, hasNext: false },
      likes:     { items: null, page: 1, total: 0, hasNext: false },
      notifications: { items: null, page: 1, total: 0, hasNext: false },
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

    // Overview
    overviewGreeting: document.getElementById('overview-greeting'),
    statBookmarks: document.getElementById('stat-bookmarks'),
    statLikes: document.getElementById('stat-likes'),
    statNotifications: document.getElementById('stat-notifications'),
    overviewBookmarks: document.getElementById('overview-bookmarks'),
    overviewBookmarksEmpty: document.getElementById('overview-bookmarks-empty'),

    // Bookmarks
    bookmarksGrid: document.getElementById('bookmarks-grid'),
    bookmarksSkeleton: document.getElementById('bookmarks-skeleton'),
    bookmarksEmpty: document.getElementById('bookmarks-empty'),
    bookmarksPagination: document.getElementById('bookmarks-pagination'),
    bookmarksCount: document.getElementById('bookmarks-count'),

    // Likes
    likesGrid: document.getElementById('likes-grid'),
    likesSkeleton: document.getElementById('likes-skeleton'),
    likesEmpty: document.getElementById('likes-empty'),
    likesPagination: document.getElementById('likes-pagination'),
    likesCount: document.getElementById('likes-count'),

    // Notifications
    notificationsList: document.getElementById('notifications-list'),
    notificationsSkeleton: document.getElementById('notifications-skeleton'),
    notificationsEmpty: document.getElementById('notifications-empty'),
    notificationsPagination: document.getElementById('notifications-pagination'),
    notificationsCount: document.getElementById('notifications-count'),
    notificationsReadAll: document.getElementById('notifications-read-all'),

    // Profile
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

      // Start from URL hash or query (?tab=bookmarks)
      const params = new URLSearchParams(window.location.search);
      const initialTab = params.get('tab') || 'overview';
      switchTab(initialTab);

      // Update the topbar so the user avatar shows there too
      // (topbar.js handles this, but we can trigger a re-render)
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

    // Prefill profile form
    els.profileFirstName.value = user.first_name || '';
    els.profileLastName.value = user.last_name || '';
    els.profileEmail.value = user.email || '';
    els.profileBio.value = user.bio || '';
    els.profileWebsite.value = user.website || '';
    els.avatarPreview.src = user.avatar_url || '/static/img/default-avatar.jpg';

    updateBioCount();
  }

  /**
   * Show or hide the "My Posts" tab etc. based on role.
   * For a reader-only dashboard, this is a no-op, but it's here
   * so the code is easy to extend when authors and editors get
   * their own tabs.
   */
  function renderTabsAvailability(user) {
    const isAuthor = user.role === 'author' || user.role === 'editor';
    const isEditor = user.role === 'editor';

    // Currently only reader tabs. When you add author tabs:
    //   document.querySelector('[data-tab="my-posts"]').hidden = !isAuthor;
    //   document.querySelector('[data-tab="analytics"]').hidden = !isAuthor;
    //   document.querySelector('[data-tab="review-queue"]').hidden = !isEditor;
    void isAuthor;
    void isEditor;
  }

  // ============================================================
  // Tabs
  // ============================================================

  function switchTab(name) {
    // Validate
    const valid = ['overview', 'bookmarks', 'likes', 'notifications', 'profile'];
    if (!valid.includes(name)) name = 'overview';

    state.activeTab = name;

    // Update tab buttons
    for (const btn of els.tabs.querySelectorAll('.dashboard__tab')) {
      const isActive = btn.dataset.tab === name;
      btn.classList.toggle('is-active', isActive);
      btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    }

    // Update panels
    for (const panel of els.panels) {
      const isActive = panel.dataset.panel === name;
      panel.hidden = !isActive;
      panel.classList.toggle('is-active', isActive);
    }

    // Update the URL (without reloading) so the tab is shareable
    const params = new URLSearchParams(window.location.search);
    if (name === 'overview') params.delete('tab');
    else params.set('tab', name);
    const qs = params.toString();
    window.history.replaceState(
      {},
      '',
      window.location.pathname + (qs ? '?' + qs : '')
    );

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'auto' });

    // Lazy-load data for this tab (once)
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
    if (name === 'profile') return Promise.resolve(); // form is already prefilled
  }

  // ============================================================
  // Overview
  // ============================================================

  async function loadOverview() {
    const name = state.user?.display_name || state.user?.username || '';
    els.overviewGreeting.textContent = `Welcome back, ${name}.`;

    // Fetch bookmarks and likes counts + notifications unread count
    // in parallel. Use page_size=1 to keep payloads tiny.
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

    // Fetch the 3 most recent bookmarks for the "recent bookmarks" row.
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
  // Bookmarks
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

      renderPagination(els.bookmarksPagination, cache, (p) => loadBookmarks(p, false));
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

      renderPagination(els.likesPagination, cache, (p) => loadLikes(p, false));
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
        (p) => loadNotifications(p, false)
      );

      // Update unread badge
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

  // Mark a notification as read when it's clicked
  async function onNotificationClick(e) {
    const link = e.target.closest('.notification');
    if (!link) return;

    const id = link.dataset.notificationId;
    if (!id) return;

    // Optimistic: mark as read visually now, then fire the API call.
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

    // Let the browser follow the link href normally.
  }

  async function markAllRead() {
    els.notificationsReadAll.disabled = true;
    try {
      await apiFetch('/notifications/read-all/', { method: 'POST' });
      // Update UI
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
  // Pagination (shared for bookmarks, likes, notifications)
  // ============================================================

  function renderPagination(container, cache, onPageChange) {
    const pageSize = 12;
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
  // Profile form
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
  // Avatar upload
  // ============================================================

  els.avatarInput.addEventListener('change', () => {
    const file = els.avatarInput.files[0];
    els.avatarSubmit.disabled = !file;
    if (file) {
      // Preview
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
  // Password change
  // ============================================================

  function clearPasswordErrors() {
    for (const el of [
      [els.passwordCurrent, els.passwordCurrentError],
      [els.passwordNew, els.passwordNewError],
      [els.passwordConfirm, els.passwordConfirmError],
    ]) {
      el[0].classList.remove('is-invalid');
      el[1].textContent = '';
    }
    els.passwordFormError.hidden = true;
    els.passwordFormError.textContent = '';
  }

  // Clear errors as the user types
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
        els.passwordConfirmError.textContent = Array.isArray(body.new_password_confirm)
          ? body.new_password_confirm[0]
          : String(body.new_password_confirm);
      }
      if (!body.old_password && !body.new_password && !body.new_password_confirm) {
        els.passwordFormError.textContent =
          body.detail || 'Could not change the password. Please try again.';
        els.passwordFormError.hidden = false;
      }
    } finally {
      els.passwordSubmit.disabled = false;
      els.passwordSubmit.textContent = 'Change password';
    }
  });

  // ------------------------------------------------------------
  // Password visibility toggles (shared across the profile form)
  // ------------------------------------------------------------

  for (const btn of document.querySelectorAll('.auth-input-toggle')) {
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
