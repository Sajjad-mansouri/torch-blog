// static/js/search.js

(function () {
  const form = document.getElementById('search-form');
  const input = document.getElementById('search-input');
  const clearBtn = document.getElementById('search-clear');
  const suggestBox = document.getElementById('search-suggest');

  if (!form || !input || !suggestBox) return;

  const { escapeHtml } = window.TorchUI;

  // ------------------------------------------------------------
  // State
  // ------------------------------------------------------------

  let query = '';
  let results = [];
  let activeIndex = -1;
  let fetchSeq = 0;
  let debounceTimer = null;
  let suggestOpen = false;

  const TYPES = {
    post:   { label: 'Posts',   icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 4h12l4 4v12H4z"/><path d="M8 12h8M8 16h8M8 8h4"/></svg>' },
    author: { label: 'Authors', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="8" r="4"/><path d="M4 21v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2"/></svg>' },
    tag:    { label: 'Tags',    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M20.6 13.4L11.6 22.4 2 12.8V2h10.8l7.8 7.8a2 2 0 0 1 0 3.6z"/><circle cx="7" cy="7" r="1.4" fill="currentColor" stroke="none"/></svg>' },
  };

  // ------------------------------------------------------------
  // API
  // ------------------------------------------------------------

  async function fetchSuggestions(q) {
    const res = await apiFetch(`/search/suggest/?q=${encodeURIComponent(q)}`);
    return res.results || [];
  }

  // ------------------------------------------------------------
  // Dropdown rendering
  // ------------------------------------------------------------

  function openSuggest() {
    suggestBox.hidden = false;
    suggestOpen = true;
    input.setAttribute('aria-expanded', 'true');
  }

  function closeSuggest() {
    suggestBox.hidden = true;
    suggestOpen = false;
    activeIndex = -1;
    input.setAttribute('aria-expanded', 'false');
  }

  function renderSuggest() {
    if (!results.length) {
      suggestBox.innerHTML = `<div class="search-suggest__empty">No matches for "${escapeHtml(query)}"</div>`;
      return;
    }

    // Group by type: post, author, tag (in that order)
    const order = ['post', 'author', 'tag'];
    const grouped = {};
    for (const r of results) {
      if (!grouped[r.type]) grouped[r.type] = [];
      grouped[r.type].push(r);
    }

    const parts = [];
    let flatIndex = 0;

    for (const type of order) {
      const items = grouped[type];
      if (!items || !items.length) continue;
      const meta = TYPES[type] || { label: type, icon: '' };

      parts.push(`<div class="search-suggest__group">`);
      parts.push(`<div class="search-suggest__group-title">${escapeHtml(meta.label)}</div>`);

      for (const item of items) {
        const isActive = flatIndex === activeIndex;
        parts.push(`
          <a class="search-suggest__item ${isActive ? 'is-active' : ''}"
             href="${escapeHtml(item.url)}"
             data-index="${flatIndex}"
             role="option"
             aria-selected="${isActive}">
            ${meta.icon}
            <span class="search-suggest__item-label">${escapeHtml(item.label)}</span>
            <span class="search-suggest__item-meta">${escapeHtml(type)}</span>
          </a>
        `);
        flatIndex++;
      }

      parts.push(`</div>`);
    }

    // "See all results" footer
    parts.push(`
      <a class="search-suggest__item search-suggest__item--all"
         href="/search/?q=${encodeURIComponent(query)}"
         data-index="${flatIndex}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>
        </svg>
        <span class="search-suggest__item-label">
          See all results for "${escapeHtml(query)}"
        </span>
      </a>
    `);

    suggestBox.innerHTML = parts.join('');

    // Track the total number of selectable items (including "see all")
    suggestBox.dataset.total = String(flatIndex + 1);
  }

  // ------------------------------------------------------------
  // Fetch with debounce and sequence guard
  // ------------------------------------------------------------

  function scheduleFetch() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runFetch, 180);
  }

  async function runFetch() {
    const q = query.trim();

    if (q.length < 2) {
      results = [];
      closeSuggest();
      return;
    }

    const mySeq = ++fetchSeq;

    suggestBox.innerHTML = `<div class="search-suggest__loading">Searching…</div>`;
    openSuggest();

    try {
      const items = await fetchSuggestions(q);
      if (mySeq !== fetchSeq) return;
      results = items;
      activeIndex = -1;
      renderSuggest();
    } catch (err) {
      if (mySeq !== fetchSeq) return;
      console.error(err);
      suggestBox.innerHTML = `<div class="search-suggest__empty">Couldn't search. Please try again.</div>`;
    }
  }

  // ------------------------------------------------------------
  // Input events
  // ------------------------------------------------------------

  input.addEventListener('input', () => {
    query = input.value;
    clearBtn.hidden = !query;
    scheduleFetch();
  });

  input.addEventListener('focus', () => {
    if (input.value.trim().length >= 2 && results.length) {
      openSuggest();
    }
  });

  // Submit (Enter) → navigate to the search results page
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q) return;
    closeSuggest();
    window.location.href = `/search/?q=${encodeURIComponent(q)}`;
  });

  // Clear button
  clearBtn.addEventListener('click', () => {
    input.value = '';
    query = '';
    results = [];
    clearBtn.hidden = true;
    closeSuggest();
    input.focus();
  });

  // ------------------------------------------------------------
  // Keyboard navigation
  // ------------------------------------------------------------

  input.addEventListener('keydown', (e) => {
    const total = parseInt(suggestBox.dataset.total || '0', 10);

    if (e.key === 'ArrowDown') {
      if (!suggestOpen) {
        openSuggest();
        return;
      }
      e.preventDefault();
      if (total === 0) return;
      activeIndex = (activeIndex + 1) % total;
      renderSuggest();
      scrollActiveIntoView();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (total === 0) return;
      activeIndex = (activeIndex - 1 + total) % total;
      renderSuggest();
      scrollActiveIntoView();
    } else if (e.key === 'Enter') {
      if (suggestOpen && activeIndex >= 0) {
        e.preventDefault();
        const el = suggestBox.querySelector(`[data-index="${activeIndex}"]`);
        if (el) {
          window.location.href = el.getAttribute('href');
          closeSuggest();
        }
      }
      // Otherwise, the form's submit handler runs and navigates to /search/
    } else if (e.key === 'Escape') {
      closeSuggest();
    }
  });

  function scrollActiveIntoView() {
    const el = suggestBox.querySelector('.search-suggest__item.is-active');
    if (el) el.scrollIntoView({ block: 'nearest' });
  }

  // ------------------------------------------------------------
  // Close on outside click
  // ------------------------------------------------------------

  document.addEventListener('click', (e) => {
    if (!e.target.closest('#topbar-search')) {
      closeSuggest();
    }
  });

  // ------------------------------------------------------------
  // Prefill from ?q=… on the search results page
  // (harmless elsewhere — it just won't match)
  // ------------------------------------------------------------

  const params = new URLSearchParams(window.location.search);
  const initialQ = params.get('q');
  if (initialQ && getPathParts()[0] === 'search') {
    input.value = initialQ;
    query = initialQ;
    clearBtn.hidden = false;
  }
})();
