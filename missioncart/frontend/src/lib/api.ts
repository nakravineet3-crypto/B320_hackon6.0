import axios from 'axios'

import { API_BASE } from './constants'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

export { api }

export const missionAPI = {
  parse: (goal: string) => api.post('/api/mission/parse', { goal }),

  build: (goal: string, budget: number) =>
    api.post('/api/mission/build', { goal, budget }),

  audit: (existingCart: object[], goal: string) =>
    api.post('/api/mission/audit', { existing_cart: existingCart, goal }),
}

export const demoAPI = {
  getScenarios: () => api.get('/api/demo/scenarios'),
  getOccasions: () => api.get('/api/demo/occasions'),
  getReorderAlerts: () => api.get('/api/demo/reorder-alerts'),
  getUserProfile: () => api.get('/api/demo/user-profile'),
}

export const catalogAPI = {
  getProducts: (search?: string) =>
    api.get('/api/catalog/products', { params: search ? { search } : {} }),
}

export const hiveAPI = {
  getDemo: () => api.get('/api/hive/demo'),

  vote: (cartId: string, itemId: string, userId: string, value: 1 | -1) =>
    api.post(`/api/hive/cart/${cartId}/vote`, null, {
      params: { item_id: itemId, user_id: userId, value },
    }),

  optimize: (cartId: string) =>
    api.post(`/api/hive/cart/${cartId}/optimize`),

  getSplit: (cartId: string, method: string = 'equal') =>
    api.get(`/api/hive/cart/${cartId}/split`, { params: { method } }),

  addItem: (
    cartId: string,
    asin: string,
    title: string,
    category: string,
    price: number,
    quantity: number,
    addedBy: string = 'U001',
    note?: string,
  ) =>
    api.post(`/api/hive/cart/${cartId}/add-item`, null, {
      params: { asin, title, category, price, quantity, added_by: addedBy, note },
    }),

  placeOrder: (cartId: string, splitMethod: string = 'equal') =>
    api.post(`/api/hive/cart/${cartId}/place-order`, null, {
      params: { split_method: splitMethod },
    }),

  getMessages: (hiveId: string, since?: string) =>
    api.get(`/api/hive/messages/${hiveId}`, {
      params: since ? { since } : {},
    }),
}

export const searchAPI = {
  search: (q: string, occasion: string = 'general', withBadges: boolean = true) =>
    api.get('/api/search/products', {
      params: { q, occasion, with_badges: withBadges },
    }),
  suggest: (q: string) => api.get('/api/search/suggest', { params: { q } }),
  getBadge: (asin: string) => api.get(`/api/search/badge/${asin}`),
}

export const comparisonAPI = {
  evaluate: (
    productA: any,
    productB: any,
    missionSpec: any,
  ) =>
    api.post('/api/comparison/evaluate', {
      product_a: productA,
      product_b: productB,
      mission_spec: missionSpec,
      user_id: 'U001',
    }),
}

export const reorderAPI = {
  getDraft: (removed: string[] = []) =>
    api.get('/api/reorder/draft', {
      params: {
        user_id: 'U001',
        removed: removed.join(','),
      },
    }),

  getAlerts: () =>
    api.get('/api/reorder/alerts', {
      params: { user_id: 'U001' },
    }),

  updateQuantity: (draftId: string, itemId: string, qty: number) =>
    api.post('/api/reorder/draft/update-quantity', {
      draft_id: draftId,
      item_id: itemId,
      new_quantity: qty,
      user_id: 'U001',
    }),

  approve: (draftId: string, idempotencyKey: string, items: any[]) =>
    api.post('/api/reorder/approve', {
      draft_id: draftId,
      user_id: 'U001',
      idempotency_key: idempotencyKey,
      items,
    }),

  reject: (draftId: string) =>
    api.post('/api/reorder/reject', {
      draft_id: draftId,
      user_id: 'U001',
    }),

  getOrderStatus: (orderId: string) =>
    api.get(`/api/reorder/order-status/${orderId}`),
}

