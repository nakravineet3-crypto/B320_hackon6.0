import { Ionicons } from '@expo/vector-icons'
import * as Haptics from 'expo-haptics'
import { useRouter } from 'expo-router'
import { useEffect, useState } from 'react'
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { SwipeableSearchBar } from '../../components/SwipeableSearchBar'
import { occasionAPI, demoAPI, reorderAPI } from '../../lib/api'
import { Colors } from '../../lib/constants'
import { FALLBACK_OCCASIONS } from '../../lib/fallbacks'
import type { OccasionCard, UpcomingRecurrence } from '../../lib/types'
import { useReorderStore } from '../../store/reorder'

type IoniconName = keyof typeof Ionicons.glyphMap

interface Category {
  id: string
  label: string
  icon: IoniconName
}

interface ReorderItem {
  id?: string
  asin?: string
  item_id?: string
  item_name: string
  quantity: number
  unit: string
  price_inr: number
  amazon_now_eligible: boolean
  urgency_copy?: string
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
    item_id: 'fallback_1',
    asin: 'MC_ARIEL_001',
    item_name: 'Ariel Matic Front Load Detergent 2kg',
    quantity: 1,
    unit: 'kg',
    price_inr: 399,
    amazon_now_eligible: true,
    urgency_copy: 'Almost out',
  },
  {
    item_id: 'fallback_2',
    asin: 'MC_SHAMPOO_001',
    item_name: 'Head & Shoulders Anti-Dandruff Shampoo 400ml',
    quantity: 1,
    unit: 'bottle',
    price_inr: 349,
    amazon_now_eligible: true,
    urgency_copy: 'Running low',
  },
  {
    item_id: 'fallback_3',
    asin: 'MC_DOGFOOD_001',
    item_name: "Pedigree Adult Chicken & Vegetables 3kg",
    quantity: 1,
    unit: 'kg',
    price_inr: 649,
    amazon_now_eligible: true,
    urgency_copy: 'Order soon',
  },
]

const REORDER_TILE_COLORS = [
  { bg: '#E8F5E9', text: '#2E7D32' },
  { bg: '#E3F2FD', text: '#1565C0' },
  { bg: '#FFF8E1', text: '#F57F17' },
]

const URGENCY_COLORS = {
  discovery: '#5C6BC0',
  preparation: '#FF6B00',
  urgent: '#E53935',
  emergency: '#B71C1C',
} as const

function formatInr(value: number) {
  return value.toLocaleString('en-IN')
}

function truncate(text: string, max: number) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text
}

export default function HomeScreen() {
  const router = useRouter()
  const [search, setSearch] = useState('')
  const [goal, setGoal] = useState('')
  const [isApproving, setIsApproving] = useState(false)
  const [reorderItems, setReorderItems] =
    useState<ReorderItem[]>(fallbackReorderItems)
  const [occasions, setOccasions] = useState<OccasionCard[]>(FALLBACK_OCCASIONS)
  const [upcomingRecurrence, setUpcomingRecurrence] =
    useState<UpcomingRecurrence | null>(null)
  const [isRecurrenceDismissed, setIsRecurrenceDismissed] = useState(false)

  useEffect(() => {
    occasionAPI
      .getFeed('U001')
      .then((feed) => {
        if (Array.isArray(feed) && feed.length > 0) {
          setOccasions(feed)
        }
      })
      .catch(() => {
        // Keep fallback occasions
      })

    reorderAPI
      .getDraft()
      .then((res) => {
        const draft = res.data?.data || res.data
        const items: unknown[] = draft?.items ?? []
        if (Array.isArray(items) && items.length > 0) {
          setReorderItems(
            items.map((raw: unknown) => {
              const item = raw as Record<string, unknown>
              const qty =
                typeof item.user_quantity === 'number'
                  ? item.user_quantity
                  : typeof item.suggested_quantity === 'number'
                    ? item.suggested_quantity
                    : 1
              return {
                item_id: typeof item.item_id === 'string' ? item.item_id : undefined,
                asin: typeof item.asin === 'string' ? item.asin : undefined,
                item_name:
                  typeof item.title === 'string'
                    ? item.title
                    : typeof item.item_name === 'string'
                      ? item.item_name
                      : 'Item',
                quantity: qty,
                unit: typeof item.unit === 'string' ? item.unit : qty === 1 ? 'pack' : 'packs',
                price_inr:
                  typeof item.total_cost === 'number'
                    ? item.total_cost
                    : typeof item.price_per_unit === 'number'
                      ? item.price_per_unit * qty
                      : 0,
                amazon_now_eligible: item.amazon_now_eligible !== false,
                urgency_copy:
                  typeof item.urgency_copy === 'string' ? item.urgency_copy : undefined,
              } satisfies ReorderItem
            }),
          )
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

  const handleApprove = async () => {
    if (isApproving) {
      return
    }

    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy).catch(() => {
      // Haptics are unavailable on some browser and simulator environments.
    })
    setIsApproving(true)

    try {
      const draftResponse = await reorderAPI.getDraft()
      const draft = draftResponse.data?.data || draftResponse.data
      const orderResponse = await reorderAPI.approve(
        draft.draft_id,
        Date.now().toString(),
        draft.items || [],
      )
      const order = orderResponse.data?.data || orderResponse.data

      useReorderStore.getState().setDraft(draft)
      useReorderStore.getState().setOrder(order)
      router.push({
        pathname: '/reorder/placing',
        params: { order_data: JSON.stringify(order) },
      })
    } catch {
      router.push('/reorder/draft')
    } finally {
      setIsApproving(false)
    }
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

        {/* SECTION 1.2 — SWIPEABLE SEARCH / MISSION BAR */}
        <View style={styles.discoverySection}>
          <SwipeableSearchBar
            search={search}
            onSearchChange={setSearch}
            goal={goal}
            onGoalChange={setGoal}
            onBuildCart={handleBuildCart}
            onSearchFocus={() => router.push('/search')}
          />

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

        {/* SECTION 1.4 — CONCEPT CARD */}
        <Pressable
          onPress={() => router.push('/(tabs)/missions')}
          style={styles.conceptCard}
          accessibilityRole="button"
          accessibilityLabel="Describe your goal and get the cart"
        >
          <Text style={styles.conceptLabel}>⚡ amazon now · MissionCart</Text>
          <Text style={styles.conceptTagline}>
            {'Delivery is already fast.\nShopping is still slow.'}
          </Text>
          <Text style={styles.conceptCta}>Describe your goal. Get the cart. →</Text>
        </Pressable>

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

          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.reorderScrollContent}
          >
            {reorderItems.slice(0, 5).map((item, index) => {
              const tileColor =
                REORDER_TILE_COLORS[index % REORDER_TILE_COLORS.length]
              return (
                <View
                  key={item.id || item.asin || item.item_name}
                  style={styles.productCard}
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
                  <Text style={styles.productName} numberOfLines={2}>
                    {item.item_name}
                  </Text>
                  <Text style={styles.productQuantity}>
                    {item.quantity} {item.unit}
                  </Text>
                  <Text style={styles.productPrice}>₹{item.price_inr}</Text>
                  {item.urgency_copy ? (
                    <Text
                      style={[
                        styles.urgencyLabel,
                        {
                          color:
                            item.urgency_copy.toLowerCase().includes('urgent') ||
                            item.urgency_copy.toLowerCase().includes('out')
                              ? '#D32F2F'
                              : '#E65100',
                        },
                      ]}
                    >
                      {item.urgency_copy}
                    </Text>
                  ) : null}
                  {item.amazon_now_eligible && (
                    <View style={styles.nowPill}>
                      <Text style={styles.nowPillText}>NOW</Text>
                    </View>
                  )}
                </View>
              )
            })}
          </ScrollView>

          {reorderItems.length > 3 && (
            <Pressable
              onPress={() => router.push('/reorder/draft')}
              style={styles.viewAllReorders}
              accessibilityRole="button"
            >
              <Text style={styles.viewAllReordersText}>
                View all {reorderItems.length} items â†’
              </Text>
            </Pressable>
          )}

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
                onPress={() => router.push('/reorder/draft')}
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

        {/* SECTION 1.9 — REMOVED: Mission input now integrated in search bar */}

        {/* SECTION 1.10 — DIVIDER */}
        <View style={styles.dividerSpaced} />

        {/* SECTION 1.11 — CART AUDIT BANNER */}
        <Pressable
          onPress={() => router.push('/audit-entry')}
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

        {/* QUORUM CARD */}
        <TouchableOpacity
          style={styles.hivesCard}
          onPress={() => router.push('/')}
          activeOpacity={0.8}
        >
          <View style={styles.hivesCardLeft}>
            <Text style={styles.hivesCardLabel}>BIRTHDAY PARTY SQUAD</Text>
            <Text style={styles.hivesCardTitle}>Shop together with QUORUM</Text>
            <Text style={styles.hivesCardSub}>4 members · ₹4,720 cart · Vote on items</Text>
          </View>
          <View style={styles.hivesAvatarStack}>
            {['S', 'R', 'A', 'K'].map((letter, i) => (
              <View
                key={i}
                style={[
                  styles.hivesAvatar,
                  {
                    backgroundColor: ['#FF9900', '#007185', '#007600', '#CC0C39'][i],
                    marginLeft: i > 0 ? -8 : 0,
                    zIndex: 4 - i,
                  },
                ]}
              >
                <Text style={styles.hivesAvatarText}>{letter}</Text>
              </View>
            ))}
          </View>
        </TouchableOpacity>

        {/* SECTION 1.13 — COMING UP SECTION */}
        <View style={styles.comingSection}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Coming up</Text>
            <Pressable accessibilityRole="button" onPress={() => router.navigate('/(tabs)/discover')}>
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
                key={occasion.occasion_type}
                onPress={() =>
                  router.push({
                    pathname: '/cart/building',
                    params: {
                      goal: occasion.tap_goal,
                      budget: String(occasion.estimated_budget),
                      headcount: String(occasion.headcount),
                      occasion_type: occasion.occasion_type,
                    },
                  })
                }
                style={[
                  styles.occasionCard,
                  { borderLeftColor: URGENCY_COLORS[occasion.urgency_state] },
                ]}
                accessibilityRole="button"
              >
                <Text style={styles.occasionEmoji}>{occasion.emoji}</Text>
                <Text style={styles.occasionTitle} numberOfLines={2}>
                  {occasion.title}
                </Text>
                <View
                  style={[
                    styles.urgencyPill,
                    { backgroundColor: URGENCY_COLORS[occasion.urgency_state] },
                  ]}
                >
                  <Text style={styles.urgencyPillText}>{occasion.urgency_label}</Text>
                </View>
                <Text style={styles.occasionBudget}>
                  ~₹{formatInr(occasion.estimated_budget)}
                </Text>
                <Text style={styles.occasionSignal} numberOfLines={2}>
                  {occasion.community_signal}
                </Text>
                <TouchableOpacity
                  style={styles.startCartBtn}
                  onPress={() =>
                    router.push({
                      pathname: '/cart/building',
                      params: {
                        goal: occasion.tap_goal,
                        budget: String(occasion.estimated_budget),
                        headcount: String(occasion.headcount),
                        occasion_type: occasion.occasion_type,
                      },
                    })
                  }
                  activeOpacity={0.85}
                >
                  <Text style={styles.startCartBtnText}>
                    {occasion.urgency_state === 'emergency' ? 'Order Now · 20 min' : 'Start Cart'}
                  </Text>
                </TouchableOpacity>
              </Pressable>
            ))}
          </ScrollView>
        </View>

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
  // Concept card
  conceptCard: {
    marginHorizontal: 16,
    marginTop: 8,
    marginBottom: 4,
    backgroundColor: '#1A3A5C',
    borderRadius: 8,
    padding: 16,
  },
  conceptLabel: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  conceptTagline: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '700',
    lineHeight: 22,
    marginTop: 6,
  },
  conceptCta: {
    color: '#FF9900',
    fontSize: 13,
    fontWeight: '600',
    marginTop: 8,
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
  reorderScrollContent: {
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  productCard: {
    width: 110,
    marginRight: 10,
    alignItems: 'center',
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 8,
    padding: 10,
  },
  letterTile: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
    marginBottom: 6,
  },
  letterTileText: {
    fontSize: 18,
    fontWeight: '700',
  },
  productName: {
    color: Colors.textPrimary,
    fontSize: 11,
    lineHeight: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
  productQuantity: {
    marginTop: 2,
    color: Colors.textSecondary,
    fontSize: 10,
    lineHeight: 13,
  },
  productPrice: {
    marginTop: 4,
    color: Colors.textPrimary,
    fontSize: 13,
    lineHeight: 16,
    fontWeight: '700',
  },
  urgencyLabel: {
    fontSize: 11,
    fontWeight: '600',
    marginTop: 2,
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
  viewAllReorders: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: Colors.divider,
  },
  viewAllReordersText: {
    color: Colors.linkBlue,
    fontSize: 13,
    fontWeight: '600',
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
  occasionEmoji: {
    fontSize: 20,
    lineHeight: 24,
    marginBottom: 4,
  },
  urgencyPill: {
    alignSelf: 'flex-start',
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
    marginTop: 4,
    marginBottom: 4,
  },
  urgencyPillText: {
    color: Colors.white,
    fontSize: 10,
    fontWeight: '700',
    lineHeight: 14,
  },
  occasionSignal: {
    marginTop: 4,
    color: Colors.textSecondary,
    fontSize: 11,
    lineHeight: 15,
  },
  startCartBtn: {
    marginTop: 8,
    backgroundColor: Colors.primary,
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  startCartBtnText: {
    color: Colors.white,
    fontSize: 13,
    fontWeight: '600',
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
  // Hives card
  hivesCard: {
    margin: 16,
    marginBottom: 8,
    backgroundColor: '#1A3A5C',
    borderRadius: 8,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
  },
  hivesCardLeft: { flex: 1 },
  hivesCardLabel: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  hivesCardTitle: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
    marginTop: 4,
  },
  hivesCardSub: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 12,
    marginTop: 4,
  },
  hivesAvatarStack: {
    flexDirection: 'row',
    marginLeft: 12,
  },
  hivesAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: '#1A3A5C',
  },
  hivesAvatarText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '700',
  },
})
