// static/js/blog/password-reset-confirm.js

(function () {
  const form = document.getElementById('reset-confirm-form');
  if (!form) return;

  const els = {
    loadingState: document.getElementById('reset-confirm-loading'),
    invalidState: document.getElementById('reset-confirm-invalid'),
    formState: document.getElementById('reset-confirm-form-state'),
    successState: document.getElementById('reset-confirm-success-state'),

    password: document.getElementById('reset-password'),
    passwordConfirm: document.getElementById('reset-password-confirm'),
    passwordError: document.getElementById('reset-password-error'),
    passwordConfirmError: document.getElementById('reset-password-confirm-error'),

    formError: document.getElementById('reset-confirm-error'),
    submit: document.getElementById('reset-confirm-submit'),

    passwordToggle: document.getElementById('reset-password-toggle'),
    passwordConfirmToggle: document.getElementById('reset-password-confirm-toggle'),

    goLogin: document.getElementById('reset-confirm-go-login'),
  };

  // ------------------------------------------------------------
  // Read uidb64 and token.
  //
  // The inline script in <head> strips them from the URL as soon
  // as the page loads and stores them on window.__resetParams.
  // Prefer that source; fall back to the query string for the
  // unlikely case the inline script didn't run.
  // ------------------------------------------------------------

  const params = window.__resetParams || {};
  let uidb64 = params.uidb64;
  let token = params.token;

  if (!uidb64 || !token) {
    const urlParams = new URLSearchParams(window.location.search);
    uidb64 = uidb64 || urlParams.get('uidb64');
    token = token || urlParams.get('token');
  }

  // ------------------------------------------------------------
  // Preserve ?next= across the "go to login" link
  // ------------------------------------------------------------

  const nextUrl = new URLSearchParams(window.location.search).get('next') || '';

  function withNext(baseUrl) {
    if (!nextUrl) return baseUrl;
    const sep = baseUrl.includes('?') ? '&' : '?';
    return `${baseUrl}${sep}next=${encodeURIComponent(nextUrl)}`;
  }

  if (els.goLogin) els.goLogin.href = withNext('/login/');

  // ------------------------------------------------------------
  // If the URL doesn't contain uidb64 or token, show the invalid
  // state immediately. No request to the API is made.
  // ------------------------------------------------------------

  if (!uidb64 || !token) {
    els.loadingState.hidden = true;
    els.invalidState.hidden = false;
    return;
  }

  // Otherwise, show the form. The token is validated only when
  // the user submits — that keeps the flow to one API call.
  els.loadingState.hidden = true;
  els.formState.hidden = false;

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
  // Field errors
  // ------------------------------------------------------------

  function clearPasswordError() {
    els.password.classList.remove('is-invalid');
    els.passwordError.textContent = '';
  }

  function clearPasswordConfirmError() {
    els.passwordConfirm.classList.remove('is-invalid');
    els.passwordConfirmError.textContent = '';
  }

  function clearFormError() {
    els.formError.hidden = true;
    els.formError.textContent = '';
  }

  els.password.addEventListener('input', () => {
    clearPasswordError();
    clearFormError();
  });
  els.passwordConfirm.addEventListener('input', () => {
    clearPasswordConfirmError();
    clearFormError();
  });

  // ------------------------------------------------------------
  // Loading
  // ------------------------------------------------------------

  function setLoading(isLoading) {
    els.submit.disabled = isLoading;
    if (isLoading) {
      els.submit.innerHTML =
        '<span class="auth-spinner" aria-hidden="true"></span> Resetting…';
    } else {
      els.submit.textContent = 'Reset password';
    }
  }

  // ------------------------------------------------------------
  // Success
  // ------------------------------------------------------------

  function showSuccess() {
    els.formState.hidden = true;
    els.invalidState.hidden = true;
    els.successState.hidden = false;
    window.scrollTo({ top: 0, behavior: 'auto' });
  }

  function showInvalid() {
    els.formState.hidden = true;
    els.successState.hidden = true;
    els.invalidState.hidden = false;
    window.scrollTo({ top: 0, behavior: 'auto' });
  }

  // ------------------------------------------------------------
  // Submit
  // ------------------------------------------------------------

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearPasswordError();
    clearPasswordConfirmError();
    clearFormError();

    const password = els.password.value;
    const passwordConfirm = els.passwordConfirm.value;

    let hasError = false;

    if (!password) {
      els.password.classList.add('is-invalid');
      els.passwordError.textContent = 'Password is required.';
      hasError = true;
    } else if (password.length < 8) {
      els.password.classList.add('is-invalid');
      els.passwordError.textContent =
        'Password must be at least 8 characters.';
      hasError = true;
    }

    if (!passwordConfirm) {
      els.passwordConfirm.classList.add('is-invalid');
      els.passwordConfirmError.textContent =
        'Please confirm your new password.';
      hasError = true;
    } else if (password !== passwordConfirm) {
      els.passwordConfirm.classList.add('is-invalid');
      els.passwordConfirmError.textContent = 'Passwords do not match.';
      hasError = true;
    }

    if (hasError) {
      const firstInvalid = form.querySelector('.auth-input.is-invalid');
      if (firstInvalid) firstInvalid.focus();
      return;
    }

    setLoading(true);

    try {
      const res = await fetch('/api/v1/auth/password-reset/confirm/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uidb64,
          token,
          password,
          password_confirm: passwordConfirm,
        }),
      });

      if (res.status === 429) {
        els.formError.textContent =
          'Too many attempts. Please wait a moment and try again.';
        els.formError.hidden = false;
        return;
      }

      if (!res.ok) {
        let body = null;
        try { body = await res.json(); } catch { body = null; }

        // Token invalid or expired → show the invalid-link state.
        if (body && body.token) {
          showInvalid();
          return;
        }

        // Field errors → map back to the inputs.
        if (body && body.password) {
          els.password.classList.add('is-invalid');
          els.passwordError.textContent = Array.isArray(body.password)
            ? body.password[0]
            : String(body.password);
        }
        if (body && body.password_confirm) {
          els.passwordConfirm.classList.add('is-invalid');
          els.passwordConfirmError.textContent = Array.isArray(body.password_confirm)
            ? body.password_confirm[0]
            : String(body.password_confirm);
        }

        // Form-level error fallback.
        if (body && body.detail) {
          els.formError.textContent = body.detail;
          els.formError.hidden = false;
        } else if (
          !body ||
          (!body.password && !body.password_confirm && !body.token)
        ) {
          els.formError.textContent =
            'Could not reset your password. Please try again.';
          els.formError.hidden = false;
        }

        const firstInvalid = form.querySelector('.auth-input.is-invalid');
        if (firstInvalid) firstInvalid.focus();
        return;
      }

      showSuccess();
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
  // Focus the first password field
  // ------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', () => {
    if (els.password) els.password.focus();
  });
})();
