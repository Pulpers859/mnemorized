(function () {
  function getApiBase() {
    return window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';
  }

  function getApiUrl(path) {
    return `${getApiBase()}${path}`;
  }

  async function request(path, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };
    if (options.token) {
      headers.Authorization = `Bearer ${options.token}`;
    }

    const res = await fetch(getApiUrl(path), {
      method: options.method || 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body)
    });

    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = payload.detail || payload.error?.message || `HTTP ${res.status}`;
      throw new Error(detail);
    }
    return payload;
  }

  window.MnemorizedPalaceApi = {
    list(token) {
      return request('/api/palaces', { token });
    },
    load(token, palaceId) {
      return request(`/api/palaces/${encodeURIComponent(palaceId)}`, { token });
    },
    save(token, body) {
      return request('/api/palaces/save', {
        method: 'POST',
        token,
        body
      });
    },
    rename(token, palaceId, title) {
      return request(`/api/palaces/${encodeURIComponent(palaceId)}`, {
        method: 'PATCH',
        token,
        body: { title }
      });
    },
    delete(token, palaceId) {
      return request(`/api/palaces/${encodeURIComponent(palaceId)}`, {
        method: 'DELETE',
        token
      });
    }
  };
})();
