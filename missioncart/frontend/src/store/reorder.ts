import { create } from 'zustand'

export interface ReorderConfidence {
  score: number
  percentage: number
  label: 'High' | 'Medium' | 'Estimated'
}

export interface ReorderExplanation {
  avg_interval_days: number
  last_purchased: string
  days_since: number
  days_remaining: number
  purchase_count: number
  pattern: string
  availability: string
}

export interface ReorderItem {
  item_id: string
  asin: string
  title: string
  category: string
  suggested_quantity: number
  user_quantity: number
  unit: string
  price_per_unit: number
  total_cost: number
  confidence: ReorderConfidence
  urgency_copy: string
  explanation: ReorderExplanation
  inventory_status: string
  amazon_now_eligible: boolean
  delivery_eta_mins: number
}

export interface ReorderDraft {
  draft_id: string
  user_id: string
  status: string
  items: ReorderItem[]
  item_count: number
  total_price: number
  all_amazon_now: boolean
  delivery_estimate_mins: number
  delivery_copy: string
}

export interface ReorderOrder {
  order_id: string
  draft_id: string
  status: string
  total_price: number
  item_count: number
  items: ReorderItem[]
  delivery_estimate: string
  delivery_by: string
  amazon_now_confirmed: boolean
  placed_at: string
  steps: Array<{ step: string; label: string; delay_ms: number }>
}

interface ReorderStore {
  draft: ReorderDraft | null
  order: ReorderOrder | null
  setDraft: (draft: ReorderDraft | null) => void
  setOrder: (order: ReorderOrder | null) => void
  clear: () => void
}

export const useReorderStore = create<ReorderStore>((set) => ({
  draft: null,
  order: null,
  setDraft: (draft) => set({ draft }),
  setOrder: (order) => set({ order }),
  clear: () => set({ draft: null, order: null }),
}))
