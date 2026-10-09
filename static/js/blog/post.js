// static/js/post.js

const { escapeHtml, formatDate, formatDateTime, ICONS, renderCard, postUrl, authorUrl, categoryUrl, tagUrl } = window.TorchUI;

// ============================================================
// Read slug from path: /posts/<slug>/
// ============================================================

function getSlugFromPath() {
  const parts = getPathParts();
  if (parts[0] === 'posts' && parts[1]) {
    return decodeURIComponent(parts[1]);
  }
  return null;
}

// ============================================================
// State
// ============================================================

const state = {
  slug: null,
  post: null,
  commentsPage: 1,
  commentsTotal: 0,
  commentsHasNext: false,
  user: null,
};

// ============================================================
// Elements
// ============================================================

const els = {
  skeleton: document.getElementById('post-skeleton'),
  error: document.getElementById('post-error'),
  errorTitle: document.getElementById('post-error-title'),
  errorMessage: document.getElementById('post-error-message'),
  article: document.getElementById('post-article'),

  category: document.getElementById('post-category'),
  title: document.getElementById('post-title'),
  summary: document.getElementById('post-summary'),
  authorLink: document.getElementById('post-author-link'),
  authorAvatar: document.getElementById('post-author-avatar'),
  authorName: document.getElementById('post-author-name'),
  authorSub: document.getElementById('post-author-sub'),
  published: document.getElementById('post-published'),
  reading: document.getElementById('post-reading'),

  hero: document.getElementById('post-hero'),
  heroImage: document.getElementById('post-hero-image'),

  btnLike: document.getElementById('btn-like'),
  iconLike: document.getElementById('icon-like'),
  labelLike: document.getElementById('label-like'),
  countLike: document.getElementById('count-like'),

  btnBookmark: document.getElementById('btn-bookmark'),
  iconBookmark: document.getElementById('icon-bookmark'),
  labelBookmark: document.getElementById('label-bookmark'),
  countBookmark: document.getElementById('count-bookmark'),

  btnShare: document.getElementById('btn-share'),

  postViews: document.getElementById('post-views'),
  postCommentsCount: document.getElementById('post-comments-count'),

  body: document.getElementById('post-body'),
  tags: document.getElementById('post-tags'),

  authorCard: document.getElementById('author-card'),
  authorCardAvatar: document.getElementById('author-card-avatar'),
  authorCardName: document.getElementById('author-card-name'),
  authorCardBio: document.getElementById('author-card-bio'),
  authorCardLinks: document.getElementById('author-card-links'),

  commentsSection: document.getElementById('comments-section'),
  commentsTotal: document.getElementById('comments-total'),
  commentFormWrap: document.getElementById('comment-form-wrap'),
  commentsList: document.getElementById('comments-list'),
  commentsEmpty: document.getElementById('comments-empty'),
  commentsMore: document.getElementById('comments-more'),
  commentsLoadMore: document.getElementById('comments-load-more'),

  relatedSection: document.getElementById('related-section'),
  relatedGrid: document.getElementById('related-grid'),

  authorPostsSection: document.getElementById('author-posts-section'),
  authorPostsTitle: document.getElementById('author-posts-title'),
  authorPostsGrid: document.getElementById('author-posts-grid'),

  topbarAuth: document.getElementById('topbar-auth'),
  footerYear: document.getElementById('footer-year'),
};

// ============================================================
// API calls
// ============================================================

async function fetchPost(slug) {
  return apiFetch(`/posts/${encodeURIComponent(slug)}/`);
}

async function fetchComments(slug, page = 1) {
  return apiFetch(`/posts/${encodeURIComponent(slug)}/comments/?page=${page}`);
}

async function createComment(slug, { body, parent }) {
  const payload = { body };
  if (parent) payload.parent = parent;
  return apiFetch(`/posts/${encodeURIComponent(slug)}/comments/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

async function toggleLike(slug) {
  return apiFetch(`/posts/${encodeURIComponent(slug)}/like/`, {
    method: 'POST',
  });
}

async function toggleBookmark(slug) {
  return apiFetch(`/posts/${encodeURIComponent(slug)}/bookmark/`, {
    method: 'POST',
  });
}

async function toggleCommentLike(commentId) {
  return apiFetch(`/comments/${commentId}/like/`, { method: 'POST' });
}

async function deleteComment(commentId) {
  return apiFetch(`/comments/${commentId}/`, { method: 'DELETE' });
}

async function editComment(commentId, body) {
  return apiFetch(`/comments/${commentId}/`, {
    method: 'PATCH',
    body: JSON.stringify({ body }),
  });
}

// ============================================================
// Rendering — post
// ============================================================

function renderPost(post) {
  els.title.textContent = post.title;
  els.summary.textContent = post.summary || '';
  els.summary.hidden = !post.summary;

  if (post.category && post.category.slug) {
    els.category.textContent = post.category.name;
    els.category.href = categoryUrl(post.category.slug);
    els.category.hidden = false;
  }

  const author = post.author || {};
  const authorName = author.display_name || author.username || 'Unknown';
  const avatar = author.avatar_url || '/static/img/default-avatar.jpg';
  els.authorAvatar.src = avatar;
  els.authorName.textContent = authorName;
  els.authorSub.textContent = author.username ? `@${author.username}` : '';
  els.authorLink.href = author.username ? authorUrl(author.username) : '#';

  const publishedIso = post.published_at || post.created_at;
  els.published.textContent = formatDate(publishedIso);
  els.published.setAttribute('datetime', publishedIso || '');
  els.reading.textContent = post.reading_time ? `${post.reading_time} min read` : '';

  if (post.featured_image) {
    els.heroImage.src = post.featured_image;
    els.heroImage.alt = post.title;
    els.hero.hidden = false;
  } else {
    els.hero.hidden = true;
  }

  els.countLike.textContent = post.like_count ?? 0;
  els.countBookmark.textContent = post.bookmark_count ?? 0;
  els.postViews.textContent = `${post.views_count ?? 0} views`;
  els.postCommentsCount.textContent = `${post.comment_count ?? 0} comments`;

  updateLikeButton(post.is_liked);
  updateBookmarkButton(post.is_bookmarked);

  els.body.innerHTML = post.body || '';

  renderTags(post.tags || []);
  renderAuthorCard(post.author);
  renderRelated(post.similar_posts || [], els.relatedSection, els.relatedGrid);
  renderAuthorPosts(
    post.author_other_posts || [],
    els.authorPostsSection,
    els.authorPostsGrid,
    authorName
  );
}

function renderTags(tags) {
  if (!tags.length) {
    els.tags.hidden = true;
    return;
  }
  els.tags.hidden = false;
  els.tags.innerHTML = tags
    .map(
      (t) =>
        `<a class="tag-chip" href="${tagUrl(t.slug)}">#${escapeHtml(t.name)}</a>`
    )
    .join('');
}

function renderAuthorCard(author) {
  if (!author || !author.username) {
    els.authorCard.hidden = true;
    return;
  }
  els.authorCard.hidden = false;
  els.authorCardAvatar.src = author.avatar_url || '/static/img/default-avatar.jpg';
  els.authorCardName.textContent = author.display_name || author.username;
  els.authorCardName.href = authorUrl(author.username);
  els.authorCardBio.textContent = author.bio || '';
  els.authorCardBio.hidden = !author.bio;

  const links = [];
  if (author.website) {
    links.push(
      `<a class="author-link" href="${escapeHtml(author.website)}" target="_blank" rel="noopener noreferrer">Website</a>`
    );
  }
  for (const s of author.social_links || []) {
    links.push(
      `<a class="author-link" href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(s.platform_display || s.platform)}</a>`
    );
  }
  els.authorCardLinks.innerHTML = links.join('');
  els.authorCardLinks.hidden = links.length === 0;
}

function renderRelated(posts, section, grid) {
  if (!posts.length) {
    section.hidden = true;
    return;
  }
  section.hidden = false;
  grid.innerHTML = posts.map((p) => renderCard(p)).join('');
}

function renderAuthorPosts(posts, section, grid, authorName) {
  if (!posts.length) {
    section.hidden = true;
    return;
  }
  section.hidden = false;
  els.authorPostsTitle.textContent = `More from ${authorName}`;
  grid.innerHTML = posts.map((p) => renderCard(p)).join('');
}

function updateLikeButton(isLiked) {
  els.btnLike.classList.toggle('is-active', !!isLiked);
  els.btnLike.setAttribute('aria-pressed', isLiked ? 'true' : 'false');
  els.iconLike.innerHTML = isLiked ? ICONS.heartFilled : ICONS.heart;
  els.labelLike.textContent = isLiked ? 'Liked' : 'Like';
}

function updateBookmarkButton(isBookmarked) {
  els.btnBookmark.classList.toggle('is-active', !!isBookmarked);
  els.btnBookmark.setAttribute('aria-pressed', isBookmarked ? 'true' : 'false');
  els.iconBookmark.innerHTML = isBookmarked ? ICONS.bookmarkFilled : ICONS.bookmark;
  els.labelBookmark.textContent = isBookmarked ? 'Saved' : 'Bookmark';
}

// ============================================================
// Rendering — comments
// ============================================================

function renderComment(comment, depth = 0) {
  const author = comment.author || {};
  const authorName = author.display_name || author.username || '[deleted]';
  const avatar = author.avatar_url || '/static/img/default-avatar.jpg';
  const isMine = state.user && author.id === state.user.id;
  const isDeleted = comment.is_deleted === true;

  const repliesHtml =
    depth === 0 && comment.replies && comment.replies.length
      ? `<div class="comment__replies">${comment.replies
          .map((r) => renderComment(r, depth + 1))
          .join('')}</div>`
      : '';

  const editedHtml = comment.edited_at
    ? ` <span class="comment__edited">(edited)</span>`
    : '';

  const actionsHtml = isDeleted
    ? ''
    : `
      <div class="comment__actions">
        <button type="button" class="comment__action" data-action="like" data-id="${comment.id}" aria-pressed="${comment.is_liked ? 'true' : 'false'}">
          ${comment.is_liked ? ICONS.heartFilled : ICONS.heart}
          <span>${comment.like_count ?? 0}</span>
        </button>
        ${
          depth === 0
            ? `<button type="button" class="comment__action" data-action="reply" data-id="${comment.id}">
                 ${ICONS.reply} Reply
               </button>`
            : ''
        }
        ${
          isMine
            ? `
              <button type="button" class="comment__action" data-action="edit" data-id="${comment.id}">Edit</button>
              <button type="button" class="comment__action comment__action--danger" data-action="delete" data-id="${comment.id}">Delete</button>
            `
            : ''
        }
      </div>
    `;

  const bodyHtml = isDeleted
    ? `<p class="comment__body comment__body--deleted">[deleted]</p>`
    : `<p class="comment__body" data-body="${comment.id}">${escapeHtml(comment.body)}</p>`;

  return `
    <article class="comment ${depth > 0 ? 'comment--reply' : ''}" data-id="${comment.id}" id="comment-${comment.id}">
      <img class="comment__avatar" src="${escapeHtml(avatar)}" alt="">
      <div class="comment__main">
        <div class="comment__header">
          <span class="comment__author">${escapeHtml(authorName)}</span>
          <time class="comment__time" datetime="${escapeHtml(comment.created_at)}">${formatDateTime(comment.created_at)}${editedHtml}</time>
        </div>
        ${bodyHtml}
        ${actionsHtml}
        ${repliesHtml}
      </div>
    </article>
  `;
}

function renderComments(comments, append = false) {
  if (!append) {
    els.commentsList.innerHTML = '';
  }

  if (!comments.length && !append) {
    els.commentsEmpty.hidden = false;
    return;
  }
  els.commentsEmpty.hidden = true;

  const html = comments.map((c) => renderComment(c, 0)).join('');
  els.commentsList.insertAdjacentHTML('beforeend', html);
}

function renderCommentForm() {
  if (!state.user) {
    const next = encodeURIComponent(window.location.pathname);
    els.commentFormWrap.innerHTML = `
      <div class="comment-prompt">
        <p>Join the conversation.</p>
        <a class="btn btn--primary" href="/login/?next=${next}">
          Log in to comment
        </a>
      </div>
    `;
    return;
  }

  const avatar = state.user.avatar_url || '/static/img/default-avatar.jpg';

  els.commentFormWrap.innerHTML = `
    <form class="comment-form" id="comment-form">
      <img class="comment-form__avatar" src="${escapeHtml(avatar)}" alt="">
      <div class="comment-form__main">
        <textarea
          id="comment-body"
          class="comment-form__input"
          placeholder="Write a comment…"
          rows="3"
          maxlength="2000"
          required
        ></textarea>
        <div class="comment-form__error" id="comment-form-error" hidden></div>
        <div class="comment-form__actions">
          <button type="submit" class="btn btn--primary" id="comment-submit">Post comment</button>
        </div>
      </div>
    </form>
  `;

  document
    .getElementById('comment-form')
    .addEventListener('submit', onCommentSubmit);
}

function renderReplyForm(parentId) {
  document.querySelectorAll('.comment-reply-form').forEach((f) => f.remove());

  const parent = document.querySelector(
    `.comment[data-id="${parentId}"] .comment__main`
  );
  if (!parent) return;

  const avatar = state.user.avatar_url || '/static/img/default-avatar.jpg';

  const form = document.createElement('form');
  form.className = 'comment-reply-form';
  form.innerHTML = `
    <img class="comment-form__avatar comment-form__avatar--sm" src="${escapeHtml(avatar)}" alt="">
    <div class="comment-form__main">
      <textarea class="comment-form__input" rows="2" maxlength="2000" placeholder="Write a reply…" required></textarea>
      <div class="comment-form__error" hidden></div>
      <div class="comment-form__actions">
        <button type="button" class="btn btn--ghost" data-cancel>Cancel</button>
        <button type="submit" class="btn btn--primary">Reply</button>
      </div>
    </div>
  `;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const ta = form.querySelector('textarea');
    const body = ta.value.trim();
    if (!body) return;
    await submitComment(body, parentId, form);
  });

  form
    .querySelector('[data-cancel]')
    .addEventListener('click', () => form.remove());

  parent.appendChild(form);
  form.querySelector('textarea').focus();
}

// ============================================================
// Comment actions
// ============================================================

async function onCommentSubmit(e) {
  e.preventDefault();
  const bodyEl = document.getElementById('comment-body');
  const body = bodyEl.value.trim();
  if (!body) return;
  await submitComment(body, null, document.getElementById('comment-form'));
}

async function submitComment(body, parentId, formEl) {
  const submitBtn = formEl.querySelector('button[type="submit"]');
  const errorBox = formEl.querySelector('.comment-form__error');
  submitBtn.disabled = true;
  errorBox.hidden = true;

  try {
    const created = await createComment(state.slug, { body, parent: parentId });
    formEl.reset();

    if (parentId) {
      await reloadComments();
    } else {
      els.commentsEmpty.hidden = true;
      els.commentsList.insertAdjacentHTML(
        'afterbegin',
        renderComment(created, 0)
      );
      state.commentsTotal += 1;
      updateCommentsCount();
    }
    if (formEl.classList.contains('comment-reply-form')) {
      formEl.remove();
    }
  } catch (err) {
    const msg =
      (err.body &&
        (err.body.detail || (err.body.body && err.body.body[0]) || err.body.message)) ||
      'Could not post your comment. Please try again.';
    errorBox.textContent = msg;
    errorBox.hidden = false;
  } finally {
    submitBtn.disabled = false;
  }
}

async function onCommentActionClick(e) {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const action = btn.dataset.action;
  const id = parseInt(btn.dataset.id, 10);
  if (!Number.isFinite(id)) return;

  if (action === 'like') {
    await handleCommentLike(id, btn);
  } else if (action === 'reply') {
    renderReplyForm(id);
  } else if (action === 'edit') {
    handleCommentEdit(id, btn);
  } else if (action === 'delete') {
    await handleCommentDelete(id);
  }
}

async function handleCommentLike(id, btn) {
  if (!state.user) {
    redirectToLogin();
    return;
  }
  btn.disabled = true;
  try {
    const res = await toggleCommentLike(id);
    const active = res && typeof res.active === 'boolean'
      ? res.active
      : !btn.getAttribute('aria-pressed').includes('true');
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    btn.innerHTML = `${
      active ? ICONS.heartFilled : ICONS.heart
    }<span>${(res && res.count) ?? 0}</span>`;
  } catch (err) {
    console.error(err);
  } finally {
    btn.disabled = false;
  }
}

function handleCommentEdit(id, btn) {
  const bodyEl = document.querySelector(`[data-body="${id}"]`);
  if (!bodyEl) return;

  const currentText = bodyEl.textContent;
  const container = bodyEl.parentElement;

  container.innerHTML = `
    <form class="comment-edit-form">
      <textarea class="comment-form__input" rows="2" maxlength="2000">${escapeHtml(currentText)}</textarea>
      <div class="comment-form__error" hidden></div>
      <div class="comment-form__actions">
        <button type="button" class="btn btn--ghost" data-cancel>Cancel</button>
        <button type="submit" class="btn btn--primary">Save</button>
      </div>
    </form>
  `;

  const form = container.querySelector('.comment-edit-form');
  const ta = form.querySelector('textarea');
  ta.focus();

  form
    .querySelector('[data-cancel]')
    .addEventListener('click', () => reloadComments());

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = ta.value.trim();
    if (!body) return;
    const errBox = form.querySelector('.comment-form__error');
    errBox.hidden = true;
    try {
      await editComment(id, body);
      await reloadComments();
    } catch (err) {
      errBox.textContent =
        (err.body && (err.body.detail || (err.body.body && err.body.body[0]))) ||
        'Could not update.';
      errBox.hidden = false;
    }
  });
}

async function handleCommentDelete(id) {
  if (!confirm('Delete this comment?')) return;
  try {
    await deleteComment(id);
    await reloadComments();
  } catch (err) {
    console.error(err);
    alert('Could not delete the comment.');
  }
}

function updateCommentsCount() {
  els.commentsTotal.textContent =
    state.commentsTotal === 1 ? '1 comment' : `${state.commentsTotal} comments`;
}

// ============================================================
// Comments loading
// ============================================================

async function loadComments(page = 1, append = false) {
  const data = await fetchComments(state.slug, page);
  state.commentsTotal = data.count ?? 0;
  state.commentsHasNext = !!data.next;
  state.commentsPage = page;

  updateCommentsCount();
  renderComments(data.results || [], append);

  els.commentsMore.hidden = !state.commentsHasNext;
}

async function reloadComments() {
  await loadComments(1, false);
}

// ============================================================
// Like / bookmark
// ============================================================

async function onLikeClick() {
  if (!state.user) {
    redirectToLogin();
    return;
  }
  els.btnLike.disabled = true;
  try {
    const res = await toggleLike(state.slug);
    const active = !!(res && res.active);
    updateLikeButton(active);
    if (res && typeof res.count !== 'undefined') {
      els.countLike.textContent = res.count;
    }
  } catch (err) {
    console.error(err);
  } finally {
    els.btnLike.disabled = false;
  }
}

async function onBookmarkClick() {
  if (!state.user) {
    redirectToLogin();
    return;
  }
  els.btnBookmark.disabled = true;
  try {
    const res = await toggleBookmark(state.slug);
    const active = !!(res && res.active);
    updateBookmarkButton(active);
    if (res && typeof res.count !== 'undefined') {
      els.countBookmark.textContent = res.count;
    }
  } catch (err) {
    console.error(err);
  } finally {
    els.btnBookmark.disabled = false;
  }
}

// ============================================================
// Share
// ============================================================

async function onShareClick() {
  const shareData = {
    title: state.post?.title || document.title,
    text: state.post?.summary || '',
    url: window.location.href,
  };
  if (navigator.share) {
    try {
      await navigator.share(shareData);
    } catch {}
    return;
  }
  try {
    await navigator.clipboard.writeText(window.location.href);
    flashShareLabel('Link copied');
  } catch {
    flashShareLabel('Copy failed');
  }
}

function flashShareLabel(text) {
  const label = els.btnShare.querySelector('.tool-btn__label');
  if (!label) return;
  const original = label.textContent;
  label.textContent = text;
  setTimeout(() => (label.textContent = original), 1500);
}

// ============================================================
// Topbar auth
// ============================================================

async function renderTopbarAuth() {
  const token = getAccessToken();
  if (!token) {
    els.topbarAuth.innerHTML = `<a href="/login/" class="btn btn--ghost">Login</a>`;
    state.user = null;
    return;
  }
  try {
    const user = await apiFetch('/auth/me/');
    state.user = user;
    const name = user.display_name || user.username;
    const avatar = user.avatar_url || '/static/img/default-avatar.jpg';
    els.topbarAuth.innerHTML = `
      <span class="topbar__user">
        <img class="topbar__avatar" src="${escapeHtml(avatar)}" alt="">
        <span>${escapeHtml(name)}</span>
      </span>
    `;
  } catch {
    clearTokens();
    state.user = null;
    els.topbarAuth.innerHTML = `<a href="/login/" class="btn btn--ghost">Login</a>`;
  }
}

// ============================================================
// Load
// ============================================================

function showSkeleton() {
  els.skeleton.hidden = false;
  els.error.hidden = true;
  els.article.hidden = true;
  els.commentsSection.hidden = true;
  els.relatedSection.hidden = true;
  els.authorPostsSection.hidden = true;
}

function showArticle() {
  els.skeleton.hidden = true;
  els.error.hidden = true;
  els.article.hidden = false;
  els.commentsSection.hidden = false;
}

function showError(title, message) {
  els.skeleton.hidden = true;
  els.article.hidden = true;
  els.commentsSection.hidden = true;
  els.relatedSection.hidden = true;
  els.authorPostsSection.hidden = true;
  els.errorTitle.textContent = title;
  els.errorMessage.textContent = message;
  els.error.hidden = false;
}

async function load() {
  const slug = getSlugFromPath();
  if (!slug) {
    showError('Post not found', 'No post was specified in the URL.');
    return;
  }
  state.slug = slug;

  showSkeleton();
  document.title = 'Loading… — Torch';

  await renderTopbarAuth();

  try {
    const post = await fetchPost(slug);
    state.post = post;

    document.title = `${post.title} — Torch`;
    const desc =
      document.querySelector('meta[name="description"]') ||
      (() => {
        const m = document.createElement('meta');
        m.name = 'description';
        document.head.appendChild(m);
        return m;
      })();
    desc.content = post.meta_description || post.summary || '';

    renderPost(post);
    showArticle();

    renderCommentForm();
    await loadComments(1, false);
  } catch (err) {
    console.error(err);
    if (err.status === 404) {
      showError('Post not found', 'This post may have been removed or unpublished.');
    } else {
      showError(
        "Couldn't load this post",
        (err.body && (err.body.detail || err.body.message)) ||
          'Please check your connection and try again.'
      );
    }
  }
}

// ============================================================
// Events
// ============================================================

els.btnLike.addEventListener('click', onLikeClick);
els.btnBookmark.addEventListener('click', onBookmarkClick);
els.btnShare.addEventListener('click', onShareClick);

els.commentsList.addEventListener('click', onCommentActionClick);

els.commentsLoadMore.addEventListener('click', async () => {
  els.commentsLoadMore.disabled = true;
  try {
    await loadComments(state.commentsPage + 1, true);
  } finally {
    els.commentsLoadMore.disabled = false;
  }
});

// ============================================================
// Init
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  els.footerYear.textContent = new Date().getFullYear();
  load();
});
