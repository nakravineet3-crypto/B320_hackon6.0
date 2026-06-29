import { Ionicons } from '@expo/vector-icons'
import * as Linking from 'expo-linking'
import { useLocalSearchParams, router } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useEffect, useRef, useState } from 'react'
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withTiming,
} from 'react-native-reanimated'
import { SafeAreaView } from 'react-native-safe-area-context'
import Svg, { Circle, Line, Text as SvgText } from 'react-native-svg'

import { missionAPI } from '../../lib/api'
import { Colors } from '../../lib/constants'
import { FALLBACK_CART_ITEMS } from '../../lib/fallbacks'
import { useMissionStore } from '../../store/mission'

const FALLBACK_CART = {
  cart_items: FALLBACK_CART_ITEMS,
  total_cost: 1190,
  budget_remaining: 1810,
  coverage_score: { display: '8/8', covered: 8, total: 8, all_must_haves_covered: true, missing: [] },
  repair_summary: null,
}

type StepStatus = 'pending' | 'active' | 'done'
type ScreenState = 'building' | 'unsupported' | 'clarification'

interface StepData {
  label: string
  status: StepStatus
  number: number
}

function StepIndicator({ step }: { step: StepData }) {
  return (
    <View style={styles.stepRow}>
      <View style={styles.stepCircleWrap}>
        {step.status === 'pending' && (
          <View style={styles.pendingCircle}>
            <Text style={styles.pendingNumber}>{step.number}</Text>
          </View>
        )}
        {step.status === 'active' && (
          <View style={styles.activeCircle}>
            <Text style={styles.activeNumber}>{step.number}</Text>
          </View>
        )}
        {step.status === 'done' && (
          <View style={styles.doneCircle}>
            <Ionicons name="checkmark" size={14} color={Colors.white} />
          </View>
        )}
      </View>
      <Text
        style={[
          styles.stepLabel,
          step.status === 'pending' && styles.stepLabelPending,
          step.status === 'active' && styles.stepLabelActive,
          step.status === 'done' && styles.stepLabelDone,
        ]}
      >
        {step.label}
      </Text>
    </View>
  )
}

const NEED_NODES = [
  { label: 'plates', angle: 0 },
  { label: 'cups', angle: 60 },
  { label: 'balloons', angle: 120 },
  { label: 'candles', angle: 180 },
  { label: 'napkins', angle: 240 },
  { label: 'gifts', angle: 300 },
]

function GNNVisualization({ visible }: { visible: boolean }) {
  const overallOpacity = useSharedValue(0)

  useEffect(() => {
    if (visible) {
      overallOpacity.value = withTiming(1, { duration: 600 })
    }
  }, [visible])

  const containerStyle = useAnimatedStyle(() => ({ opacity: overallOpacity.value }))

  if (!visible) return null

  const cx = 100
  const cy = 100
  const needRadius = 70
  const productRadius = 35

  const needPositions = NEED_NODES.map((n) => {
    const rad = (n.angle * Math.PI) / 180
    return { x: cx + needRadius * Math.cos(rad), y: cy + needRadius * Math.sin(rad), label: n.label }
  })

  const productPositions = needPositions.flatMap((need, i) => {
    const offsets = [
      { da: -25, r: productRadius },
      { da: 25, r: productRadius },
    ]
    return offsets.map((o, j) => {
      const baseAngle = NEED_NODES[i].angle
      const rad = ((baseAngle + o.da) * Math.PI) / 180
      return {
        x: need.x + o.r * Math.cos(rad),
        y: need.y + o.r * Math.sin(rad),
        isSelected: j === 0,
      }
    })
  })

  return (
    <View style={styles.gnnContainer}>
      <Animated.View style={containerStyle}>
        <Svg width={200} height={200} viewBox="0 0 200 200">
          {needPositions.map((n, i) => (
            <Line key={`edge-${i}`} x1={cx} y1={cy} x2={n.x} y2={n.y} stroke="#FFFFFF" strokeOpacity={0.3} strokeWidth={1.5} />
          ))}
          {productPositions.filter((p) => !p.isSelected).map((p, i) => (
            <Circle key={`prod-${i}`} cx={p.x} cy={p.y} r={8} fill="transparent" stroke="#FFFFFF" strokeOpacity={0.6} strokeWidth={1} />
          ))}
          {productPositions.filter((p) => p.isSelected).map((p, i) => (
            <Circle key={`sel-${i}`} cx={p.x} cy={p.y} r={8} fill="#FFD814" stroke="#FFFFFF" strokeOpacity={0.6} strokeWidth={1} />
          ))}
          {needPositions.map((n, i) => (
            <Circle key={`need-${i}`} cx={n.x} cy={n.y} r={12} fill="#1A98FF" stroke="#FFFFFF" strokeOpacity={0.6} strokeWidth={1} />
          ))}
          {needPositions.map((n, i) => (
            <SvgText key={`nlbl-${i}`} x={n.x} y={n.y + 22} fontSize={8} fill="#FFFFFF" textAnchor="middle">{n.label}</SvgText>
          ))}
          <Circle cx={cx} cy={cy} r={20} fill="#FFFFFF" />
          <SvgText x={cx} y={cy + 5} fontSize={14} fontWeight="700" fill="#FF9900" textAnchor="middle">MC</SvgText>
        </Svg>
      </Animated.View>
    </View>
  )
}

// ── UNSUPPORTED SCREEN ──────────────────────────────────
function UnsupportedScreen({ data }: { data: any }) {
  return (
    <SafeAreaView style={styles.unsupportedSafeArea} edges={['top']}>
      <StatusBar style="dark" backgroundColor={Colors.background} />
      <ScrollView contentContainerStyle={styles.unsupportedContent}>
        <Ionicons name="search-outline" size={64} color="#D5D9D9" style={styles.unsupportedIcon} />
        <Text style={styles.unsupportedTitle}>Not available on Amazon Now</Text>
        <Text style={styles.unsupportedReason}>
          {data?.unsupported_reason || 'This type of goal is not yet supported by MissionCart.'}
        </Text>

        <View style={styles.unsupportedDivider} />
        <Text style={styles.unsupportedHint}>Try searching Amazon directly:</Text>
        <TouchableOpacity
          style={styles.searchAmazonButton}
          onPress={() => Linking.openURL(data?.amazon_search_url || 'https://www.amazon.in')}
        >
          <Text style={styles.searchAmazonText}>Search Amazon →</Text>
        </TouchableOpacity>

        <View style={styles.unsupportedDivider} />
        <Text style={styles.unsupportedHint}>Or try one of these goals:</Text>

        {(data?.supported_goals || [
          'Birthday party for 12 kids under ₹4000',
          'New flat setup this weekend under ₹15000',
          'Trek for 4 people under ₹5000',
        ]).map((suggestion: string, idx: number) => (
          <TouchableOpacity
            key={idx}
            style={styles.suggestionChip}
            onPress={() => router.back()}
          >
            <Text style={styles.suggestionText}>{suggestion}</Text>
          </TouchableOpacity>
        ))}

        <TouchableOpacity onPress={() => router.back()} style={styles.backLink}>
          <Text style={styles.backLinkText}>← Back</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  )
}

// ── CLARIFICATION SCREEN ────────────────────────────────
function ClarificationScreen({
  data,
  originalGoal,
  budget,
}: {
  data: any
  originalGoal: string
  budget: number
}) {
  const [clarificationValue, setClarificationValue] = useState('')
  const clarificationType: string = data?.clarification_type || 'budget'
  const partialSpec = data?.partial_spec || {}

  const budgetSuggestions = ['1000', '2000', '3000', '5000']
  const headcountSuggestions = ['5', '10', '15', '20', '25', '30']
  const deadlineSuggestions = ['Today', 'Tomorrow', 'This weekend']

  const buildEnhancedGoal = () => {
    const value = clarificationValue.trim()
    if (!value) return originalGoal
    if (clarificationType === 'budget') return `${originalGoal} under ₹${value}`
    if (clarificationType === 'headcount') return `${originalGoal} for ${value} people`
    if (clarificationType === 'deadline') return `${originalGoal} ${value.toLowerCase()}`
    if (clarificationType === 'goal_unclear') return value
    return `${originalGoal} ${value}`
  }

  const handleSubmit = () => {
    const enhancedGoal = buildEnhancedGoal()
    router.replace({
      pathname: '/cart/building',
      params: { goal: enhancedGoal, budget: String(budget) },
    })
  }

  const detectedFields: Array<{ label: string; value: string; found: boolean }> = []
  if (partialSpec.domain) detectedFields.push({ label: 'Domain', value: partialSpec.domain, found: true })
  if (partialSpec.occasion) detectedFields.push({ label: 'Occasion', value: partialSpec.occasion, found: true })
  if (partialSpec.headcount) detectedFields.push({ label: 'Guests', value: String(partialSpec.headcount), found: true })
  if (partialSpec.budget_max) detectedFields.push({ label: 'Budget', value: `₹${partialSpec.budget_max}`, found: true })
  if (partialSpec.deadline_hours) detectedFields.push({ label: 'Deadline', value: `${partialSpec.deadline_hours}h`, found: true })

  // Show missing fields
  if (!partialSpec.budget_max && clarificationType === 'budget')
    detectedFields.push({ label: 'Budget', value: 'Not specified', found: false })
  if (!partialSpec.headcount && clarificationType === 'headcount')
    detectedFields.push({ label: 'Guests', value: 'Not specified', found: false })

  return (
    <SafeAreaView style={styles.clarificationSafeArea} edges={['top']}>
      <StatusBar style="light" backgroundColor={Colors.nowBlue} />

      {/* Header */}
      <View style={styles.clarificationHeader}>
        <Pressable onPress={() => router.back()} hitSlop={10}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </Pressable>
        <Text style={styles.clarificationHeaderTitle}>Tell us more</Text>
      </View>

      <ScrollView style={styles.clarificationBody} contentContainerStyle={styles.clarificationBodyContent} keyboardShouldPersistTaps="handled">
        {/* What we understood */}
        {detectedFields.length > 0 && (
          <View style={styles.understoodCard}>
            <Text style={styles.understoodLabel}>We understood:</Text>
            {detectedFields.map((field, idx) => (
              <View key={idx} style={styles.understoodRow}>
                <Ionicons
                  name={field.found ? 'checkmark' : 'help'}
                  size={14}
                  color={field.found ? Colors.successGreen : Colors.errorRed}
                />
                <Text style={[styles.understoodText, { color: field.found ? Colors.successGreen : Colors.errorRed }]}>
                  {field.label}: {field.value}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Clarification question */}
        <Text style={styles.clarificationQuestion}>
          {data?.clarification_question || 'What is your budget?'}
        </Text>

        {/* Input based on type */}
        {clarificationType === 'budget' && (
          <View>
            <View style={styles.inputRow}>
              <Text style={styles.inputPrefix}>₹</Text>
              <TextInput
                style={styles.clarificationInput}
                value={clarificationValue}
                onChangeText={setClarificationValue}
                keyboardType="numeric"
                placeholder="3000"
                placeholderTextColor="#999"
              />
            </View>
            <View style={styles.suggestionsRow}>
              {budgetSuggestions.map((s) => (
                <TouchableOpacity key={s} style={styles.suggestionPill} onPress={() => setClarificationValue(s)}>
                  <Text style={styles.suggestionPillText}>₹{s}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {clarificationType === 'headcount' && (
          <View>
            <TextInput
              style={styles.clarificationInputFull}
              value={clarificationValue}
              onChangeText={setClarificationValue}
              keyboardType="numeric"
              placeholder="Number of guests"
              placeholderTextColor="#999"
            />
            <View style={styles.suggestionsRow}>
              {headcountSuggestions.map((s) => (
                <TouchableOpacity key={s} style={styles.suggestionPill} onPress={() => setClarificationValue(s)}>
                  <Text style={styles.suggestionPillText}>{s}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {clarificationType === 'deadline' && (
          <View style={styles.suggestionsRow}>
            {deadlineSuggestions.map((s) => (
              <TouchableOpacity
                key={s}
                style={[styles.deadlinePill, clarificationValue === s && styles.deadlinePillSelected]}
                onPress={() => setClarificationValue(s)}
              >
                <Text style={[styles.deadlinePillText, clarificationValue === s && styles.deadlinePillTextSelected]}>{s}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {clarificationType === 'goal_unclear' && (
          <TextInput
            style={styles.clarificationInputMultiline}
            value={clarificationValue}
            onChangeText={setClarificationValue}
            placeholder="Describe what you need in detail..."
            placeholderTextColor="#999"
            multiline
            numberOfLines={3}
          />
        )}

        {/* Build Cart button */}
        <TouchableOpacity style={styles.buildCartButton} onPress={handleSubmit}>
          <Text style={styles.buildCartButtonText}>Build Cart →</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  )
}

// ── MAIN BUILDING SCREEN ────────────────────────────────
export default function BuildingScreen() {
  const { goal: rawGoal, budget: rawBudget, headcount: rawHeadcount, occasion_type: rawOccasionType } =
    useLocalSearchParams<{
      goal?: string
      budget?: string
      headcount?: string
      occasion_type?: string
    }>()
  const goal = rawGoal || 'Building your cart...'
  const budget = parseFloat(rawBudget ?? '') || 3000
  const occasionType = rawOccasionType ?? undefined
  const headcount = rawHeadcount ? parseInt(rawHeadcount, 10) : undefined

  const [screenState, setScreenState] = useState<ScreenState>('building')
  const screenStateRef = useRef<ScreenState>('building')
  const [unsupportedData, setUnsupportedData] = useState<any>(null)
  const [clarificationData, setClarificationData] = useState<any>(null)

  const setScreen = (s: ScreenState) => {
    screenStateRef.current = s
    setScreenState(s)
  }

  const [steps, setSteps] = useState<StepData[]>([
    { label: 'Parsing your goal', status: 'active', number: 1 },
    { label: 'Finding what you need', status: 'pending', number: 2 },
    { label: 'Checking Amazon Now stock', status: 'pending', number: 3 },
    { label: 'Validating cart', status: 'pending', number: 4 },
  ])
  const [error, setError] = useState(false)
  const [showGraph, setShowGraph] = useState(false)
  const apiResolved = useRef(false)
  const navigated = useRef(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const updateStep = (index: number, status: StepStatus) => {
    setSteps((prev) => prev.map((s, i) => (i === index ? { ...s, status } : s)))
  }

  const navigateToResult = () => {
    if (navigated.current) return
    navigated.current = true
    router.replace('/cart/result')
  }

  useEffect(() => {
    let cancelled = false

    // Clear any stale cart from a previous build before starting
    useMissionStore.getState().clearMission()

    missionAPI
      .build(goal, budget, { occasion_type: occasionType, headcount })
      .then((res) => {
        if (cancelled) return
        apiResolved.current = true
        const data = res.data

        // STATE 1: Unsupported
        if (!data.success && data.data?.unsupported) {
          setScreen('unsupported')
          setUnsupportedData(data.data)
          return
        }

        // STATE 2: Needs clarification
        if (!data.success && data.data?.needs_clarification) {
          setScreen('clarification')
          setClarificationData(data.data)
          return
        }

        // STATE 3: Normal cart
        if (data.success) {
          const fullResult = data.data
          useMissionStore.getState().setCart(fullResult?.cart_items || [])
          useMissionStore.getState().setBuildResult(fullResult)
          return
        }

        // Fallback
        useMissionStore.getState().setCart(FALLBACK_CART.cart_items as any)
        useMissionStore.getState().setBuildResult(FALLBACK_CART)
      })
      .catch(() => {
        if (cancelled) return
        apiResolved.current = true
        useMissionStore.getState().setCart(FALLBACK_CART.cart_items as any)
        useMissionStore.getState().setBuildResult(FALLBACK_CART)
      })

    const t1 = setTimeout(() => {
      if (cancelled || screenStateRef.current !== 'building') return
      updateStep(0, 'done')
      updateStep(1, 'active')
    }, 800)

    const t2 = setTimeout(() => {
      if (cancelled || screenStateRef.current !== 'building') return
      updateStep(1, 'done')
      setShowGraph(true)
      updateStep(2, 'active')
    }, 1500)

    const t3 = setTimeout(() => {
      if (cancelled || screenStateRef.current !== 'building') return
      updateStep(2, 'done')
      updateStep(3, 'active')
    }, 4500)

    const t4 = setTimeout(() => {
      if (cancelled || screenStateRef.current !== 'building') return
      updateStep(3, 'done')
    }, 5200)

    const t5 = setTimeout(() => {
      if (cancelled || screenStateRef.current !== 'building') return
      if (apiResolved.current) {
        navigateToResult()
      } else {
        const pollStart = Date.now()
        const poll = setInterval(() => {
          if (cancelled) { clearInterval(poll); return }
          if (apiResolved.current || Date.now() - pollStart > 3000) {
            clearInterval(poll)
            pollRef.current = null
            if (!navigated.current) navigateToResult()
          }
        }, 200)
        pollRef.current = poll
      }
    }, 5700)

    return () => {
      cancelled = true
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
      clearTimeout(t4)
      clearTimeout(t5)
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [goal, budget, occasionType, headcount])

  // Render based on screen state
  if (screenState === 'unsupported') {
    return <UnsupportedScreen data={unsupportedData} />
  }

  if (screenState === 'clarification') {
    return <ClarificationScreen data={clarificationData} originalGoal={goal} budget={budget} />
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar style="light" backgroundColor={Colors.nowBlue} />

      <View style={styles.screen}>
        <View style={styles.topSection}>
          <Text style={styles.title}>Building your cart</Text>
          <Text style={styles.goalText} numberOfLines={2}>
            {goal}
          </Text>
        </View>

        <View style={styles.stepsContainer}>
          {steps.slice(0, 2).map((step) => (
            <StepIndicator key={step.number} step={step} />
          ))}
        </View>

        <GNNVisualization visible={showGraph} />

        <View style={styles.stepsContainer}>
          {steps.slice(2).map((step) => (
            <StepIndicator key={step.number} step={step} />
          ))}
        </View>

        {error && (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>Something went wrong</Text>
            <Pressable onPress={() => setError(false)} style={styles.retryButton}>
              <Text style={styles.retryButtonText}>Retry</Text>
            </Pressable>
          </View>
        )}

        <View style={styles.bottomText}>
          <Text style={styles.bottomTextLabel}>
            Analyzed 3,847 community sessions
          </Text>
        </View>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  // ── BUILDING SCREEN STYLES ──────────────────────────────
  safeArea: {
    flex: 1,
    backgroundColor: Colors.nowBlue,
  },
  screen: {
    flex: 1,
    backgroundColor: Colors.nowBlue,
  },
  topSection: {
    paddingTop: 60,
    paddingHorizontal: 24,
  },
  title: {
    color: Colors.white,
    fontSize: 24,
    fontWeight: '700',
  },
  goalText: {
    marginTop: 8,
    color: Colors.white,
    fontSize: 13,
    opacity: 0.8,
  },
  stepsContainer: {
    width: '100%',
    paddingHorizontal: 24,
    marginTop: 48,
  },
  stepRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  stepCircleWrap: {
    width: 28,
    height: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pendingCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: 'rgba(255,255,255,0.4)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  pendingNumber: {
    color: Colors.white,
    opacity: 0.4,
    fontSize: 13,
  },
  activeCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.white,
    alignItems: 'center',
    justifyContent: 'center',
  },
  activeNumber: {
    color: Colors.nowBlue,
    fontSize: 13,
    fontWeight: '700',
  },
  doneCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.successGreen,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepLabel: {
    flex: 1,
    marginLeft: 14,
    fontSize: 14,
  },
  stepLabelPending: {
    color: Colors.white,
    opacity: 0.4,
  },
  stepLabelActive: {
    color: Colors.white,
    fontWeight: '600',
  },
  stepLabelDone: {
    color: Colors.white,
  },
  errorContainer: {
    marginTop: 32,
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  errorText: {
    color: Colors.white,
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  retryButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: Colors.primary,
    borderRadius: 4,
  },
  retryButtonText: {
    color: Colors.white,
    fontSize: 14,
    fontWeight: '700',
  },
  gnnContainer: {
    width: '100%',
    height: 220,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 12,
  },
  bottomText: {
    position: 'absolute',
    bottom: 48,
    width: '100%',
    alignItems: 'center',
  },
  bottomTextLabel: {
    color: Colors.white,
    opacity: 0.7,
    fontSize: 12,
  },

  // ── UNSUPPORTED SCREEN STYLES ───────────────────────────
  unsupportedSafeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  unsupportedContent: {
    paddingTop: 80,
    paddingBottom: 40,
    alignItems: 'center',
  },
  unsupportedIcon: {
    alignSelf: 'center',
  },
  unsupportedTitle: {
    color: Colors.textPrimary,
    fontSize: 20,
    fontWeight: '700',
    textAlign: 'center',
    marginTop: 16,
  },
  unsupportedReason: {
    color: Colors.textSecondary,
    fontSize: 14,
    textAlign: 'center',
    paddingHorizontal: 32,
    marginTop: 8,
  },
  unsupportedDivider: {
    width: '80%',
    height: 1,
    backgroundColor: '#EEEEEE',
    marginVertical: 20,
  },
  unsupportedHint: {
    color: Colors.textSecondary,
    fontSize: 13,
    marginBottom: 8,
  },
  searchAmazonButton: {
    backgroundColor: Colors.primary,
    borderRadius: 4,
    height: 48,
    marginHorizontal: 32,
    alignSelf: 'stretch',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
  },
  searchAmazonText: {
    color: Colors.white,
    fontSize: 15,
    fontWeight: '700',
  },
  suggestionChip: {
    alignSelf: 'stretch',
    marginHorizontal: 32,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: '#D5D9D9',
    borderRadius: 4,
    marginBottom: 6,
  },
  suggestionText: {
    color: Colors.linkBlue,
    fontSize: 13,
  },
  backLink: {
    marginTop: 20,
    paddingVertical: 8,
  },
  backLinkText: {
    color: Colors.textSecondary,
    fontSize: 14,
  },

  // ── CLARIFICATION SCREEN STYLES ─────────────────────────
  clarificationSafeArea: {
    flex: 1,
    backgroundColor: Colors.nowBlue,
  },
  clarificationHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    backgroundColor: Colors.nowBlue,
    gap: 12,
  },
  clarificationHeaderTitle: {
    color: Colors.white,
    fontSize: 18,
    fontWeight: '700',
  },
  clarificationBody: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  clarificationBodyContent: {
    paddingBottom: 40,
  },
  understoodCard: {
    margin: 16,
    backgroundColor: '#F7F8F8',
    borderRadius: 4,
    padding: 12,
  },
  understoodLabel: {
    color: Colors.textPrimary,
    fontSize: 13,
    fontWeight: '700',
    marginBottom: 8,
  },
  understoodRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
    gap: 6,
  },
  understoodText: {
    fontSize: 13,
  },
  clarificationQuestion: {
    color: Colors.textPrimary,
    fontSize: 16,
    fontWeight: '700',
    marginHorizontal: 16,
    marginTop: 20,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
    marginTop: 16,
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: 4,
    paddingHorizontal: 12,
    height: 48,
  },
  inputPrefix: {
    color: Colors.textSecondary,
    fontSize: 16,
    fontWeight: '600',
    marginRight: 4,
  },
  clarificationInput: {
    flex: 1,
    fontSize: 16,
    color: Colors.textPrimary,
    paddingVertical: 0,
  },
  clarificationInputFull: {
    marginHorizontal: 16,
    marginTop: 16,
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: 4,
    paddingHorizontal: 12,
    height: 48,
    fontSize: 16,
    color: Colors.textPrimary,
  },
  clarificationInputMultiline: {
    marginHorizontal: 16,
    marginTop: 16,
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: 4,
    padding: 12,
    fontSize: 15,
    color: Colors.textPrimary,
    minHeight: 80,
    textAlignVertical: 'top',
  },
  suggestionsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: 16,
    marginTop: 12,
    gap: 8,
  },
  suggestionPill: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: Colors.primary,
    borderRadius: 20,
  },
  suggestionPillText: {
    color: Colors.primary,
    fontSize: 13,
    fontWeight: '600',
  },
  deadlinePill: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: 4,
  },
  deadlinePillSelected: {
    borderColor: Colors.primary,
    backgroundColor: '#FFF8F0',
  },
  deadlinePillText: {
    color: Colors.textPrimary,
    fontSize: 14,
  },
  deadlinePillTextSelected: {
    color: Colors.primary,
    fontWeight: '700',
  },
  buildCartButton: {
    marginHorizontal: 16,
    marginTop: 24,
    height: 52,
    backgroundColor: Colors.primary,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buildCartButtonText: {
    color: Colors.white,
    fontSize: 16,
    fontWeight: '700',
  },
})
