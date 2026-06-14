import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet'
import { Ionicons } from '@expo/vector-icons'
import * as Haptics from 'expo-haptics'
import * as Linking from 'expo-linking'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import axios from 'axios'

import { Colors } from '../lib/constants'

const API_BASE = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000'

interface PreCheckoutSheetProps {
  visible: boolean
  cartItems: any[]
  goal: string
  budgetMax: number
  headcount: number
  occasionType: string
  amazonCartUrl: string
  onDismiss: () => void
  onProceed?: () => void
}

const WARNING_CONFIG: Record<string, { icon: string; color: string; borderColor: string; label: string }> = {
  late_item: {
    icon: 'time-outline',
    color: '#CC0C39',
    borderColor: '#CC0C39',
    label: 'DELIVERY RISK',
  },
  price_drop: {
    icon: 'trending-down-outline',
    color: '#E47911',
    borderColor: '#E47911',
    label: 'PRICE ALERT',
  },
  compatibility_gap: {
    icon: 'warning-outline',
    color: '#CC0C39',
    borderColor: '#CC0C39',
    label: 'MISSING ITEM',
  },
  quantity_risk: {
    icon: 'stats-chart-outline',
    color: '#E47911',
    borderColor: '#E47911',
    label: 'QUANTITY CHECK',
  },
  budget_insight: {
    icon: 'wallet-outline',
    color: '#007185',
    borderColor: '#007185',
    label: 'BUDGET',
  },
}

export default function PreCheckoutSheet({
  visible,
  cartItems,
  goal,
  budgetMax,
  headcount,
  occasionType,
  amazonCartUrl,
  onDismiss,
  onProceed,
}: PreCheckoutSheetProps) {
  const sheetRef = useRef<BottomSheet>(null)
  const snapPoints = useMemo(() => ['65%'], [])
  const [warnings, setWarnings] = useState<any[]>([])
  const [allClear, setAllClear] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (visible) {
      sheetRef.current?.expand()
      fetchWarnings()
    } else {
      sheetRef.current?.close()
    }
  }, [visible])

  const fetchWarnings = async () => {
    setLoading(true)
    try {
      const res = await axios.post(
        `${API_BASE}/api/intelligence/pre-checkout`,
        {
          cart_items: cartItems,
          goal,
          budget_max: budgetMax,
          headcount,
          occasion_type: occasionType,
          user_id: 'U001',
        },
      )
      const data = res.data.data
      setWarnings(data.warnings || [])
      setAllClear(data.all_clear || false)
    } catch {
      // Fallback warnings for demo
      setWarnings([
        {
          warning_id: 'w1',
          type: 'late_item',
          severity: 'critical',
          title: 'Streamers arrive tomorrow',
          detail:
            'Not available on Amazon Now. We found a Now-eligible alternative.',
          action_label: 'Swap to Now item',
          action_type: 'swap_item',
        },
        {
          warning_id: 'w2',
          type: 'price_drop',
          severity: 'warning',
          title: '₹50 saving available',
          detail:
            'Balloon Pump was ₹99 last month (now ₹149). Price is rising.',
          action_label: 'See alternatives',
          action_type: 'swap_item',
          saving_amount: 50,
        },
        {
          warning_id: 'w3',
          type: 'budget_insight',
          severity: 'info',
          title: '₹150 under budget',
          detail:
            'Cart total ₹3,850 vs budget ₹4,000. Small buffer available.',
          action_label: 'Review cart',
          action_type: 'continue',
        },
      ])
      setAllClear(false)
    }
    setLoading(false)
  }

  const proceedToCheckout = async () => {
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy).catch(
      () => {},
    )
    onDismiss()
    if (onProceed) {
      onProceed()
      return
    }
    Linking.openURL(amazonCartUrl || 'https://www.amazon.in')
  }

  const handleClose = useCallback(() => {
    onDismiss()
  }, [onDismiss])

  return (
    <BottomSheet
      ref={sheetRef}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={handleClose}
      backgroundStyle={styles.sheetBg}
      handleIndicatorStyle={styles.handle}
    >
      <BottomSheetScrollView contentContainerStyle={styles.scrollContent}>
        {/* HEADER */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <Text style={styles.headerTitle}>Before you checkout</Text>
            <Text style={styles.headerSubtitle}>
              {loading
                ? 'Checking your cart...'
                : allClear
                  ? 'Everything looks good'
                  : `${warnings.length} thing${warnings.length > 1 ? 's' : ''} to review`}
            </Text>
          </View>
          <TouchableOpacity onPress={onDismiss} hitSlop={10}>
            <Ionicons name="close" size={20} color={Colors.textSecondary} />
          </TouchableOpacity>
        </View>

        {/* DIVIDER */}
        <View style={styles.divider} />

        {/* LOADING STATE */}
        {loading && (
          <View style={styles.loadingContainer}>
            <Text style={styles.loadingText}>
              Running 5 pre-checkout checks...
            </Text>
          </View>
        )}

        {/* ALL CLEAR STATE */}
        {!loading && allClear && (
          <View style={styles.allClear}>
            <Ionicons name="checkmark-circle" size={48} color={Colors.successGreen} />
            <Text style={styles.allClearTitle}>Cart looks great</Text>
            <Text style={styles.allClearSubtitle}>
              All items on Amazon Now · Within budget · No compatibility issues
            </Text>
          </View>
        )}

        {/* WARNINGS LIST */}
        {!loading &&
          !allClear &&
          warnings.map((w: any, idx: number) => {
            const config =
              WARNING_CONFIG[w.type as string] || WARNING_CONFIG.budget_insight
            return (
              <View key={w.warning_id || idx}>
                <View
                  style={[
                    styles.warningRow,
                    { borderLeftColor: config.borderColor },
                  ]}
                >
                  <Ionicons
                    name={config.icon as any}
                    size={18}
                    color={config.color}
                    style={styles.warningIcon}
                  />
                  <View style={styles.warningContent}>
                    <Text style={[styles.warningLabel, { color: config.color }]}>
                      {config.label}
                    </Text>
                    <Text style={styles.warningTitle}>{w.title}</Text>
                    <Text style={styles.warningDetail}>{w.detail}</Text>
                  </View>
                  {w.saving_amount ? (
                    <View style={styles.savingBadge}>
                      <Text style={styles.savingText}>
                        Save ₹{w.saving_amount}
                      </Text>
                    </View>
                  ) : null}
                </View>
                {idx < warnings.length - 1 && <View style={styles.rowDivider} />}
              </View>
            )
          })}

        {/* Spacer for bottom buttons */}
        <View style={{ height: 100 }} />
      </BottomSheetScrollView>

      {/* BOTTOM BUTTONS */}
      <View style={styles.bottomButtons}>
        {!loading && !allClear && warnings.length > 0 && (
          <TouchableOpacity style={styles.reviewButton} onPress={onDismiss}>
            <Text style={styles.reviewButtonText}>Review cart</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity
          style={[
            styles.checkoutButton,
            (allClear || loading) && styles.checkoutButtonFull,
          ]}
          onPress={proceedToCheckout}
        >
          <Text style={styles.checkoutButtonText}>
            {allClear ? 'Add to Amazon Cart' : 'Proceed anyway'}
          </Text>
          <Ionicons
            name="arrow-forward"
            size={16}
            color="white"
            style={{ marginLeft: 6 }}
          />
        </TouchableOpacity>
      </View>
    </BottomSheet>
  )
}

const styles = StyleSheet.create({
  sheetBg: {
    backgroundColor: Colors.background,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
  },
  handle: {
    backgroundColor: '#D5D9D9',
    width: 40,
  },
  scrollContent: {
    paddingBottom: 32,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
  },
  headerLeft: { flex: 1 },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.textPrimary,
  },
  headerSubtitle: {
    fontSize: 13,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  divider: {
    height: 1,
    backgroundColor: '#F0F2F2',
  },
  warningRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderLeftWidth: 3,
    marginLeft: 16,
    marginRight: 16,
    marginTop: 8,
    borderRadius: 4,
  },
  warningIcon: {
    marginTop: 2,
    marginRight: 10,
  },
  warningContent: { flex: 1 },
  warningLabel: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  warningTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.textPrimary,
    marginTop: 2,
  },
  warningDetail: {
    fontSize: 12,
    color: Colors.textSecondary,
    marginTop: 4,
    lineHeight: 17,
  },
  rowDivider: {
    height: 1,
    backgroundColor: '#F0F2F2',
    marginHorizontal: 16,
  },
  savingBadge: {
    backgroundColor: '#E7F5EA',
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginLeft: 8,
    alignSelf: 'flex-start',
  },
  savingText: {
    fontSize: 11,
    fontWeight: '700',
    color: Colors.successGreen,
  },
  loadingContainer: {
    padding: 32,
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 14,
    color: Colors.textSecondary,
  },
  allClear: {
    padding: 32,
    alignItems: 'center',
  },
  allClearTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.successGreen,
    marginTop: 12,
  },
  allClearSubtitle: {
    fontSize: 13,
    color: Colors.textSecondary,
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 19,
  },
  bottomButtons: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 12,
    paddingBottom: 28,
    backgroundColor: Colors.background,
    borderTopWidth: 1,
    borderTopColor: '#F0F2F2',
    gap: 8,
  },
  reviewButton: {
    flex: 1,
    height: 48,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#D5D9D9',
    justifyContent: 'center',
    alignItems: 'center',
  },
  reviewButtonText: {
    fontSize: 15,
    fontWeight: '400',
    color: Colors.textPrimary,
  },
  checkoutButton: {
    flex: 1,
    height: 48,
    borderRadius: 4,
    backgroundColor: Colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    flexDirection: 'row',
  },
  checkoutButtonFull: {
    flex: 1,
  },
  checkoutButtonText: {
    fontSize: 15,
    fontWeight: '700',
    color: Colors.white,
  },
})
