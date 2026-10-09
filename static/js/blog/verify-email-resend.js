// static/js/blog/verify-email-resend.js

(function () {
  const form = document.getElementById('resend-form');
  if (!form) return;

  const els = {
    formState: document.getElementById('resend-form-state'),
    successState: document.getElementById('resend-success-state'),

    email: document.getElementById('resend-email'),
    emailError: document.getElementById('resend-email-error'),

    formError: document.getElementById('resend-error'),
    submit: document.getElementById('resend-submit'),

    successMessage: document.getElementById('resend-success-message'),
    backToLogin: document.getElementById('resend-back-to-login'),
    goRegister: document.getElementById('resend-go-register'),
    successBack: document.getElementById('resend-success-back'),
  };

  // ------------------------------------------------------------
  // Preserve ?next= across the login and register links
  // ------------------------------------------------------------

  const params = new URLSearchParams(window.location.search);
  const nextUrl = params.get('next') || '';

  function withNext(baseUrl) {
    if (!nextUrl) return baseUrl;
    const sep = baseUrl.includes('?') ? '&' : '?';
    return `${baseUrl}${sep}next=${encodeURIComponent(nextUrl)}`;
  }

  if (els.backToLogin) els.backToLogin.href = withNext('/login/');
  if (els.goRegister) els.goRegister.href = withNext('/register/');
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
      els.submit.textContent = 'Send verification link';
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
      const res = await fetch('/api/v1/auth/verify-email/resend/', {
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
          'Could not send the verification email. Please try again.';
        els.formError.textContent = msg;
        els.formError.hidden = false;
        return;
      }

      // Always 200, whether or not the email exists.
      let body = null;
      try { body = await res.json(); } catch { body = null; }
      const message =
        (body && body.detail) ||
        'If an unverified account with that email exists, a new verification link has been sent. Check your inbox and spam folder.';

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
  // Focus the email input on load
  // ------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', () => {
    if (els.email) els.email.focus();
  });
})();
