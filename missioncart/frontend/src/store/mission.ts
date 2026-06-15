import { create } from 'zustand'

import type { CartItem, MissionBuildResult } from '../lib/types'

interface MissionStore {
  cart: CartItem[]
  currentCart: CartItem[]
  currentMission: MissionBuildResult | null
  currentBuildResult: any | null
  auditResult: any | null
  isLoading: boolean
  comparisonVisible: boolean
  comparisonItemA: any | null
  comparisonItemB: any | null
  showCompareChip: boolean
  lastComparisonTime: number
  _viewHistory: Array<{ item: any; timestamp: number }>
  undoToast: {
    visible: boolean
    message: string
    onUndo: (() => void) | null
    duration: number
  } | null
  setCart: (cart: CartItem[]) => void
  setMission: (mission: MissionBuildResult | null) => void
  setBuildResult: (result: any) => void
  setAuditResult: (result: any) => void
  setLoading: (isLoading: boolean) => void
  clearMission: () => void
  trackItemView: (item: any) => void
  setComparisonItems: (a: any, b: any) => void
  dismissComparison: () => void
  dismissChip: () => void
  showUndoToast: (config: {
    message: string
    onUndo: (() => void) | null
    duration: number
  }) => void
  hideUndoToast: () => void
}

export const useMissionStore = create<MissionStore>((set, get) => ({
  cart: [],
  currentCart: [],
  currentMission: null,
  currentBuildResult: null,
  auditResult: null,
  isLoading: false,
  comparisonVisible: false,
  comparisonItemA: null,
  comparisonItemB: null,
  showCompareChip: false,
  lastComparisonTime: 0,
  _viewHistory: [],
  undoToast: null,
  setCart: (cart) => set({ cart, currentCart: cart }),
  setMission: (currentMission) => set({ currentMission }),
  setBuildResult: (currentBuildResult) => set({ currentBuildResult }),
  setAuditResult: (auditResult) => set({ auditResult }),
  setLoading: (isLoading) => set({ isLoading }),
  clearMission: () =>
    set({
      cart: [],
      currentCart: [],
      currentMission: null,
      currentBuildResult: null,
      isLoading: false,
      comparisonVisible: false,
      comparisonItemA: null,
      comparisonItemB: null,
      showCompareChip: false,
      _viewHistory: [],
      undoToast: null,
    }),
  trackItemView: (item) => {
    const now = Date.now()
    const history = [...get()._viewHistory, { item, timestamp: now }].slice(-10)
    const recentViews = history
      .filter((view) => now - view.timestamp < 60000)
      .slice(-6)
    const uniqueItems = new Set(
      recentViews.map((view) => view.item.cart_item_id),
    )
    const cooldownOk = now - get().lastComparisonTime > 300000

    if (uniqueItems.size === 2 && cooldownOk) {
      const ids = [...uniqueItems]
      const countA = recentViews.filter(
        (view) => view.item.cart_item_id === ids[0],
      ).length
      const countB = recentViews.filter(
        (view) => view.item.cart_item_id === ids[1],
      ).length
      const itemA = recentViews.find(
        (view) => view.item.cart_item_id === ids[0],
      )?.item
      const itemB = recentViews.find(
        (view) => view.item.cart_item_id === ids[1],
      )?.item

      if (countA >= 3 && countB >= 3) {
        set({
          _viewHistory: history,
          comparisonVisible: true,
          comparisonItemA: itemA,
          comparisonItemB: itemB,
          lastComparisonTime: now,
          showCompareChip: false,
        })
        return
      }

      if (countA >= 2 && countB >= 1) {
        set({
          _viewHistory: history,
          showCompareChip: true,
          comparisonItemA: itemA,
          comparisonItemB: itemB,
        })
        return
      }
    }

    set({ _viewHistory: history })
  },
  setComparisonItems: (a, b) =>
    set({
      comparisonVisible: true,
      comparisonItemA: a,
      comparisonItemB: b,
      lastComparisonTime: Date.now(),
      showCompareChip: false,
    }),
  dismissComparison: () =>
    set({
      comparisonVisible: false,
      showCompareChip: false,
      _viewHistory: [],
    }),
  dismissChip: () => set({ showCompareChip: false, _viewHistory: [] }),
  showUndoToast: (config) => {
    const toast = { visible: true, ...config }
    set({ undoToast: toast })
    setTimeout(() => {
      if (get().undoToast === toast) {
        set({ undoToast: null })
      }
    }, config.duration)
  },
  hideUndoToast: () => set({ undoToast: null }),
}))
