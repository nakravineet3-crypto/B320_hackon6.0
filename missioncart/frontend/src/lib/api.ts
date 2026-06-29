import axios from 'axios'

import { API_BASE } from './constants'
import type { OccasionCard } from './types'

export type { OccasionCard }

export type GroupProduct = {
  asin: string
  title: string
  price_inr: number
  rating: number
  category: string
  amazon_now_eligible: boolean
  image_placeholder: string
  adoption_copy?: string
  image_url?: string  // Amazon CDN URL, may be empty string when not yet populated
}

interface GroupProductsResponse {
  group_id: string
  group_name: string
  product_count: number
  products: GroupProduct[]
}

export const DEMO_USER_ID = 'U001' // Hardcoded for HackOn demo — replace with auth

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

export { api }

export const missionAPI = {
  parse: (goal: string) => api.post('/api/mission/parse', { goal }),

  build: (
    goal: string,
    budget: number,
    extra?: { occasion_type?: string; headcount?: number },
  ) =>
    api.post('/api/mission/build', {
      goal,
      budget,
      ...(extra?.occasion_type !== undefined && { occasion_type: extra.occasion_type }),
      ...(extra?.headcount !== undefined && { headcount: extra.headcount }),
    }),

  audit: (existingCart: object[], goal: string) =>
    api.post('/api/mission/audit', { existing_cart: existingCart, goal }),
}

export const demoAPI = {
  getScenarios: () => api.get('/api/demo/scenarios'),
  getOccasions: () => api.get('/api/demo/occasions'),
  getReorderAlerts: () => api.get('/api/demo/reorder-alerts'),
  getUserProfile: () => api.get('/api/demo/user-profile'),
}

export const occasionAPI = {
  getFeed: (userId: string = 'U001'): Promise<OccasionCard[]> =>
    api
      .get<{ occasions: OccasionCard[] }>(`/api/occasions/feed?user_id=${userId}`)
      .then((r) => r.data.occasions),
}

export const catalogAPI = {
  getProducts: (search?: string) =>
    api.get('/api/catalog/products', { params: search ? { search } : {} }),
}

export const hiveAPI = {
  getDemo: () => api.get('/api/quorum/demo'),

  vote: (cartId: string, itemId: string, userId: string, value: 1 | -1) =>
    api.post(`/api/quorum/cart/${cartId}/vote`, null, {
      params: { item_id: itemId, user_id: userId, value },
    }),

  optimize: (cartId: string) =>
    api.post(`/api/quorum/cart/${cartId}/optimize`),

  getSplit: (cartId: string, method: string = 'equal') =>
    api.get(`/api/quorum/cart/${cartId}/split`, { params: { method } }),

  addItem: (cartId: string, item: any) =>
    api.post(`/api/quorum/cart/${cartId}/add-item`, item),

  removeItem: (cartId: string, itemId: string) =>
    api.delete(`/api/quorum/cart/${cartId}/item/${itemId}`),

  placeOrder: (cartId: string, splitMethod: string = 'equal') =>
    api.post(`/api/quorum/cart/${cartId}/place-order`, null, {
      params: { split_method: splitMethod },
    }),

  getMessages: (hiveId: string, since?: string) =>
    api.get(`/api/quorum/messages/${hiveId}`, {
      params: since ? { since } : {},
    }),

  sendMessage: (hiveId: string, userId: string, content: string) =>
    api.post('/api/quorum/messages/send', {
      hive_id: hiveId,
      user_id: userId,
      content,
    }),

  updateBudget: (hiveId: string, budget: number) =>
    api.post(`/api/quorum/hive/${hiveId}/budget`, { budget_cap: budget }),
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
      user_id: DEMO_USER_ID,
    }),
}

export const communityAPI = {
  getGroupProducts: (groupId: string): Promise<GroupProductsResponse> =>
    api
      .get<GroupProductsResponse>(`/api/community/groups/${groupId}/products`)
      .then((r) => r.data)
      .catch(() => ({
        group_id: groupId,
        group_name: '',
        product_count: 0,
        products: [],
      })),
}

// ---------------------------------------------------------------------------
// Community Goal Pages API
// ---------------------------------------------------------------------------

export type GoalPageSummary = {
  goal_id: string
  title: string
  occasion_type: string
  occasion_emoji: string
  participant_count: number
  items_total: number
  items_claimed: number
  coverage_pct: number
  days_until: number
  community_signal: string
}

export type GoalItem = {
  item_id: string
  asin: string
  title: string
  price_inr: number
  category: string
  claimed_by: string | null
  claimed_by_name: string | null
  status: 'claimed' | 'unclaimed'
}

export type GoalPageDetail = {
  goal_id: string
  title: string
  occasion_type: string
  occasion_emoji: string
  created_by: string
  participants: string[]
  participant_names: string[]
  target_date: string
  budget_total: number
  budget_per_person: number
  items: GoalItem[]
  items_total: number
  items_claimed: number
  coverage_pct: number
  days_until: number
  community_signal: string
}

const _FALLBACK_GOALS: GoalPageSummary[] = [
  {
    goal_id: 'goal_diwali_2026_sharma',
    title: 'Sharma Family Diwali 2026',
    occasion_type: 'diwali_celebration',
    occasion_emoji: '🪔',
    participant_count: 5,
    items_total: 8,
    items_claimed: 5,
    coverage_pct: 63,
    days_until: 118,
    community_signal: '87% of Diwali goal pages complete 2 weeks before the date',
  },
  {
    goal_id: 'goal_potluck_3rdfloor',
    title: '3rd Floor Potluck Friday',
    occasion_type: 'office_potluck',
    occasion_emoji: '🍽️',
    participant_count: 8,
    items_total: 7,
    items_claimed: 3,
    coverage_pct: 43,
    days_until: 3,
    community_signal: 'Pre-assigned potlucks waste 62% less food on average',
  },
  {
    goal_id: 'goal_birthday_arjun',
    title: "Arjun's 7th Birthday Bash",
    occasion_type: 'kids_birthday',
    occasion_emoji: '🎂',
    participant_count: 3,
    items_total: 9,
    items_claimed: 7,
    coverage_pct: 78,
    days_until: 7,
    community_signal: 'Coordinated birthday carts save an average of ₹480 vs solo orders',
  },
]

export const communityGoalAPI = {
  listGoals: (): Promise<GoalPageSummary[]> =>
    api
      .get<{ success: boolean; data: { goals: GoalPageSummary[] } }>('/api/community/goals')
      .then((r) => r.data.data?.goals ?? [])
      .catch(() => _FALLBACK_GOALS),

  getGoal: (goalId: string): Promise<GoalPageDetail> =>
    api
      .get<{ success: boolean; data: GoalPageDetail }>(`/api/community/goals/${goalId}`)
      .then((r) => r.data.data)
      .catch(() => {
        throw new Error(`Failed to load goal ${goalId}`)
      }),

  createGoal: (payload: {
    title: string
    occasion_type: string
    occasion_emoji?: string
    target_date: string
    budget_total: number
    participant_names?: string[]
    created_by?: string
  }): Promise<GoalPageDetail> =>
    api
      .post<{ success: boolean; data: GoalPageDetail }>('/api/community/goals', payload)
      .then((r) => r.data.data),
}

export const reorderAPI = {
  getDraft: (removed: string[] = []) =>
    api.get('/api/reorder/draft', {
      params: {
        user_id: DEMO_USER_ID,
        removed: removed.join(','),
      },
    }),

  getAlerts: () =>
    api.get('/api/reorder/alerts', {
      params: { user_id: DEMO_USER_ID },
    }),

  updateQuantity: (draftId: string, itemId: string, qty: number) =>
    api.post('/api/reorder/draft/update-quantity', {
      draft_id: draftId,
      item_id: itemId,
      new_quantity: qty,
      user_id: DEMO_USER_ID,
    }),

  approve: (draftId: string, idempotencyKey: string, items: any[]) =>
    api.post('/api/reorder/approve', {
      draft_id: draftId,
      user_id: DEMO_USER_ID,
      idempotency_key: idempotencyKey,
      items,
    }),

  reject: (draftId: string) =>
    api.post('/api/reorder/reject', {
      draft_id: draftId,
      user_id: DEMO_USER_ID,
    }),

  getOrderStatus: (orderId: string) =>
    api.get(`/api/reorder/order-status/${orderId}`),
}

