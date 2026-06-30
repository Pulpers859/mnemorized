(function () {
  var API_BASE_CACHED = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';

  function getApiUrl(path) {
    return API_BASE_CACHED + path;
  }

  function escapeHtml(text) {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function escapeJsString(text) {
    return String(text || '')
      .replace(/\\/g, '\\\\')
      .replace(/'/g, "\\'")
      .replace(/\r/g, '\\r')
      .replace(/\n/g, '\\n')
      .replace(/\u2028/g, '\\u2028')
      .replace(/\u2029/g, '\\u2029');
  }

  function withTimeout(promise, ms, label) {
    var timeoutId;
    var normalizedPromise = Promise.resolve(promise);
    var timeoutPromise = new Promise(function (_, reject) {
      timeoutId = setTimeout(function () {
        reject(new Error(label + ' timed out after ' + Math.round(ms / 1000) + 's'));
      }, ms);
    });
    return Promise.race([
      normalizedPromise.finally(function () { clearTimeout(timeoutId); }),
      timeoutPromise
    ]);
  }

  async function runSupabaseQuery(label, promise, timeoutMs) {
    try {
      return await withTimeout(promise, timeoutMs || 15000, label);
    } catch (error) {
      console.error('[Mnemorized] ' + label + ' failed', error);
      throw error;
    }
  }

  async function request(path, options) {
    options = options || {};
    var headers = {
      'Content-Type': 'application/json'
    };
    if (options.headers) {
      Object.assign(headers, options.headers);
    }
    if (options.token) {
      headers.Authorization = 'Bearer ' + options.token;
    }

    var res = await fetch(getApiUrl(path), {
      method: options.method || 'GET',
      headers: headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body)
    });

    var payload = await res.json().catch(function () { return {}; });
    if (!res.ok) {
      var detail = payload.detail || (payload.error && payload.error.message) || ('HTTP ' + res.status);
      throw new Error(detail);
    }
    return payload;
  }

  window.MnemorizedUtils = {
    getApiBase: function () { return API_BASE_CACHED; },
    getApiUrl: getApiUrl,
    escapeHtml: escapeHtml,
    escapeJsString: escapeJsString,
    withTimeout: withTimeout,
    runSupabaseQuery: runSupabaseQuery
  };

  window.MnemorizedPalaceApi = {
    ensureProfile: function (token) {
      return request('/api/profile/ensure', { method: 'POST', token: token });
    },
    list: function (token) {
      return request('/api/palaces', { token: token });
    },
    load: function (token, palaceId) {
      return request('/api/palaces/' + encodeURIComponent(palaceId), { token: token });
    },
    save: function (token, body) {
      return request('/api/palaces/save', { method: 'POST', token: token, body: body });
    },
    rename: function (token, palaceId, title) {
      return request('/api/palaces/' + encodeURIComponent(palaceId), { method: 'PATCH', token: token, body: { title: title } });
    },
    delete: function (token, palaceId) {
      return request('/api/palaces/' + encodeURIComponent(palaceId), { method: 'DELETE', token: token });
    }
  };

  window.MnemorizedCatalogApi = {
    list: function (params) {
      var parts = [];
      if (params && params.tag) parts.push('tag=' + encodeURIComponent(params.tag));
      if (params && params.q) parts.push('q=' + encodeURIComponent(params.q));
      var query = parts.length ? '?' + parts.join('&') : '';
      return request('/api/catalog' + query, {});
    },
    get: function (catalogId) {
      return request('/api/catalog/' + encodeURIComponent(catalogId), {});
    },
    publish: function (token, body) {
      return request('/api/catalog/publish', { method: 'POST', token: token, body: body });
    },
    unpublish: function (token, catalogId) {
      return request('/api/catalog/' + encodeURIComponent(catalogId), { method: 'DELETE', token: token });
    }
  };
})();
