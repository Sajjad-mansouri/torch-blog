// static/js/blog/verify-email-confirm.js

(function () {
  const els = {
    loading: document.getElementById('verify-loading'),
    success: document.getElementById('verify-success'),
    invalid: document.getElementById('verify-invalid'),
    successMessage: document.getElementById('verify-success-message'),
    invalidMessage: document.getElementById('verify-invalid-message'),
    goLogin: document.getElementById('verify-go-login'),
  };

  if (!els.loading) return;

  // ------------------------------------------------------------
  // Read uidb64 and token.
  //
  // The inline script in <head> strips them from the URL as
  // soon as the page loads and stores them on
  // window.__verifyParams. Prefer that source; fall back to
  // the query string if the inline script didn't run.
  // ------------------------------------------------------------

  const params = window.__verifyParams || {};
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

  const nextUrl =
    new URLSearchParams(window.location.search).get('next') || '';

  if (els.goLogin && nextUrl) {
    els.goLogin.href =
      '/login/?next=' + encodeURIComponent(nextUrl);
  }

  // ------------------------------------------------------------
  // State transitions
  // ------------------------------------------------------------

  function showLoading() {
    els.loading.hidden = false;
    els.success.hidden = true;
    els.invalid.hidden = true;
  }

  function showSuccess(message) {
    els.loading.hidden = true;
    els.success.hidden = false;
    els.invalid.hidden = true;
    if (message) els.successMessage.textContent = message;
    window.scrollTo({ top: 0, behavior: 'auto' });
  }

  function showInvalid(message) {
    els.loading.hidden = true;
    els.success.hidden = true;
    els.invalid.hidden = false;
    if (message) els.invalidMessage.textContent = message;
    window.scrollTo({ top: 0, behavior: 'auto' });
  }

  // ------------------------------------------------------------
  // If the URL didn't carry uidb64 or token, show invalid
  // immediately. No API call — nothing to verify.
  // ------------------------------------------------------------

  if (!uidb64 || !token) {
    showInvalid(
      'This verification link is missing its token. Please use the ' +
      'link from the email, or request a new one.'
    );
    return;
  }

  // ------------------------------------------------------------
  // Extract a readable message from a DRF error body.
  // ------------------------------------------------------------

  function extractErrorMessage(body) {
    if (!body) return null;
    if (typeof body === 'string') return body;
    if (body.detail) return body.detail;
    if (Array.isArray(body.token) && body.token.length) return body.token[0];
    if (Array.isArray(body.non_field_errors) && body.non_field_errors.length) {
      return body.non_field_errors[0];
    }
    for (const value of Object.values(body)) {
      if (Array.isArray(value) && value.length) return value[0];
      if (typeof value === 'string') return value;
    }
    return null;
  }

  // ------------------------------------------------------------
  // Post the token to the API
  // ------------------------------------------------------------

  async function verify() {
    showLoading();

    try {
      const res = await fetch('/api/v1/auth/verify-email/confirm/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uidb64, token }),
      });

      if (res.status === 429) {
        showInvalid(
          'Too many verification attempts. Please wait a moment and try again.'
        );
        return;
      }

      if (!res.ok) {
        let body = null;
        try { body = await res.json(); } catch { body = null; }
        showInvalid(
          extractErrorMessage(body) ||
          'The verification link is invalid or has expired.'
        );
        return;
      }

      // Success.
      let body = null;
      try { body = await res.json(); } catch { body = null; }
      const message =
        (body && body.detail) ||
        'Your email has been verified. You can now log in.';
      showSuccess(message);
    } catch (err) {
      console.error(err);
      showInvalid(
        'Network error. Please check your connection and try again.'
      );
    }
  }

  // ------------------------------------------------------------
  // Kick off on page load
  // ------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', verify);
})();
