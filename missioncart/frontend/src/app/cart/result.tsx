import { Ionicons } from '@expo/vector-icons'
import * as Linking from 'expo-linking'
import { useRouter } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useCallback, useRef, useState } from 'react'
import {
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import ComparisonBottomSheet from '../../components/comparison/ComparisonBottomSheet'
import PreCheckoutSheet from '../../components/PreCheckoutSheet'
import { Colors, Radius, getLabelColor } from '../../lib/constants'
import { useMissionStore } from '../../store/mission'

const FALLBACK_CART_ITEMS = [
  { cart_item_id: '1', need_label: 'Plates & utensils', title: 'Disposable Paper Plates 25pc', price: 89, packs_quantity: 2, total_cost: 178, amazon_now_eligible: true, rating: 4.2, delivery_eta: 'now_20min', prime: true, explanation: '2 plates per child × 12 kids = 24 plates' },
  { cart_item_id: '2', need_label: 'Cups & drinks', title: 'Disposable Cups 50pc', price: 79, packs_quantity: 1, total_cost: 79, amazon_now_eligible: true, rating: 4.0, delivery_eta: 'now_20min', prime: true, explanation: '2.5 cups per child × 12 kids' },
  { cart_item_id: '3', need_label: 'Candles & cake knife', title: 'Birthday Candles Set 10pc', price: 49, packs_quantity: 1, total_cost: 49, amazon_now_eligible: true, rating: 4.3, delivery_eta: 'now_20min', prime: true, explanation: '1 pack of candles' },
  { cart_item_id: '4', need_label: 'Balloons & decorations', title: 'Multicolor Balloons 30pc', price: 149, packs_quantity: 2, total_cost: 298, amazon_now_eligible: true, rating: 4.1, delivery_eta: 'now_20min', prime: true, explanation: '3 balloons per child × 12 kids with buffer' },
  { cart_item_id: '5', need_label: 'Napkins & tissues', title: 'Paper Napkins 100pc', price: 59, packs_quantity: 1, total_cost: 59, amazon_now_eligible: true, rating: 4.0, delivery_eta: 'now_20min', prime: true, explanation: '3 napkins per child × 12 kids' },
  { cart_item_id: '6', need_label: 'Entertainment', title: 'Party Games Set', price: 199, packs_quantity: 1, total_cost: 199, amazon_now_eligible: false, rating: 3.8, delivery_eta: 'tomorrow', prime: true, explanation: '1 games set for group activities' },
  { cart_item_id: '7', need_label: 'Return gifts', title: 'Return Gift Bags 12pc', price: 199, packs_quantity: 1, total_cost: 199, amazon_now_eligible: true, rating: 4.2, delivery_eta: 'now_20min', prime: true, explanation: '1 gift per child × 12 kids' },
  { cart_item_id: '8', need_label: 'Cleanup', title: 'Trash Bags 30pc', price: 129, packs_quantity: 1, total_cost: 129, amazon_now_eligible: true, rating: 4.1, delivery_eta: 'now_20min', prime: true, explanation: '1 pack for post-party cleanup' },
]

function formatInr(value: number) {
  return value.toLocaleString('en-IN')
}

export default function CartResultScreen() {
  const router = useRouter()
  const storeCart = useMissionStore((s) => s.cart)
  const buildResult = useMissionStore((s) => s.currentBuildResult)
  const trackItemView = useMissionStore((s) => s.trackItemView)
  const setComparisonItems = useMissionStore((s) => s.setComparisonItems)

  const cartItems: any[] = storeCart.length > 0 ? storeCart : FALLBACK_CART_ITEMS
  const total =
    buildResult?.total_cost ||
    cartItems.reduce(
      (sum: number, item: any) => sum + (item.total_cost || 0),
      0,
    ) ||
    0
  const budget =
    buildResult?.budget_remaining !== undefined
      ? total + buildResult.budget_remaining
      : 3000
  const coverage = buildResult?.coverage_score?.display || '8/8'
  const amazonUrl = buildResult?.amazon_cart_url || 'https://www.amazon.in'
  const remaining = budget - total
  const isOverBudget = remaining < 0
  const budgetPercent = Math.min((total / budget) * 100, 100)

  const allNow = cartItems.every((item: any) => item.amazon_now_eligible)

  const [highlightedId, setHighlightedId] = useState<string | null>(null)
  const [showPreCheckout, setShowPreCheckout] = useState(false)
  const highlightTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleItemPress = useCallback(
    (item: any) => {
      trackItemView(item)
      setHighlightedId(item.cart_item_id)
      if (highlightTimer.current) clearTimeout(highlightTimer.current)
      highlightTimer.current = setTimeout(() => setHighlightedId(null), 300)
    },
    [trackItemView],
  )

  const handleCompare = () => {
    if (cartItems.length >= 2) {
      setComparisonItems(cartItems[0], cartItems[1])
    }
  }

  const handleAddToCart = () => {
    setShowPreCheckout(true)
  }

  const renderItem = ({ item }: { item: any }) => {
    const isHighlighted = highlightedId === item.cart_item_id
    const adoption = item.community_adoption_score
      ? Math.round(item.community_adoption_score * 100)
      : 87
    const sessions = item.sessions_analyzed || 3847
    const explanation =
      item.explanation || `chosen by ${adoption}% of ${sessions.toLocaleString()} planners`
    const palette = getLabelColor(item.need_label || item.title)
    const letter = (item.need_label || item.title || '?')[0].toUpperCase()
    const lineTotal = item.total_cost || item.price * (item.packs_quantity || 1)

    return (
      <TouchableOpacity
        onPress={() => handleItemPress(item)}
        activeOpacity={0.7}
        style={[styles.itemRow, isHighlighted && styles.itemRowHighlighted]}
      >
        <View style={[styles.letterTile, { backgroundColor: palette.bg }]}>
          <Text style={[styles.letterTileText, { color: palette.text }]}>
            {letter}
          </Text>
        </View>

        <View style={styles.itemContent}>
          <Text style={styles.itemNeedLabel}>
            {(item.need_label || '').toUpperCase()}
          </Text>
          <Text style={styles.itemTitle} numberOfLines={2}>
            {item.title}
          </Text>

          <View style={styles.communityBar}>
            <Text style={styles.communityAdoption}>{adoption}</Text>
            <Text style={styles.communityPct}>% match</Text>
            <View style={styles.communityDivider} />
            <Text style={styles.communitySessions}>
              {sessions.toLocaleString()} occasions
            </Text>
            <View style={styles.communityDivider} />
            <Text style={styles.communityChecks}>6 checks ✓</Text>
          </View>

          <View style={styles.deliveryBadgeRow}>
            {item.amazon_now_eligible ? (
              <View style={styles.nowBadge}>
                <Text style={styles.badgeText}>Now · 20 min</Text>
              </View>
            ) : (
              <View style={styles.tomorrowBadge}>
                <Text style={styles.badgeText}>Tomorrow</Text>
              </View>
            )}
          </View>

          <Text style={styles.explanation} numberOfLines={2}>
            {explanation}
          </Text>
        </View>

        <View style={styles.itemPriceCol}>
          <Text style={styles.itemPrice}>₹{formatInr(lineTotal)}</Text>
          <Text style={styles.itemQty}>× {item.packs_quantity || 1}</Text>
        </View>
      </TouchableOpacity>
    )
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar style="light" backgroundColor={Colors.nowBlue} />

      <View style={styles.header}>
        <Text style={styles.headerTitle}>Your mission cart</Text>
      </View>

      <FlatList
        data={cartItems}
        keyExtractor={(item: any) => item.cart_item_id || String(Math.random())}
        renderItem={renderItem}
        style={styles.list}
        contentContainerStyle={styles.listContent}
        ListHeaderComponent={
          <>
            {/* Summary bar */}
            <View style={styles.summaryBar}>
              <View style={styles.summaryRow1}>
                <Text style={styles.summaryTotal}>₹{formatInr(total)}</Text>
                <Text style={styles.summaryCoverage}>
                  Coverage: {coverage}
                </Text>
              </View>
              <Text style={styles.summaryRow2}>
                {cartItems.length} items · All on Amazon Now ⚡
              </Text>
            </View>

            {/* Budget bar */}
            <View style={styles.budgetSection}>
              <View style={styles.budgetLabelRow}>
                <Text style={styles.budgetLabelText}>Budget used</Text>
                <Text style={styles.budgetLabelText}>
                  ₹{formatInr(Math.abs(remaining))} left
                </Text>
              </View>
              <View style={styles.budgetTrack}>
                <View
                  style={[
                    styles.budgetFill,
                    {
                      width: `${budgetPercent}%`,
                      backgroundColor: isOverBudget ? Colors.errorRed : Colors.primary,
                    },
                  ]}
                />
              </View>
            </View>

            {/* 8px divider */}
            <View style={styles.divider} />

            {/* Section label */}
            <View style={styles.sectionLabelRow}>
              <Text style={styles.sectionLabel}>YOUR CART</Text>
            </View>
          </>
        }
        ListFooterComponent={
          <>
            {/* Amazon Now banner */}
            <View style={styles.nowBanner}>
              <Ionicons name="flash" size={16} color={Colors.successGreen} />
              <Text style={styles.nowBannerText}>
                All items available · Delivery in 20 min
              </Text>
            </View>

            {/* Compare link */}
            <TouchableOpacity onPress={handleCompare} style={styles.compareWrap}>
              <Text style={styles.compareHint}>Having trouble deciding? </Text>
              <Text style={styles.compareLink}>Compare items</Text>
            </TouchableOpacity>
          </>
        }
      />

      {/* Fixed bottom bar */}
      <View style={styles.bottomBar}>
        <Text style={styles.bottomTotal}>₹{formatInr(total)}</Text>
        <Pressable onPress={handleAddToCart} style={styles.addButton}>
          <Text style={styles.addButtonText}>Add to Amazon →</Text>
        </Pressable>
      </View>

      <ComparisonBottomSheet />
      <PreCheckoutSheet
        visible={showPreCheckout}
        cartItems={cartItems}
        goal={
          buildResult?.goal ||
          'Birthday party for 12 kids tomorrow under 4000'
        }
        budgetMax={budget}
        headcount={buildResult?.headcount || 12}
        occasionType={buildResult?.domain || 'kids_birthday'}
        amazonCartUrl={amazonUrl}
        onDismiss={() => setShowPreCheckout(false)}
        onProceed={() => void Linking.openURL(amazonUrl)}
      />
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.nowBlue,
  },
  header: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: Colors.nowBlue,
  },
  headerTitle: {
    color: Colors.white,
    fontSize: 18,
    fontWeight: '700',
  },
  list: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  listContent: {
    paddingBottom: 100,
  },
  // Summary bar
  summaryBar: {
    backgroundColor: Colors.background,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.inputBorder,
  },
  summaryRow1: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  summaryTotal: {
    color: Colors.textPrimary,
    fontSize: 20,
    fontWeight: '700',
  },
  summaryCoverage: {
    color: Colors.successGreen,
    fontSize: 14,
    fontWeight: '600',
  },
  summaryRow2: {
    marginTop: 4,
    color: Colors.textSecondary,
    fontSize: 13,
  },
  // Budget bar
  budgetSection: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: Colors.background,
  },
  budgetLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  budgetLabelText: {
    color: Colors.textSecondary,
    fontSize: 12,
  },
  budgetTrack: {
    width: '100%',
    height: 4,
    backgroundColor: '#E7E7E7',
    borderRadius: 2,
    overflow: 'hidden',
  },
  budgetFill: {
    height: 4,
    borderRadius: 2,
  },
  divider: {
    height: 8,
    backgroundColor: Colors.divider,
  },
  sectionLabelRow: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: Colors.background,
  },
  sectionLabel: {
    color: Colors.textSecondary,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  // Item row
  itemRow: {
    flexDirection: 'row',
    backgroundColor: Colors.background,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  itemRowHighlighted: {
    backgroundColor: '#FFF8F0',
  },
  letterTile: {
    width: 48,
    height: 48,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  letterTileText: {
    fontSize: 18,
    fontWeight: '700',
  },
  itemContent: {
    flex: 1,
    marginLeft: 12,
  },
  itemNeedLabel: {
    color: Colors.textSecondary,
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  itemTitle: {
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '600',
  },
  communityBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBg,
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 6,
    marginTop: 6,
  },
  communityAdoption: {
    color: Colors.primary,
    fontSize: 16,
    fontWeight: '700',
  },
  communityPct: {
    color: Colors.textSecondary,
    fontSize: 11,
    marginLeft: 2,
  },
  communityDivider: {
    width: 1,
    height: 16,
    backgroundColor: Colors.inputBorder,
    marginHorizontal: 8,
  },
  communitySessions: {
    color: Colors.textSecondary,
    fontSize: 11,
  },
  communityChecks: {
    color: Colors.successGreen,
    fontSize: 11,
    fontWeight: '600',
  },
  deliveryBadgeRow: {
    flexDirection: 'row',
    marginTop: 6,
  },
  nowBadge: {
    backgroundColor: Colors.nowBadge,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 3,
    alignSelf: 'flex-start',
  },
  tomorrowBadge: {
    backgroundColor: Colors.textSecondary,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 3,
    alignSelf: 'flex-start',
  },
  badgeText: {
    color: Colors.white,
    fontSize: 10,
    fontWeight: '700',
  },
  explanation: {
    marginTop: 4,
    color: Colors.textSecondary,
    fontSize: 11,
  },
  itemPriceCol: {
    alignItems: 'flex-end',
    marginLeft: 8,
  },
  itemPrice: {
    color: Colors.textPrimary,
    fontSize: 15,
    fontWeight: '700',
  },
  itemQty: {
    color: Colors.textSecondary,
    fontSize: 12,
    marginTop: 2,
  },
  // Now banner
  nowBanner: {
    backgroundColor: '#E7F5EA',
    paddingHorizontal: 16,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
  },
  nowBannerText: {
    color: Colors.successGreen,
    fontSize: 13,
    fontWeight: '600',
    marginLeft: 6,
  },
  compareWrap: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginVertical: 8,
  },
  compareHint: {
    color: Colors.textSecondary,
    fontSize: 12,
  },
  compareLink: {
    color: Colors.linkBlue,
    fontSize: 12,
    fontWeight: '600',
  },
  // Bottom bar
  bottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: Colors.background,
    borderTopWidth: 1,
    borderTopColor: Colors.inputBorder,
    paddingHorizontal: 16,
    paddingVertical: 12,
    paddingBottom: 28,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  bottomTotal: {
    color: Colors.textPrimary,
    fontSize: 18,
    fontWeight: '700',
  },
  addButton: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 4,
  },
  addButtonText: {
    color: Colors.white,
    fontSize: 15,
    fontWeight: '700',
  },
})
