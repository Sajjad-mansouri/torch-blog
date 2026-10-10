// static/js/blog/dashboard-post-edit.js
//
// Endpoints used:
//   GET    /api/v1/dashboard/posts/<slug>/
//   POST   /api/v1/dashboard/posts/
//   PATCH  /api/v1/dashboard/posts/<slug>/
//   DELETE /api/v1/dashboard/posts/<slug>/
//   POST   /api/v1/dashboard/posts/<slug>/submit/
//   GET    /api/v1/categories/
//   GET    /api/v1/tags/

(() => {
  'use strict';

  const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
  const DASHBOARD_URL = '/dashboard/?tab=posts';

  // ============================================================
  // Boot guard
  // ============================================================

  const REQUIRED_IDS = [
    'post-form', 'editor-mode-label', 'editor-status-pill',
    'field-title', 'field-slug', 'field-summary',
    'body-editor', 'field-body',
    'field-category', 'field-extra-categories',
    'tag-chips', 'tag-input', 'tag-suggestions',
  ];

  function missingIds() {
    return REQUIRED_IDS.filter((id) => !document.getElementById(id));
  }

  // ============================================================
  // DOM
  // ============================================================

  const $ = (id) => document.getElementById(id);

  const els = {
    modeLabel:       $('editor-mode-label'),
    statusPill:      $('editor-status-pill'),
    saveState:       $('editor-save-state'),
    saveStateText:   document.querySelector('.editor-topbar__save-text'),
    previewBtn:      $('preview-btn'),
    saveBtn:         $('save-btn'),
    submitBtn:       $('submit-btn'),

    loading:         $('editor-loading'),
    error:           $('editor-error'),
    errorTitle:      $('editor-error-title'),
    errorMsg:        $('editor-error-msg'),
    form:            $('post-form'),

    title:           $('field-title'),
    slug:            $('field-slug'),
    summary:         $('field-summary'),
    body:            $('field-body'),
    metaTitle:       $('field-meta-title'),
    metaDescription: $('field-meta-description'),
    noIndex:         $('field-no-index'),

    titleCount:      $('title-count'),
    summaryCount:    $('summary-count'),
    regenSlugBtn:    $('regen-slug-btn'),

    errorTitleEl:    $('error-title'),
    errorSlugEl:     $('error-slug'),
    errorSummaryEl:  $('error-summary'),
    errorBodyEl:     $('error-body'),

    category:        $('field-category'),
    extraCategories: $('field-extra-categories'),

    featuredDropzone:    $('featured-preview'),
    featuredImg:         $('featured-img'),
    featuredPlaceholder: $('featured-placeholder'),
    featuredInput:       $('field-featured-image'),
    featuredRemoveBtn:   $('featured-remove-btn'),

    tagChips:        $('tag-chips'),
    tagInput:        $('tag-input'),
    tagSuggestions:  $('tag-suggestions'),
    tagBrowseBtn:    $('tag-browse-btn'),

    sideSaveBtn:     $('side-save-btn'),
    sideSubmitBtn:   $('side-submit-btn'),
    sidePreviewLink: $('side-preview-link'),
    sideDeleteBtn:   $('side-delete-btn'),

    modalBackdrop:   $('modal-backdrop'),
    modalCancel:     $('modal-cancel'),
    modalConfirm:    $('modal-confirm'),

    toastHost:       $('toast-host'),
  };

  // ============================================================
  // State
  // ============================================================

  const state = {
    mode: 'create',
    slug: null,
    post: null,
    categories: [],
    allTags: [],
    selectedTags: [],
    editor: null,
    imageFile: null,
    imageRemoved: false,
    slugTouched: false,
    dirty: false,
    saving: false,
    activeSuggestionIndex: -1,
  };

  // ============================================================
  // Utilities
  // ============================================================

  const escapeHTML = (s) => s == null ? '' : String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

  const slugify = (text) => (text || '')
    .toString().normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-').replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 280);

  const humanStatus = (s) => ({
    draft: 'Draft', pending: 'Pending review', changes_requested: 'Changes requested',
    approved: 'Approved', scheduled: 'Scheduled', published: 'Published',
    rejected: 'Rejected', unpublished: 'Unpublished', archived: 'Archived',
  }[s] || s);

  function toast(message, type = 'info') {
    if (!els.toastHost) return;
    const el = document.createElement('div');
    el.className = `toast toast--${type}`;
    el.textContent = message;
    els.toastHost.appendChild(el);
    setTimeout(() => {
      el.style.transition = 'opacity 0.25s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 260);
    }, 3200);
  }

  // ============================================================
  // Mode detection
  // ============================================================

  function detectMode() {
    const parts = window.location.pathname.split('/').filter(Boolean);
    if (parts[0] !== 'dashboard' || parts[1] !== 'posts') return null;
    if (parts[2] === 'new') return { mode: 'create', slug: null };
    if (parts[2] && parts[3] === 'edit') {
      return { mode: 'edit', slug: decodeURIComponent(parts[2]) };
    }
    return null;
  }

  // ============================================================
  // CKEditor init
  // ============================================================

  async function initEditor() {
    if (typeof window.ClassicEditor === 'undefined') {
      throw new Error('CKEditor classic build did not load.');
    }

    state.editor = await window.ClassicEditor.create($('body-editor'), {
      licenseKey: 'GPL',
      toolbar: [
        'undo', 'redo', '|',
        'heading', '|',
        'bold', 'italic', 'underline', 'strikethrough', '|',
        'link', 'blockQuote', 'code', 'codeBlock', '|',
        'bulletedList', 'numberedList', '|',
        'alignment', 'outdent', 'indent', '|',
        'insertTable', 'horizontalLine', '|',
        'removeFormat',
      ],
      heading: {
        options: [
          { model: 'paragraph', title: 'Paragraph' },
          { model: 'heading2', view: 'h2', title: 'Heading 2' },
          { model: 'heading3', view: 'h3', title: 'Heading 3' },
          { model: 'heading4', view: 'h4', title: 'Heading 4' },
        ],
      },
      link: {
        addTargetToExternalLinks: true,
        defaultProtocol: 'https://',
      },
    });

    state.editor.model.document.on('change:data', () => {
      els.body.value = state.editor.getData();
      markDirty();
    });
  }

  // ============================================================
  // Categories
  // ============================================================

  async function loadCategories() {
    try {
      const data = await apiFetch('/categories/');
      state.categories = Array.isArray(data) ? data : (data.results || []);
      renderCategoryOptions();
    } catch (err) {
      console.warn('[editor] categories failed', err);
    }
  }

  function renderCategoryOptions() {
    els.category.innerHTML = '<option value="">— None —</option>';
    els.extraCategories.innerHTML = '';
    for (const c of state.categories) {
      const o1 = document.createElement('option');
      o1.value = c.id;
      o1.textContent = c.name;
      els.category.appendChild(o1);

      const o2 = document.createElement('option');
      o2.value = c.id;
      o2.textContent = c.name;
      els.extraCategories.appendChild(o2);
    }
  }

  // ============================================================
  // Tags
  // ============================================================

  async function loadTags() {
    try {
      const data = await apiFetch('/tags/');
      console.log('[editor] tags response:', data);

      if (Array.isArray(data)) {
        state.allTags = data;
      } else if (data && Array.isArray(data.results)) {
        state.allTags = data.results;
      } else {
        console.warn('[editor] unexpected tags response:', data);
        state.allTags = [];
      }

      console.log('[editor] allTags loaded:', state.allTags.length);
    } catch (err) {
      console.error('[editor] tags request failed:', err);
      state.allTags = [];
    }
  }

  function renderTagChips() {
    els.tagChips.innerHTML = state.selectedTags.map((t) => `
      <span class="tag-chip" data-id="${t.id}">
        ${escapeHTML(t.name)}
        <button type="button" class="tag-chip__remove"
                aria-label="Remove tag" data-tag-id="${t.id}">×</button>
      </span>`).join('');
  }

  function addTag(tag) {
    if (!tag || state.selectedTags.some((t) => t.id === tag.id)) return;
    state.selectedTags.push(tag);
    renderTagChips();
    markDirty();
  }

  function removeTag(id) {
    state.selectedTags = state.selectedTags.filter((t) => t.id !== id);
    renderTagChips();
    markDirty();
  }

  function showTagSuggestions(query) {
    const q = (query || '').trim().toLowerCase();
    const chosen = new Set(state.selectedTags.map((t) => t.id));

    let matches;
    if (!q) {
      matches = state.allTags.filter((t) => !chosen.has(t.id)).slice(0, 30);
    } else {
      matches = state.allTags
        .filter((t) => !chosen.has(t.id) && t.name.toLowerCase().includes(q))
        .slice(0, 8);
    }

    if (!matches.length) {
      els.tagSuggestions.hidden = true;
      state.activeSuggestionIndex = -1;
      return;
    }

    els.tagSuggestions.innerHTML = matches.map((t, i) => `
      <div class="tag-suggestion ${i === 0 ? 'is-active' : ''}"
           data-tag-id="${t.id}" data-tag-index="${i}">
        <span>${escapeHTML(t.name)}</span>
        <span class="tag-suggestion__count">${t.usage_count ?? 0} posts</span>
      </div>`).join('');

    els.tagSuggestions.hidden = false;
    els.tagSuggestions.removeAttribute('hidden');
    state.activeSuggestionIndex = 0;
  }

  function highlightSuggestion(rows) {
    rows.forEach((r, i) => r.classList.toggle('is-active', i === state.activeSuggestionIndex));
    rows[state.activeSuggestionIndex]?.scrollIntoView({ block: 'nearest' });
  }

  // ============================================================
  // Featured image
  // ============================================================

  function setFeaturedImagePreview(src) {
    if (src) {
      els.featuredImg.src = src;
      els.featuredImg.hidden = false;
      els.featuredPlaceholder.hidden = true;
      els.featuredRemoveBtn.hidden = false;
    } else {
      els.featuredImg.removeAttribute('src');
      els.featuredImg.hidden = true;
      els.featuredPlaceholder.hidden = false;
      els.featuredRemoveBtn.hidden = true;
    }
  }

  function handleImageFile(file) {
    if (!file) return;
    if (!file.type.startsWith('image/')) return toast('Please select an image file.', 'error');
    if (file.size > MAX_IMAGE_BYTES)     return toast('Image is larger than 5 MB.', 'error');
    state.imageFile = file;
    state.imageRemoved = false;
    setFeaturedImagePreview(URL.createObjectURL(file));
    markDirty();
  }

  // ============================================================
  // Dirty tracking
  // ============================================================

  function markDirty() {
    state.dirty = true;
    if (els.saveState) els.saveState.hidden = false;
    if (els.saveStateText) els.saveStateText.textContent = 'Unsaved changes';
  }

  function markClean() {
    state.dirty = false;
    if (els.saveState) els.saveState.hidden = true;
  }

  function setSavingUI(saving) {
    [els.saveBtn, els.sideSaveBtn, els.submitBtn, els.sideSubmitBtn]
      .forEach((b) => { if (b) b.disabled = saving; });
    if (els.saveState) els.saveState.hidden = !saving;
    if (saving && els.saveStateText) els.saveStateText.textContent = 'Saving…';
  }

  // ============================================================
  // FormData — always sends tags/extra_categories keys
  // ============================================================

  function collectFormData() {
    els.body.value = state.editor ? state.editor.getData() : '';

    const fd = new FormData();
    fd.append('title', els.title.value.trim());
    fd.append('summary', els.summary.value.trim());
    fd.append('body', els.body.value);

    const slug = els.slug.value.trim();
    if (slug) fd.append('slug', slug);

    const mt = els.metaTitle.value.trim();
    if (mt) fd.append('meta_title', mt);
    const md = els.metaDescription.value.trim();
    if (md) fd.append('meta_description', md);
    if (els.noIndex.checked) fd.append('no_index', 'true');

    if (els.category.value) fd.append('category', els.category.value);

    if (els.extraCategories.selectedOptions.length === 0) {
      fd.append('extra_categories', '');
    } else {
      for (const opt of els.extraCategories.selectedOptions) {
        fd.append('extra_categories', opt.value);
      }
    }

    if (state.selectedTags.length === 0) {
      fd.append('tags', '');
    } else {
      for (const t of state.selectedTags) {
        fd.append('tags', String(t.id));
      }
    }

    if (state.imageFile) {
      fd.append('featured_image', state.imageFile);
    }

    return fd;
  }

  // ============================================================
  // Validation
  // ============================================================

  function setFieldError(id, msg) {
    const el = $(id);
    if (!el) return;
    el.textContent = msg;
    el.hidden = false;
  }

  function clearFieldErrors() {
    [els.errorTitleEl, els.errorSlugEl, els.errorSummaryEl, els.errorBodyEl]
      .forEach((el) => { if (el) { el.textContent = ''; el.hidden = true; } });
  }

  function validateForm() {
    clearFieldErrors();
    let ok = true;

    if (!els.title.value.trim()) {
      setFieldError('error-title', 'Title is required.');
      ok = false;
    }

    const html = state.editor ? state.editor.getData() : '';
    const text = html.replace(/<[^>]*>/g, '').trim();
    if (!text) {
      setFieldError('error-body', 'Body is required.');
      ok = false;
    }

    if (!ok) {
      document.querySelector('.field__error:not([hidden])')
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    return ok;
  }

  // ============================================================
  // Save / submit / delete
  // ============================================================

  async function saveDraft() {
    if (state.saving) return;
    if (!validateForm()) return;

    state.saving = true;
    setSavingUI(true);

    try {
      const fd = collectFormData();
      let saved;

      if (state.mode === 'create') {
        saved = await apiFetch('/dashboard/posts/', { method: 'POST', body: fd });
        const newSlug = saved.slug;
        history.replaceState({}, '',
          `/dashboard/posts/${encodeURIComponent(newSlug)}/edit/`);
        state.mode = 'edit';
        state.slug = newSlug;
        updateModeLabel();
        toast('Draft created.', 'ok');
      } else {
        saved = await apiFetch(`/dashboard/posts/${encodeURIComponent(state.slug)}/`, {
          method: 'PATCH',
          body: fd,
        });
        toast('Draft saved.', 'ok');
      }

      state.post = saved;
      state.imageFile = null;
      state.imageRemoved = false;
      updateStatusPill(saved.status);
      updateActionButtons();
      markClean();
    } catch (err) {
      handleSaveError(err);
    } finally {
      state.saving = false;
      setSavingUI(false);
    }
  }

  async function submitForReview() {
    if (state.dirty || state.mode === 'create') {
      await saveDraft();
      if (state.dirty) return;
    }
    if (state.mode !== 'edit' || !state.slug) return;
    if (!confirm('Submit this post for editorial review?')) return;

    try {
      setSavingUI(true);
      const updated = await apiFetch(
        `/dashboard/posts/${encodeURIComponent(state.slug)}/submit/`,
        { method: 'POST', body: JSON.stringify({}) }
      );
      state.post = updated;
      updateStatusPill(updated.status);
      updateActionButtons();
      toast('Submitted for review.', 'ok');
    } catch (err) {
      toast(err?.body?.detail || 'Could not submit for review.', 'error');
    } finally {
      setSavingUI(false);
    }
  }

  function openDeleteModal() {
    if (!els.modalBackdrop) return;
    els.modalBackdrop.hidden = false;
  }

  function closeDeleteModal() {
    if (els.modalBackdrop) els.modalBackdrop.hidden = true;
  }

  async function confirmDelete() {
    closeDeleteModal();
    if (state.mode !== 'edit' || !state.slug) return;
    try {
      setSavingUI(true);
      await apiFetch(`/dashboard/posts/${encodeURIComponent(state.slug)}/`, {
        method: 'DELETE',
      });
      toast('Post deleted.', 'ok');
      setTimeout(() => { window.location.href = DASHBOARD_URL; }, 700);
    } catch (err) {
      toast(err?.body?.detail || 'Could not delete post.', 'error');
    } finally {
      setSavingUI(false);
    }
  }

  function handleSaveError(err) {
    const body = err?.body || {};
    if (err?.status === 401 || err?.status === 403) {
      toast('You are not signed in. Redirecting…', 'error');
      setTimeout(() => redirectToLogin(), 800);
      return;
    }
    let shown = false;
    for (const key of ['title', 'slug', 'summary', 'body']) {
      if (body[key]) {
        const msg = Array.isArray(body[key]) ? body[key][0] : String(body[key]);
        setFieldError(`error-${key}`, msg);
        shown = true;
      }
    }
    if (!shown) toast(body.detail || body.message || 'Save failed.', 'error');
  }

  // ============================================================
  // UI state
  // ============================================================

  function updateModeLabel() {
    if (els.modeLabel) {
      els.modeLabel.textContent = state.mode === 'create' ? 'New post' : 'Edit post';
    }
    document.title = state.mode === 'create'
      ? 'New post · Torch'
      : `${state.post?.title || 'Edit post'} · Torch`;
  }

  function updateStatusPill(status) {
    if (!els.statusPill) return;
    const s = status || 'draft';
    els.statusPill.dataset.status = s;
    els.statusPill.textContent = humanStatus(s);
  }

  function updateActionButtons() {
    const p = state.post;
    const status = p?.status || 'draft';

    const canSubmit = p && ['draft', 'rejected', 'changes_requested'].includes(status);
    if (els.submitBtn)     els.submitBtn.hidden = !canSubmit;
    if (els.sideSubmitBtn) els.sideSubmitBtn.hidden = !canSubmit;

    if (els.previewBtn) {
      els.previewBtn.disabled = !p?.slug;
      els.previewBtn.onclick = p?.slug
        ? () => window.open(
            `/dashboard/posts/${encodeURIComponent(p.slug)}/preview/`, '_blank'
          )
        : null;
    }

    if (els.sidePreviewLink) {
      if (p?.slug) {
        els.sidePreviewLink.href =
          `/dashboard/posts/${encodeURIComponent(p.slug)}/preview/`;
        els.sidePreviewLink.hidden = false;
      } else {
        els.sidePreviewLink.hidden = true;
      }
    }

    if (els.sideDeleteBtn) {
      const canDelete = p && ['draft', 'rejected', 'archived'].includes(status);
      els.sideDeleteBtn.hidden = !canDelete;
    }
  }

  function updateCounters() {
    if (els.titleCount) els.titleCount.textContent = String(els.title.value.length);
    if (els.summaryCount) els.summaryCount.textContent = String(els.summary.value.length);
  }

  // ============================================================
  // Populate
  // ============================================================

  function populateForm(post) {
    els.title.value = post.title || '';
    els.slug.value = post.slug || '';
    state.slugTouched = !!post.slug;
    els.summary.value = post.summary || '';
    els.metaTitle.value = post.meta_title || '';
    els.metaDescription.value = post.meta_description || '';
    els.noIndex.checked = !!post.no_index;

    if (state.editor) state.editor.setData(post.body || '');

    if (post.category?.id) els.category.value = String(post.category.id);

    const extraIds = new Set((post.extra_categories || []).map((c) => String(c.id)));
    for (const opt of els.extraCategories.options) {
      opt.selected = extraIds.has(opt.value);
    }

    state.selectedTags = (post.tags || []).map((t) => ({
      id: t.id, name: t.name, slug: t.slug,
    }));
    renderTagChips();

    setFeaturedImagePreview(post.featured_image || null);

    updateCounters();
    updateStatusPill(post.status);
    updateActionButtons();
  }

  // ============================================================
  // Load existing
  // ============================================================

  async function loadExistingPost(slug) {
    showLoading();
    const url = `/dashboard/posts/${encodeURIComponent(slug)}/`;
    try {
      const post = await apiFetch(url);
      state.post = post;
      populateForm(post);
      showForm();
      markClean();
    } catch (err) {
      showError(err);
    }
  }

  function showLoading() {
    els.loading.hidden = false;
    els.error.hidden = true;
    els.form.hidden = true;
  }

  function showForm() {
    els.loading.hidden = true;
    els.error.hidden = true;
    els.form.hidden = false;
  }

  function showError(err) {
    els.loading.hidden = true;
    els.form.hidden = true;
    els.error.hidden = false;
    const status = err?.status;
    if (status === 404) {
      els.errorTitle.textContent = 'Post not found';
      els.errorMsg.textContent = 'It may have been deleted or the URL is incorrect.';
    } else if (status === 403 || status === 401) {
      els.errorTitle.textContent = 'Access denied';
      els.errorMsg.textContent = 'You do not have permission to edit this post.';
    } else {
      els.errorTitle.textContent = 'Unable to load post';
      els.errorMsg.textContent = err?.body?.detail || 'Please try again.';
    }
  }

  // ============================================================
  // Events
  // ============================================================

  function bindEvents() {
    els.title.addEventListener('input', () => { updateCounters(); markDirty(); });
    els.summary.addEventListener('input', () => { updateCounters(); markDirty(); });
    els.slug.addEventListener('input', () => { state.slugTouched = true; markDirty(); });
    els.metaTitle.addEventListener('input', markDirty);
    els.metaDescription.addEventListener('input', markDirty);
    els.noIndex.addEventListener('change', markDirty);
    els.category.addEventListener('change', markDirty);
    els.extraCategories.addEventListener('change', markDirty);

    els.title.addEventListener('blur', () => {
      if (!state.slugTouched && !els.slug.value && els.title.value) {
        els.slug.value = slugify(els.title.value);
        markDirty();
      }
    });

    els.regenSlugBtn.addEventListener('click', () => {
      if (!els.title.value) return;
      els.slug.value = slugify(els.title.value);
      markDirty();
    });

    // Featured image
    els.featuredDropzone.addEventListener('click', () => els.featuredInput.click());
    els.featuredDropzone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        els.featuredInput.click();
      }
    });
    els.featuredInput.addEventListener('change', (e) => {
      const f = e.target.files?.[0];
      if (f) handleImageFile(f);
      els.featuredInput.value = '';
    });

    ['dragenter', 'dragover'].forEach((ev) =>
      els.featuredDropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        els.featuredDropzone.classList.add('is-dragover');
      }));

    ['dragleave', 'drop'].forEach((ev) =>
      els.featuredDropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        els.featuredDropzone.classList.remove('is-dragover');
      }));

    els.featuredDropzone.addEventListener('drop', (e) => {
      const f = e.dataTransfer?.files?.[0];
      if (f) handleImageFile(f);
    });

    els.featuredRemoveBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      state.imageFile = null;
      state.imageRemoved = true;
      setFeaturedImagePreview(null);
      markDirty();
    });

    // Tags
    els.tagChips.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-tag-id]');
      if (btn) removeTag(Number(btn.dataset.tagId));
    });

    els.tagInput.addEventListener('input', () => showTagSuggestions(els.tagInput.value));
    els.tagInput.addEventListener('focus', () => showTagSuggestions(els.tagInput.value));

    if (els.tagBrowseBtn) {
      els.tagBrowseBtn.addEventListener('click', () => {
        els.tagInput.value = '';
        showTagSuggestions('');
        els.tagInput.focus();
      });
    }

    els.tagInput.addEventListener('keydown', (e) => {
      const rows = [...els.tagSuggestions.querySelectorAll('.tag-suggestion')];

      if (e.key === 'ArrowDown' && rows.length) {
        e.preventDefault();
        state.activeSuggestionIndex = Math.min(
          state.activeSuggestionIndex + 1, rows.length - 1
        );
        highlightSuggestion(rows);
      } else if (e.key === 'ArrowUp' && rows.length) {
        e.preventDefault();
        state.activeSuggestionIndex = Math.max(state.activeSuggestionIndex - 1, 0);
        highlightSuggestion(rows);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (state.activeSuggestionIndex >= 0 && rows[state.activeSuggestionIndex]) {
          const id = Number(rows[state.activeSuggestionIndex].dataset.tagId);
          const tag = state.allTags.find((t) => t.id === id);
          if (tag) addTag(tag);
        } else if (els.tagInput.value.trim()) {
          const name = els.tagInput.value.trim().toLowerCase();
          const match = state.allTags.find((t) => t.name.toLowerCase() === name);
          if (match) addTag(match);
          else toast('Tag must already exist. Ask an editor to create it.', 'error');
        }
        els.tagInput.value = '';
        els.tagSuggestions.hidden = true;
        state.activeSuggestionIndex = -1;
      } else if (e.key === 'Escape') {
        els.tagSuggestions.hidden = true;
        state.activeSuggestionIndex = -1;
      }
    });

    els.tagSuggestions.addEventListener('click', (e) => {
      const row = e.target.closest('.tag-suggestion');
      if (!row) return;
      const tag = state.allTags.find((t) => t.id === Number(row.dataset.tagId));
      if (tag) addTag(tag);
      els.tagInput.value = '';
      els.tagSuggestions.hidden = true;
    });

    document.addEventListener('click', (e) => {
      if (!e.target.closest('#tag-picker')) els.tagSuggestions.hidden = true;
    });

    // Actions
    els.saveBtn.addEventListener('click', saveDraft);
    els.sideSaveBtn.addEventListener('click', saveDraft);
    els.submitBtn.addEventListener('click', submitForReview);
    els.sideSubmitBtn.addEventListener('click', submitForReview);
    els.sideDeleteBtn.addEventListener('click', openDeleteModal);

    els.modalCancel.addEventListener('click', closeDeleteModal);
    els.modalConfirm.addEventListener('click', confirmDelete);
    els.modalBackdrop.addEventListener('click', (e) => {
      if (e.target === els.modalBackdrop) closeDeleteModal();
    });

    window.addEventListener('beforeunload', (e) => {
      if (state.dirty && !state.saving) {
        e.preventDefault();
        e.returnValue = '';
      }
    });

    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        saveDraft();
      }
    });
  }

  // ============================================================
  // Boot
  // ============================================================

  async function init() {
    if (typeof isAuthenticated === 'function' && !isAuthenticated()) {
      redirectToLogin();
      return;
    }

    const missing = missingIds();
    if (missing.length) {
      console.error(
        '[editor] Missing DOM ids:', missing,
        '\nMake sure templates/dashboard-post-edit.html is the template rendering this page.'
      );
      return;
    }

    const info = detectMode();
    if (!info) {
      document.body.innerHTML =
        '<p style="padding:40px;font-family:sans-serif">Invalid editor URL.</p>';
      return;
    }
    state.mode = info.mode;
    state.slug = info.slug;
    updateModeLabel();

    try {
      await initEditor();
    } catch (err) {
      console.error('[editor] CKEditor init failed', err);
      showError({ body: { detail: 'Editor failed to load. Check the CKEditor CDN URL.' } });
      return;
    }

    const tasks = [loadCategories(), loadTags()];
    if (state.mode === 'edit' && state.slug) {
      tasks.push(loadExistingPost(state.slug));
    } else {
      showForm();
      updateStatusPill('draft');
      updateActionButtons();
      updateCounters();
      markClean();
    }
    await Promise.allSettled(tasks);

    bindEvents();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
