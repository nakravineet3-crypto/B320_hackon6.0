import { Ionicons } from '@expo/vector-icons'
import * as Haptics from 'expo-haptics'
import { useRouter } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useEffect, useRef, useState } from 'react'
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import Animated, {
  cancelAnimation,
  FadeInDown,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated'
import { SafeAreaView } from 'react-native-safe-area-context'

import { api } from '../lib/api'
import { Colors, getLabelColor } from '../lib/constants'

type FlagSeverity = 'red' | 'amber' | 'blue'

interface CartProduct {
  id: string
  name: string
  quantity: number
  price: number
  sponsored?: boolean
}

interface AuditFlagDemo {
  id: string
  severity: FlagSeverity
  message: string
  ms: number
}

const CART_PRODUCTS: CartProduct[] = [
  { id: 'plates', name: 'Paper Plates 10pc', quantity: 1, price: 120 },
  { id: 'balloons', name: 'Balloon Set 20pc', quantity: 1, price: 180 },
  { id: 'streamers', name: 'Streamers 5pc', quantity: 2, price: 180 },
  {
    id: 'cups',
    name: 'Party Cups 10pc',
    quantity: 2,
    price: 190,
    sponsored: true,
  },
]

const FLAGS: AuditFlagDemo[] = [
  {
    id: 'f1',
    severity: 'red',
    message: '12 plates — you need 24',
    ms: 1500,
  },
  {
    id: 'f2',
    severity: 'red',
    message: 'Balloon set — no pump included',
    ms: 3000,
  },
  {
    id: 'f3',
    severity: 'amber',
    message: 'Streamers not on Amazon Now — swapping',
    ms: 4500,
  },
  {
    id: 'f4',
    severity: 'blue',
    message: 'Sponsored cups blocked — failed child_safe check',
    ms: 6000,
  },
]

const AUDIT_PAYLOAD = {
  goal: 'Birthday party for 12 kids tomorrow evening under 4000',
  existing_cart: [
    {
      asin: 'DEMO_PLATES_01',
      title: 'Paper Plates 10pc',
      price: 120,
      quantity: 1,
      category: 'plates',
      pack_size: 10,
      prime: true,
      amazon_now_eligible: true,
      delivery_eta: 'now_20min',
      rating: 4.1,
      return_risk: 0.05,
      safety_tags: ['child_safe', 'food_grade'],
      sponsored: false,
    },
    {
      asin: 'DEMO_BALLOONS_01',
      title: 'Balloon Set 20pc',
      price: 180,
      quantity: 1,
      category: 'balloon_set',
      pack_size: 20,
      prime: true,
      amazon_now_eligible: true,
      delivery_eta: 'now_20min',
      rating: 4.3,
      return_risk: 0.08,
      safety_tags: ['child_safe'],
      sponsored: false,
    },
    {
      asin: 'DEMO_STREAMERS_01',
      title: 'Streamers 5pc',
      price: 90,
      quantity: 2,
      category: 'decoration_streamers',
      pack_size: 5,
      prime: false,
      amazon_now_eligible: false,
      delivery_eta: '2_days',
      rating: 4,
      return_risk: 0.1,
      safety_tags: ['child_safe'],
      sponsored: false,
    },
    {
      asin: 'DEMO_CUPS_SPONSORED',
      title: 'Party Cups 10pc',
      price: 95,
      quantity: 2,
      category: 'disposable_cups',
      pack_size: 10,
      prime: true,
      amazon_now_eligible: true,
      delivery_eta: 'now_20min',
      rating: 3.8,
      return_risk: 0.06,
      safety_tags: [],
      sponsored: true,
    },
  ],
}

function PulseIndicator() {
  const dotOne = useSharedValue(0.25)
  const dotTwo = useSharedValue(0.25)
  const dotThree = useSharedValue(0.25)

  useEffect(() => {
    const pulse = () =>
      withRepeat(
        withSequence(
          withTiming(1, { duration: 280 }),
          withTiming(0.25, { duration: 280 }),
          withTiming(0.25, { duration: 280 }),
        ),
        -1,
      )

    dotOne.value = pulse()
    dotTwo.value = withDelay(180, pulse())
    dotThree.value = withDelay(360, pulse())

    return () => {
      cancelAnimation(dotOne)
      cancelAnimation(dotTwo)
      cancelAnimation(dotThree)
    }
  }, [dotOne, dotThree, dotTwo])

  const dotOneStyle = useAnimatedStyle(() => ({
    opacity: dotOne.value,
    transform: [{ scale: 0.8 + dotOne.value * 0.2 }],
  }))
  const dotTwoStyle = useAnimatedStyle(() => ({
    opacity: dotTwo.value,
    transform: [{ scale: 0.8 + dotTwo.value * 0.2 }],
  }))
  const dotThreeStyle = useAnimatedStyle(() => ({
    opacity: dotThree.value,
    transform: [{ scale: 0.8 + dotThree.value * 0.2 }],
  }))

  return (
    <View style={styles.pulseDots}>
      <Animated.View style={[styles.pulseDot, dotOneStyle]} />
      <Animated.View style={[styles.pulseDot, dotTwoStyle]} />
      <Animated.View style={[styles.pulseDot, dotThreeStyle]} />
    </View>
  )
}

const MATH_EXPLANATIONS: Record<string, string> = {
  f1: '2 plates per child × 12 kids = 24 plates. You have 1 pack of 12. Need 2 packs.',
  f2: 'This balloon set requires a pump to inflate. No pump found in cart.',
  f3: 'Streamers arrive in 2 days. Party is tomorrow (18hrs). Swapped to Now-eligible.',
  f4: 'Sponsored product — no child_safe certification. Blocked per MissionCart policy.',
}

const FLAG_CONFIG: Record<
  FlagSeverity,
  { bar: string; icon: keyof typeof Ionicons.glyphMap; label: string }
> = {
  red: { bar: Colors.errorRed, icon: 'warning-outline', label: 'ISSUE' },
  amber: { bar: Colors.primary, icon: 'swap-horizontal-outline', label: 'SWAPPING' },
  blue: {
    bar: Colors.linkBlue,
    icon: 'shield-checkmark-outline',
    label: 'SPONSORED BLOCKED',
  },
}

function FlagRow({
  flag,
  isExpanded,
  onToggle,
}: {
  flag: AuditFlagDemo
  isExpanded: boolean
  onToggle: () => void
}) {
  const cfg = FLAG_CONFIG[flag.severity]

  return (
    <TouchableOpacity onPress={onToggle} activeOpacity={0.8}>
      <Animated.View entering={FadeInDown.duration(400)} style={styles.flagRow}>
        <View style={[styles.flagBar, { backgroundColor: cfg.bar }]} />
        <Ionicons
          name={cfg.icon}
          size={18}
          color={cfg.bar}
          style={styles.flagIcon}
        />
        <View style={styles.flagContent}>
          <Text style={[styles.flagLabel, { color: cfg.bar }]}>{cfg.label}</Text>
          <Text style={styles.flagMessage}>{flag.message}</Text>
          {isExpanded && MATH_EXPLANATIONS[flag.id] && (
            <View style={styles.mathContainer}>
              <Text style={styles.mathText}>{MATH_EXPLANATIONS[flag.id]}</Text>
            </View>
          )}
        </View>
        {flag.severity === 'blue' && (
          <Ionicons
            name="checkmark-circle"
            size={20}
            color={Colors.linkBlue}
            style={styles.flagRightIcon}
          />
        )}
      </Animated.View>
    </TouchableOpacity>
  )
}

export default function AuditScreen() {
  const router = useRouter()
  const scrollRef = useRef<ScrollView>(null)
  const [visibleFlagCount, setVisibleFlagCount] = useState(0)
  const [isChecking, setIsChecking] = useState(true)
  const [showRepair, setShowRepair] = useState(false)
  const [showPrice, setShowPrice] = useState(false)
  const [showCoverage, setShowCoverage] = useState(false)
  const [showCta, setShowCta] = useState(false)
  const [orderPlaced, setOrderPlaced] = useState(false)
  const [expandedFlag, setExpandedFlag] = useState<string | null>(null)
  const progress = useSharedValue(0)

  const progressStyle = useAnimatedStyle(() => ({
    width: `${progress.value * 100}%`,
  }))

  useEffect(() => {
    void api.post('/api/mission/audit', AUDIT_PAYLOAD).catch(() => {
      // The deterministic demo sequence continues without the API response.
    })

    const timers: Array<ReturnType<typeof setTimeout>> = FLAGS.map(
      (flag, index) =>
        setTimeout(() => setVisibleFlagCount(index + 1), flag.ms),
    )

    timers.push(
      setTimeout(() => {
        setIsChecking(false)
        setShowRepair(true)
        progress.value = withTiming(1, { duration: 1500 })
      }, 6500),
      setTimeout(() => setShowPrice(true), 8000),
      setTimeout(() => setShowCoverage(true), 8200),
      setTimeout(() => setShowCta(true), 8400),
    )

    return () => timers.forEach(clearTimeout)
  }, [progress])

  useEffect(() => {
    if (visibleFlagCount === 0 && !showRepair) {
      return
    }

    const timer = setTimeout(
      () => scrollRef.current?.scrollToEnd({ animated: true }),
      showCta ? 450 : 100,
    )
    return () => clearTimeout(timer)
  }, [showCoverage, showCta, showPrice, showRepair, visibleFlagCount])

  const handleOrder = () => {
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy).catch(() => {
      // Haptics are unavailable on some browser and simulator environments.
    })
    setOrderPlaced(true)
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar style="light" backgroundColor={Colors.nowBlue} />

      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          style={styles.backButton}
          hitSlop={10}
          accessibilityRole="button"
          accessibilityLabel="Go back"
        >
          <Ionicons name="arrow-back" size={24} color={Colors.white} />
        </Pressable>
        <View style={styles.headerCopy}>
          <Text style={styles.headerTitle}>Cart Audit</Text>
          <Text style={styles.headerSubtitle}>Sneha's Birthday Party</Text>
        </View>
      </View>

      <ScrollView
        ref={scrollRef}
        style={styles.screen}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* ORIGINAL CART SECTION */}
        <View style={styles.cartSectionHeader}>
          <Text style={styles.cartEyebrow}>YOUR CART</Text>
          <Text style={styles.cartSummary}>4 items · ₹4,340</Text>
        </View>

        {CART_PRODUCTS.map((product) => {
          const palette = getLabelColor(product.name)
          return (
            <View key={product.id} style={styles.cartRow}>
              <View style={[styles.letterTile, { backgroundColor: palette.bg }]}>
                <Text style={[styles.letterTileText, { color: palette.text }]}>
                  {product.name[0].toUpperCase()}
                </Text>
              </View>
              <View style={styles.cartRowCopy}>
                <Text style={styles.productName}>{product.name}</Text>
                <Text style={styles.productQuantity}>Qty: {product.quantity}</Text>
              </View>
              <View style={styles.cartRowRight}>
                <Text style={styles.productPrice}>₹{product.price}</Text>
                {product.sponsored && (
                  <Text style={styles.sponsoredLabel}>Sponsored</Text>
                )}
              </View>
            </View>
          )
        })}

        <View style={styles.totalRow}>
          <Text style={styles.totalText}>Total</Text>
          <Text style={styles.totalValue}>₹4,340</Text>
        </View>

        <View style={styles.sectionDivider} />

        {/* AUDIT RUNNING SECTION */}
        <View style={styles.auditHeader}>
          <Text style={styles.auditTitle}>MissionCart Audit</Text>
          <Text style={styles.poweredRow}>
            Powered by <Text style={styles.bedrockText}>Amazon Bedrock</Text>
          </Text>
        </View>

        {isChecking && (
          <View style={styles.checkingRow}>
            <PulseIndicator />
            <Text style={styles.checkingText}>Checking your cart...</Text>
          </View>
        )}

        <View style={styles.flagsList}>
          {FLAGS.slice(0, visibleFlagCount).map((flag) => (
            <FlagRow
              key={flag.id}
              flag={flag}
              isExpanded={expandedFlag === flag.id}
              onToggle={() =>
                setExpandedFlag((prev) => (prev === flag.id ? null : flag.id))
              }
            />
          ))}
        </View>

        {showRepair && (
          <Animated.View entering={FadeInDown.duration(400)}>
            <View style={styles.sectionDivider} />

            <Text style={styles.repairTitle}>Repairing your cart</Text>
            <View style={styles.progressTrack}>
              <Animated.View style={[styles.progressFill, progressStyle]} />
            </View>

            {showPrice && (
              <Animated.View entering={FadeInDown.duration(300)}>
                <View style={styles.priceRow}>
                  <Text style={styles.oldPrice}>₹4,340</Text>
                  <Text style={styles.newPrice}>₹3,850</Text>
                </View>
                <View style={styles.savingsPill}>
                  <Text style={styles.savingsText}>You save ₹490</Text>
                </View>
              </Animated.View>
            )}

            {showCoverage && (
              <Animated.View
                entering={FadeInDown.duration(300)}
                style={styles.coverageRow}
              >
                <Ionicons
                  name="checkmark-circle"
                  size={16}
                  color={Colors.successGreen}
                />
                <Text style={styles.coverageStrong}>Coverage: 9/9</Text>
                <Text style={styles.coverageMuted}> · All items on Amazon Now</Text>
              </Animated.View>
            )}

            {showCta && (
              <Animated.View entering={FadeInDown.duration(300)}>
                <Pressable
                  onPress={handleOrder}
                  style={styles.orderButton}
                  accessibilityRole="button"
                >
                  <Text style={styles.orderButtonText}>Order repaired cart</Text>
                </Pressable>
                {orderPlaced && (
                  <Text style={styles.orderPlacedText}>
                    Order placed · Arriving in 12 mins
                  </Text>
                )}
              </Animated.View>
            )}
          </Animated.View>
        )}
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.nowBlue,
  },
  header: {
    minHeight: 64,
    paddingHorizontal: 12,
    paddingVertical: 8,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.nowBlue,
  },
  backButton: {
    width: 40,
    height: 40,
    marginRight: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerCopy: {
    flex: 1,
  },
  headerTitle: {
    color: Colors.white,
    fontSize: 18,
    lineHeight: 23,
    fontWeight: '700',
  },
  headerSubtitle: {
    marginTop: 1,
    color: Colors.white,
    fontSize: 12,
    lineHeight: 16,
  },
  screen: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  content: {
    paddingBottom: 32,
  },
  // Cart section
  cartSectionHeader: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: Colors.background,
    borderBottomWidth: 1,
    borderBottomColor: Colors.inputBorder,
  },
  cartEyebrow: {
    color: Colors.textSecondary,
    fontSize: 11,
    lineHeight: 14,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  cartSummary: {
    color: Colors.textSecondary,
    fontSize: 11,
    lineHeight: 14,
  },
  cartRow: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
    flexDirection: 'row',
    alignItems: 'center',
  },
  letterTile: {
    width: 44,
    height: 44,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  letterTileText: {
    fontSize: 18,
    fontWeight: '700',
  },
  cartRowCopy: {
    flex: 1,
    marginLeft: 12,
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
  cartRowRight: {
    alignItems: 'flex-end',
    marginLeft: 8,
  },
  productPrice: {
    color: Colors.textPrimary,
    fontSize: 14,
    lineHeight: 18,
    fontWeight: '700',
  },
  sponsoredLabel: {
    marginTop: 2,
    color: Colors.textSecondary,
    fontSize: 10,
  },
  totalRow: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderTopWidth: 2,
    borderTopColor: Colors.inputBorder,
  },
  totalText: {
    color: Colors.textPrimary,
    fontSize: 14,
    lineHeight: 18,
    fontWeight: '700',
  },
  totalValue: {
    color: Colors.textPrimary,
    fontSize: 16,
    lineHeight: 21,
    fontWeight: '700',
  },
  sectionDivider: {
    width: '100%',
    height: 8,
    backgroundColor: Colors.divider,
  },
  // Audit running
  auditHeader: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
  },
  auditTitle: {
    color: Colors.textPrimary,
    fontSize: 16,
    lineHeight: 21,
    fontWeight: '700',
  },
  poweredRow: {
    marginTop: 2,
    color: Colors.textSecondary,
    fontSize: 11,
    lineHeight: 15,
  },
  bedrockText: {
    color: Colors.primary,
    fontWeight: '600',
  },
  checkingRow: {
    paddingHorizontal: 16,
    marginBottom: 8,
    flexDirection: 'row',
    alignItems: 'center',
  },
  pulseDots: {
    width: 38,
    marginRight: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  pulseDot: {
    width: 8,
    height: 8,
    backgroundColor: Colors.primary,
    borderRadius: 4,
  },
  checkingText: {
    color: Colors.textSecondary,
    fontSize: 13,
    lineHeight: 18,
  },
  flagsList: {
    marginTop: 0,
  },
  // Flag rows
  flagRow: {
    backgroundColor: Colors.background,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
    paddingHorizontal: 16,
    paddingVertical: 14,
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  flagBar: {
    width: 3,
    alignSelf: 'stretch',
    marginRight: 12,
    borderRadius: 2,
  },
  flagIcon: {
    marginRight: 10,
    marginTop: 1,
  },
  flagContent: {
    flex: 1,
  },
  flagLabel: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  flagMessage: {
    marginTop: 2,
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '600',
  },
  flagRightIcon: {
    marginLeft: 8,
  },
  mathContainer: {
    marginTop: 8,
    backgroundColor: Colors.cardBg,
    borderRadius: 4,
    paddingVertical: 8,
    paddingHorizontal: 10,
  },
  mathText: {
    color: Colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
  },
  // Repair
  repairTitle: {
    color: Colors.textPrimary,
    fontSize: 16,
    fontWeight: '700',
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  progressTrack: {
    height: 4,
    marginHorizontal: 16,
    marginTop: 12,
    overflow: 'hidden',
    backgroundColor: '#E7E7E7',
    borderRadius: 2,
  },
  progressFill: {
    height: 4,
    backgroundColor: Colors.primary,
    borderRadius: 2,
  },
  priceRow: {
    marginHorizontal: 16,
    marginTop: 16,
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 12,
  },
  oldPrice: {
    color: Colors.textSecondary,
    fontSize: 18,
    textDecorationLine: 'line-through',
  },
  newPrice: {
    color: Colors.successGreen,
    fontSize: 28,
    fontWeight: '700',
  },
  savingsPill: {
    marginHorizontal: 16,
    marginTop: 4,
    backgroundColor: '#E7F5EA',
    borderRadius: 4,
    paddingHorizontal: 10,
    paddingVertical: 4,
    alignSelf: 'flex-start',
  },
  savingsText: {
    color: Colors.successGreen,
    fontSize: 12,
    fontWeight: '600',
  },
  coverageRow: {
    paddingHorizontal: 16,
    marginTop: 12,
    flexDirection: 'row',
    alignItems: 'center',
  },
  coverageStrong: {
    color: Colors.successGreen,
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
  },
  coverageMuted: {
    color: Colors.textSecondary,
    fontSize: 14,
  },
  orderButton: {
    height: 52,
    margin: 16,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.primary,
    borderRadius: 4,
  },
  orderButtonText: {
    color: Colors.white,
    fontSize: 16,
    fontWeight: '700',
  },
  orderPlacedText: {
    marginTop: -4,
    marginBottom: 12,
    color: Colors.successGreen,
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
})
