// Shared fallback data for cart screens and identity groups.
// Used when the API is unavailable or returns no data.
// Source of truth: building.tsx FALLBACK_CART.cart_items

import type { OccasionCard } from './types'

export interface FallbackGroupProduct {
  asin: string
  title: string
  price_inr: number
  rating: number
  category: string
  amazon_now_eligible: boolean
  image_placeholder: string
  adoption_copy?: string
  image_url?: string
}

export const FALLBACK_GROUP_PRODUCTS: Record<string, FallbackGroupProduct[]> = {
  office_gym_dad: [
    { asin: 'B08BLCZ3NV', title: 'MuscleBlaze Whey Protein 1kg – Rich Milk Chocolate', price_inr: 1299, rating: 4.7, category: 'protein_supplements', amazon_now_eligible: true, image_placeholder: '#4A90D9', image_url: '', adoption_copy: 'Reordered monthly by 89% of Office Gym Dads' },
    { asin: 'B07HX7JNRC', title: 'Boldfit Gym Gloves with Wrist Support', price_inr: 449, rating: 4.4, category: 'sports', amazon_now_eligible: false, image_placeholder: '#5C6BC0', image_url: '', adoption_copy: 'In 76% of Office Gym Dad carts' },
    { asin: 'B09DWVVR7X', title: 'Boldfit Shaker Bottle 700ml Leak-Proof', price_inr: 299, rating: 4.5, category: 'sports', amazon_now_eligible: true, image_placeholder: '#26A69A', image_url: '', adoption_copy: '84% pair this with their protein' },
    { asin: 'B08YB8KHHP', title: 'Classmate Premium Ballpoint Pens 10-pack', price_inr: 149, rating: 4.3, category: 'stationery', amazon_now_eligible: true, image_placeholder: '#FFA726', image_url: '', adoption_copy: 'Desk staple for 71% of Office Gym Dads' },
  ],
  jee_student: [
    { asin: 'B07Y9PSXMN', title: 'Classmate 6-Subject Spiral Notebook 300 Pages', price_inr: 199, rating: 4.6, category: 'stationery', amazon_now_eligible: true, image_placeholder: '#42A5F5', image_url: '', adoption_copy: 'In 94% of JEE student orders' },
    { asin: 'B08P9DFKVK', title: 'Pilot V7 Hi-Tecpoint Pen – Black, 10-pack', price_inr: 349, rating: 4.7, category: 'stationery', amazon_now_eligible: true, image_placeholder: '#66BB6A', image_url: '', adoption_copy: 'Reordered every 3 weeks by 81%' },
    { asin: 'B09N3H7J5P', title: 'Stabilo Boss Original Highlighter 6 Colours', price_inr: 249, rating: 4.5, category: 'stationery', amazon_now_eligible: true, image_placeholder: '#FFCA28', image_url: '', adoption_copy: '91% of JEE students rely on these' },
    { asin: 'B07YPGX3R4', title: 'Glucon-D Instant Energy Drink 400g', price_inr: 89, rating: 4.4, category: 'food_beverages', amazon_now_eligible: true, image_placeholder: '#29B6F6', image_url: '', adoption_copy: '82% reorder during exam season' },
  ],
  college_girl: [
    { asin: 'B08ZXKHC6F', title: 'Himalaya Purifying Neem Face Wash 150ml', price_inr: 119, rating: 4.6, category: 'personal_care', amazon_now_eligible: true, image_placeholder: '#EC407A', image_url: '', adoption_copy: 'Top reorder for 88% of college girls' },
    { asin: 'B09B6YDMK9', title: 'Neutrogena Hydro Boost Water Gel 50g', price_inr: 599, rating: 4.5, category: 'personal_care', amazon_now_eligible: true, image_placeholder: '#AB47BC', image_url: '', adoption_copy: 'In 79% of college girl carts' },
    { asin: 'B08JX9K5PW', title: 'Batiste Dry Shampoo Original 200ml', price_inr: 449, rating: 4.3, category: 'personal_care', amazon_now_eligible: false, image_placeholder: '#8D6E63', image_url: '', adoption_copy: 'Saves time for 72% on busy mornings' },
    { asin: 'B07P8SMQF5', title: 'Too Yumm Multigrain Chips 12-pack', price_inr: 199, rating: 4.4, category: 'snacks', amazon_now_eligible: true, image_placeholder: '#FFA726', image_url: '', adoption_copy: 'Hostel snack staple for 93%' },
  ],
  home_chef: [
    { asin: 'B09C8MFH7X', title: 'MDH Chunky Chat Masala 100g', price_inr: 89, rating: 4.6, category: 'spices', amazon_now_eligible: true, image_placeholder: '#E57373', image_url: '', adoption_copy: 'Reordered monthly by 87% of home chefs' },
    { asin: 'B07Z4PQSLX', title: 'Kissan Mixed Fruit Jam 700g', price_inr: 149, rating: 4.5, category: 'food_beverages', amazon_now_eligible: true, image_placeholder: '#FF7043', image_url: '', adoption_copy: 'In 91% of home chef weekly orders' },
    { asin: 'B08DFB2QCX', title: 'Cello Checkers Airtight Storage Container Set of 4', price_inr: 399, rating: 4.4, category: 'storage', amazon_now_eligible: true, image_placeholder: '#66BB6A', image_url: '', adoption_copy: 'Owned by 78% of home chefs' },
    { asin: 'B09LLXQJ5P', title: 'Tata Tea Gold 500g', price_inr: 219, rating: 4.5, category: 'beverages', amazon_now_eligible: true, image_placeholder: '#9E9E9E', image_url: '', adoption_copy: 'Stocked by 83% of home chefs' },
  ],
}

export const FALLBACK_OCCASIONS: OccasionCard[] = [
  {
    occasion_type: 'diwali_celebration',
    title: 'Diwali',
    emoji: '✨',
    days_until: 118,
    urgency_state: 'discovery',
    urgency_label: '118 days · Plan ahead',
    estimated_budget: 2400,
    headcount: 6,
    community_signal: '87% of households prepare 3 weeks before Diwali',
    tap_goal: 'Diwali celebration at home for 6 people under ₹2400',
    relevance_score: 0.52,
  },
  {
    occasion_type: 'kids_birthday',
    title: 'Birthday Party',
    emoji: '🎂',
    days_until: null,
    urgency_state: 'preparation',
    urgency_label: 'Plan ahead',
    estimated_budget: 3000,
    headcount: 20,
    community_signal: '91% of birthday carts include balloons and plates',
    tap_goal: 'Kids birthday party for 20 children under ₹3000',
    relevance_score: 0.48,
  },
  {
    occasion_type: 'office_potluck',
    title: 'Office Potluck',
    emoji: '🍱',
    days_until: null,
    urgency_state: 'preparation',
    urgency_label: 'Plan ahead',
    estimated_budget: 800,
    headcount: 10,
    community_signal: 'Disposable plates, serving spoons, and one dish contribution',
    tap_goal: 'Office potluck lunch for 10 colleagues under ₹800',
    relevance_score: 0.45,
  },
  {
    occasion_type: 'travel_trek',
    title: 'Trek / Travel',
    emoji: '🎒',
    days_until: null,
    urgency_state: 'preparation',
    urgency_label: 'Plan ahead',
    estimated_budget: 3500,
    headcount: 2,
    community_signal: 'First aid, energy bars, and waterproof gear for safety',
    tap_goal: 'Weekend trek for 2 people under ₹3500',
    relevance_score: 0.42,
  },
]

export const FALLBACK_CART_ITEMS = [
  { cart_item_id: '1', need_label: 'Plates & utensils', title: 'Disposable Paper Plates 25pc', price: 89, packs_quantity: 2, total_cost: 178, amazon_now_eligible: true, rating: 4.2, delivery_eta: 'now_20min', prime: true, explanation: '2 plates per child × 12 kids = 24 plates' },
  { cart_item_id: '2', need_label: 'Cups & drinks', title: 'Disposable Cups 50pc', price: 79, packs_quantity: 1, total_cost: 79, amazon_now_eligible: true, rating: 4.0, delivery_eta: 'now_20min', prime: true, explanation: '2.5 cups per child × 12 kids' },
  { cart_item_id: '3', need_label: 'Candles & cake knife', title: 'Birthday Candles Set 10pc', price: 49, packs_quantity: 1, total_cost: 49, amazon_now_eligible: true, rating: 4.3, delivery_eta: 'now_20min', prime: true, explanation: '1 pack of candles' },
  { cart_item_id: '4', need_label: 'Balloons & decorations', title: 'Multicolor Balloons 30pc', price: 149, packs_quantity: 2, total_cost: 298, amazon_now_eligible: true, rating: 4.1, delivery_eta: 'now_20min', prime: true, explanation: '3 balloons per child × 12 kids with buffer' },
  { cart_item_id: '5', need_label: 'Napkins & tissues', title: 'Paper Napkins 100pc', price: 59, packs_quantity: 1, total_cost: 59, amazon_now_eligible: true, rating: 4.0, delivery_eta: 'now_20min', prime: true, explanation: '3 napkins per child × 12 kids' },
  { cart_item_id: '6', need_label: 'Entertainment', title: 'Party Games Set', price: 199, packs_quantity: 1, total_cost: 199, amazon_now_eligible: false, rating: 3.8, delivery_eta: 'tomorrow', prime: true, explanation: '1 games set for group activities' },
  { cart_item_id: '7', need_label: 'Return gifts', title: 'Return Gift Bags 12pc', price: 199, packs_quantity: 1, total_cost: 199, amazon_now_eligible: true, rating: 4.2, delivery_eta: 'now_20min', prime: true, explanation: '1 gift per child × 12 kids' },
  { cart_item_id: '8', need_label: 'Cleanup', title: 'Trash Bags 30pc', price: 129, packs_quantity: 1, total_cost: 129, amazon_now_eligible: true, rating: 4.1, delivery_eta: 'now_20min', prime: true, explanation: '1 pack for post-party cleanup' },
]
