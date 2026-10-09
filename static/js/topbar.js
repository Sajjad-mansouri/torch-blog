// static/js/topbar.js

(function () {
  // ============================================================
  // Mobile menu
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

    // Close when a link inside the menu is clicked
    menu.addEventListener('click', (e) => {
      if (e.target.closest('a')) closeMenu();
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (menu.hidden) return;
      if (e.target.closest('.topbar__left')) return;
      if (e.target.closest('#topbar-menu')) return;
      closeMenu();
    });

    // Close on Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !menu.hidden) {
        closeMenu();
        menuBtn.focus();
      }
    });
  }

  // ============================================================
  // Filters toggle (mobile only, present on /posts/ only)
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
})();
