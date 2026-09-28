/**
 * ResQFood AI — API Service
 * Centralized HTTP client for all backend communication.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

function getToken() {
  return localStorage.getItem('resqfood_token');
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = { ...options.headers };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }

  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────
export const api = {
  auth: {
    login: (email, password) =>
      request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
    register: (data) =>
      request('/api/auth/register', { method: 'POST', body: JSON.stringify(data) }),
    me: () => request('/api/auth/me'),
  },

  // ── Users ────────────────────────────────────────────────────────────
  users: {
    list: () => request('/api/users/'),
    get: (id) => request(`/api/users/${id}`),
    kitchens: () => request('/api/users/kitchens/all'),
    ngos: () => request('/api/users/ngos/all'),
    drivers: () => request('/api/users/drivers/all'),
  },

  // ── Demand ───────────────────────────────────────────────────────────
  demand: {
    predict: (kitchenId, predictionDate = null) =>
      request('/api/demand/predict', {
        method: 'POST',
        body: JSON.stringify({ kitchen_id: kitchenId, prediction_date: predictionDate }),
      }),
    predictions: (kitchenId = null) =>
      request(`/api/demand/predictions${kitchenId ? `?kitchen_id=${kitchenId}` : ''}`),
    history: (kitchenId) => request(`/api/demand/history?kitchen_id=${kitchenId}`),
  },

  // ── Surplus ──────────────────────────────────────────────────────────
  surplus: {
    create: (data) =>
      request('/api/surplus/', { method: 'POST', body: JSON.stringify(data) }),
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return request(`/api/surplus/${qs ? `?${qs}` : ''}`);
    },
    get: (id) => request(`/api/surplus/${id}`),
    update: (id, data) =>
      request(`/api/surplus/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    uploadImage: (id, file) => {
      const form = new FormData();
      form.append('file', file);
      return request(`/api/surplus/${id}/image`, { method: 'POST', body: form });
    },
  },

  // ── Requests ─────────────────────────────────────────────────────────
  requests: {
    create: (data) =>
      request('/api/requests/', { method: 'POST', body: JSON.stringify(data) }),
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return request(`/api/requests/${qs ? `?${qs}` : ''}`);
    },
    get: (id) => request(`/api/requests/${id}`),
    update: (id, data) =>
      request(`/api/requests/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },

  // ── Allocation ───────────────────────────────────────────────────────
  allocation: {
    run: (surplusId) =>
      request('/api/allocation/run', { method: 'POST', body: JSON.stringify({ surplus_id: surplusId }) }),
    get: (surplusId) => request(`/api/allocation/${surplusId}`),
  },

  // ── Deliveries ───────────────────────────────────────────────────────
  deliveries: {
    create: (data) =>
      request('/api/deliveries/', { method: 'POST', body: JSON.stringify(data) }),
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return request(`/api/deliveries/${qs ? `?${qs}` : ''}`);
    },
    get: (id) => request(`/api/deliveries/${id}`),
    update: (id, data) =>
      request(`/api/deliveries/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    updateStop: (deliveryId, stopId, data) =>
      request(`/api/deliveries/${deliveryId}/stops/${stopId}`, {
        method: 'PATCH', body: JSON.stringify(data),
      }),
    generateOtp: (deliveryId, stopId) =>
      request(`/api/deliveries/${deliveryId}/stops/${stopId}/generate-otp`, { method: 'POST' }),
    verifyOtp: (deliveryId, stopId, otpCode) =>
      request(`/api/deliveries/${deliveryId}/stops/${stopId}/verify-otp`, {
        method: 'POST', body: JSON.stringify({ otp_code: otpCode }),
      }),
  },

  // ── Analytics ────────────────────────────────────────────────────────
  analytics: {
    impact: () => request('/api/analytics/impact'),
    dashboard: () => request('/api/analytics/dashboard'),
  },
};
