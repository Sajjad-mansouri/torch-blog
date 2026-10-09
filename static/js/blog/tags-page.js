// static/js/blog/tags-page.js

(function () {
  const cloud = document.getElementById('tags-cloud');
  if (!cloud) return;

  const { escapeHtml } = window.TorchUI;

  const els = {
    skeleton: document.getElementById('tags-skeleton'),
    error: document.getElementById('tags-error'),
    errorMessage: document.getElementById('tags-error-message'),
    cloud,
    empty: document.getElementById('tags-empty'),
    count: document.getElementById('tags-count'),
  };

  // ------------------------------------------------------------
  // Rendering
  // ------------------------------------------------------------

  function renderChip(tag) {
    const count =
      typeof tag.usage_count === 'number' ? tag.usage_count : 0;
    return `
      <a class="tag-chip" href="/tags/${encodeURIComponent(tag.slug)}/">
        <span class="tag-chip__hash">#</span>${escapeHtml(tag.name)}
        <span class="tag-chip__count">${count}</span>
      </a>
    `;
  }

  // ------------------------------------------------------------
  // Load
  // ------------------------------------------------------------

  async function load() {
    try {
      const data = await apiFetch('/tags/');
      const tags = Array.isArray(data) ? data : [];

      els.skeleton.hidden = true;

      if (!tags.length) {
        els.empty.hidden = false;
        return;
      }

      els.count.textContent =
        tags.length === 1 ? '1 tag' : `${tags.length} tags`;

      els.cloud.innerHTML = tags.map(renderChip).join('');
      els.cloud.hidden = false;
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
