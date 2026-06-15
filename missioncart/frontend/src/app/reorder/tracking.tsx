import { Ionicons } from '@expo/vector-icons'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { useEffect, useState } from 'react'
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { reorderAPI } from '../../lib/api'
import { Colors } from '../../lib/constants'
import { useReorderStore } from '../../store/reorder'

interface TrackingStep {
  step: string
  label: string
  done: boolean
  time: string
}

interface TrackingData {
  order_id: string
  status: string
  steps: TrackingStep[]
  delivery_partner: string
  eta_minutes: number
  can_cancel: boolean
  cancel_window_expired: boolean
}

export default function ReorderTrackingScreen() {
  const router = useRouter()
  const params = useLocalSearchParams<{ order_id?: string }>()
  const storedOrder = useReorderStore((state) => state.order)
  const orderId = params.order_id || storedOrder?.order_id || 'MC-2026-000000'
  const [tracking, setTracking] = useState<TrackingData | null>(null)

  useEffect(() => {
    let cancelled = false
    reorderAPI
      .getOrderStatus(orderId)
      .then((response) => {
        if (!cancelled) {
          setTracking(response.data?.data || response.data)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setTracking({
            order_id: orderId,
            status: 'out_for_delivery',
            delivery_partner: 'Amazon Now',
            eta_minutes: 8,
            can_cancel: false,
            cancel_window_expired: true,
            steps: [
              { step: 'placed', label: 'Order placed', done: true, time: '7:02 AM' },
              { step: 'picked', label: 'Picked from store', done: true, time: '7:08 AM' },
              { step: 'on_the_way', label: 'Out for delivery', done: true, time: '7:14 AM' },
              { step: 'delivered', label: 'Delivered', done: false, time: '~7:22 AM' },
            ],
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [orderId])

  const currentIndex = tracking
    ? Math.max(
        0,
        tracking.steps.findIndex(
          (step, index) =>
            step.done && !tracking.steps[index + 1]?.done,
        ),
      )
    : 0

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </Pressable>
        <View>
          <Text style={styles.headerTitle}>Track Order</Text>
          <Text style={styles.headerSubtitle}>{orderId}</Text>
        </View>
      </View>

      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.mapPlaceholder}>
          <Ionicons name="map-outline" size={48} color="#7B9DC5" />
          <Text style={styles.mapTitle}>Live tracking</Text>
          <Text style={styles.mapCopy}>Amazon Now · Bangalore</Text>
        </View>

        {!tracking ? (
          <View style={styles.loading}>
            <ActivityIndicator color={Colors.primary} />
          </View>
        ) : (
          <>
            <View style={styles.etaCard}>
              <Text style={styles.etaLabel}>Arriving in</Text>
              <Text style={styles.etaValue}>~{tracking.eta_minutes} minutes</Text>
              <Text style={styles.etaCopy}>
                Your delivery partner is nearby
              </Text>
            </View>

            <View style={styles.progressCard}>
              {tracking.steps.map((step, index) => {
                const isCurrent = index === currentIndex
                const isDone = step.done && !isCurrent
                return (
                  <View key={step.step} style={styles.progressRow}>
                    <View style={styles.timelineColumn}>
                      {index > 0 && <View style={styles.lineTop} />}
                      <View
                        style={[
                          styles.progressCircle,
                          isDone && styles.doneCircle,
                          isCurrent && styles.currentCircle,
                          !step.done && styles.pendingCircle,
                        ]}
                      >
                        {isDone && (
                          <Ionicons
                            name="checkmark"
                            size={14}
                            color={Colors.white}
                          />
                        )}
                        {isCurrent && (
                          <Ionicons
                            name="navigate"
                            size={13}
                            color={Colors.white}
                          />
                        )}
                      </View>
                      {index < tracking.steps.length - 1 && (
                        <View style={styles.lineBottom} />
                      )}
                    </View>
                    <View style={styles.progressCopy}>
                      <Text
                        style={[
                          styles.progressLabel,
                          isCurrent && styles.currentLabel,
                        ]}
                      >
                        {step.label}
                      </Text>
                      <Text style={styles.progressTime}>{step.time}</Text>
                    </View>
                  </View>
                )
              })}
            </View>

            <Text
              style={
                tracking.can_cancel
                  ? styles.cancelAction
                  : styles.cancelExpired
              }
            >
              {tracking.can_cancel
                ? 'Cancel order'
                : 'Cancel window expired · Order is on its way'}
            </Text>
          </>
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
  headerTitle: {
    color: Colors.white,
    fontSize: 18,
    fontWeight: '700',
  },
  headerSubtitle: {
    color: Colors.white,
    fontSize: 11,
    opacity: 0.8,
  },
  screen: {
    flex: 1,
    backgroundColor: Colors.secondaryBg,
  },
  content: {
    paddingBottom: 32,
  },
  mapPlaceholder: {
    height: 200,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#E8F0FE',
  },
  mapTitle: {
    marginTop: 8,
    color: '#7B9DC5',
    fontSize: 14,
  },
  mapCopy: {
    color: '#7B9DC5',
    fontSize: 12,
  },
  loading: {
    padding: 40,
  },
  etaCard: {
    marginHorizontal: 16,
    marginTop: 8,
    marginBottom: 8,
    padding: 16,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 8,
  },
  etaLabel: {
    color: Colors.textSecondary,
    fontSize: 13,
  },
  etaValue: {
    color: Colors.textPrimary,
    fontSize: 28,
    fontWeight: '700',
  },
  etaCopy: {
    color: Colors.textSecondary,
    fontSize: 12,
  },
  progressCard: {
    marginHorizontal: 16,
    marginVertical: 8,
    paddingVertical: 8,
  },
  progressRow: {
    minHeight: 72,
    flexDirection: 'row',
  },
  timelineColumn: {
    width: 32,
    alignItems: 'center',
  },
  lineTop: {
    position: 'absolute',
    top: 0,
    width: 2,
    height: 20,
    backgroundColor: Colors.inputBorder,
  },
  lineBottom: {
    position: 'absolute',
    top: 36,
    bottom: 0,
    width: 2,
    backgroundColor: Colors.inputBorder,
  },
  progressCircle: {
    width: 32,
    height: 32,
    marginTop: 4,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 16,
  },
  doneCircle: {
    backgroundColor: Colors.successGreen,
  },
  currentCircle: {
    backgroundColor: Colors.primary,
  },
  pendingCircle: {
    backgroundColor: Colors.background,
    borderWidth: 2,
    borderColor: Colors.inputBorder,
  },
  progressCopy: {
    flex: 1,
    paddingTop: 5,
    paddingLeft: 12,
  },
  progressLabel: {
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '600',
  },
  currentLabel: {
    color: Colors.primaryDark,
    fontWeight: '700',
  },
  progressTime: {
    marginTop: 3,
    color: Colors.textSecondary,
    fontSize: 12,
  },
  cancelAction: {
    color: Colors.errorRed,
    fontSize: 13,
    textAlign: 'center',
  },
  cancelExpired: {
    color: Colors.textSecondary,
    fontSize: 12,
    textAlign: 'center',
  },
})
