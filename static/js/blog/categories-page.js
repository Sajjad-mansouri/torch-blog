// static/js/blog/categories-page.js

(function () {
  const grid = document.getElementById('categories-grid');
  if (!grid) return;

  const { escapeHtml } = window.TorchUI;

  const els = {
    skeleton: document.getElementById('categories-skeleton'),
    error: document.getElementById('categories-error'),
    errorMessage: document.getElementById('categories-error-message'),
    grid,
    empty: document.getElementById('categories-empty'),
    count: document.getElementById('categories-count'),
  };

  // ------------------------------------------------------------
  // Group categories into parent + children for display.
  // Parents come first (with their post count), then a nested
  // row showing each child as a small chip underneath.
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

  // ------------------------------------------------------------
  // Rendering
  // ------------------------------------------------------------

  function renderCard(group) {
    const { parent, children } = group;

    const url = `/categories/${encodeURIComponent(parent.slug)}/`;
    const image = parent.image
      ? `<img src="${escapeHtml(parent.image)}" alt="" loading="lazy">`
      : '';
    const description = parent.description
      ? `<p class="taxonomy-card__description">${escapeHtml(parent.description)}</p>`
      : '';

    const postCount =
      typeof parent.post_count === 'number'
        ? parent.post_count === 1
          ? '1 post'
          : `${parent.post_count} posts`
        : '';

    const childChips = children.length
      ? `<div class="taxonomy-card__children">
           ${children
             .map(
               (c) => `
                 <a class="taxonomy-card__child"
                    href="/categories/${encodeURIComponent(c.slug)}/">
                   ${escapeHtml(c.name)}
                 </a>
               `
             )
             .join('')}
         </div>`
      : '';

    return `
      <article class="taxonomy-card taxonomy-card--category">
        <a class="taxonomy-card__media" href="${url}">${image}</a>
        <div class="taxonomy-card__body">
          <h2 class="taxonomy-card__title">
            <a href="${url}">${escapeHtml(parent.name)}</a>
          </h2>
          ${description}
          ${postCount ? `<div class="taxonomy-card__meta">${postCount}</div>` : ''}
          ${childChips}
        </div>
      </article>
    `;
  }

  // ------------------------------------------------------------
  // Load
  // ------------------------------------------------------------

  async function load() {
    try {
      const data = await apiFetch('/categories/');
      const categories = Array.isArray(data) ? data : [];

      els.skeleton.hidden = true;

      if (!categories.length) {
        els.empty.hidden = false;
        return;
      }

      const groups = buildGroups(categories);

      els.count.textContent =
        groups.length === 1 ? '1 category' : `${groups.length} categories`;

      els.grid.innerHTML = groups.map(renderCard).join('');
      els.grid.hidden = false;
    } catch (err) {
      console.error(err);
      els.skeleton.hidden = true;
      els.errorMessage.textContent =
        (err.body && (err.body.detail || err.body.message)) ||
        'Please check your connection and try again.';
      els.error.hidden = false;
    }
  }

  document.addEventListener('DOMContentLoaded', load);
})();
