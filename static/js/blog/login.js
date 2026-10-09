// static/js/blog/login.js

(function () {
  const form = document.getElementById('login-form');
  if (!form) return;

  const els = {
    username: document.getElementById('login-username'),
    password: document.getElementById('login-password'),
    usernameError: document.getElementById('login-username-error'),
    passwordError: document.getElementById('login-password-error'),
    error: document.getElementById('login-error'),
    submit: document.getElementById('login-submit'),
    passwordToggle: document.getElementById('login-password-toggle'),
    registerLink: document.getElementById('login-register-link'),
  };

  // ------------------------------------------------------------
  // Preserve ?next= across the register link
  // ------------------------------------------------------------

  const params = new URLSearchParams(window.location.search);
  const nextUrl = params.get('next') || '/home/';

  if (els.registerLink) {
    const registerParams = new URLSearchParams();
    if (params.get('next')) registerParams.set('next', params.get('next'));
    els.registerLink.href =
      '/register/' + (registerParams.toString() ? '?' + registerParams.toString() : '');
  }

  // ------------------------------------------------------------
  // If already logged in, bounce to the next destination
  // ------------------------------------------------------------

  if (typeof getAccessToken === 'function' && getAccessToken()) {
    window.location.replace(nextUrl);
    return;
  }

  // ------------------------------------------------------------
  // Password visibility toggle
  // ------------------------------------------------------------

  if (els.passwordToggle) {
    els.passwordToggle.addEventListener('click', () => {
      const showing = els.passwordToggle.getAttribute('aria-pressed') === 'true';
      const next = !showing;

      els.passwordToggle.setAttribute('aria-pressed', next ? 'true' : 'false');
      els.passwordToggle.setAttribute(
        'aria-label',
        next ? 'Hide password' : 'Show password'
      );
      els.password.type = next ? 'text' : 'password';
    });
  }

  // ------------------------------------------------------------
  // Clear errors while typing
  // ------------------------------------------------------------

  function clearFieldError(input, errorEl) {
    input.classList.remove('is-invalid');
    if (errorEl) errorEl.textContent = '';
  }

  function clearAllErrors() {
    clearFieldError(els.username, els.usernameError);
    clearFieldError(els.password, els.passwordError);
    if (els.error) {
      els.error.hidden = true;
      els.error.textContent = '';
      els.error.classList.remove('auth-error--warning');
    }
  }

  els.username.addEventListener('input', () => {
    clearFieldError(els.username, els.usernameError);
  });

  els.password.addEventListener('input', () => {
    clearFieldError(els.password, els.passwordError);
  });

  // ------------------------------------------------------------
  // Helpers
  // ------------------------------------------------------------

  function setLoading(isLoading) {
    els.submit.disabled = isLoading;
    if (isLoading) {
      els.submit.innerHTML =
        '<span class="auth-spinner" aria-hidden="true"></span> Logging in…';
    } else {
      els.submit.textContent = 'Log in';
    }
  }

  function showFormError(message, { warning = false } = {}) {
    els.error.textContent = message;
    els.error.hidden = false;
    els.error.classList.toggle('auth-error--warning', warning);
  }

  function markFieldError(input, errorEl, message) {
    input.classList.add('is-invalid');
    if (errorEl) errorEl.textContent = message;
  }

  // ------------------------------------------------------------
  // Extract a human-readable message from a DRF error body
  // ------------------------------------------------------------

  function extractErrorMessage(body) {
    if (!body) return 'Login failed. Please try again.';
    if (typeof body === 'string') return body;

    if (body.detail) return body.detail;

    if (Array.isArray(body.non_field_errors) && body.non_field_errors.length) {
      return body.non_field_errors[0];
    }

    if (Array.isArray(body.username) && body.username.length) {
      return body.username[0];
    }
    if (Array.isArray(body.password) && body.password.length) {
      return body.password[0];
    }

    // Fallback: first array value found
    for (const key of Object.keys(body)) {
      const v = body[key];
      if (Array.isArray(v) && v.length) return v[0];
      if (typeof v === 'string') return v;
    }

    return 'Login failed. Please try again.';
  }

  // ------------------------------------------------------------
  // Submit
  // ------------------------------------------------------------

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearAllErrors();

    const username = els.username.value.trim();
    const password = els.password.value;

    let hasError = false;
    if (!username) {
      markFieldError(els.username, els.usernameError, 'Username is required.');
      hasError = true;
    }
    if (!password) {
      markFieldError(els.password, els.passwordError, 'Password is required.');
      hasError = true;
    }
    if (hasError) return;

    setLoading(true);

    try {
      const res = await fetch('/api/v1/auth/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (res.status === 429) {
        showFormError(
          'Too many login attempts. Please wait a moment and try again.',
          { warning: true }
        );
        return;
      }

      if (!res.ok) {
        let body = null;
        try {
          body = await res.json();
        } catch {
          body = null;
        }
        showFormError(extractErrorMessage(body));
        return;
      }

      const data = await res.json();

      // data: { access, refresh, user }
      if (!data.access || !data.refresh) {
        showFormError('Login failed. The server returned an unexpected response.');
        return;
      }

      setTokens({ access: data.access, refresh: data.refresh });
      if (data.user) {
        localStorage.setItem('user', JSON.stringify(data.user));
      }

      window.location.replace(nextUrl);
    } catch (err) {
      console.error(err);
      showFormError('Network error. Please check your connection.');
    } finally {
      setLoading(false);
    }
  });

  // ------------------------------------------------------------
  // Focus username on load
  // ------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', () => {
    if (els.username) els.username.focus();
  });
})();
