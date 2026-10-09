// static/js/topbar.js

(function () {
  // ============================================================
  // Helpers
  // ============================================================

  const { escapeHtml } = window.TorchUI || {
    escapeHtml: (s) => String(s ?? ''),
  };

  // ============================================================
  // Mobile menu toggle
  // ============================================================

  const menuBtn = document.getElementById('topbar-menu-btn');
  const menu = document.getElementById('topbar-menu');

  if (menuBtn && menu) {
    const closeMenu = () => {
      menu.hidden = true;
      menuBtn.setAttribute('aria-expanded', 'false');
      menuBtn.setAttribute('aria-label', 'Open menu');
    };

    const openMenu = () => {
      menu.hidden = false;
      menuBtn.setAttribute('aria-expanded', 'true');
      menuBtn.setAttribute('aria-label', 'Close menu');
    };

    menuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = menuBtn.getAttribute('aria-expanded') === 'true';
      if (isOpen) closeMenu();
      else openMenu();
    });

    menu.addEventListener('click', (e) => {
      if (e.target.closest('a') && !e.target.closest('#mobile-user-logout')) {
        closeMenu();
      }
    });

    document.addEventListener('click', (e) => {
      if (menu.hidden) return;
      if (e.target.closest('.topbar__left')) return;
      if (e.target.closest('#topbar-menu')) return;
      closeMenu();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !menu.hidden) {
        closeMenu();
        menuBtn.focus();
      }
    });
  }

  // ============================================================
  // Filters toggle (posts page only)
  // ============================================================

  const filtersToggle = document.getElementById('filters-toggle');
  const filtersPanel = document.getElementById('filters-panel');

  if (filtersToggle && filtersPanel) {
    filtersToggle.addEventListener('click', () => {
      const isOpen = filtersToggle.getAttribute('aria-expanded') === 'true';
      const next = !isOpen;

      filtersToggle.setAttribute('aria-expanded', next ? 'true' : 'false');
      filtersPanel.classList.toggle('is-open', next);
    });
  }

  // ============================================================
  // Categories — desktop dropdown (two-panel)
  // ============================================================

  const ddWrapper = document.getElementById('nav-categories');
  const ddBtn = document.getElementById('nav-categories-btn');
  const ddMenu = document.getElementById('nav-categories-menu');
  const parentsPanel = document.getElementById('nav-categories-parents');
  const childrenPanel = document.getElementById('nav-categories-children');

  const mobileCategoriesBtn = document.getElementById('mobile-categories-btn');
  const mobileCategoriesList = document.getElementById('mobile-categories');

  let categoriesCache = null;
  let loadCategoriesPromise = null;

  async function loadCategories() {
    if (categoriesCache) return categoriesCache;
    if (loadCategoriesPromise) return loadCategoriesPromise;

    loadCategoriesPromise = (async () => {
      try {
        const data = await apiFetch('/categories/');
        categoriesCache = Array.isArray(data) ? data : [];
        return categoriesCache;
      } catch (err) {
        console.error('Failed to load categories:', err);
        categoriesCache = [];
        return categoriesCache;
      }
    })();

    return loadCategoriesPromise;
  }

  function buildCategoryGroups(categories) {
    const byId = new Map();
    for (const c of categories) byId.set(c.id, c);

    function rootIdOf(c) {
      let current = c;
      const seen = new Set();
      while (current.parent && typeof current.parent.id === 'number') {
        if (seen.has(current.id)) break;
        seen.add(current.id);
        const parent = byId.get(current.parent.id);
        if (!parent) break;
        current = parent;
      }
      return current.id;
    }

    const roots = categories.filter((c) => {
      if (!c.parent || typeof c.parent.id !== 'number') return true;
      return !byId.has(c.parent.id);
    });

    return roots.map((root) => ({
      parent: root,
      children: categories.filter(
        (c) => c.id !== root.id && rootIdOf(c) === root.id
      ),
    }));
  }

  // Desktop two-panel dropdown
  let categoryGroups = [];
  let activeCategoryIndex = -1;
  let hoverCloseTimer = null;

  function renderCategoryParents() {
    if (!parentsPanel) return;

    parentsPanel.innerHTML = categoryGroups
      .map((g, i) => {
        const active = i === activeCategoryIndex;
        const hasChildren = g.children.length > 0;
        const arrow = hasChildren
          ? `<svg class="topbar__dropdown-parent-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="9 6 15 12 9 18"/></svg>`
          : '';

        return `
          <a class="topbar__dropdown-parent ${active ? 'is-active' : ''}"
             href="/categories/${encodeURIComponent(g.parent.slug)}/"
             data-index="${i}"
             role="menuitem"
             tabindex="0">
            <span class="topbar__dropdown-parent-label">${escapeHtml(g.parent.name)}</span>
            <span class="topbar__dropdown-parent-aside">${arrow}</span>
          </a>
        `;
      })
      .join('');

    parentsPanel.insertAdjacentHTML(
      'beforeend',
      `<a class="topbar__dropdown-more" href="/categories/">Browse all categories</a>`
    );

    attachCategoryParentListeners();
  }

  function renderCategoryChildren() {
    if (!childrenPanel) return;

    const group = categoryGroups[activeCategoryIndex];

    if (!group) {
      childrenPanel.innerHTML = '';
      childrenPanel.classList.remove('is-open');
      childrenPanel.setAttribute('aria-hidden', 'true');
      return;
    }

    childrenPanel.classList.add('is-open');
    childrenPanel.setAttribute('aria-hidden', 'false');

    if (!group.children.length) {
      childrenPanel.innerHTML = `
        <div class="topbar__dropdown-children-header">
          ${escapeHtml(group.parent.name)}
        </div>
        <div class="topbar__dropdown-empty">
          No subcategories.
        </div>
      `;
      return;
    }

    childrenPanel.innerHTML = `
      <div class="topbar__dropdown-children-header">
        ${escapeHtml(group.parent.name)}
      </div>
      ${group.children
        .map((child) => {
          return `
            <a class="topbar__dropdown-child"
               href="/categories/${encodeURIComponent(child.slug)}/"
               role="menuitem">
              <span class="topbar__dropdown-child-label">${escapeHtml(child.name)}</span>
            </a>
          `;
        })
        .join('')}
    `;
  }

  function setActiveCategoryIndex(index) {
    if (index === activeCategoryIndex) return;
    activeCategoryIndex = index;

    if (parentsPanel) {
      for (const el of parentsPanel.querySelectorAll(
        '.topbar__dropdown-parent'
      )) {
        const idx = parseInt(el.dataset.index, 10);
        el.classList.toggle('is-active', idx === activeCategoryIndex);
      }
    }

    renderCategoryChildren();
  }

  function clearActiveCategoryIndex() {
    if (activeCategoryIndex === -1) return;
    activeCategoryIndex = -1;

    if (parentsPanel) {
      for (const el of parentsPanel.querySelectorAll(
        '.topbar__dropdown-parent'
      )) {
        el.classList.remove('is-active');
      }
    }

    if (childrenPanel) {
      childrenPanel.classList.remove('is-open');
      childrenPanel.setAttribute('aria-hidden', 'true');
      childrenPanel.innerHTML = '';
    }
  }

  function attachCategoryParentListeners() {
    if (!parentsPanel) return;

    for (const el of parentsPanel.querySelectorAll(
      '.topbar__dropdown-parent'
    )) {
      const idx = parseInt(el.dataset.index, 10);
      if (!Number.isFinite(idx)) continue;

      el.addEventListener('mouseenter', () => setActiveCategoryIndex(idx));
      el.addEventListener('focus', () => setActiveCategoryIndex(idx));
    }
  }

  if (ddBtn && ddMenu && parentsPanel && childrenPanel) {
    const closeDD = () => {
      ddMenu.hidden = true;
      ddBtn.setAttribute('aria-expanded', 'false');
      clearActiveCategoryIndex();
    };

    const scheduleCloseDD = () => {
      if (hoverCloseTimer) clearTimeout(hoverCloseTimer);
      hoverCloseTimer = setTimeout(closeDD, 200);
    };

    const cancelScheduledClose = () => {
      if (hoverCloseTimer) {
        clearTimeout(hoverCloseTimer);
        hoverCloseTimer = null;
      }
    };

    const openDD = async () => {
      cancelScheduledClose();

      if (!ddMenu.dataset.loaded) {
        parentsPanel.innerHTML =
          `<div class="topbar__dropdown-loading">Loading…</div>`;
        childrenPanel.innerHTML = '';
        const categories = await loadCategories();

        if (!categories.length) {
          parentsPanel.innerHTML =
            `<div class="topbar__dropdown-empty">No categories yet.</div>`;
          ddMenu.dataset.loaded = '1';
        } else {
          categoryGroups = buildCategoryGroups(categories);
          activeCategoryIndex = -1;
          renderCategoryParents();
          renderCategoryChildren();
          ddMenu.dataset.loaded = '1';
        }
      }

      ddMenu.hidden = false;
      ddBtn.setAttribute('aria-expanded', 'true');
    };

    ddBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = ddBtn.getAttribute('aria-expanded') === 'true';
      if (isOpen) closeDD();
      else openDD();
    });

    if (ddWrapper) {
      ddWrapper.addEventListener('mouseenter', () => {
        cancelScheduledClose();
        openDD();
      });

      ddWrapper.addEventListener('mouseleave', () => {
        scheduleCloseDD();
      });
    }

    document.addEventListener('click', (e) => {
      if (ddMenu.hidden) return;
      if (e.target.closest('#nav-categories')) return;
      closeDD();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !ddMenu.hidden) {
        closeDD();
        ddBtn.focus();
      }
    });
  }

  // ============================================================
  // Categories — mobile accordion
  // ============================================================

  if (mobileCategoriesBtn && mobileCategoriesList) {
    let populated = false;

    async function populateMobileCategories() {
      if (populated) return;
      populated = true;

      const categories = await loadCategories();

      if (!categories.length) {
        mobileCategoriesList.innerHTML =
          `<a href="/categories/">Browse categories</a>`;
        return;
      }

      const groups = buildCategoryGroups(categories);

      mobileCategoriesList.innerHTML = groups
        .map((g, i) => {
          const hasChildren = g.children.length > 0;
          const parentCount =
            typeof g.parent.post_count === 'number'
              ? `<span class="topbar__dropdown-item-count">${g.parent.post_count}</span>`
              : '';

          if (!hasChildren) {
            return `
              <a class="topbar__menu-item--standalone"
                 href="/categories/${encodeURIComponent(g.parent.slug)}/">
                <span class="topbar__dropdown-item-label">${escapeHtml(g.parent.name)}</span>
                ${parentCount}
              </a>
            `;
          }

          const chevron = `
            <svg class="topbar__menu-item-chevron" viewBox="0 0 24 24"
                 fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round"
                 stroke-linejoin="round" aria-hidden="true">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          `;

          const childrenRows = g.children
            .map((child) => {
              const count =
                typeof child.post_count === 'number'
                  ? `<span class="topbar__dropdown-item-count">${child.post_count}</span>`
                  : '';
              return `
                <a class="topbar__menu-item--child"
                   href="/categories/${encodeURIComponent(child.slug)}/">
                  <span class="topbar__dropdown-item-label">${escapeHtml(child.name)}</span>
                  ${count}
                </a>
              `;
            })
            .join('');

          return `
            <div class="topbar__menu-accordion" data-index="${i}">
              <button
                type="button"
                class="topbar__menu-accordion-btn"
                aria-expanded="false"
              >
                <span class="topbar__dropdown-item-label">${escapeHtml(g.parent.name)}</span>
                <span class="topbar__menu-accordion-aside">
                  ${parentCount}
                  ${chevron}
                </span>
              </button>
              <div class="topbar__menu-accordion-body" hidden>
                <a class="topbar__menu-item--parentlink"
                   href="/categories/${encodeURIComponent(g.parent.slug)}/">
                  <span class="topbar__dropdown-item-label">View all ${escapeHtml(g.parent.name)}</span>
                </a>
                ${childrenRows}
              </div>
            </div>
          `;
        })
        .join('');

      attachMobileAccordionListeners();
    }

    function attachMobileAccordionListeners() {
      const accordions = mobileCategoriesList.querySelectorAll(
        '.topbar__menu-accordion'
      );

      for (const acc of accordions) {
        const btn = acc.querySelector('.topbar__menu-accordion-btn');
        const body = acc.querySelector('.topbar__menu-accordion-body');
        if (!btn || !body) continue;

        btn.addEventListener('click', () => {
          const isOpen = btn.getAttribute('aria-expanded') === 'true';
          const next = !isOpen;

          for (const other of accordions) {
            if (other === acc) continue;
            const otherBtn = other.querySelector('.topbar__menu-accordion-btn');
            const otherBody = other.querySelector('.topbar__menu-accordion-body');
            if (otherBtn && otherBody) {
              otherBtn.setAttribute('aria-expanded', 'false');
              otherBody.hidden = true;
            }
          }

          btn.setAttribute('aria-expanded', next ? 'true' : 'false');
          body.hidden = !next;
        });
      }
    }

    mobileCategoriesBtn.addEventListener('click', async () => {
      const isOpen =
        mobileCategoriesBtn.getAttribute('aria-expanded') === 'true';
      const next = !isOpen;

      if (next) {
        await populateMobileCategories();
      }

      mobileCategoriesBtn.setAttribute(
        'aria-expanded',
        next ? 'true' : 'false'
      );
      mobileCategoriesList.hidden = !next;
    });
  }

  // ============================================================
  // Topbar auth — desktop avatar menu + mobile user items
  // ============================================================

  const authSlot = document.getElementById('topbar-auth');
  const mobileUserGroup = document.getElementById('mobile-user-group');
  const mobileUserAvatar = document.getElementById('mobile-user-avatar');
  const mobileUserName = document.getElementById('mobile-user-name');
  const mobileUserRole = document.getElementById('mobile-user-role');
  const mobileUserBadge = document.getElementById('mobile-user-badge');
  const mobileUserLogout = document.getElementById('mobile-user-logout');

  // ------------------------------------------------------------
  // Logout helper
  // ------------------------------------------------------------

  async function performLogout() {
    const refresh = getRefreshToken();

    // Best effort — clear local state even if the API call fails.
    try {
      if (refresh) {
        await fetch('/api/v1/auth/logout/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(getAccessToken()
              ? { Authorization: `Bearer ${getAccessToken()}` }
              : {}),
          },
          body: JSON.stringify({ refresh }),
        });
      }
    } catch (err) {
      console.warn('Logout request failed:', err);
    }

    clearTokens();
    window.location.href = '/';
  }

  // ------------------------------------------------------------
  // Desktop avatar menu
  // ------------------------------------------------------------

  function renderLoggedOutTopbar() {
    if (authSlot) {
      authSlot.innerHTML = `<a href="/login/" class="btn btn--ghost">Login</a>`;
    }
    if (mobileUserGroup) {
      mobileUserGroup.hidden = true;
    }
  }

  function renderLoggedInTopbar(user, unreadCount) {
    const name = user.display_name || user.username || 'Account';
    const avatar = user.avatar_url || '/static/img/default-avatar.jpg';

    if (authSlot) {
      authSlot.innerHTML = `
        <div class="topbar__user-menu" id="topbar-user-menu">
          <button
            type="button"
            class="topbar__user-btn"
            id="topbar-user-btn"
            aria-haspopup="true"
            aria-expanded="false"
            aria-controls="topbar-user-panel"
          >
            <img class="topbar__avatar" src="${escapeHtml(avatar)}" alt="">
            <span class="topbar__user-name">${escapeHtml(name)}</span>
            <svg class="topbar__chevron" viewBox="0 0 24 24"
                 fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round"
                 stroke-linejoin="round" aria-hidden="true">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>

          <div
            class="topbar__user-panel"
            id="topbar-user-panel"
            role="menu"
            hidden
          >
            <a class="topbar__user-item" href="/dashboard/" role="menuitem">
              Dashboard
            </a>
            <a class="topbar__user-item" href="/dashboard/?tab=bookmarks" role="menuitem">
              My bookmarks
            </a>
            <a class="topbar__user-item" href="/dashboard/?tab=likes" role="menuitem">
              Liked posts
            </a>
            <a class="topbar__user-item" href="/dashboard/?tab=notifications" role="menuitem">
              <span>Notifications</span>
              <span class="topbar__user-badge" id="topbar-user-badge" ${unreadCount > 0 ? '' : 'hidden'}>${unreadCount > 0 ? (unreadCount > 99 ? '99+' : unreadCount) : ''}</span>
            </a>
            <div class="topbar__user-divider" role="separator"></div>
            <a class="topbar__user-item" href="/dashboard/?tab=profile" role="menuitem">
              Profile settings
            </a>
            <button
              type="button"
              class="topbar__user-item topbar__user-item--danger"
              id="topbar-user-logout"
              role="menuitem"
            >
              Log out
            </button>
          </div>
        </div>
      `;

      wireDesktopUserMenu();
    }

    // Mobile user group
    if (mobileUserGroup && mobileUserAvatar && mobileUserName && mobileUserRole) {
      mobileUserAvatar.src = avatar;
      mobileUserAvatar.alt = name;
      mobileUserName.textContent = name;
      mobileUserRole.textContent = user.role_display || user.role || '';

      if (mobileUserBadge) {
        if (unreadCount > 0) {
          mobileUserBadge.textContent = unreadCount > 99 ? '99+' : unreadCount;
          mobileUserBadge.hidden = false;
        } else {
          mobileUserBadge.hidden = true;
        }
      }

      mobileUserGroup.hidden = false;
    }
  }

  function wireDesktopUserMenu() {
    const userBtn = document.getElementById('topbar-user-btn');
    const userPanel = document.getElementById('topbar-user-panel');
    const logoutBtn = document.getElementById('topbar-user-logout');

    if (!userBtn || !userPanel) return;

    const close = () => {
      userPanel.hidden = true;
      userBtn.setAttribute('aria-expanded', 'false');
    };

    const open = () => {
      userPanel.hidden = false;
      userBtn.setAttribute('aria-expanded', 'true');
    };

    userBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = userBtn.getAttribute('aria-expanded') === 'true';
      if (isOpen) close();
      else open();
    });

    document.addEventListener('click', (e) => {
      if (userPanel.hidden) return;
      if (e.target.closest('#topbar-user-menu')) return;
      close();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !userPanel.hidden) {
        close();
        userBtn.focus();
      }
    });

    if (logoutBtn) {
      logoutBtn.addEventListener('click', (e) => {
        e.preventDefault();
        performLogout();
      });
    }
  }

  async function renderTopbarAuth() {
    const token = getAccessToken();

    if (!token) {
      renderLoggedOutTopbar();
      return;
    }

    // Fetch the current user and unread count in parallel.
    let user = null;
    let unreadCount = 0;

    try {
      const [userRes, countRes] = await Promise.allSettled([
        apiFetch('/auth/me/'),
        apiFetch('/notifications/unread-count/'),
      ]);

      if (userRes.status === 'fulfilled') user = userRes.value;
      if (countRes.status === 'fulfilled' && countRes.value) {
        unreadCount = countRes.value.unread || 0;
      }
    } catch (err) {
      console.error('Failed to load user data:', err);
    }

    if (!user) {
      // Token is present but invalid/expired — clean up and show login.
      clearTokens();
      renderLoggedOutTopbar();
      return;
    }

    renderLoggedInTopbar(user, unreadCount);
  }

  // Mobile logout button
  if (mobileUserLogout) {
    mobileUserLogout.addEventListener('click', (e) => {
      e.preventDefault();
      performLogout();
    });
  }

  // ============================================================
  // Background preload
  // ============================================================

  loadCategories();

  // Kick off topbar auth rendering
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderTopbarAuth);
  } else {
    renderTopbarAuth();
  }
})();
