import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import { useEffect, useRef, useState } from 'react'
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated'
import { SafeAreaView } from 'react-native-safe-area-context'

import { reorderAPI } from '../../lib/api'
import { Colors } from '../../lib/constants'
import { type ReorderOrder, useReorderStore } from '../../store/reorder'

type StepState = 'pending' | 'active' | 'done'

interface PlacementStep {
  label: string
  state: StepState
}

const DEFAULT_STEPS = [
  { step: 'validated', label: 'Cart validated', delay_ms: 800 },
  { step: 'authorized', label: 'Payment authorized', delay_ms: 1600 },
  { step: 'reserved', label: 'Inventory reserved', delay_ms: 2400 },
  { step: 'placed', label: 'Order placed', delay_ms: 3200 },
]

function ActiveSpinner() {
  const rotation = useSharedValue(0)

  useEffect(() => {
    rotation.value = withRepeat(
      withTiming(360, { duration: 800, easing: Easing.linear }),
      -1,
      false,
    )
  }, [rotation])

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${rotation.value}deg` }],
  }))

  return <Animated.View style={[styles.activeArc, animatedStyle]} />
}

export default function ReorderPlacingScreen() {
  const router = useRouter()
  const draft = useReorderStore((state) => state.draft)
  const setOrder = useReorderStore((state) => state.setOrder)
  const idempotencyKey = useRef(
    `${Date.now()}-${Math.random().toString(36).slice(2)}`,
  ).current
  const [steps, setSteps] = useState<PlacementStep[]>(
    DEFAULT_STEPS.map((step, index) => ({
      label: step.label,
      state: index === 0 ? 'active' : 'pending',
    })),
  )
  const [hasError, setHasError] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    let cancelled = false
    const timers: Array<ReturnType<typeof setTimeout>> = []

    const run = async () => {
      const items = draft?.items || []
      const draftId = draft?.draft_id || `DRAFT-${Date.now()}`
      let order: ReorderOrder
      const existingOrder = useReorderStore.getState().order

      try {
        if (existingOrder) {
          order = existingOrder
        } else {
          const response = await reorderAPI.approve(
            draftId,
            idempotencyKey,
            items,
          )
          order = response.data?.data || response.data
        }
      } catch (error) {
        console.error('Approve failed:', error)
        if (!cancelled) {
          setHasError(true)
          setErrorMessage(
            'Could not place your order. Please check your connection and try again.',
          )
        }
        return
      }

      if (cancelled) {
        return
      }
      setOrder(order)
      const apiSteps = order.steps?.length ? order.steps : DEFAULT_STEPS

      apiSteps.forEach((step, index) => {
        timers.push(
          setTimeout(() => {
            if (cancelled) {
              return
            }
            setSteps((current) =>
              current.map((currentStep, currentIndex) => ({
                ...currentStep,
                state:
                  currentIndex <= index
                    ? 'done'
                    : currentIndex === index + 1
                      ? 'active'
                      : 'pending',
              })),
            )
          }, step.delay_ms),
        )
      })

      const finalDelay =
        Math.max(...apiSteps.map((step) => step.delay_ms), 3200) + 500
      timers.push(
        setTimeout(() => {
          if (!cancelled) {
            router.replace({
              pathname: '/reorder/confirmation',
              params: { order_id: order.order_id },
            })
          }
        }, finalDelay),
      )
    }

    void run()
    return () => {
      cancelled = true
      timers.forEach(clearTimeout)
    }
  }, [draft, idempotencyKey, router, setOrder])

  if (hasError) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle-outline" size={56} color="#CC0C39" />
          <Text style={styles.errorTitle}>Order Failed</Text>
          <Text style={styles.errorMessage}>{errorMessage}</Text>
          <TouchableOpacity
            style={styles.retryButton}
            onPress={() => {
              setHasError(false)
              setErrorMessage('')
              router.replace('/reorder/review')
            }}
          >
            <Text style={styles.retryText}>Go back and try again</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.content}>
        <View style={styles.logoRow}>
          <Text style={styles.amazonText}>amazon</Text>
          <Ionicons name="flash" color={Colors.successGreen} size={20} />
          <Text style={styles.nowText}>now</Text>
        </View>

        <Text style={styles.title}>Placing your order...</Text>

        <View style={styles.steps}>
          {steps.map((step, index) => (
            <View key={step.label} style={styles.stepRow}>
              <View
                style={[
                  styles.stepCircle,
                  step.state === 'pending' && styles.pendingCircle,
                  step.state === 'active' && styles.activeCircle,
                  step.state === 'done' && styles.doneCircle,
                ]}
              >
                {step.state === 'pending' && (
                  <Text style={styles.pendingNumber}>{index + 1}</Text>
                )}
                {step.state === 'active' && <ActiveSpinner />}
                {step.state === 'done' && (
                  <Ionicons name="checkmark" size={18} color={Colors.white} />
                )}
              </View>
              <Text
                style={[
                  styles.stepLabel,
                  step.state === 'pending' && styles.pendingLabel,
                  step.state === 'active' && styles.activeLabel,
                  step.state === 'done' && styles.doneLabel,
                ]}
              >
                {step.label}
              </Text>
            </View>
          ))}
        </View>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  content: {
    flex: 1,
    paddingHorizontal: 36,
    justifyContent: 'center',
  },
  logoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  amazonText: {
    color: Colors.textPrimary,
    fontSize: 22,
    fontWeight: '400',
  },
  nowText: {
    color: Colors.successGreen,
    fontSize: 22,
    fontWeight: '700',
  },
  title: {
    marginTop: 32,
    color: Colors.textPrimary,
    fontSize: 20,
    fontWeight: '700',
    textAlign: 'center',
  },
  steps: {
    marginTop: 32,
  },
  stepRow: {
    minHeight: 58,
    flexDirection: 'row',
    alignItems: 'center',
  },
  stepCircle: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 16,
  },
  pendingCircle: {
    borderWidth: 2,
    borderColor: Colors.inputBorder,
  },
  activeCircle: {
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  doneCircle: {
    backgroundColor: Colors.successGreen,
  },
  pendingNumber: {
    color: Colors.inputBorder,
    fontSize: 13,
  },
  activeArc: {
    width: 20,
    height: 20,
    borderWidth: 2,
    borderColor: 'transparent',
    borderTopColor: Colors.primary,
    borderRadius: 10,
  },
  stepLabel: {
    marginLeft: 14,
    fontSize: 15,
  },
  pendingLabel: {
    color: Colors.inputBorder,
  },
  activeLabel: {
    color: Colors.textPrimary,
    fontWeight: '700',
  },
  doneLabel: {
    color: Colors.successGreen,
  },
  errorContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  errorTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#0F1111',
    marginTop: 16,
  },
  errorMessage: {
    fontSize: 14,
    color: '#565959',
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 20,
  },
  retryButton: {
    marginTop: 24,
    backgroundColor: '#FF9900',
    borderRadius: 4,
    paddingHorizontal: 24,
    paddingVertical: 14,
  },
  retryText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
})
