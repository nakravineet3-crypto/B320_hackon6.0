export type DeliveryEta =
  | 'now_20min'
  | 'today'
  | 'tomorrow'
  | '2_days'
  | '3_plus'

export interface Product {
  asin: string
  title: string
  category: string
  price: number
  pack_size: number
  price_per_unit: number
  rating: number
  review_count: number
  prime: boolean
  amazon_now_eligible: boolean
  delivery_eta: DeliveryEta
  return_risk: number
  compatibility_tags: string[]
  safety_tags: string[]
  sponsored: boolean
  stock_available: boolean
}

export interface CartItem {
  cart_item_id: string
  need_id: string
  need_label: string
  asin: string
  title: string
  price: number
  pack_size: number
  packs_quantity: number
  units_total: number
  total_cost: number
  delivery_eta: string
  prime: boolean
  amazon_now_eligible: boolean
  rating: number
  explanation: string
  is_sponsored: boolean
  was_repaired: boolean
  repair_reason: string | null
  compatibility_flags: string[]
}

export type AuditFlagType =
  | 'quantity_error'
  | 'missing_accessory'
  | 'delivery_failure'
  | 'budget_overage'
  | 'sponsored_blocked'
  | 'incompatibility'
  | 'not_amazon_now'

export interface AuditFlag {
  flag_id: string
  type: AuditFlagType
  severity: 'error' | 'warning' | 'info'
  item_asin: string | null
  title: string
  detail: string
  math_explanation: string | null
  fix_available: boolean
}

export interface CoverageScore {
  fraction: number
  covered: number
  total: number
  display: string
  all_must_haves_covered: boolean
  missing: string[]
}

export interface MissionBuildResult {
  mission_id: string
  cart_items: CartItem[]
  total_cost: number
  budget_remaining: number
  coverage_score: CoverageScore
  delivery_status: {
    all_on_time: boolean
    all_amazon_now: boolean
    bottleneck_items: CartItem[]
    message: string | null
  }
  repair_summary: {
    was_repaired: boolean
    original_total: number
    final_total: number
    steps: Array<{ action: string; saved: number }>
  } | null
  flags: AuditFlag[]
  amazon_cart_url: string
}

export interface AuditResult extends MissionBuildResult {
  original_cart: CartItem[]
}

export interface MorningAlert {
  id: string
  item_name: string
  quantity: number
  unit: string
  price_inr: number
  reason: string
  image_url: string
  asin: string
}

export interface OccasionCard {
  occasion_type: string
  title: string
  emoji: string
  days_until: number | null
  urgency_state: 'discovery' | 'preparation' | 'urgent' | 'emergency'
  urgency_label: string
  estimated_budget: number
  headcount: number
  community_signal: string
  tap_goal: string
  relevance_score: number
}

export interface UpcomingRecurrence {
  occasion_label: string
  occasion_type: string
  budget_used: number
  headcount: number
  coverage_score: string
  days_until_recurrence: number
  recurrence_date: string
  recurrence_alert: string
}
