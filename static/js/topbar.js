// static/js/topbar.js

(function () {
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
      if (e.target.closest('a')) closeMenu();
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
  // Categories — shared loader
  // ============================================================

  const ddWrapper = document.getElementById('nav-categories');
  const ddBtn = document.getElementById('nav-categories-btn');
  const ddMenu = document.getElementById('nav-categories-menu');
  const parentsPanel = document.getElementById('nav-categories-parents');
  const childrenPanel = document.getElementById('nav-categories-children');

  const mobileCategoriesBtn = document.getElementById('mobile-categories-btn');
  const mobileCategoriesList = document.getElementById('mobile-categories');

  if (!ddBtn && !mobileCategoriesBtn) return;

  const { escapeHtml } = window.TorchUI || {
    escapeHtml: (s) => String(s ?? ''),
  };

  // ------------------------------------------------------------
  // Data loading
  // ------------------------------------------------------------

  let categoriesCache = null;
  let loadPromise = null;

  async function loadCategories() {
    if (categoriesCache) return categoriesCache;
    if (loadPromise) return loadPromise;

    loadPromise = (async () => {
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

    return loadPromise;
  }

  // ------------------------------------------------------------
  // Build two-level groups
  // ------------------------------------------------------------

  function buildGroups(categories) {
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

  // ============================================================
  // Desktop dropdown (two-column)
  // ============================================================

  let groups = [];
  let activeIndex = -1;
  let hoverCloseTimer = null;

  function renderParents() {
    if (!parentsPanel) return;

    parentsPanel.innerHTML = groups
      .map((g, i) => {
        const active = i === activeIndex;
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

    attachParentListeners();
  }

  function renderChildren() {
    if (!childrenPanel) return;

    const group = groups[activeIndex];

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
          const count =
            typeof child.post_count === 'number'
              ? `<span class="topbar__dropdown-item-count">${child.post_count}</span>`
              : '';
          return `
            <a class="topbar__dropdown-child"
               href="/categories/${encodeURIComponent(child.slug)}/"
               role="menuitem">
              <span class="topbar__dropdown-child-label">${escapeHtml(child.name)}</span>
              ${count}
            </a>
          `;
        })
        .join('')}
    `;
  }

  function setActiveIndex(index) {
    if (index === activeIndex) return;
    activeIndex = index;

    if (parentsPanel) {
      for (const el of parentsPanel.querySelectorAll(
        '.topbar__dropdown-parent'
      )) {
        const idx = parseInt(el.dataset.index, 10);
        el.classList.toggle('is-active', idx === activeIndex);
      }
    }

    renderChildren();
  }

  function clearActiveIndex() {
    if (activeIndex === -1) return;
    activeIndex = -1;

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

  function attachParentListeners() {
    if (!parentsPanel) return;

    for (const el of parentsPanel.querySelectorAll(
      '.topbar__dropdown-parent'
    )) {
      const idx = parseInt(el.dataset.index, 10);
      if (!Number.isFinite(idx)) continue;

      el.addEventListener('mouseenter', () => setActiveIndex(idx));
      el.addEventListener('focus', () => setActiveIndex(idx));
      el.addEventListener('click', () => setActiveIndex(idx));
    }
  }

  if (ddBtn && ddMenu && parentsPanel && childrenPanel) {
    const closeDD = () => {
      ddMenu.hidden = true;
      ddBtn.setAttribute('aria-expanded', 'false');
      clearActiveIndex();
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

    async function populate() {
      const categories = await loadCategories();

      if (!categories.length) {
        parentsPanel.innerHTML =
          `<div class="topbar__dropdown-empty">No categories yet.</div>`;
        childrenPanel.innerHTML = '';
        childrenPanel.classList.remove('is-open');
        return;
      }

      groups = buildGroups(categories);
      activeIndex = -1;

      renderParents();
      renderChildren();
    }

    const openDD = async () => {
      cancelScheduledClose();

      if (!ddMenu.dataset.loaded) {
        parentsPanel.innerHTML =
          `<div class="topbar__dropdown-loading">Loading…</div>`;
        childrenPanel.innerHTML = '';
        await populate();
        ddMenu.dataset.loaded = '1';
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
  // Mobile categories — accordion
  // Each parent is a row. Tapping it expands its children
  // directly below. Only one parent open at a time.
  // ============================================================

  if (mobileCategoriesBtn && mobileCategoriesList) {
    let populated = false;

    async function populateMobileList() {
      if (populated) return;
      populated = true;

      const categories = await loadCategories();

      if (!categories.length) {
        mobileCategoriesList.innerHTML =
          `<a href="/categories/">Browse categories</a>`;
        return;
      }

      const groups = buildGroups(categories);

      mobileCategoriesList.innerHTML = groups
        .map((g, i) => {
          const hasChildren = g.children.length > 0;
          const parentCount =
            typeof g.parent.post_count === 'number'
              ? `<span class="topbar__dropdown-item-count">${g.parent.post_count}</span>`
              : '';

          if (!hasChildren) {
            // No children — plain row linking to the category
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

      attachAccordionListeners();
    }

    function attachAccordionListeners() {
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

          // Close all other accordions (only one open at a time)
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
        await populateMobileList();
      }

      mobileCategoriesBtn.setAttribute(
        'aria-expanded',
        next ? 'true' : 'false'
      );
      mobileCategoriesList.hidden = !next;
    });
  }

  // ============================================================
  // Background preload
  // ============================================================

  loadCategories();
})();
