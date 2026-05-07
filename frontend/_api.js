(function() {
  'use strict';

  const TOKEN_KEY = 'crb_token';
  const SESSION_KEY = 'crb_logged_in';

  function getCookie(name) {
    return document.cookie
      .split('; ')
      .find(row => row.startsWith(name + '='))
      ?.split('=')
      .slice(1)
      .join('=') || '';
  }

  function normalizePath(path) {
    if (!path) return '/api';
    return path.startsWith('/api/') || path === '/api' ? path : '/api' + (path.startsWith('/') ? path : '/' + path);
  }

  async function parseResponse(response) {
    const text = await response.text();
    if (!text) return null;
    const type = response.headers.get('content-type') || '';
    if (type.includes('application/json')) return JSON.parse(text);
    return text;
  }

  async function apiFetch(path, opts = {}) {
    const headers = new Headers(opts.headers || {});
    const hasBody = opts.body !== undefined && opts.body !== null;
    const isFormData = typeof FormData !== 'undefined' && opts.body instanceof FormData;

    if (hasBody && !isFormData && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    const token = API.getToken();
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', 'Bearer ' + token);
    }

    const csrf = getCookie('__crb_csrf');
    if (csrf && !headers.has('X-CSRF-Token')) {
      headers.set('X-CSRF-Token', decodeURIComponent(csrf));
    }

    const response = await fetch(normalizePath(path), {
      credentials: 'include',
      ...opts,
      headers,
      body: hasBody && !isFormData && typeof opts.body !== 'string' ? JSON.stringify(opts.body) : opts.body,
    });

    const data = await parseResponse(response);
    if (!response.ok) {
      const error = new Error((data && data.detail) || response.statusText || 'Request failed');
      error.status = response.status;
      error.data = data;
      if (response.status === 401 && opts.redirectOnUnauthorized !== false) {
        API.clearToken();
        window.location.href = '/login.html';
      }
      throw error;
    }
    return data;
  }

  const API = {
    fetch: apiFetch,
    get(path, opts = {}) { return apiFetch(path, { ...opts, method: 'GET' }); },
    post(path, body, opts = {}) { return apiFetch(path, { ...opts, method: 'POST', body }); },
    patch(path, body, opts = {}) { return apiFetch(path, { ...opts, method: 'PATCH', body }); },
    put(path, body, opts = {}) { return apiFetch(path, { ...opts, method: 'PUT', body }); },
    del(path, opts = {}) { return apiFetch(path, { ...opts, method: 'DELETE' }); },

    getToken() { return sessionStorage.getItem(TOKEN_KEY); },
    setToken(token) {
      if (token) sessionStorage.setItem(TOKEN_KEY, token);
      sessionStorage.setItem(SESSION_KEY, '1');
    },
    markLoggedIn() { sessionStorage.setItem(SESSION_KEY, '1'); },
    clearToken() {
      sessionStorage.removeItem(TOKEN_KEY);
      sessionStorage.removeItem(SESSION_KEY);
    },
    isLoggedIn() {
      return !!(sessionStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(SESSION_KEY));
    },
    async redirectIfUnauth() {
      if (API.isLoggedIn()) return true;
      try {
        await API.get('/auth/me', { redirectOnUnauthorized: false });
        API.markLoggedIn();
        return true;
      } catch (_error) {
        window.location.href = '/login.html';
        return false;
      }
    },
    async refreshUserPill() {
      try {
        const session = await API.get('/auth/me', { redirectOnUnauthorized: false });
        const user = session.user || session;
        const who = document.querySelector('.side-foot .who');
        const role = document.querySelector('.side-foot .role');
        const ava = document.querySelector('.side-foot .ava');
        if (who && user.display_name) who.textContent = user.display_name;
        if (role) role.textContent = [user.role, user.workspace_name].filter(Boolean).join(' · ') || 'Workspace member';
        if (ava && user.display_name) {
          ava.textContent = user.display_name.split(/\s+/).map(part => part[0]).join('').slice(0, 3).toUpperCase();
        }
        return user;
      } catch (_error) {
        return null;
      }
    },
    detail(error) {
      return (error && error.data && error.data.detail) || (error && error.message) || 'Something went wrong';
    },
  };

  window.API = API;
})();
