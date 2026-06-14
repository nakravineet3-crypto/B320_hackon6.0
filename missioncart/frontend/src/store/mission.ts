import { create } from 'zustand'

import type { CartItem, MissionBuildResult } from '../lib/types'

interface MissionStore {
  cart: CartItem[]
  currentMission: MissionBuildResult | null
  currentBuildResult: any | null
  isLoading: boolean
  comparisonVisible: boolean
  comparisonItemA: any | null
  comparisonItemB: any | null
  viewHistory: string[]
  setCart: (cart: CartItem[]) => void
  setMission: (mission: MissionBuildResult | null) => void
  setBuildResult: (result: any) => void
  setLoading: (isLoading: boolean) => void
  clearMission: () => void
  trackItemView: (item: any) => void
  setComparisonItems: (a: any, b: any) => void
  dismissComparison: () => void
}

export const useMissionStore = create<MissionStore>((set, get) => ({
  cart: [],
  currentMission: null,
  currentBuildResult: null,
  isLoading: false,
  comparisonVisible: false,
  comparisonItemA: null,
  comparisonItemB: null,
  viewHistory: [],
  setCart: (cart) => set({ cart }),
  setMission: (currentMission) => set({ currentMission }),
  setBuildResult: (currentBuildResult) => set({ currentBuildResult }),
  setLoading: (isLoading) => set({ isLoading }),
  clearMission: () =>
    set({
      cart: [],
      currentMission: null,
      currentBuildResult: null,
      isLoading: false,
    }),
  trackItemView: (item) => {
    const { viewHistory } = get()
    const key = item.title || item.cart_item_id || item.asin
    const newHistory = [...viewHistory, key].slice(-10)
    const last6 = newHistory.slice(-6)
    const uniqueKeys = [...new Set(last6)]

    if (uniqueKeys.length === 2) {
      const countA = last6.filter((k) => k === uniqueKeys[0]).length
      const countB = last6.filter((k) => k === uniqueKeys[1]).length

      if (countA >= 3 && countB >= 3) {
        const { cart } = get()
        const itemA = cart.find(
          (c) => c.title === uniqueKeys[0] || c.cart_item_id === uniqueKeys[0],
        )
        const itemB = cart.find(
          (c) => c.title === uniqueKeys[1] || c.cart_item_id === uniqueKeys[1],
        )
        set({
          viewHistory: newHistory,
          comparisonVisible: true,
          comparisonItemA: itemA || item,
          comparisonItemB: itemB || item,
        })
        return
      }
    }

    set({ viewHistory: newHistory })
  },
  setComparisonItems: (a, b) =>
    set({ comparisonVisible: true, comparisonItemA: a, comparisonItemB: b }),
  dismissComparison: () =>
    set({ comparisonVisible: false, viewHistory: [] }),
}))
