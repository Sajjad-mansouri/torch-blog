// static/js/blog/register.js

(function () {
  const form = document.getElementById('register-form');
  if (!form) return;

  // ------------------------------------------------------------
  // Elements
  // ------------------------------------------------------------

  const els = {
    // form state
    formState: document.getElementById('register-form-state'),
    successState: document.getElementById('register-success-state'),

    firstName: document.getElementById('register-first-name'),
    lastName: document.getElementById('register-last-name'),
    username: document.getElementById('register-username'),
    email: document.getElementById('register-email'),
    password: document.getElementById('register-password'),
    passwordConfirm: document.getElementById('register-password-confirm'),

    firstNameError: document.getElementById('register-first-name-error'),
    lastNameError: document.getElementById('register-last-name-error'),
    usernameError: document.getElementById('register-username-error'),
    emailError: document.getElementById('register-email-error'),
    passwordError: document.getElementById('register-password-error'),
    passwordConfirmError: document.getElementById('register-password-confirm-error'),

    formError: document.getElementById('register-error'),
    submit: document.getElementById('register-submit'),

    passwordToggle: document.getElementById('register-password-toggle'),
    passwordConfirmToggle: document.getElementById('register-password-confirm-toggle'),

    loginLink: document.getElementById('register-login-link'),
    successLogin: document.getElementById('register-success-login'),
    successMessage: document.getElementById('register-success-message'),
    successResend: document.getElementById('register-success-resend'),
  };

  // ------------------------------------------------------------
  // URL params — preserve ?next= across the login and success links
  // ------------------------------------------------------------

  const params = new URLSearchParams(window.location.search);
  const nextUrl = params.get('next') || '';

  function withNext(baseUrl) {
    if (!nextUrl) return baseUrl;
    const sep = baseUrl.includes('?') ? '&' : '?';
    return `${baseUrl}${sep}next=${encodeURIComponent(nextUrl)}`;
  }

  if (els.loginLink) els.loginLink.href = withNext('/login/');
  if (els.successLogin) els.successLogin.href = withNext('/login/');
  if (els.successResend) els.successResend.href = withNext('/verify-email-resend/');

  // ------------------------------------------------------------
  // If already logged in, bounce away
  // ------------------------------------------------------------

  if (typeof getAccessToken === 'function' && getAccessToken()) {
    window.location.replace(nextUrl || '/home/');
    return;
  }

  // ------------------------------------------------------------
  // Password visibility toggles
  // ------------------------------------------------------------

  function attachToggle(button, input) {
    if (!button || !input) return;
    button.addEventListener('click', () => {
      const showing = button.getAttribute('aria-pressed') === 'true';
      const next = !showing;
      button.setAttribute('aria-pressed', next ? 'true' : 'false');
      button.setAttribute(
        'aria-label',
        next ? 'Hide password' : 'Show password'
      );
      input.type = next ? 'text' : 'password';
    });
  }

  attachToggle(els.passwordToggle, els.password);
  attachToggle(els.passwordConfirmToggle, els.passwordConfirm);

  // ------------------------------------------------------------
  // Field-level error management
  // ------------------------------------------------------------

  function clearFieldError(input, errorEl) {
    if (input) input.classList.remove('is-invalid');
    if (errorEl) errorEl.textContent = '';
  }

  function setFieldError(input, errorEl, message) {
    if (input) input.classList.add('is-invalid');
    if (errorEl) errorEl.textContent = message || '';
  }

  function clearAllErrors() {
    clearFieldError(els.firstName, els.firstNameError);
    clearFieldError(els.lastName, els.lastNameError);
    clearFieldError(els.username, els.usernameError);
    clearFieldError(els.email, els.emailError);
    clearFieldError(els.password, els.passwordError);
    clearFieldError(els.passwordConfirm, els.passwordConfirmError);
    if (els.formError) {
      els.formError.hidden = true;
      els.formError.textContent = '';
    }
  }

  // Clear each field's error as the user types
  const fieldPairs = [
    [els.firstName, els.firstNameError],
    [els.lastName, els.lastNameError],
    [els.username, els.usernameError],
    [els.email, els.emailError],
    [els.password, els.passwordError],
    [els.passwordConfirm, els.passwordConfirmError],
  ];

  for (const [input, errorEl] of fieldPairs) {
    if (!input) continue;
    input.addEventListener('input', () => clearFieldError(input, errorEl));
  }

  // ------------------------------------------------------------
  // Client-side validation
  // ------------------------------------------------------------

  const USERNAME_RE = /^[a-zA-Z0-9_.-]+$/;

  function validateForm() {
    clearAllErrors();

    let ok = true;

    const username = els.username.value.trim();
    const email = els.email.value.trim();
    const password = els.password.value;
    const passwordConfirm = els.passwordConfirm.value;

    if (!username) {
      setFieldError(els.username, els.usernameError, 'Username is required.');
      ok = false;
    } else if (username.length < 3) {
      setFieldError(els.username, els.usernameError, 'Username must be at least 3 characters.');
      ok = false;
    } else if (username.length > 30) {
      setFieldError(els.username, els.usernameError, 'Username must be at most 30 characters.');
      ok = false;
    } else if (!USERNAME_RE.test(username)) {
      setFieldError(
        els.username,
        els.usernameError,
        'Username may only contain letters, digits, underscore, dot, and hyphen.'
      );
      ok = false;
    }

    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setFieldError(els.email, els.emailError, 'Please enter a valid email.');
      ok = false;
    }

    if (!password) {
      setFieldError(els.password, els.passwordError, 'Password is required.');
      ok = false;
    } else if (password.length < 8) {
      setFieldError(els.password, els.passwordError, 'Password must be at least 8 characters.');
      ok = false;
    }

    if (!passwordConfirm) {
      setFieldError(
        els.passwordConfirm,
        els.passwordConfirmError,
        'Please confirm your password.'
      );
      ok = false;
    } else if (password !== passwordConfirm) {
      setFieldError(
        els.passwordConfirm,
        els.passwordConfirmError,
        'Passwords do not match.'
      );
      ok = false;
    }

    return ok;
  }

  // ------------------------------------------------------------
  // Loading state
  // ------------------------------------------------------------

  function setLoading(isLoading) {
    els.submit.disabled = isLoading;
    if (isLoading) {
      els.submit.innerHTML =
        '<span class="auth-spinner" aria-hidden="true"></span> Creating account…';
    } else {
      els.submit.textContent = 'Create account';
    }
  }

  // ------------------------------------------------------------
  // Server error extraction and mapping
  // ------------------------------------------------------------

  function showFormError(message) {
    els.formError.textContent = message;
    els.formError.hidden = false;
  }

  /**
   * Map a DRF field-error body to individual inputs.
   * Returns true if at least one error was displayed.
   */
  function applyServerErrors(body) {
    if (!body) return false;

    // Top-level "detail" or "non_field_errors"
    if (body.detail) {
      showFormError(body.detail);
      return true;
    }
    if (Array.isArray(body.non_field_errors) && body.non_field_errors.length) {
      showFormError(body.non_field_errors[0]);
      return true;
    }

    // Field-level errors
    const map = {
      first_name: [els.firstName, els.firstNameError],
      last_name: [els.lastName, els.lastNameError],
      username: [els.username, els.usernameError],
      email: [els.email, els.emailError],
      password: [els.password, els.passwordError],
      password_confirm: [els.passwordConfirm, els.passwordConfirmError],
    };

    let anyShown = false;

    for (const [key, value] of Object.entries(body)) {
      const pair = map[key];
      if (!pair) continue;

      const [input, errorEl] = pair;
      const message = Array.isArray(value) ? value[0] : String(value);
      setFieldError(input, errorEl, message);
      anyShown = true;
    }

    // If nothing mapped, fall back to the first available message
    if (!anyShown) {
      for (const value of Object.values(body)) {
        const message = Array.isArray(value) ? value[0] : String(value);
        if (message) {
          showFormError(message);
          anyShown = true;
          break;
        }
      }
    }

    return anyShown;
  }

  // ------------------------------------------------------------
  // Success state
  // ------------------------------------------------------------

  function showSuccess(message) {
    els.formState.hidden = true;
    els.successState.hidden = false;
    if (message) els.successMessage.textContent = message;

    // Scroll to the top so the success card is fully visible
    window.scrollTo({ top: 0, behavior: 'auto' });
  }

  // ------------------------------------------------------------
  // Submit
  // ------------------------------------------------------------

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      // Focus the first invalid field
      const firstInvalid = form.querySelector('.auth-input.is-invalid');
      if (firstInvalid) firstInvalid.focus();
      return;
    }

    const payload = {
      username: els.username.value.trim(),
      email: els.email.value.trim(),
      first_name: els.firstName.value.trim(),
      last_name: els.lastName.value.trim(),
      password: els.password.value,
      password_confirm: els.passwordConfirm.value,
    };

    setLoading(true);

    try {
      const res = await fetch('/api/v1/auth/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.status === 429) {
        showFormError(
          'Too many signup attempts. Please wait a moment and try again.'
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

        if (!applyServerErrors(body)) {
          showFormError('Registration failed. Please try again.');
        }

        const firstInvalid = form.querySelector('.auth-input.is-invalid');
        if (firstInvalid) firstInvalid.focus();
        return;
      }

      const data = await res.json();
      const message = data && data.message
        ? data.message
        : 'Your account was created. Check your email to verify your address before logging in.';
      showSuccess(message);
    } catch (err) {
      console.error(err);
      showFormError('Network error. Please check your connection.');
    } finally {
      setLoading(false);
    }
  });

  // ------------------------------------------------------------
  // Focus the first name on load
  // ------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', () => {
    if (els.firstName) els.firstName.focus();
  });
})();
