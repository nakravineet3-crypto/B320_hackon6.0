import { Ionicons } from '@expo/vector-icons'
import * as Haptics from 'expo-haptics'
import { useRouter } from 'expo-router'
import { useEffect, useRef, useState } from 'react'
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { demoAPI } from '../../lib/api'
import { Colors } from '../../lib/constants'
import { scheduleTestNotification } from '../../lib/notifications'
import type { OccasionCard, UpcomingRecurrence } from '../../lib/types'

type IoniconName = keyof typeof Ionicons.glyphMap

interface Category {
  id: string
  label: string
  icon: IoniconName
}

interface ReorderItem {
  id?: string
  asin?: string
  item_name: string
  quantity: number
  unit: string
  price_inr: number
  amazon_now_eligible: boolean
}

const categories: Category[] = [
  { id: 'beverages', label: 'Beverages', icon: 'wine-outline' },
  { id: 'snacks', label: 'Snacks', icon: 'fast-food-outline' },
  { id: 'ice-cream', label: 'Ice cream', icon: 'ice-cream-outline' },
  { id: 'bath-body', label: 'Bath & body', icon: 'sparkles-outline' },
  { id: 'cleaners', label: 'Cleaners', icon: 'water-outline' },
  { id: 'grocery', label: 'Grocery', icon: 'basket-outline' },
  { id: 'party', label: 'Party', icon: 'balloon-outline' },
  { id: 'health', label: 'Health', icon: 'medkit-outline' },
]

const fallbackReorderItems: ReorderItem[] = [
  {
    item_name: 'Tata Salt 1kg',
    quantity: 2,
    unit: 'packs',
    price_inr: 42,
    amazon_now_eligible: true,
  },
  {
    item_name: 'Surf Excel 1kg',
    quantity: 1,
    unit: 'pack',
    price_inr: 189,
    amazon_now_eligible: true,
  },
  {
    item_name: 'Parle-G 800g',
    quantity: 3,
    unit: 'packs',
    price_inr: 105,
    amazon_now_eligible: true,
  },
]

const REORDER_TILE_COLORS = [
  { bg: '#E8F5E9', text: '#2E7D32' },
  { bg: '#E3F2FD', text: '#1565C0' },
  { bg: '#FFF8E1', text: '#F57F17' },
]

interface FallbackOccasion extends OccasionCard {
  accent: string
}

const fallbackOccasions: FallbackOccasion[] = [
  {
    id: 'diwali',
    title: 'Diwali',
    days_until: 24,
    emoji: '🪔',
    category: 'festival',
    estimated_budget: 2400,
    tap_action: '/missions/diwali',
    accent: '#FF6B00',
  },
  {
    id: 'moms-birthday',
    title: "Mom's Birthday",
    days_until: 6,
    emoji: '🎂',
    category: 'birthday',
    estimated_budget: 1800,
    tap_action: '/missions/moms-birthday',
    accent: '#007185',
  },
  {
    id: 'coorg-trek',
    title: 'Trek to Coorg',
    days_until: 12,
    emoji: '🥾',
    category: 'travel',
    estimated_budget: 3200,
    tap_action: '/missions/coorg-trek',
    accent: '#2E7D32',
  },
  {
    id: 'office-potluck',
    title: 'Office Potluck',
    days_until: 3,
    emoji: '🍲',
    category: 'event',
    estimated_budget: 800,
    tap_action: '/missions/office-potluck',
    accent: '#6B3FA0',
  },
]

const ACCENTS = ['#FF6B00', '#007185', '#2E7D32', '#6B3FA0']

function formatInr(value: number) {
  return value.toLocaleString('en-IN')
}

function truncate(text: string, max: number) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text
}

export default function HomeScreen() {
  const router = useRouter()
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [search, setSearch] = useState('')
  const [goal, setGoal] = useState('')
  const [isApproving, setIsApproving] = useState(false)
  const [reorderItems, setReorderItems] =
    useState<ReorderItem[]>(fallbackReorderItems)
  const [occasions, setOccasions] = useState<FallbackOccasion[]>(fallbackOccasions)
  const [upcomingRecurrence, setUpcomingRecurrence] =
    useState<UpcomingRecurrence | null>(null)
  const [isRecurrenceDismissed, setIsRecurrenceDismissed] = useState(false)

  useEffect(() => {
    demoAPI
      .getOccasions()
      .then((res) => {
        if (res.data?.data && Array.isArray(res.data.data)) {
          const mapped = res.data.data.map(
            (o: OccasionCard, i: number): FallbackOccasion => ({
              ...o,
              accent: ACCENTS[i % ACCENTS.length],
            }),
          )
          setOccasions(mapped)
        }
      })
      .catch(() => {
        // Keep fallback occasions
      })

    demoAPI
      .getReorderAlerts()
      .then((res) => {
        const alerts = res.data?.data || res.data || []
        if (Array.isArray(alerts) && alerts.length > 0) {
          setReorderItems(alerts.slice(0, 3))
        }
      })
      .catch(() => {
        // Keep fallback reorder items.
      })

    demoAPI
      .getUserProfile()
      .then((res) => {
        const recurrence = res.data?.data?.upcoming_recurrence
        if (recurrence?.recurrence_alert) {
          setUpcomingRecurrence(recurrence)
        }
      })
      .catch(() => {
        // The recurrence card is optional when profile data is unavailable.
      })
  }, [])

  useEffect(
    () => () => {
      if (successTimerRef.current) {
        clearTimeout(successTimerRef.current)
      }
    },
    [],
  )

  const openBuilding = (missionGoal: string) => {
    router.push({
      pathname: '/cart/building',
      params: { goal: missionGoal, budget: '3000' },
    })
  }

  const handleCategoryPress = (category: Category) => {
    if (category.id === 'party') {
      openBuilding('Party supplies')
    }
  }

  const handleApprove = () => {
    if (isApproving) {
      return
    }

    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy).catch(() => {
      // Haptics are unavailable on some browser and simulator environments.
    })
    setIsApproving(true)

    if (successTimerRef.current) {
      clearTimeout(successTimerRef.current)
    }
    successTimerRef.current = setTimeout(() => setIsApproving(false), 800)
  }

  const handleBuildCart = () => {
    openBuilding(goal.trim() || 'Birthday party for 20 people under ₹3000')
  }

  const handleRebuildMission = () => {
    if (!upcomingRecurrence) {
      return
    }

    router.push({
      pathname: '/cart/building',
      params: {
        goal: upcomingRecurrence.occasion_label,
        budget: upcomingRecurrence.budget_used.toString(),
      },
    })
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {/* SECTION 1.1 — HEADER */}
        <View style={styles.nowHeader}>
          <View style={styles.topHeaderRow}>
            <Pressable style={styles.headerIconButton} accessibilityRole="button">
              <Ionicons name="person-circle" size={30} color={Colors.white} />
            </Pressable>

            <View style={styles.logo}>
              <Text style={styles.amazonLogoText}>amazon</Text>
              <Text style={styles.logoBolt}>⚡</Text>
              <Text style={styles.nowLogoText}>now</Text>
            </View>

            <Pressable style={styles.headerIconButton} accessibilityRole="button">
              <Ionicons name="cart-outline" size={26} color={Colors.white} />
            </Pressable>
          </View>

          <Pressable style={styles.deliveryRow} accessibilityRole="button">
            <View style={styles.deliveryPill}>
              <Text style={styles.deliveryPillText}>⚡ 10 mins</Text>
            </View>
            <Text style={styles.deliveryAddress}>
              {truncate('Bangalore, 560001', 20)}
            </Text>
            <Ionicons name="chevron-down" size={16} color={Colors.white} />
          </Pressable>
        </View>

        {/* SECTION 1.2 — SEARCH BAR */}
        <View style={styles.discoverySection}>
          <View style={styles.searchBar}>
            <Ionicons name="search" size={21} color={Colors.textSecondary} />
            <TextInput
              value={search}
              onChangeText={setSearch}
              placeholder="Search for groceries, snacks..."
              placeholderTextColor={Colors.placeholder}
              style={styles.searchInput}
              returnKeyType="search"
              accessibilityLabel="Search products"
            />
            <Ionicons name="mic-outline" size={21} color={Colors.textSecondary} />
          </View>

          {/* SECTION 1.3 — CATEGORY PILLS */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.categoryList}
          >
            {categories.map((category) => (
              <Pressable
                key={category.id}
                onPress={() => handleCategoryPress(category)}
                style={styles.categoryItem}
                accessibilityRole="button"
              >
                <Ionicons
                  name={category.icon}
                  size={28}
                  color={Colors.textPrimary}
                />
                <Text style={styles.categoryLabel} numberOfLines={1}>
                  {category.label}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>

        {/* SECTION 1.4 — PROMOTIONAL BANNER */}
        <View style={styles.banner}>
          <View style={styles.bannerLeft}>
            <Text style={styles.bannerBrand}>MissionCart</Text>
            <Text style={styles.bannerHeadline}>Plan any occasion</Text>
            <Text style={styles.bannerHeadline}>in under 60 seconds</Text>
            <Pressable style={styles.bannerCta} accessibilityRole="button">
              <Text style={styles.bannerCtaText}>Get started →</Text>
            </Pressable>
          </View>
          <View style={styles.bannerRight}>
            <View style={styles.bannerStatPill}>
              <Text style={styles.bannerStatText}>3,847 occasions</Text>
            </View>
            <View style={styles.bannerStatPill}>
              <Text style={styles.bannerStatText}>234 products</Text>
            </View>
            <View style={styles.bannerStatPill}>
              <Text style={styles.bannerStatText}>94% accuracy</Text>
            </View>
          </View>
        </View>

        {/* SECTION 1.5 — BENEFIT PILLS ROW */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.benefitRow}
        >
          <View style={styles.benefitPill}>
            <Ionicons name="flash-outline" size={20} color={Colors.primary} />
            <View style={styles.benefitTextWrap}>
              <Text style={styles.benefitTitle}>Fast Delivery</Text>
              <Text style={styles.benefitSubtitle}>Above ₹149</Text>
            </View>
          </View>
          <View style={styles.benefitPill}>
            <Ionicons
              name="shield-checkmark-outline"
              size={20}
              color={Colors.successGreen}
            />
            <View style={styles.benefitTextWrap}>
              <Text style={styles.benefitTitle}>Zero Sponsored</Text>
              <Text style={styles.benefitSubtitle}>In mission carts</Text>
            </View>
          </View>
        </ScrollView>

        {/* SECTION 1.6 — DIVIDER */}
        <View style={styles.divider} />

        {/* SECTION 1.7 — MORNING APPROVAL CARD */}
        <View style={styles.reorderCard}>
          <View style={styles.reorderTopBar}>
            <Text style={styles.reorderTopTitle}>Your daily reorder</Text>
            <View style={styles.reorderReady}>
              <Ionicons name="time-outline" size={16} color={Colors.white} />
              <Text style={styles.reorderReadyText}>Ready now</Text>
            </View>
          </View>

          <View style={styles.reorderRows}>
            {reorderItems.map((item, index) => {
              const tileColor =
                REORDER_TILE_COLORS[index % REORDER_TILE_COLORS.length]
              return (
                <View
                  key={item.id || item.asin || item.item_name}
                  style={[
                    styles.productRow,
                    index < reorderItems.length - 1 &&
                      styles.productRowDivider,
                  ]}
                >
                  <View
                    style={[
                      styles.letterTile,
                      { backgroundColor: tileColor.bg },
                    ]}
                  >
                    <Text
                      style={[
                        styles.letterTileText,
                        { color: tileColor.text },
                      ]}
                    >
                      {item.item_name.charAt(0).toUpperCase()}
                    </Text>
                  </View>
                  <View style={styles.productCopy}>
                    <Text style={styles.productName}>{item.item_name}</Text>
                    <Text style={styles.productQuantity}>
                      {item.quantity} {item.unit}
                    </Text>
                  </View>
                  <View style={styles.productMeta}>
                    <Text style={styles.productPrice}>₹{item.price_inr}</Text>
                    {item.amazon_now_eligible && (
                      <View style={styles.nowPill}>
                        <Text style={styles.nowPillText}>NOW</Text>
                      </View>
                    )}
                  </View>
                </View>
              )
            })}
          </View>

          <View style={styles.reorderFooter}>
            <View style={styles.actionButtons}>
              <Pressable
                onPress={handleApprove}
                style={[
                  styles.approveButton,
                  isApproving && styles.approveButtonSuccess,
                ]}
                accessibilityRole="button"
              >
                <Text style={styles.approveButtonText}>Approve & Order</Text>
              </Pressable>
              <Pressable
                onPress={() => console.log('Review daily reorder')}
                style={styles.reviewButton}
                accessibilityRole="button"
              >
                <Text style={styles.reviewButtonText}>Review</Text>
              </Pressable>
            </View>
          </View>
        </View>

        {/* SECTION 1.8 — DIVIDER */}
        <View style={styles.divider} />

        {upcomingRecurrence &&
          upcomingRecurrence.recurrence_alert &&
          !isRecurrenceDismissed && (
            <View style={styles.recurrenceCard}>
              <Text style={styles.recurrenceEyebrow}>Last year</Text>
              <Text style={styles.recurrenceTitle}>
                {upcomingRecurrence.occasion_label}
              </Text>
              <Text style={styles.recurrenceMeta}>
                ₹{formatInr(upcomingRecurrence.budget_used)} ·{' '}
                {upcomingRecurrence.headcount} guests ·{' '}
                {upcomingRecurrence.coverage_score}
              </Text>
              <Text style={styles.recurrenceAlert}>
                {upcomingRecurrence.recurrence_alert}
              </Text>
              <View style={styles.recurrenceActions}>
                <Pressable
                  onPress={handleRebuildMission}
                  accessibilityRole="button"
                  accessibilityLabel="Rebuild mission"
                >
                  <Text style={styles.recurrencePrimaryAction}>
                    Rebuild mission
                  </Text>
                </Pressable>
                <Pressable
                  onPress={() => setIsRecurrenceDismissed(true)}
                  accessibilityRole="button"
                  accessibilityLabel="Dismiss recurrence"
                >
                  <Text style={styles.recurrenceDismissAction}>Dismiss</Text>
                </Pressable>
              </View>
            </View>
          )}

        {/* SECTION 1.9 — MISSION INPUT SECTION */}
        <Text style={styles.missionHeader}>What do you need?</Text>
        <TextInput
          value={goal}
          onChangeText={setGoal}
          placeholder="e.g. Birthday party for 20 people"
          placeholderTextColor={Colors.placeholder}
          style={styles.goalInput}
          returnKeyType="done"
          accessibilityLabel="Mission goal"
        />
        <View style={styles.budgetRow}>
          <Text style={styles.budgetLabel}>Budget</Text>
          <Pressable accessibilityRole="button">
            <Text style={styles.budgetValue}>₹3,000</Text>
          </Pressable>
        </View>
        <Pressable
          onPress={handleBuildCart}
          style={styles.buildCartButton}
          accessibilityRole="button"
        >
          <Text style={styles.buildCartText}>Build Cart</Text>
        </Pressable>

        {/* SECTION 1.10 — DIVIDER */}
        <View style={styles.dividerSpaced} />

        {/* SECTION 1.11 — CART AUDIT BANNER */}
        <Pressable
          onPress={() => router.push('/audit')}
          style={styles.auditBanner}
          accessibilityRole="button"
        >
          <View style={styles.auditCopy}>
            <Text style={styles.auditTitle}>Cart health check</Text>
            <Text style={styles.auditSubtitle}>Find issues before checkout</Text>
          </View>
          <View style={styles.auditAction}>
            <Text style={styles.auditActionText}>Check now</Text>
            <Ionicons name="chevron-forward" size={14} color={Colors.linkBlue} />
          </View>
        </Pressable>

        {/* SECTION 1.12 — DIVIDER */}
        <View style={styles.divider} />

        {/* SECTION 1.13 — COMING UP SECTION */}
        <View style={styles.comingSection}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Coming up</Text>
            <Pressable accessibilityRole="button">
              <Text style={styles.seeAllText}>See all</Text>
            </Pressable>
          </View>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.occasionList}
          >
            {occasions.map((occasion) => (
              <Pressable
                key={occasion.id}
                onPress={() => console.log('Plan occasion:', occasion.id)}
                style={[styles.occasionCard, { borderLeftColor: occasion.accent }]}
                accessibilityRole="button"
              >
                <Text style={styles.occasionTitle} numberOfLines={2}>
                  {occasion.title}
                </Text>
                <Text style={styles.occasionDays}>In {occasion.days_until} days</Text>
                <Text style={styles.occasionBudget}>
                  ~₹{formatInr(occasion.estimated_budget)}
                </Text>
                <Text style={styles.planText}>Plan →</Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>

        <Pressable
          onPress={scheduleTestNotification}
          style={styles.testNotifLink}
          accessibilityRole="button"
        >
          <Text style={styles.testNotifText}>Test morning notification</Text>
        </Pressable>

        {/* SECTION 1.14 — BOTTOM PERSISTENT BAR */}
        <View style={styles.persistentBar}>
          <View style={styles.persistentLeft}>
            <Ionicons name="bag-outline" size={20} color={Colors.textSecondary} />
            <Text style={styles.persistentItems}>0 items</Text>
          </View>
          <Text style={styles.persistentHint}>
            Add items worth ₹149 for free delivery
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.nowBlue,
  },
  screen: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  content: {
    paddingBottom: 24,
  },
  nowHeader: {
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 12,
    backgroundColor: Colors.nowBlue,
  },
  topHeaderRow: {
    minHeight: 40,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerIconButton: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  amazonLogoText: {
    color: Colors.white,
    fontSize: 22,
    lineHeight: 26,
    fontWeight: '400',
    letterSpacing: -0.5,
  },
  logoBolt: {
    marginHorizontal: 2,
    color: Colors.deliveryYellow,
    fontSize: 16,
    lineHeight: 22,
  },
  nowLogoText: {
    color: Colors.white,
    fontSize: 22,
    lineHeight: 26,
    fontWeight: '700',
    letterSpacing: -0.5,
  },
  deliveryRow: {
    alignSelf: 'center',
    marginTop: 4,
    flexDirection: 'row',
    alignItems: 'center',
  },
  deliveryPill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    backgroundColor: Colors.deliveryYellow,
    borderRadius: 4,
  },
  deliveryPillText: {
    color: Colors.textPrimary,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '700',
  },
  deliveryAddress: {
    marginLeft: 8,
    marginRight: 4,
    color: Colors.white,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '600',
  },
  discoverySection: {
    paddingTop: 12,
    paddingBottom: 8,
    backgroundColor: Colors.background,
  },
  searchBar: {
    height: 44,
    marginHorizontal: 16,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
  },
  searchInput: {
    flex: 1,
    height: 42,
    marginHorizontal: 8,
    paddingVertical: 0,
    color: Colors.textPrimary,
    fontSize: 14,
  },
  categoryList: {
    paddingHorizontal: 12,
    paddingTop: 12,
  },
  categoryItem: {
    width: 72,
    alignItems: 'center',
  },
  categoryLabel: {
    marginTop: 4,
    color: Colors.textPrimary,
    fontSize: 11,
    lineHeight: 14,
    fontWeight: '400',
    textAlign: 'center',
  },
  // Banner
  banner: {
    marginHorizontal: 0,
    height: 140,
    flexDirection: 'row',
    padding: 16,
    backgroundColor: Colors.bannerGreen,
  },
  bannerLeft: {
    flex: 0.6,
    justifyContent: 'center',
  },
  bannerBrand: {
    color: Colors.deliveryYellow,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.5,
    marginBottom: 4,
  },
  bannerHeadline: {
    color: Colors.white,
    fontSize: 20,
    fontWeight: '700',
    lineHeight: 24,
  },
  bannerCta: {
    marginTop: 12,
    backgroundColor: Colors.deliveryYellow,
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 4,
    alignSelf: 'flex-start',
  },
  bannerCtaText: {
    color: Colors.textPrimary,
    fontWeight: '700',
    fontSize: 13,
  },
  bannerRight: {
    flex: 0.4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bannerStatPill: {
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 4,
    paddingVertical: 6,
    paddingHorizontal: 10,
    marginBottom: 4,
  },
  bannerStatText: {
    color: Colors.white,
    fontSize: 11,
    fontWeight: '600',
  },
  // Benefit pills
  benefitRow: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  benefitPill: {
    width: 160,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 4,
    paddingVertical: 10,
    paddingHorizontal: 12,
    marginRight: 8,
  },
  benefitTextWrap: {
    marginLeft: 8,
  },
  benefitTitle: {
    color: Colors.textPrimary,
    fontSize: 13,
    fontWeight: '700',
  },
  benefitSubtitle: {
    color: Colors.textSecondary,
    fontSize: 11,
  },
  // Dividers
  divider: {
    height: 8,
    backgroundColor: Colors.divider,
  },
  dividerSpaced: {
    height: 8,
    backgroundColor: Colors.divider,
  },
  // Reorder card
  reorderCard: {
    overflow: 'hidden',
    backgroundColor: Colors.background,
  },
  reorderTopBar: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: Colors.primary,
  },
  reorderTopTitle: {
    color: Colors.white,
    fontSize: 14,
    lineHeight: 18,
    fontWeight: '700',
  },
  reorderReady: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  reorderReadyText: {
    marginLeft: 4,
    color: Colors.white,
    fontSize: 11,
  },
  reorderRows: {
    paddingHorizontal: 16,
  },
  productRow: {
    minHeight: 64,
    flexDirection: 'row',
    alignItems: 'center',
  },
  productRowDivider: {
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  letterTile: {
    width: 36,
    height: 36,
    marginRight: 12,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 4,
  },
  letterTileText: {
    fontSize: 18,
    fontWeight: '700',
  },
  productCopy: {
    flex: 1,
  },
  productName: {
    color: Colors.textPrimary,
    fontSize: 14,
    lineHeight: 18,
    fontWeight: '600',
  },
  productQuantity: {
    marginTop: 2,
    color: Colors.textSecondary,
    fontSize: 12,
    lineHeight: 15,
  },
  productMeta: {
    alignItems: 'flex-end',
  },
  productPrice: {
    color: Colors.textPrimary,
    fontSize: 14,
    lineHeight: 18,
    fontWeight: '700',
  },
  nowPill: {
    marginTop: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
    backgroundColor: Colors.nowBadge,
    borderRadius: 3,
  },
  nowPillText: {
    color: Colors.white,
    fontSize: 9,
    lineHeight: 12,
    fontWeight: '700',
  },
  reorderFooter: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 12,
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  approveButton: {
    flex: 1,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.primary,
    borderRadius: 4,
  },
  approveButtonSuccess: {
    backgroundColor: Colors.successGreen,
  },
  approveButtonText: {
    color: Colors.white,
    fontSize: 15,
    lineHeight: 18,
    fontWeight: '700',
  },
  reviewButton: {
    flex: 1,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
  },
  reviewButtonText: {
    color: Colors.textPrimary,
    fontSize: 15,
    lineHeight: 18,
    fontWeight: '400',
  },
  // Occasion recurrence
  recurrenceCard: {
    marginHorizontal: 16,
    marginTop: 12,
    padding: 12,
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: '#D5D9D9',
    borderLeftWidth: 4,
    borderLeftColor: '#FF9900',
    borderRadius: 4,
  },
  recurrenceEyebrow: {
    color: '#565959',
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  recurrenceTitle: {
    marginTop: 6,
    color: '#0F1111',
    fontSize: 15,
    fontWeight: '700',
  },
  recurrenceMeta: {
    marginTop: 2,
    color: '#565959',
    fontSize: 12,
  },
  recurrenceAlert: {
    marginTop: 6,
    color: '#FF9900',
    fontSize: 13,
    fontWeight: '600',
  },
  recurrenceActions: {
    marginTop: 10,
    flexDirection: 'row',
    alignItems: 'center',
  },
  recurrencePrimaryAction: {
    color: '#007185',
    fontSize: 13,
    fontWeight: '600',
  },
  recurrenceDismissAction: {
    marginLeft: 16,
    color: '#565959',
    fontSize: 13,
  },
  // Mission input
  missionHeader: {
    color: Colors.textPrimary,
    fontSize: 16,
    fontWeight: '700',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
  },
  goalInput: {
    height: 52,
    marginHorizontal: 16,
    paddingHorizontal: 12,
    color: Colors.textPrimary,
    fontSize: 14,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
  },
  budgetRow: {
    marginHorizontal: 16,
    marginTop: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  budgetLabel: {
    color: Colors.textSecondary,
    fontSize: 13,
  },
  budgetValue: {
    color: Colors.linkBlue,
    fontSize: 13,
    fontWeight: '600',
  },
  buildCartButton: {
    marginHorizontal: 16,
    marginTop: 12,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.primary,
    borderRadius: 4,
  },
  buildCartText: {
    color: Colors.white,
    fontSize: 15,
    fontWeight: '700',
  },
  // Audit banner
  auditBanner: {
    backgroundColor: Colors.divider,
    paddingHorizontal: 16,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
  },
  auditCopy: {
    flex: 1,
  },
  auditTitle: {
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '700',
  },
  auditSubtitle: {
    marginTop: 2,
    color: Colors.textSecondary,
    fontSize: 12,
  },
  auditAction: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  auditActionText: {
    color: Colors.linkBlue,
    fontSize: 13,
    fontWeight: '600',
    marginRight: 2,
  },
  // Coming up
  comingSection: {
    paddingTop: 16,
  },
  sectionHeader: {
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  sectionTitle: {
    color: Colors.textPrimary,
    fontSize: 16,
    lineHeight: 21,
    fontWeight: '700',
  },
  seeAllText: {
    color: Colors.linkBlue,
    fontSize: 13,
    lineHeight: 18,
  },
  occasionList: {
    paddingLeft: 16,
    paddingRight: 8,
    paddingTop: 12,
  },
  occasionCard: {
    width: 160,
    marginRight: 8,
    padding: 12,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
    borderLeftWidth: 3,
  },
  occasionTitle: {
    color: Colors.textPrimary,
    fontSize: 14,
    lineHeight: 18,
    fontWeight: '700',
  },
  occasionDays: {
    marginTop: 2,
    color: Colors.textSecondary,
    fontSize: 12,
    lineHeight: 16,
  },
  occasionBudget: {
    marginTop: 4,
    color: Colors.successGreen,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '600',
  },
  planText: {
    marginTop: 8,
    color: Colors.linkBlue,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '600',
  },
  testNotifLink: {
    alignSelf: 'center',
    marginTop: 16,
    marginBottom: 8,
  },
  testNotifText: {
    color: Colors.linkBlue,
    fontSize: 11,
  },
  // Persistent bar
  persistentBar: {
    height: 52,
    marginTop: 8,
    backgroundColor: Colors.background,
    borderTopWidth: 1,
    borderTopColor: Colors.inputBorder,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  persistentLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  persistentItems: {
    fontSize: 13,
    color: Colors.textSecondary,
    marginLeft: 8,
  },
  persistentHint: {
    fontSize: 12,
    color: Colors.textSecondary,
  },
})
