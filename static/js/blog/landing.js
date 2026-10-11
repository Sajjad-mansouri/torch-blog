// static/js/blog/landing.js
//
// Loads GET /api/v1/landing/ and renders the landing page.
// Handles contact form submission, section navigation, and
// a back-to-top button.

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

  const humanStatus = (s) => ({
    done: 'Shipped',
    in_progress: 'In progress',
    planned: 'Planned',
  }[s] || s);

  const statusIcon = (s) => ({
    done: '✓',
    in_progress: '●',
    planned: '○',
  }[s] || '·');

  const humanPlatform = (p) => ({
    github: 'GitHub',
    twitter: 'Twitter / X',
    linkedin: 'LinkedIn',
    instagram: 'Instagram',
    youtube: 'YouTube',
    facebook: 'Facebook',
    telegram: 'Telegram',
    website: 'Website',
    email: 'Email',
    stackoverflow: 'Stack Overflow',
    medium: 'Medium',
    reddit: 'Reddit',
    dev: 'Dev.to',
    discord: 'Discord',
    rss: 'RSS',
  }[p] || p);

  const platformIcon = (p) => ({
    github: '🐙',
    twitter: '🐦',
    linkedin: '💼',
    instagram: '📸',
    youtube: '▶️',
    facebook: '📘',
    telegram: '✈️',
    website: '🌐',
    email: '✉️',
    stackoverflow: '📚',
    medium: '📝',
    reddit: '👽',
    dev: '👩‍💻',
    discord: '💬',
    rss: '📡',
  }[p] || '🔗');

  /**
   * Return HTML for a social icon.
   * - If `icon` looks like a Font Awesome class (contains "fa-"),
   *   render it as <i class="...">.
   * - Otherwise fall back to the emoji map for the platform.
   */
  function renderIconHTML(icon, platform) {
    const raw = (icon || '').trim();
    if (raw && raw.includes('fa-')) {
      return `<i class="${escapeHTML(raw)}" aria-hidden="true"></i>`;
    }
    const emoji = raw || platformIcon(platform);
    return `<span class="social-card__emoji">${escapeHTML(emoji)}</span>`;
  }

  // ============================================================
  // Hero + stats
  // ============================================================

  function renderHero(project, stats) {
    const host = $('landing-hero');
    if (!host) return;

    const repoUrl = project.project_repo_url || '';
    const demoUrl = project.project_demo_url || '';

    const ctaButtons = [
      repoUrl
        ? `<a class="btn btn--primary" href="${escapeHTML(repoUrl)}" target="_blank" rel="noopener">View on GitHub →</a>`
        : '',
      demoUrl
        ? `<a class="btn btn--ghost" href="${escapeHTML(demoUrl)}" target="_blank" rel="noopener">Live demo →</a>`
        : '',
      `<a class="btn btn--ghost" href="#landing-features">Explore features</a>`,
    ].filter(Boolean).join('');

    const statsHTML = (stats || []).map((s) => `
      <div class="landing-stat">
        <span class="landing-stat__value">
          ${s.icon ? `<span class="landing-stat__icon">${escapeHTML(s.icon)}</span>` : ''}
          ${escapeHTML(s.value)}
        </span>
        <span class="landing-stat__label">${escapeHTML(s.label)}</span>
      </div>
    `).join('');

    host.innerHTML = `
      <div class="landing-hero__inner">
        <div class="landing-hero__text">
          <span class="landing-hero__eyebrow">Portfolio project</span>
          <h1 class="landing-hero__title">
            ${escapeHTML(project.project_name || 'Torch')}
            <em>— ${escapeHTML(project.project_tagline || '')}</em>
          </h1>
          <p class="landing-hero__description">
            ${escapeHTML(project.project_description || '')}
          </p>
          <p class="landing-hero__tagline">
            <strong>Goal:</strong> ${escapeHTML(project.project_goal || '')}
          </p>
          <div class="landing-hero__cta">${ctaButtons}</div>
        </div>
        ${statsHTML ? `<div class="landing-hero__stats">${statsHTML}</div>` : ''}
      </div>
    `;
  }

  // ============================================================
  // Tech stack
  // ============================================================

  function renderTechStack(categories) {
    const grid = $('tech-grid');
    const section = $('landing-tech');
    if (!grid || !section) return;

    if (!categories || !categories.length) {
      section.hidden = true;
      return;
    }
    section.hidden = false;

    grid.innerHTML = categories.map((cat) => `
      <div class="tech-category">
        <div class="tech-category__head">
          ${cat.icon ? `<span class="tech-category__icon">${escapeHTML(cat.icon)}</span>` : ''}
          <h3 class="tech-category__name">${escapeHTML(cat.name)}</h3>
        </div>
        <div class="tech-category__items">
          ${(cat.items || []).map((item) => `
            <a class="tech-item"
               href="${escapeHTML(item.url || '#')}"
               ${item.url ? 'target="_blank" rel="noopener"' : ''}>
              <span class="tech-item__icon">${escapeHTML(item.icon || '·')}</span>
              <span class="tech-item__name">${escapeHTML(item.name)}</span>
              ${item.version ? `<span class="tech-item__version">${escapeHTML(item.version)}</span>` : ''}
              ${item.description ? `<span class="tech-item__desc">${escapeHTML(item.description)}</span>` : ''}
            </a>
          `).join('')}
        </div>
      </div>
    `).join('');
  }

  // ============================================================
  // Features
  // ============================================================

  function renderFeatures(groups) {
    const grid = $('features-grid');
    const section = $('landing-features');
    if (!grid || !section) return;

    if (!groups || !groups.length) {
      section.hidden = true;
      return;
    }
    section.hidden = false;

    grid.innerHTML = groups.map((g) => `
      <div class="feature-group">
        <div class="feature-group__head">
          ${g.icon ? `<span class="feature-group__icon">${escapeHTML(g.icon)}</span>` : ''}
          <div>
            <h3 class="feature-group__title">${escapeHTML(g.title)}</h3>
            ${g.description ? `<p class="feature-group__desc">${escapeHTML(g.description)}</p>` : ''}
          </div>
        </div>
        <div class="feature-items">
          ${(g.items || []).map((item) => `
            <div class="feature-item">
              <span class="feature-item__bullet"></span>
              <div class="feature-item__text">
                <span class="feature-item__title">${escapeHTML(item.title)}</span>
                ${item.description ? `<p class="feature-item__desc">${escapeHTML(item.description)}</p>` : ''}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');
  }

  // ============================================================
  // API endpoints
  // ============================================================

  function renderApiEndpoints(endpoints) {
    const host = $('api-groups');
    const section = $('landing-api');
    if (!host || !section) return;

    if (!endpoints || !endpoints.length) {
      section.hidden = true;
      return;
    }
    section.hidden = false;

    const grouped = {};
    for (const ep of endpoints) {
      const key = ep.group || 'Other';
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(ep);
    }

    host.innerHTML = Object.entries(grouped).map(([groupName, eps]) => `
      <div class="api-group">
        <h3 class="api-group__title">${escapeHTML(groupName)}</h3>
        ${eps.map((ep) => `
          <div class="api-row">
            <span class="api-row__method" data-method="${escapeHTML(ep.method)}">
              ${escapeHTML(ep.method)}
            </span>
            <div class="api-row__body">
              <code class="api-row__path">
                ${escapeHTML(ep.path)}
                ${ep.auth_required ? '<span class="api-row__auth">auth</span>' : ''}
              </code>
              ${ep.description ? `<span class="api-row__desc">${escapeHTML(ep.description)}</span>` : ''}
            </div>
          </div>
        `).join('')}
      </div>
    `).join('');
  }

  // ============================================================
  // Roadmap
  // ============================================================

  function renderRoadmap(phases) {
    const list = $('roadmap-list');
    const section = $('landing-roadmap');
    if (!list || !section) return;

    if (!phases || !phases.length) {
      section.hidden = true;
      return;
    }
    section.hidden = false;

    list.innerHTML = phases.map((phase) => `
      <div class="roadmap-phase" data-status="${escapeHTML(phase.status)}">
        <div class="roadmap-phase__meta">
          <span class="roadmap-phase__status" data-status="${escapeHTML(phase.status)}">
            ${escapeHTML(humanStatus(phase.status))}
          </span>
          <h3 class="roadmap-phase__title">${escapeHTML(phase.title)}</h3>
          ${phase.description ? `<p class="roadmap-phase__desc">${escapeHTML(phase.description)}</p>` : ''}
        </div>
        <ul class="roadmap-phase__items">
          ${(phase.items || []).map((item) => `
            <li class="roadmap-item">
              <span class="roadmap-item__check">${statusIcon(phase.status)}</span>
              <span>${escapeHTML(item.text)}</span>
            </li>
          `).join('')}
        </ul>
      </div>
    `).join('');
  }

  // ============================================================
  // Social links
  // ============================================================

  function renderSocialSection(links) {
    const grid = $('social-grid');
    const section = $('landing-social');
    if (!grid || !section) return;

    if (!links || !links.length) {
      section.hidden = true;
      return;
    }
    section.hidden = false;

    grid.innerHTML = links.map((link) => {
      const platformLabel = humanPlatform(link.platform) || link.platform;
      const username = link.username || '';
      const url = link.url || '#';

      return `
        <a class="social-card"
           href="${escapeHTML(url)}"
           target="_blank" rel="noopener">
          <span class="social-card__icon">
            ${renderIconHTML(link.icon, link.platform)}
          </span>
          <span class="social-card__body">
            <span class="social-card__platform">${escapeHTML(platformLabel)}</span>
            ${username ? `<span class="social-card__username">@${escapeHTML(username)}</span>` : ''}
          </span>
          <span class="social-card__arrow">→</span>
        </a>
      `;
    }).join('');
  }

  // ============================================================
  // Contact form
  // ============================================================

  const CONTACT_LIMITS = {
    name:    { min: 2, max: 150 },
    email:   { max: 150 },
    subject: { max: 250 },
    message: { min: 10, max: 3000 },
  };

  function bindContactForm() {
    const form = $('contact-form');
    if (!form) return;

    const successBox = $('contact-success');
    const submitBtn = $('contact-submit');
    const submitLabel = submitBtn?.querySelector('.contact-form__submit-label');
    const submitSpinner = submitBtn?.querySelector('.contact-form__submit-spinner');
    const globalError = $('contact-global-error');
    const globalErrorText = $('contact-global-error-text');
    const messageCounter = $('c-message-counter');
    const messageField = form.elements['message'];

    if (messageField && messageCounter) {
      const updateCounter = () => {
        const len = messageField.value.length;
        const max = CONTACT_LIMITS.message.max;
        messageCounter.textContent = `${len} / ${max}`;
        messageCounter.classList.toggle('is-warning', len > max * 0.75 && len <= max * 0.95);
        messageCounter.classList.toggle('is-danger', len > max * 0.95);
      };
      messageField.addEventListener('input', updateCounter);
      updateCounter();
    }

    function setFieldError(fieldName, message) {
      const field = form.querySelector(`[name="${fieldName}"]`);
      const errorEl = form.querySelector(`[data-error-for="${fieldName}"]`);
      if (!field || !errorEl) return;

      const wrapper = field.closest('.contact-form__field');
      if (message) {
        errorEl.textContent = message;
        errorEl.hidden = false;
        wrapper?.classList.add('has-error');
        field.setAttribute('aria-invalid', 'true');
      } else {
        errorEl.textContent = '';
        errorEl.hidden = true;
        wrapper?.classList.remove('has-error');
        field.removeAttribute('aria-invalid');
      }
    }

    function clearAllErrors() {
      for (const name of ['name', 'email', 'subject', 'message']) {
        setFieldError(name, '');
      }
      if (globalError) globalError.hidden = true;
    }

    function validateField(name, value) {
      const v = (value || '').trim();
      const limits = CONTACT_LIMITS[name] || {};

      if (name === 'name') {
        if (!v) return 'Please enter your name.';
        if (v.length < limits.min) return `Name must be at least ${limits.min} characters.`;
      }
      if (name === 'email') {
        if (!v) return 'Please enter your email.';
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) {
          return 'Please enter a valid email address.';
        }
      }
      if (name === 'message') {
        if (!v) return 'Please write a message.';
        if (v.length < limits.min) {
          return `Message must be at least ${limits.min} characters.`;
        }
      }
      return '';
    }

    for (const name of ['name', 'email', 'subject', 'message']) {
      const field = form.elements[name];
      if (!field) continue;

      field.addEventListener('blur', () => {
        setFieldError(name, validateField(name, field.value));
      });

      field.addEventListener('input', () => {
        const wrapper = field.closest('.contact-form__field');
        if (wrapper?.classList.contains('has-error')) {
          setFieldError(name, validateField(name, field.value));
        }
      });
    }

    function showForm() {
      if (successBox) successBox.hidden = true;
      form.hidden = false;
    }

    function showSuccess() {
      form.hidden = true;
      if (successBox) successBox.hidden = false;
      clearAllErrors();
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearAllErrors();

      let firstInvalid = null;
      for (const name of ['name', 'email', 'subject', 'message']) {
        const field = form.elements[name];
        if (!field) continue;
        const error = validateField(name, field.value);
        if (error) {
          setFieldError(name, error);
          if (!firstInvalid) firstInvalid = field;
        }
      }

      if (firstInvalid) {
        firstInvalid.focus();
        return;
      }

      if (submitBtn) submitBtn.disabled = true;
      if (submitLabel) submitLabel.textContent = 'Sending…';
      if (submitSpinner) submitSpinner.hidden = false;

      const payload = new FormData(form);

      try {
        await apiFetch('/contact/', { method: 'POST', body: payload });
        form.reset();
        if (messageCounter) {
          messageCounter.textContent = `0 / ${CONTACT_LIMITS.message.max}`;
          messageCounter.classList.remove('is-warning', 'is-danger');
        }
        showSuccess();
      } catch (err) {
        console.error('[landing] contact failed', err);

        const body = err?.body || {};
        let shown = false;

        for (const name of ['name', 'email', 'subject', 'message']) {
          if (body[name]) {
            const msg = Array.isArray(body[name]) ? body[name][0] : String(body[name]);
            setFieldError(name, msg);
            shown = true;
          }
        }

        if (!shown) {
          const detail =
            body.detail ||
            body.message ||
            (err.status === 429
              ? "You've sent too many messages. Please try again in a bit."
              : 'Something went wrong. Please try again.');
          if (globalError) globalError.hidden = false;
          if (globalErrorText) globalErrorText.textContent = detail;
        }
      } finally {
        if (submitBtn) submitBtn.disabled = false;
        if (submitLabel) submitLabel.textContent = 'Send message';
        if (submitSpinner) submitSpinner.hidden = true;
      }
    });

    const sendAnother = $('contact-send-another');
    if (sendAnother) {
      sendAnother.addEventListener('click', () => {
        showForm();
        const nameField = form.elements['name'];
        if (nameField) nameField.focus();
      });
    }
  }

  // ============================================================
  // Section nav — smooth scroll + active highlight
  // ============================================================

  function bindSectionNav() {
    const nav = $('landing-nav');
    if (!nav) return;

    const links = [...nav.querySelectorAll('.landing-nav__item')];

    links.forEach((link) => {
      link.addEventListener('click', (e) => {
        const href = link.getAttribute('href') || '';
        if (!href.startsWith('#')) return;
        const target = document.getElementById(href.slice(1));
        if (!target) return;

        e.preventDefault();
        const topOffset = parseInt(
          getComputedStyle(document.documentElement)
            .getPropertyValue('--topbar-height') || '64', 10
        ) + 60;

        const top = target.getBoundingClientRect().top + window.scrollY - topOffset;
        window.scrollTo({ top, behavior: 'smooth' });

        history.replaceState(null, '', href);
      });
    });

    const sections = links
      .map((l) => document.getElementById(l.dataset.nav))
      .filter(Boolean);

    if (!sections.length || !('IntersectionObserver' in window)) return;

    const setActive = (id) => {
      links.forEach((l) => l.classList.toggle('is-active', l.dataset.nav === id));
    };

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);

        if (visible.length) {
          setActive(visible[0].target.id);
        }
      },
      {
        rootMargin: '-40% 0px -50% 0px',
        threshold: 0,
      }
    );

    sections.forEach((s) => observer.observe(s));
  }

  // ============================================================
  // Back to top
  // ============================================================

  function bindBackToTop() {
    const btn = $('landing-top');
    if (!btn) return;

    const update = () => {
      const visible = window.scrollY > 600;
      btn.hidden = !visible;
    };

    window.addEventListener('scroll', update, { passive: true });
    update();

    btn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ============================================================
  // Error state
  // ============================================================

  function showError(message) {
    const hero = $('landing-hero');
    if (hero) hero.hidden = true;

    for (const id of ['landing-tech', 'landing-features', 'landing-api',
                      'landing-roadmap', 'landing-social', 'landing-contact']) {
      const el = $(id);
      if (el) el.hidden = true;
    }

    const nav = $('landing-nav');
    if (nav) nav.hidden = true;

    const err = $('landing-error');
    if (err) err.hidden = false;

    const msg = $('landing-error-message');
    if (msg) msg.textContent = message || 'Please try again.';
  }

  // ============================================================
  // Load
  // ============================================================

  async function loadLanding() {
    try {
      const data = await apiFetch('/landing/');

      renderHero(data.project || {}, data.stats || []);
      renderTechStack(data.tech_stack || []);
      renderFeatures(data.features || []);
      renderApiEndpoints(data.api_endpoints || []);
      renderRoadmap(data.roadmap || []);
      renderSocialSection(data.social_links || []);

      const contactSection = $('landing-contact');
      if (contactSection) contactSection.hidden = false;
    } catch (err) {
      console.error('[landing] load failed', err);
      showError(err?.body?.detail || 'The server did not respond.');
    }
  }

  // ============================================================
  // Boot
  // ============================================================

  function init() {
    const retry = $('landing-retry');
    if (retry) retry.addEventListener('click', loadLanding);

    bindContactForm();
    bindSectionNav();
    bindBackToTop();
    loadLanding();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
