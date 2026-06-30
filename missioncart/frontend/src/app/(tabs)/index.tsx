import { Ionicons } from '@expo/vector-icons'
import * as Haptics from 'expo-haptics'
import { useRouter } from 'expo-router'
import { useCallback, useEffect, useState } from 'react'
import {
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { SwipeableSearchBar } from '../../components/SwipeableSearchBar'
import { demoAPI, reorderAPI } from '../../lib/api'
import { Colors } from '../../lib/constants'
import { scheduleTestNotification } from '../../lib/notifications'
import type { OccasionCard, UpcomingRecurrence } from '../../lib/types'
import { ALL_PERSONAS, usePersonaStore } from '../../store/persona'
import { useReorderStore } from '../../store/reorder'

type IoniconName = keyof typeof Ionicons.glyphMap

interface Category {
  id: string
  label: string
  icon: IoniconName
  color: string
  bgColor: string
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
}

const categories: Category[] = [
  { id: 'beverages', label: 'Beverages', icon: 'wine', color: '#D32F2F', bgColor: '#FFEBEE' },
  { id: 'snacks', label: 'Snacks', icon: 'fast-food', color: '#F57C00', bgColor: '#FFF3E0' },
  { id: 'ice-cream', label: 'Ice cream', icon: 'ice-cream', color: '#E91E63', bgColor: '#FCE4EC' },
  { id: 'bath-body', label: 'Bath & body', icon: 'sparkles', color: '#9C27B0', bgColor: '#F3E5F5' },
  { id: 'cleaners', label: 'Cleaners', icon: 'water', color: '#1976D2', bgColor: '#E3F2FD' },
  { id: 'grocery', label: 'Grocery', icon: 'basket', color: '#388E3C', bgColor: '#E8F5E9' },
  { id: 'party', label: 'Party', icon: 'balloon', color: '#7B1FA2', bgColor: '#EDE7F6' },
  { id: 'health', label: 'Health', icon: 'medkit', color: '#00796B', bgColor: '#E0F7FA' },
  { id: 'baby', label: 'Baby', icon: 'happy', color: '#FF8F00', bgColor: '#FFF8E1' },
  { id: 'dairy', label: 'Dairy', icon: 'cafe', color: '#5D4037', bgColor: '#EFEBE9' },
  { id: 'fruits', label: 'Fruits', icon: 'nutrition', color: '#689F38', bgColor: '#F1F8E9' },
  { id: 'meat', label: 'Meat & fish', icon: 'fish', color: '#C62828', bgColor: '#FFCDD2' },
]

// ── PERSONA PRODUCTS (simulated — would come from backend) ─────
interface PersonaProduct {
  id: string
  name: string
  price: number
  buyers: number
  rating: number
}

const PERSONA_PRODUCTS: Record<string, PersonaProduct[]> = {
  fitness: [
    { id: 'f1', name: 'Whey Protein 1kg', price: 1899, buyers: 4200, rating: 4.5 },
    { id: 'f2', name: 'Peanut Butter 1kg', price: 349, buyers: 3100, rating: 4.3 },
    { id: 'f3', name: 'Resistance Bands Set', price: 499, buyers: 2800, rating: 4.4 },
    { id: 'f4', name: 'BCAA Powder 300g', price: 799, buyers: 1900, rating: 4.2 },
    { id: 'f5', name: 'Oats 2kg', price: 289, buyers: 5100, rating: 4.6 },
  ],
  dad: [
    { id: 'd1', name: 'Tool Kit 25pc', price: 1299, buyers: 2300, rating: 4.4 },
    { id: 'd2', name: 'BBQ Grill Portable', price: 2499, buyers: 1800, rating: 4.3 },
    { id: 'd3', name: 'Beard Trimmer', price: 1599, buyers: 3400, rating: 4.5 },
    { id: 'd4', name: 'Multivitamin 60 tabs', price: 449, buyers: 2900, rating: 4.2 },
    { id: 'd5', name: 'Car Phone Mount', price: 599, buyers: 4100, rating: 4.6 },
  ],
  mom: [
    { id: 'm1', name: 'Green Tea 100 bags', price: 349, buyers: 5200, rating: 4.5 },
    { id: 'm2', name: 'Yoga Mat Premium', price: 899, buyers: 3800, rating: 4.4 },
    { id: 'm3', name: 'Organic Honey 500g', price: 399, buyers: 4100, rating: 4.6 },
    { id: 'm4', name: 'Face Serum Vitamin C', price: 549, buyers: 6200, rating: 4.3 },
    { id: 'm5', name: 'Dry Fruits Mix 500g', price: 599, buyers: 3500, rating: 4.5 },
  ],
  swimmer: [
    { id: 's1', name: 'Swim Goggles Anti-fog', price: 699, buyers: 1800, rating: 4.4 },
    { id: 's2', name: 'Quick Dry Towel', price: 499, buyers: 2200, rating: 4.3 },
    { id: 's3', name: 'Waterproof Earbuds', price: 1999, buyers: 1500, rating: 4.2 },
    { id: 's4', name: 'Chlorine Shampoo', price: 349, buyers: 2800, rating: 4.5 },
    { id: 's5', name: 'Swim Cap Silicone', price: 299, buyers: 3100, rating: 4.4 },
  ],
  gamer: [
    { id: 'g1', name: 'Gaming Mouse Pad XL', price: 599, buyers: 4500, rating: 4.5 },
    { id: 'g2', name: 'Energy Drink 12-pack', price: 899, buyers: 3200, rating: 4.1 },
    { id: 'g3', name: 'Blue Light Glasses', price: 799, buyers: 2800, rating: 4.3 },
    { id: 'g4', name: 'Wrist Rest Gel', price: 449, buyers: 2100, rating: 4.4 },
    { id: 'g5', name: 'Snack Box Variety', price: 649, buyers: 3800, rating: 4.2 },
  ],
  cook: [
    { id: 'c1', name: 'Cast Iron Skillet 10"', price: 1299, buyers: 3900, rating: 4.6 },
    { id: 'c2', name: 'Spice Rack 16 jars', price: 899, buyers: 2700, rating: 4.4 },
    { id: 'c3', name: 'Chef Knife Japanese', price: 1899, buyers: 2100, rating: 4.7 },
    { id: 'c4', name: 'Olive Oil Extra Virgin 1L', price: 649, buyers: 4200, rating: 4.5 },
    { id: 'c5', name: 'Silicone Spatula Set', price: 399, buyers: 3400, rating: 4.3 },
  ],
  student: [
    { id: 'st1', name: 'Highlighters 6-pack', price: 149, buyers: 6100, rating: 4.4 },
    { id: 'st2', name: 'Instant Noodles 12pc', price: 240, buyers: 8200, rating: 4.2 },
    { id: 'st3', name: 'Notebook A4 5-pack', price: 299, buyers: 5400, rating: 4.5 },
    { id: 'st4', name: 'USB-C Hub 6-in-1', price: 1299, buyers: 3200, rating: 4.3 },
    { id: 'st5', name: 'Coffee Powder 200g', price: 349, buyers: 4800, rating: 4.4 },
  ],
  runner: [
    { id: 'r1', name: 'Electrolyte Sachets 30pc', price: 499, buyers: 3800, rating: 4.5 },
    { id: 'r2', name: 'Running Socks 3-pair', price: 599, buyers: 2900, rating: 4.4 },
    { id: 'r3', name: 'Energy Gels 12-pack', price: 899, buyers: 2100, rating: 4.3 },
    { id: 'r4', name: 'Foam Roller', price: 799, buyers: 3400, rating: 4.6 },
    { id: 'r5', name: 'Arm Band Phone Holder', price: 399, buyers: 4200, rating: 4.2 },
  ],
  yogi: [
    { id: 'y1', name: 'Yoga Block Cork', price: 599, buyers: 2800, rating: 4.5 },
    { id: 'y2', name: 'Incense Sticks 100pc', price: 199, buyers: 5100, rating: 4.4 },
    { id: 'y3', name: 'Meditation Cushion', price: 1299, buyers: 1800, rating: 4.6 },
    { id: 'y4', name: 'Herbal Tea Sampler', price: 449, buyers: 3200, rating: 4.3 },
    { id: 'y5', name: 'Essential Oil Set', price: 799, buyers: 2600, rating: 4.5 },
  ],
  'pet-parent': [
    { id: 'p1', name: 'Dog Treats Chicken 500g', price: 349, buyers: 4800, rating: 4.5 },
    { id: 'p2', name: 'Lint Roller 5-pack', price: 299, buyers: 3600, rating: 4.3 },
    { id: 'p3', name: 'Pet Shampoo 500ml', price: 449, buyers: 3100, rating: 4.4 },
    { id: 'p4', name: 'Chew Toy Durable', price: 399, buyers: 2900, rating: 4.2 },
    { id: 'p5', name: 'Poop Bags 300pc', price: 249, buyers: 5200, rating: 4.6 },
  ],
}

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
  const [search, setSearch] = useState('')
  const [goal, setGoal] = useState('')
  const [isApproving, setIsApproving] = useState(false)
  const [reorderItems, setReorderItems] =
    useState<ReorderItem[]>(fallbackReorderItems)
  const [occasions, setOccasions] = useState<FallbackOccasion[]>(fallbackOccasions)
  // Persona state (from shared store)
  const { selectedPersonas } = usePersonaStore()
  const [activePersona, setActivePersona] = useState<string | null>(null)
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

    reorderAPI
      .getAlerts()
      .then((res) => {
        const alerts = res.data?.data || res.data || []
        if (Array.isArray(alerts) && alerts.length > 0) {
          setReorderItems(
            alerts.map((alert: any) => {
              const quantity =
                alert.suggested_quantity || alert.quantity || 1
              return {
                ...alert,
                item_id: alert.item_id || alert.asin,
                item_name: alert.item_name || alert.title,
                quantity,
                unit: alert.unit || (quantity === 1 ? 'pack' : 'packs'),
                price_inr:
                  alert.price_inr ??
                  alert.total_cost ??
                  (alert.price || 0) * quantity,
                amazon_now_eligible: alert.amazon_now_eligible !== false,
              }
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

  const handlePersonaPress = useCallback((personaId: string) => {
    setActivePersona((prev) => (prev === personaId ? null : personaId))
  }, [])

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
            {/* Left: Profile + Amazon Pay Balance */}
            <View style={styles.headerLeftGroup}>
              <Pressable style={styles.headerIconButton} accessibilityRole="button">
                <Ionicons name="person-circle" size={30} color={Colors.white} />
              </Pressable>
              <View style={styles.payBalanceBadge}>
                <Ionicons name="wallet-outline" size={12} color={Colors.white} />
                <Text style={styles.payBalanceText}>₹155</Text>
              </View>
            </View>

            {/* Center: Amazon Now Logo */}
            <Image
              source={require('../../../assets/amazon-now-logo.png')}
              style={styles.logoImage}
              resizeMode="contain"
            />

            {/* Right: Cart icon */}
            <Pressable style={styles.headerIconButton} accessibilityRole="button">
              <Ionicons name="close" size={24} color={Colors.white} />
            </Pressable>
          </View>
        </View>

        {/* Delivery address row — below header on white bg */}
        <Pressable style={styles.deliveryRow} accessibilityRole="button">
          <Ionicons name="location-sharp" size={18} color={Colors.primary} />
          <Text style={styles.deliveryLabel}>Delivering to </Text>
          <Text style={styles.deliveryAddress} numberOfLines={1}>
            jai ambey co live, Doddakannelli Road, Sande...
          </Text>
          <Ionicons name="chevron-down" size={16} color={Colors.textPrimary} />
        </Pressable>

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
                <View style={[styles.categoryIconCircle, { backgroundColor: category.bgColor }]}>
                  <Ionicons
                    name={category.icon}
                    size={24}
                    color={category.color}
                  />
                </View>
                <Text style={styles.categoryLabel} numberOfLines={1}>
                  {category.label}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>

        {/* SECTION 1.4 — PROMOTIONAL BANNER */}
        <Pressable
          onPress={() => router.push('/search')}
          style={styles.banner}
          accessibilityRole="button"
          accessibilityLabel="Browse all products"
        >
          <Image
            source={require('../../../assets/banner-snack-store.png')}
            style={styles.bannerImage}
            resizeMode="cover"
          />
        </Pressable>

        {/* SECTION 1.5 — PERSONA CIRCLES (all personas shown, detected ones highlighted) */}
        <View style={styles.identitySection}>
          <Text style={styles.identitySectionTitle}>Shop by persona</Text>
          <Text style={styles.identitySectionSubtitle}>
            Based on your buying history
          </Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.identityRow}
          >
            {ALL_PERSONAS.map((persona) => {
              const isDetected = selectedPersonas.includes(persona.id)
              const isActive = activePersona === persona.id
              return (
                <Pressable
                  key={persona.id}
                  onPress={() => handlePersonaPress(persona.id)}
                  style={styles.identityItem}
                  accessibilityRole="button"
                  accessibilityLabel={persona.label}
                >
                  <View
                    style={[
                      styles.identityCircle,
                      { backgroundColor: persona.color },
                      isActive && styles.identityCircleActive,
                      !isDetected && styles.identityCircleUndetected,
                    ]}
                  >
                    <Text style={styles.identityEmoji}>{persona.emoji}</Text>
                    {isDetected && (
                      <View style={styles.detectedBadge}>
                        <Ionicons name="checkmark-circle" size={14} color="#2E7D32" />
                      </View>
                    )}
                  </View>
                  <Text
                    style={[
                      styles.identityLabel,
                      isActive && styles.identityLabelActive,
                      isDetected && styles.identityLabelDetected,
                    ]}
                    numberOfLines={1}
                  >
                    {persona.label}
                  </Text>
                </Pressable>
              )
            })}
          </ScrollView>
        </View>

        {/* SECTION 1.5b — PERSONA PRODUCTS (shown when a persona is active) */}
        {activePersona && (
          <View style={styles.identityProductsSection}>
            <View style={styles.identityProductsBanner}>
              <Ionicons name="shield-checkmark" size={16} color={Colors.white} />
              <Text style={styles.identityProductsBannerText}>
                No sponsored products, just what shoppers love and trust
              </Text>
            </View>
            <Text style={styles.identityProductsTitle}>
              Popular with{' '}
              {ALL_PERSONAS.find((p) => p.id === activePersona)?.label} shoppers
            </Text>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.identityProductsList}
            >
              {(PERSONA_PRODUCTS[activePersona] || []).map((product) => (
                <View key={product.id} style={styles.identityProductCard}>
                  <View style={styles.identityProductRatingRow}>
                    <Ionicons name="star" size={11} color="#FF9900" />
                    <Text style={styles.identityProductRating}>
                      {product.rating}
                    </Text>
                  </View>
                  <Text style={styles.identityProductName} numberOfLines={2}>
                    {product.name}
                  </Text>
                  <Text style={styles.identityProductPrice}>
                    ₹{product.price.toLocaleString('en-IN')}
                  </Text>
                  <Text style={styles.identityProductBuyers}>
                    {product.buyers.toLocaleString('en-IN')}+ bought
                  </Text>
                </View>
              ))}
            </ScrollView>
          </View>
        )}

        {/* SECTION 1.6 — DIVIDER */}
        <View style={styles.divider} />

        {/* SECTION 1.7 — MORNING APPROVAL CARD */}
        <View style={styles.reorderCard}>
          <View style={styles.reorderTopBar}>
            <Text style={styles.reorderTopTitle}>Your daily reorder</Text>
            <View style={styles.reorderReady}>
              <Ionicons name="time-outline" size={16} color={Colors.textSecondary} />
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

        {/* HIVES CARD */}
        <TouchableOpacity
          style={styles.hivesCard}
          onPress={() => router.push('/hive')}
          activeOpacity={0.8}
        >
          <View style={styles.hivesCardLeft}>
            <Text style={styles.hivesCardLabel}>BIRTHDAY PARTY SQUAD</Text>
            <Text style={styles.hivesCardTitle}>Shop together with Hives</Text>
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
                style={[styles.occasionCard, { borderLeftColor: '#FF9900' }]}
                accessibilityRole="button"
              >
                <Text style={styles.occasionEmoji}>{occasion.emoji}</Text>
                <Text style={styles.occasionTitle} numberOfLines={2}>
                  {occasion.title}
                </Text>
                {occasion.days_until != null && (
                  <Text style={styles.occasionDays}>In {occasion.days_until} days</Text>
                )}
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
          <Ionicons
            name="notifications-outline"
            size={14}
            color="#F57F17"
          />
          <Text style={styles.testNotifText}>
            Test morning notification (5s)
          </Text>
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
    backgroundColor: '#232F3E',
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
    backgroundColor: '#232F3E',
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
  headerLeftGroup: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  payBalanceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 12,
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginLeft: 4,
  },
  payBalanceText: {
    color: Colors.white,
    fontSize: 11,
    fontWeight: '700',
    marginLeft: 3,
  },
  logo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  logoImage: {
    width: 220,
    height: 48,
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
  nowLogoTextGreen: {
    color: '#00E676',
    fontSize: 22,
    lineHeight: 26,
    fontWeight: '700',
    letterSpacing: -0.5,
  },
  deliveryRow: {
    alignSelf: 'stretch',
    marginTop: 0,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: '#EAF2F8',
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  deliveryLabel: {
    color: Colors.textPrimary,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '700',
    marginLeft: 6,
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
    flex: 1,
    color: Colors.textPrimary,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '400',
  },
  discoverySection: {
    paddingTop: 12,
    paddingBottom: 8,
    backgroundColor: Colors.background,
  },
  categoryList: {
    paddingHorizontal: 8,
    paddingTop: 12,
  },
  categoryItem: {
    width: 68,
    alignItems: 'center',
    marginHorizontal: 2,
  },
  categoryIconCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  categoryLabel: {
    marginTop: 6,
    color: Colors.textPrimary,
    fontSize: 11,
    lineHeight: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
  // Banner
  banner: {
    marginHorizontal: 16,
    marginTop: 12,
    borderRadius: 8,
    overflow: 'hidden',
  },
  bannerImage: {
    width: '100%',
    height: 130,
    borderRadius: 8,
  },
  // Identity circles
  identitySection: {
    paddingTop: 10,
    paddingBottom: 6,
  },
  identitySectionTitle: {
    paddingHorizontal: 16,
    fontSize: 13,
    fontWeight: '700',
    color: Colors.textPrimary,
    marginBottom: 2,
  },
  identitySectionSubtitle: {
    paddingHorizontal: 16,
    fontSize: 11,
    color: Colors.textSecondary,
    marginBottom: 8,
  },
  identityRow: {
    paddingHorizontal: 12,
  },
  identityItem: {
    alignItems: 'center',
    marginHorizontal: 6,
    width: 60,
  },
  identityCircle: {
    width: 50,
    height: 50,
    borderRadius: 25,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  identityCircleActive: {
    borderColor: '#FF9900',
  },
  identityCircleUndetected: {
    opacity: 0.5,
  },
  detectedBadge: {
    position: 'absolute',
    bottom: -2,
    right: -2,
    backgroundColor: Colors.white,
    borderRadius: 8,
  },
  identityEmoji: {
    fontSize: 22,
  },
  identityLabel: {
    marginTop: 4,
    fontSize: 10,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
  identityLabelActive: {
    color: '#FF9900',
    fontWeight: '700',
  },
  identityLabelDetected: {
    color: Colors.textPrimary,
    fontWeight: '600',
  },
  // Identity products
  identityProductsSection: {
    paddingBottom: 8,
  },
  identityProductsBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2E7D32',
    paddingHorizontal: 16,
    paddingVertical: 8,
    gap: 8,
  },
  identityProductsBannerText: {
    color: Colors.white,
    fontSize: 12,
    fontWeight: '600',
    flex: 1,
  },
  identityProductsTitle: {
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 8,
    fontSize: 14,
    fontWeight: '700',
    color: Colors.textPrimary,
  },
  identityProductsList: {
    paddingHorizontal: 12,
  },
  identityProductCard: {
    width: 130,
    marginHorizontal: 4,
    padding: 10,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 8,
  },
  identityProductRatingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    marginBottom: 6,
  },
  identityProductRating: {
    fontSize: 11,
    color: Colors.textSecondary,
    fontWeight: '600',
  },
  identityProductName: {
    fontSize: 12,
    lineHeight: 16,
    color: Colors.textPrimary,
    fontWeight: '600',
    minHeight: 32,
  },
  identityProductPrice: {
    marginTop: 6,
    fontSize: 14,
    fontWeight: '700',
    color: Colors.textPrimary,
  },
  identityProductBuyers: {
    marginTop: 2,
    fontSize: 10,
    color: Colors.successGreen,
    fontWeight: '600',
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
    backgroundColor: Colors.background,
  },
  reorderTopTitle: {
    color: '#000000',
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
    color: Colors.textSecondary,
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
    backgroundColor: Colors.nowBlue,
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
  occasionEmoji: {
    fontSize: 20,
    lineHeight: 24,
    marginBottom: 4,
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
    marginHorizontal: 16,
    marginTop: 4,
    marginBottom: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF8E1',
    borderWidth: 1,
    borderColor: '#FFD814',
    borderRadius: 4,
  },
  testNotifText: {
    marginLeft: 6,
    color: '#F57F17',
    fontSize: 12,
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
