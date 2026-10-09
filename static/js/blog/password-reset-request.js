// static/js/blog/password-reset-request.js

(function () {
  const form = document.getElementById('reset-request-form');
  if (!form) return;

  const els = {
    formState: document.getElementById('reset-request-form-state'),
    successState: document.getElementById('reset-request-success-state'),

    email: document.getElementById('reset-email'),
    emailError: document.getElementById('reset-email-error'),

    formError: document.getElementById('reset-request-error'),
    submit: document.getElementById('reset-request-submit'),

    successMessage: document.getElementById('reset-request-success-message'),
    backToLogin: document.getElementById('reset-back-to-login'),
    successBack: document.getElementById('reset-success-back'),
    tryAgain: document.getElementById('reset-try-again'),
  };

  // ------------------------------------------------------------
  // Preserve ?next= across the back-to-login links
  // ------------------------------------------------------------

  const params = new URLSearchParams(window.location.search);
  const nextUrl = params.get('next') || '';

  function withNext(baseUrl) {
    if (!nextUrl) return baseUrl;
    const sep = baseUrl.includes('?') ? '&' : '?';
    return `${baseUrl}${sep}next=${encodeURIComponent(nextUrl)}`;
  }

  if (els.backToLogin) els.backToLogin.href = withNext('/login/');
  if (els.successBack) els.successBack.href = withNext('/login/');

  // ------------------------------------------------------------
  // Field error management
  // ------------------------------------------------------------

  function clearFieldError() {
    els.email.classList.remove('is-invalid');
    els.emailError.textContent = '';
  }

  function setFieldError(message) {
    els.email.classList.add('is-invalid');
    els.emailError.textContent = message;
  }

  function clearFormError() {
    els.formError.hidden = true;
    els.formError.textContent = '';
  }

  els.email.addEventListener('input', () => {
    clearFieldError();
    clearFormError();
  });

  // ------------------------------------------------------------
  // Loading
  // ------------------------------------------------------------

  function setLoading(isLoading) {
    els.submit.disabled = isLoading;
    if (isLoading) {
      els.submit.innerHTML =
        '<span class="auth-spinner" aria-hidden="true"></span> Sending…';
    } else {
      els.submit.textContent = 'Send reset link';
    }
  }

  // ------------------------------------------------------------
  // Submit
  // ------------------------------------------------------------

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldError();
    clearFormError();

    const email = els.email.value.trim();

    if (!email) {
      setFieldError('Email is required.');
      els.email.focus();
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setFieldError('Please enter a valid email.');
      els.email.focus();
      return;
    }

    setLoading(true);

    try {
      const res = await fetch('/api/v1/auth/password-reset/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      if (res.status === 429) {
        els.formError.textContent =
          'Too many requests. Please wait a moment and try again.';
        els.formError.hidden = false;
        return;
      }

      if (!res.ok) {
        let body = null;
        try { body = await res.json(); } catch { body = null; }
        const msg =
          (body && (body.detail || (body.email && body.email[0]))) ||
          'Could not send the reset link. Please try again.';
        els.formError.textContent = msg;
        els.formError.hidden = false;
        return;
      }

      // Always 200, whether or not the email exists.
      let body = null;
      try { body = await res.json(); } catch { body = null; }
      const message =
        (body && body.detail) ||
        'If an account with that email exists, a password reset link is on its way. Check your inbox and spam folder.';

      // Show success state
      els.formState.hidden = true;
      els.successState.hidden = false;
      els.successMessage.textContent = message;
      window.scrollTo({ top: 0, behavior: 'auto' });
    } catch (err) {
      console.error(err);
      els.formError.textContent =
        'Network error. Please check your connection and try again.';
      els.formError.hidden = false;
    } finally {
      setLoading(false);
    }
  });

  // ------------------------------------------------------------
  // Focus
  // ------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', () => {
    if (els.email) els.email.focus();
  });
})();
