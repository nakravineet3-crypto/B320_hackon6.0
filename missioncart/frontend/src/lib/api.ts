import axios from 'axios'

const BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
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
