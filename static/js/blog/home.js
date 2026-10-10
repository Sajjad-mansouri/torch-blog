// static/js/blog/home.js
//
// Loads GET /api/v1/home/ and renders the home page.

(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);

  // ============================================================
  // Utilities
  // ============================================================

  const escapeHTML = (s) =>
    s == null ? '' : String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const formatDate = (iso) => {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleDateString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
      });
    } catch { return ''; }
  };

  const formatNumber = (n) => {
    if (n == null) return '0';
    if (n < 1000) return String(n);
    if (n < 1000000) return (n / 1000).toFixed(n < 10000 ? 1 : 0) + 'k';
    return (n / 1000000).toFixed(1) + 'M';
  };

  const getInitials = (name) => {
    if (!name) return '?';
    return name.trim().split(/\s+/).slice(0, 2)
      .map((p) => (p[0] ? p[0].toUpperCase() : '')).join('');
  };

  const authorName = (a) => a?.display_name || a?.username || 'Unknown';
  const postUrl = (p) => `/posts/${encodeURIComponent(p.slug)}/`;


  // ============================================================
  // Avatars
  // ============================================================

  function heroAvatar(author) {
    if (!author) return '';
    const name = authorName(author);
    if (author.avatar_url) {
      return `<img class="home-hero__avatar" src="${escapeHTML(author.avatar_url)}" alt="" loading="lazy">`;
    }
    return `<span class="home-hero__avatar-fallback">${escapeHTML(getInitials(name))}</span>`;
  }

  function cardAvatar(author) {
    if (!author) return '';
    const name = authorName(author);
    if (author.avatar_url) {
      return `<img class="home-card__avatar" src="${escapeHTML(author.avatar_url)}" alt="" loading="lazy">`;
    }
    return `<span class="home-card__avatar-fallback">${escapeHTML(getInitials(name))}</span>`;
  }

  // ============================================================
  // Hero — primary + up to 4 secondaries + any remaining as tertiary
  // ============================================================

  function renderHero(featured) {
    const host = $('home-hero');
    if (!host) return;

    if (!featured || !featured.length) {
      host.innerHTML = `
        <div class="home-error" style="grid-column:1/-1;margin:0">
          <div class="home-error__icon">✎</div>
          <h2 class="home-error__title">Nothing featured yet</h2>
          <p class="home-error__message">
            Check back soon — the editors are preparing the next round.
          </p>
        </div>`;
      return;
    }

    const primary = featured[0];
    const secondaries = featured.slice(1, 5);   // up to 4
    const tertiary = featured.slice(5);          // remaining

    host.innerHTML = `
      ${renderPrimary(primary)}
      ${secondaries.length
        ? `<div class="home-hero__side">${secondaries.map(renderSecondary).join('')}</div>`
        : ''}
      ${tertiary.length
        ? `<div class="home-hero__tertiary">${tertiary.map(renderTertiary).join('')}</div>`
        : ''}
    `;
  }

  function renderPrimary(post) {
    const media = post.featured_image
      ? `<img src="${escapeHTML(post.featured_image)}" alt="">`
      : '';

    return `
      <a class="home-hero__primary" href="${postUrl(post)}">
        ${media}
        <div class="home-hero__overlay">
          ${post.category
            ? `<span class="home-hero__badge">${escapeHTML(post.category.name)}</span>`
            : ''}
          <h2 class="home-hero__title">${escapeHTML(post.title)}</h2>
          ${post.summary
            ? `<p class="home-hero__summary">${escapeHTML(post.summary)}</p>`
            : ''}
          <div class="home-hero__meta">
            ${heroAvatar(post.author)}
            <span>${escapeHTML(authorName(post.author))}</span>
            <span class="dot">·</span>
            <span>${escapeHTML(formatDate(post.published_at))}</span>
            ${post.reading_time
              ? `<span class="dot">·</span><span>${post.reading_time} min read</span>`
              : ''}
          </div>
        </div>
      </a>`;
  }

  function renderSecondary(post) {
    return `
      <a class="home-hero__secondary" href="${postUrl(post)}">
        <div class="home-hero__secondary-media">
          ${post.featured_image
            ? `<img src="${escapeHTML(post.featured_image)}" alt="" loading="lazy">`
            : ''}
        </div>
        <div class="home-hero__secondary-body">
          ${post.category
            ? `<span class="home-hero__secondary-cat">${escapeHTML(post.category.name)}</span>`
            : ''}
          <h3 class="home-hero__secondary-title">${escapeHTML(post.title)}</h3>
          <div class="home-hero__secondary-meta">
            ${escapeHTML(authorName(post.author))} · ${escapeHTML(formatDate(post.published_at))}
          </div>
        </div>
      </a>`;
  }

  function renderTertiary(post) {
    return `
      <a class="home-hero__tertiary-card" href="${postUrl(post)}">
        <div class="home-hero__tertiary-media">
          ${post.featured_image
            ? `<img src="${escapeHTML(post.featured_image)}" alt="" loading="lazy">`
            : ''}
        </div>
        <div class="home-hero__tertiary-body">
          ${post.category
            ? `<span class="home-hero__tertiary-cat">${escapeHTML(post.category.name)}</span>`
            : ''}
          <h3 class="home-hero__tertiary-title">${escapeHTML(post.title)}</h3>
          <div class="home-hero__tertiary-meta">
            ${escapeHTML(authorName(post.author))} · ${escapeHTML(formatDate(post.published_at))}
          </div>
        </div>
      </a>`;
  }

  // ============================================================
  // Latest grid
  // ============================================================

  function renderCard(post) {
    const media = post.featured_image
      ? `<img src="${escapeHTML(post.featured_image)}" alt="" loading="lazy">`
      : '';

    return `
      <a class="home-card" href="${postUrl(post)}">
        <div class="home-card__media">${media}</div>
        <div class="home-card__body">
          ${post.category
            ? `<span class="home-card__category">${escapeHTML(post.category.name)}</span>`
            : ''}
          <h3 class="home-card__title">${escapeHTML(post.title)}</h3>
          ${post.summary
            ? `<p class="home-card__summary">${escapeHTML(post.summary)}</p>`
            : ''}
          <div class="home-card__meta">
            ${cardAvatar(post.author)}
            <span>${escapeHTML(authorName(post.author))}</span>
            <span class="dot">·</span>
            <span>${escapeHTML(formatDate(post.published_at))}</span>
          </div>
        </div>
      </a>`;
  }

  function renderLatest(latest) {
    const grid = $('latest-grid');
    if (!grid) return;

    if (!latest || !latest.length) {
      grid.innerHTML = `
        <div class="home-error" style="grid-column:1/-1;margin:0">
          <p class="home-error__message">No posts yet.</p>
        </div>`;
      return;
    }
    grid.innerHTML = latest.map(renderCard).join('');
  }

  // ============================================================
  // Trending
  // ============================================================

  function renderTrending(trending) {
    const list = $('trending-list');
    if (!list) return;

    if (!trending || !trending.length) {
      list.innerHTML = `
        <div class="home-error" style="margin:0">
          <p class="home-error__message">Nothing trending right now.</p>
        </div>`;
      return;
    }

    list.innerHTML = trending.map((p, i) => `
      <a class="home-trending__item" href="${postUrl(p)}">
        <span class="home-trending__num">${i + 1}</span>
        <div class="home-trending__body">
          <h3 class="home-trending__title">${escapeHTML(p.title)}</h3>
          <div class="home-trending__meta">
            ${escapeHTML(authorName(p.author))} · ${escapeHTML(formatDate(p.published_at))}
          </div>
        </div>
        <div class="home-trending__stats">
          👁 ${formatNumber(p.views_count || 0)} · ♥ ${formatNumber(p.like_count || 0)}
        </div>
      </a>`).join('');
  }

  // ============================================================
  // Categories
  // ============================================================

  function renderCategories(categories) {
    const list = $('categories-list');
    const block = $('categories-block');
    if (!list) return;

    if (!categories || !categories.length) {
      if (block) block.hidden = true;
      return;
    }

    list.innerHTML = categories.map((c) => `
      <a class="home-categories__item" href="/categories/${encodeURIComponent(c.slug)}/">
        <span class="home-categories__name">${escapeHTML(c.name)}</span>
        <span class="home-categories__count">${c.post_count ?? 0}</span>
      </a>`).join('');
  }

  // ============================================================
  // Tags
  // ============================================================

  function renderTags(tags) {
    const list = $('tags-list');
    const block = $('tags-block');
    if (!list) return;

    if (!tags || !tags.length) {
      if (block) block.hidden = true;
      return;
    }

    list.innerHTML = tags.map((t) => `
      <a class="home-tags__item" href="/tags/${encodeURIComponent(t.slug)}/">
        <span>#${escapeHTML(t.name)}</span>
        <span class="home-tags__count">${t.usage_count ?? 0}</span>
      </a>`).join('');
  }

  // ============================================================
  // Error state
  // ============================================================

  function showError(message) {
    const hero = $('home-hero');
    const layout = document.querySelector('.home-layout');
    const err = $('home-error');

    if (hero) hero.hidden = true;
    if (layout) layout.hidden = true;
    if (err) err.hidden = false;

    const msg = $('home-error-message');
    if (msg) msg.textContent = message || 'Please try again.';
  }

  function hideError() {
    const hero = $('home-hero');
    const layout = document.querySelector('.home-layout');
    const err = $('home-error');

    if (hero) hero.hidden = false;
    if (layout) layout.hidden = false;
    if (err) err.hidden = true;
  }

  // ============================================================
  // Load
  // ============================================================

  async function loadHome() {
    try {
      const data = await apiFetch('/home/');
      hideError();

      renderHero(data.featured);
      renderLatest(data.latest);
      renderTrending(data.trending);
      renderCategories(data.categories);
      renderTags(data.hot_tags);
    } catch (err) {
      console.error('[home] load failed', err);
      showError(err?.body?.detail || 'The server did not respond.');
    }
  }

  // ============================================================
  // Boot
  // ============================================================

  function init() {
    const retry = $('home-retry');
    if (retry) retry.addEventListener('click', loadHome);
    loadHome();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
