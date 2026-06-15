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
  FadeInDown,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated'
import { SafeAreaView } from 'react-native-safe-area-context'

import { Colors } from '../lib/constants'
import { useMissionStore } from '../store/mission'

interface AuditFlag {
  flag_id: string
  severity: string
  message: string
  math_explanation?: string
  product_id?: string
  fix_action?: string
  animate_at_ms?: number
}

export default function AuditResultScreen() {
  const router = useRouter()
  const auditResult = useMissionStore((s) => s.auditResult)
  const scrollRef = useRef<ScrollView>(null)

  const flags: AuditFlag[] = auditResult?.flags || []
  const originalTotal: number = auditResult?.original_total || 0
  const repairedTotal: number = auditResult?.repaired_total || 0
  const coverageScore: string = auditResult?.coverage_score || '0/0'

  const [visibleFlagCount, setVisibleFlagCount] = useState(0)
  const [expandedFlag, setExpandedFlag] = useState<string | null>(null)
  const [showRepair, setShowRepair] = useState(false)
  const [showPrice, setShowPrice] = useState(false)
  const [showCoverage, setShowCoverage] = useState(false)
  const [showCta, setShowCta] = useState(false)
  const [orderPlaced, setOrderPlaced] = useState(false)

  const progress = useSharedValue(0)
  const progressStyle = useAnimatedStyle(() => ({ width: `${progress.value * 100}%` }))

  const allClear = flags.length === 0

  useEffect(() => {
    if (allClear) return

    // Animate flags in sequence using their animate_at_ms
    const timers: ReturnType<typeof setTimeout>[] = []
    flags.forEach((flag, index) => {
      const delay = flag.animate_at_ms || (index + 1) * 1500
      timers.push(setTimeout(() => setVisibleFlagCount(index + 1), delay))
    })

    // After last flag, show repair
    const lastDelay = (flags[flags.length - 1]?.animate_at_ms || flags.length * 1500) + 500
    timers.push(
      setTimeout(() => {
        setShowRepair(true)
        progress.value = withTiming(1, { duration: 1500 })
      }, lastDelay),
      setTimeout(() => setShowPrice(true), lastDelay + 1500),
      setTimeout(() => setShowCoverage(true), lastDelay + 1700),
      setTimeout(() => setShowCta(true), lastDelay + 1900),
    )

    return () => timers.forEach(clearTimeout)
  }, [flags.length])

  useEffect(() => {
    if (visibleFlagCount > 0 || showRepair) {
      const t = setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), showCta ? 450 : 100)
      return () => clearTimeout(t)
    }
  }, [visibleFlagCount, showRepair, showPrice, showCoverage, showCta])

  const handleOrder = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy).catch(() => {})
    setOrderPlaced(true)
  }

  const getSeverityStyle = (severity: string) => {
    if (severity === 'red') return { card: styles.redCard, text: styles.redText, border: Colors.errorRed }
    if (severity === 'amber') return { card: styles.amberCard, text: styles.amberText, border: Colors.primaryDark }
    return { card: styles.blueCard, text: styles.blueText, border: Colors.sponsoredBlue }
  }

  const getSeverityLabel = (severity: string) => {
    if (severity === 'red') return 'ISSUE FOUND'
    if (severity === 'amber') return 'SWAPPING'
    return 'SPONSORED BLOCKED'
  }

  const getSeverityIcon = (severity: string) => {
    if (severity === 'blue') return 'shield-checkmark'
    if (severity === 'amber') return 'swap-horizontal'
    return 'warning'
  }

  // ALL CLEAR STATE
  if (allClear) {
    return (
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <StatusBar style="light" backgroundColor={Colors.nowBlue} />
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={10} style={styles.backBtn}>
            <Ionicons name="arrow-back" size={22} color={Colors.white} />
          </Pressable>
          <View>
            <Text style={styles.headerTitle}>Cart Audit</Text>
            <Text style={styles.headerSubtitle}>All clear ✓</Text>
          </View>
        </View>
        <View style={styles.allClearBody}>
          <Ionicons name="checkmark-circle" size={64} color={Colors.successGreen} />
          <Text style={styles.allClearTitle}>Your cart looks great!</Text>
          <Text style={styles.allClearSubtitle}>
            No issues found. All items are compatible, correctly quantified, and available on Amazon Now.
          </Text>
          <Text style={styles.allClearCoverage}>Coverage: {coverageScore} ✓</Text>
          <Pressable style={styles.allClearButton} onPress={() => router.back()}>
            <Text style={styles.allClearButtonText}>Add to Amazon →</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar style="light" backgroundColor={Colors.nowBlue} />

      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </Pressable>
        <View>
          <Text style={styles.headerTitle}>Cart Audit</Text>
          <Text style={styles.headerSubtitle}>{flags.length} issues found</Text>
        </View>
      </View>

      <ScrollView ref={scrollRef} style={styles.scrollBody} contentContainerStyle={styles.scrollContent}>
        {/* FLAGS */}
        <View style={styles.flagsSection}>
          <View style={styles.auditHeaderRow}>
            <Text style={styles.auditTitle}>🔍 MissionCart Audit</Text>
            <Text style={styles.poweredText}>Powered by <Text style={styles.bedrockText}>Bedrock</Text></Text>
          </View>

          {flags.slice(0, visibleFlagCount).map((flag) => {
            const sev = getSeverityStyle(flag.severity)
            const isExpanded = expandedFlag === flag.flag_id
            return (
              <TouchableOpacity
                key={flag.flag_id}
                activeOpacity={0.8}
                onPress={() => setExpandedFlag(isExpanded ? null : flag.flag_id)}
              >
                <Animated.View entering={FadeInDown.duration(400)} style={[styles.flagCard, sev.card]}>
                  <View style={styles.flagIcon}>
                    <Ionicons name={getSeverityIcon(flag.severity) as any} size={21} color={sev.border} />
                  </View>
                  <View style={styles.flagContent}>
                    <Text style={[styles.flagLabel, sev.text]}>{getSeverityLabel(flag.severity)}</Text>
                    <Text style={[styles.flagMessage, sev.text]}>{flag.message}</Text>
                    {isExpanded && flag.math_explanation && (
                      <View style={styles.mathContainer}>
                        <Text style={styles.mathText}>📐 {flag.math_explanation}</Text>
                      </View>
                    )}
                  </View>
                  {flag.severity === 'blue' && (
                    <View style={styles.trustCheck}>
                      <Ionicons name="checkmark" size={13} color={Colors.white} />
                    </View>
                  )}
                </Animated.View>
              </TouchableOpacity>
            )
          })}
        </View>

        {/* REPAIR SECTION */}
        {showRepair && (
          <Animated.View entering={FadeInDown.duration(400)} style={styles.repairSection}>
            <Text style={styles.repairTitle}>✨ Repairing your cart</Text>
            <View style={styles.progressTrack}>
              <Animated.View style={[styles.progressFill, progressStyle]} />
            </View>

            {showPrice && (
              <Animated.View entering={FadeInDown.duration(300)} style={styles.priceBlock}>
                <View style={styles.priceRow}>
                  <Text style={styles.oldPrice}>₹{originalTotal.toLocaleString('en-IN')}</Text>
                  <Text style={styles.newPrice}>₹{repairedTotal.toLocaleString('en-IN')}</Text>
                </View>
                {originalTotal > repairedTotal && (
                  <View style={styles.savingsPill}>
                    <Text style={styles.savingsText}>You save ₹{(originalTotal - repairedTotal).toLocaleString('en-IN')}</Text>
                  </View>
                )}
              </Animated.View>
            )}

            {showCoverage && (
              <Animated.View entering={FadeInDown.duration(300)} style={styles.coverageBlock}>
                <Text style={styles.coverageTitle}>Coverage: {coverageScore} ✓</Text>
                <Text style={styles.coverageSubtitle}>All items available on Amazon Now ⚡</Text>
              </Animated.View>
            )}

            {showCta && (
              <Animated.View entering={FadeInDown.duration(300)}>
                <Pressable onPress={handleOrder} style={styles.orderButton}>
                  <Text style={styles.orderButtonText}>Order Repaired Cart via Amazon Now ⚡</Text>
                </Pressable>
                {orderPlaced && (
                  <Text style={styles.orderPlacedText}>✓ Order placed! Arriving in 12 mins</Text>
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
  safeArea: { flex: 1, backgroundColor: Colors.nowBlue },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 14, backgroundColor: Colors.nowBlue },
  backBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center', marginRight: 8 },
  headerTitle: { color: Colors.white, fontSize: 18, fontWeight: '700' },
  headerSubtitle: { color: Colors.white, fontSize: 12, opacity: 0.85, marginTop: 1 },
  scrollBody: { flex: 1, backgroundColor: Colors.background },
  scrollContent: { paddingBottom: 40 },
  flagsSection: { paddingTop: 15, paddingBottom: 8 },
  auditHeaderRow: { paddingHorizontal: 12, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  auditTitle: { color: Colors.textPrimary, fontSize: 16, fontWeight: '700' },
  poweredText: { color: Colors.textSecondary, fontSize: 11 },
  bedrockText: { color: Colors.primary, fontWeight: '700' },
  flagCard: { minHeight: 80, marginHorizontal: 12, marginVertical: 4, padding: 12, flexDirection: 'row', alignItems: 'flex-start', borderLeftWidth: 4, borderRadius: 4 },
  redCard: { backgroundColor: '#FFF5F5', borderLeftColor: Colors.errorRed },
  amberCard: { backgroundColor: '#FFFBF0', borderLeftColor: Colors.primaryDark },
  blueCard: { backgroundColor: '#F0F8FF', borderLeftColor: Colors.sponsoredBlue },
  flagIcon: { width: 30, marginRight: 3, paddingTop: 2 },
  flagContent: { flex: 1, paddingRight: 7 },
  flagLabel: { fontSize: 10, fontWeight: '800', letterSpacing: 1 },
  flagMessage: { marginTop: 3, fontSize: 14, fontWeight: '700' },
  redText: { color: Colors.errorRed },
  amberText: { color: Colors.primaryDark },
  blueText: { color: Colors.sponsoredBlue },
  mathContainer: { marginTop: 4, paddingTop: 8, paddingHorizontal: 12, paddingBottom: 8, backgroundColor: Colors.white, borderTopWidth: 1, borderTopColor: Colors.border, borderRadius: 4 },
  mathText: { color: Colors.textSecondary, fontSize: 12, lineHeight: 18 },
  trustCheck: { width: 20, height: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.sponsoredBlue, borderRadius: 10 },
  repairSection: { marginHorizontal: 12, marginTop: 12, paddingTop: 14, borderTopWidth: 1, borderTopColor: Colors.border },
  repairTitle: { color: Colors.textPrimary, fontSize: 16, fontWeight: '700' },
  progressTrack: { width: '100%', height: 6, marginTop: 12, overflow: 'hidden', backgroundColor: '#F3F3F3', borderRadius: 3 },
  progressFill: { height: 6, backgroundColor: Colors.primary, borderRadius: 3 },
  priceBlock: { marginTop: 17, alignItems: 'flex-start' },
  priceRow: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  oldPrice: { color: Colors.textSecondary, fontSize: 20, textDecorationLine: 'line-through' },
  newPrice: { color: Colors.successGreen, fontSize: 28, fontWeight: '800' },
  savingsPill: { marginTop: 6, paddingHorizontal: 8, paddingVertical: 2, backgroundColor: Colors.successGreen, borderRadius: 10 },
  savingsText: { color: Colors.white, fontSize: 12, fontWeight: '600' },
  coverageBlock: { marginTop: 15 },
  coverageTitle: { color: Colors.successGreen, fontSize: 16, fontWeight: '700' },
  coverageSubtitle: { marginTop: 3, color: Colors.textSecondary, fontSize: 13 },
  orderButton: { width: '100%', height: 52, marginTop: 17, alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.primary, borderRadius: 4 },
  orderButtonText: { color: Colors.white, fontSize: 16, fontWeight: '700', textAlign: 'center' },
  orderPlacedText: { marginTop: 10, color: Colors.successGreen, fontSize: 14, fontWeight: '600', textAlign: 'center' },
  // All clear
  allClearBody: { flex: 1, backgroundColor: Colors.background, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 24 },
  allClearTitle: { color: Colors.textPrimary, fontSize: 20, fontWeight: '700', marginTop: 16 },
  allClearSubtitle: { color: Colors.textSecondary, fontSize: 14, textAlign: 'center', marginTop: 8, lineHeight: 20 },
  allClearCoverage: { color: Colors.successGreen, fontSize: 16, fontWeight: '600', marginTop: 16 },
  allClearButton: { backgroundColor: Colors.primary, height: 52, borderRadius: 4, alignItems: 'center', justifyContent: 'center', width: '100%', marginTop: 24 },
  allClearButtonText: { color: Colors.white, fontSize: 16, fontWeight: '700' },
})
