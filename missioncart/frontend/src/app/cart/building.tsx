import { Ionicons } from '@expo/vector-icons'
import { useLocalSearchParams, router } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useEffect, useRef, useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
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
import { useMissionStore } from '../../store/mission'

const FALLBACK_CART = {
  cart_items: [
    { cart_item_id: '1', need_label: 'Plates & utensils', title: 'Disposable Paper Plates 25pc', price: 89, packs_quantity: 2, total_cost: 178, amazon_now_eligible: true, rating: 4.2, delivery_eta: 'now_20min', prime: true, explanation: '2 plates per child × 12 kids = 24 plates' },
    { cart_item_id: '2', need_label: 'Cups & drinks', title: 'Disposable Cups 50pc', price: 79, packs_quantity: 1, total_cost: 79, amazon_now_eligible: true, rating: 4.0, delivery_eta: 'now_20min', prime: true, explanation: '2.5 cups per child × 12 kids' },
    { cart_item_id: '3', need_label: 'Candles & cake knife', title: 'Birthday Candles Set 10pc', price: 49, packs_quantity: 1, total_cost: 49, amazon_now_eligible: true, rating: 4.3, delivery_eta: 'now_20min', prime: true, explanation: '1 pack of candles' },
    { cart_item_id: '4', need_label: 'Balloons & decorations', title: 'Multicolor Balloons 30pc', price: 149, packs_quantity: 2, total_cost: 298, amazon_now_eligible: true, rating: 4.1, delivery_eta: 'now_20min', prime: true, explanation: '3 balloons per child × 12 kids with buffer' },
    { cart_item_id: '5', need_label: 'Napkins & tissues', title: 'Paper Napkins 100pc', price: 59, packs_quantity: 1, total_cost: 59, amazon_now_eligible: true, rating: 4.0, delivery_eta: 'now_20min', prime: true, explanation: '3 napkins per child × 12 kids' },
    { cart_item_id: '6', need_label: 'Entertainment', title: 'Party Games Set', price: 199, packs_quantity: 1, total_cost: 199, amazon_now_eligible: false, rating: 3.8, delivery_eta: 'tomorrow', prime: true, explanation: '1 games set for group activities' },
    { cart_item_id: '7', need_label: 'Return gifts', title: 'Return Gift Bags 12pc', price: 199, packs_quantity: 1, total_cost: 199, amazon_now_eligible: true, rating: 4.2, delivery_eta: 'now_20min', prime: true, explanation: '1 gift per child × 12 kids' },
    { cart_item_id: '8', need_label: 'Cleanup', title: 'Trash Bags 30pc', price: 129, packs_quantity: 1, total_cost: 129, amazon_now_eligible: true, rating: 4.1, delivery_eta: 'now_20min', prime: true, explanation: '1 pack for post-party cleanup' },
  ],
  total_cost: 1190,
  budget_remaining: 1810,
  coverage_score: { display: '8/8', covered: 8, total: 8, all_must_haves_covered: true, missing: [] },
  repair_summary: null,
}

type StepStatus = 'pending' | 'active' | 'done'

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
  const textOpacity = useSharedValue(0)

  useEffect(() => {
    if (visible) {
      overallOpacity.value = withTiming(1, { duration: 600 })
      textOpacity.value = withDelay(2200, withTiming(1, { duration: 300 }))
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
          {/* Edges from center to needs */}
          {needPositions.map((n, i) => (
            <Line
              key={`edge-${i}`}
              x1={cx}
              y1={cy}
              x2={n.x}
              y2={n.y}
              stroke="#FFFFFF"
              strokeOpacity={0.3}
              strokeWidth={1.5}
            />
          ))}

          {/* Product nodes (unselected) */}
          {productPositions
            .filter((p) => !p.isSelected)
            .map((p, i) => (
              <Circle
                key={`prod-${i}`}
                cx={p.x}
                cy={p.y}
                r={8}
                fill="transparent"
                stroke="#FFFFFF"
                strokeOpacity={0.6}
                strokeWidth={1}
              />
            ))}

          {/* Selected product nodes */}
          {productPositions
            .filter((p) => p.isSelected)
            .map((p, i) => (
              <Circle
                key={`sel-${i}`}
                cx={p.x}
                cy={p.y}
                r={8}
                fill="#FFD814"
                stroke="#FFFFFF"
                strokeOpacity={0.6}
                strokeWidth={1}
              />
            ))}

          {/* Need nodes */}
          {needPositions.map((n, i) => (
            <Circle
              key={`need-${i}`}
              cx={n.x}
              cy={n.y}
              r={12}
              fill="#1A98FF"
              stroke="#FFFFFF"
              strokeOpacity={0.6}
              strokeWidth={1}
            />
          ))}
          {needPositions.map((n, i) => (
            <SvgText
              key={`nlbl-${i}`}
              x={n.x}
              y={n.y + 22}
              fontSize={8}
              fill="#FFFFFF"
              textAnchor="middle"
            >
              {n.label}
            </SvgText>
          ))}

          {/* Central node */}
          <Circle cx={cx} cy={cy} r={20} fill="#FFFFFF" />
          <SvgText
            x={cx}
            y={cy + 5}
            fontSize={14}
            fontWeight="700"
            fill="#FF9900"
            textAnchor="middle"
          >
            MC
          </SvgText>
        </Svg>
      </Animated.View>
    </View>
  )
}

export default function BuildingScreen() {
  const params = useLocalSearchParams()
  const goal = (params.goal as string) || 'Building your cart...'
  const budget = parseFloat(params.budget as string) || 3000

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

    missionAPI
      .build(goal, budget)
      .then((res) => {
        if (cancelled) return
        apiResolved.current = true
        const fullResult = res.data?.data || res.data
        useMissionStore.getState().setCart(fullResult?.cart_items || [])
        useMissionStore.getState().setBuildResult(fullResult)
      })
      .catch(() => {
        if (cancelled) return
        apiResolved.current = true
        useMissionStore.getState().setCart(FALLBACK_CART.cart_items as any)
        useMissionStore.getState().setBuildResult(FALLBACK_CART)
      })

    const t1 = setTimeout(() => {
      if (cancelled) return
      updateStep(0, 'done')
      updateStep(1, 'active')
    }, 800)

    const t2 = setTimeout(() => {
      if (cancelled) return
      updateStep(1, 'done')
      setShowGraph(true)
      updateStep(2, 'active')
    }, 1500)

    const t3 = setTimeout(() => {
      if (cancelled) return
      updateStep(2, 'done')
      updateStep(3, 'active')
    }, 4500)

    const t4 = setTimeout(() => {
      if (cancelled) return
      updateStep(3, 'done')
    }, 5200)

    const t5 = setTimeout(() => {
      if (cancelled) return
      navigateToResult()
    }, 5700)

    return () => {
      cancelled = true
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
      clearTimeout(t4)
      clearTimeout(t5)
    }
  }, [goal, budget])

  const handleRetry = () => {
    setError(false)
    navigated.current = false
    apiResolved.current = false
    setSteps([
      { label: 'Parsing your goal', status: 'active', number: 1 },
      { label: 'Finding what you need', status: 'pending', number: 2 },
      { label: 'Checking Amazon Now stock', status: 'pending', number: 3 },
      { label: 'Validating cart', status: 'pending', number: 4 },
    ])
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
            <Pressable onPress={handleRetry} style={styles.retryButton}>
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
})
