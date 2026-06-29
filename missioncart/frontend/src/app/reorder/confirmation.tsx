import { Ionicons } from '@expo/vector-icons'
import * as Clipboard from 'expo-clipboard'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { useEffect, useRef } from 'react'
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSequence,
  withSpring,
} from 'react-native-reanimated'
import { SafeAreaView } from 'react-native-safe-area-context'

import { Colors } from '../../lib/constants'
import { useReorderStore } from '../../store/reorder'

function formatInr(value: number) {
  return value.toLocaleString('en-IN')
}

export default function ReorderConfirmationScreen() {
  const router = useRouter()
  const params = useLocalSearchParams<{ order_id?: string }>()
  const order = useReorderStore((state) => state.order)
  const draft = useReorderStore((state) => state.draft)
  const scale = useSharedValue(0)
  const fallbackOrderId = useRef(
    `MC-2026-${Math.floor(100000 + Math.random() * 900000)}`,
  ).current
  const orderId =
    params.order_id ||
    order?.order_id ||
    fallbackOrderId
  const items = order?.items || draft?.items || []
  const total = order?.total_price || draft?.total_price || 0

  useEffect(() => {
    scale.value = withSequence(
      withSpring(1.2, { damping: 7, stiffness: 160 }),
      withSpring(1, { damping: 10, stiffness: 180 }),
    )
  }, [scale])

  const checkStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }))

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <Ionicons name="checkmark-circle" color={Colors.white} size={24} />
        <Text style={styles.headerTitle}>Order Placed</Text>
      </View>

      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.centerContent}>
          <Animated.View style={[styles.checkCircle, checkStyle]}>
            <Ionicons name="checkmark" color={Colors.white} size={44} />
          </Animated.View>

          <Text style={styles.orderIdLabel}>ORDER ID</Text>
          <View style={styles.orderIdRow}>
            <Text style={styles.orderId}>{orderId}</Text>
            <Pressable
              onPress={() => void Clipboard.setStringAsync(orderId)}
              hitSlop={10}
            >
              <Ionicons
                name="copy-outline"
                size={14}
                color={Colors.linkBlue}
              />
            </Pressable>
          </View>
        </View>

        <View style={styles.deliveryCard}>
          <View style={styles.deliveryTitleRow}>
            <Ionicons name="flash" color={Colors.successGreen} size={20} />
            <Text style={styles.deliveryTitle}>Arriving in ~20 minutes</Text>
          </View>
          <Text style={styles.deliveryCopy}>
            Your Amazon Now delivery is on the way
          </Text>
        </View>

        <Text style={styles.itemsHeading}>Your order</Text>
        {items.map((item) => (
          <View key={item.item_id} style={styles.itemRow}>
            <Text style={styles.itemName} numberOfLines={1}>
              {item.title}
            </Text>
            <Text style={styles.itemQuantity}>· {item.user_quantity}</Text>
            <Text style={styles.itemPrice}>
              ₹{formatInr(item.total_cost)}
            </Text>
          </View>
        ))}

        <View style={styles.totalRow}>
          <Text style={styles.totalLabel}>Total charged</Text>
          <Text style={styles.totalValue}>₹{formatInr(total)}</Text>
        </View>
      </ScrollView>

      <View style={styles.bottomBar}>
        <TouchableOpacity
          onPress={() =>
            router.push({
              pathname: '/reorder/tracking',
              params: { order_id: orderId },
            })
          }
          style={styles.trackButton}
        >
          <Text style={styles.trackText}>Track Order</Text>
        </TouchableOpacity>
        <Pressable
          onPress={() => router.push('/audit-entry')}
          style={styles.auditLink}
        >
          <Ionicons name="shield-checkmark-outline" size={14} color="#007185" />
          <Text style={styles.auditLinkText}>Audit this order before it ships</Text>
        </Pressable>
        <TouchableOpacity
          onPress={() => router.replace('/')}
          style={styles.homeButton}
        >
          <Text style={styles.homeText}>Back to Home</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.successGreen,
  },
  header: {
    minHeight: 64,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.successGreen,
  },
  headerTitle: {
    marginLeft: 8,
    color: Colors.white,
    fontSize: 20,
    fontWeight: '700',
  },
  screen: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  content: {
    paddingBottom: 150,
  },
  centerContent: {
    paddingTop: 36,
    alignItems: 'center',
  },
  checkCircle: {
    width: 80,
    height: 80,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.successGreen,
    borderRadius: 40,
  },
  orderIdLabel: {
    marginTop: 24,
    color: Colors.textSecondary,
    fontSize: 12,
    letterSpacing: 1,
  },
  orderIdRow: {
    marginTop: 4,
    flexDirection: 'row',
    alignItems: 'center',
  },
  orderId: {
    marginRight: 8,
    color: Colors.textPrimary,
    fontSize: 18,
    fontWeight: '700',
  },
  deliveryCard: {
    marginHorizontal: 16,
    marginVertical: 24,
    padding: 16,
    backgroundColor: '#E7F5EA',
    borderRadius: 8,
  },
  deliveryTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  deliveryTitle: {
    marginLeft: 8,
    color: Colors.successGreen,
    fontSize: 16,
    fontWeight: '700',
  },
  deliveryCopy: {
    marginTop: 4,
    marginLeft: 28,
    color: Colors.textSecondary,
    fontSize: 13,
  },
  itemsHeading: {
    paddingHorizontal: 16,
    color: Colors.textPrimary,
    fontSize: 16,
    fontWeight: '700',
  },
  itemRow: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    flexDirection: 'row',
    alignItems: 'center',
  },
  itemName: {
    flex: 1,
    color: Colors.textPrimary,
    fontSize: 13,
  },
  itemQuantity: {
    marginHorizontal: 8,
    color: Colors.textSecondary,
    fontSize: 12,
  },
  itemPrice: {
    color: Colors.textPrimary,
    fontSize: 13,
    fontWeight: '600',
  },
  totalRow: {
    marginTop: 12,
    paddingHorizontal: 16,
    paddingTop: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderTopWidth: 1,
    borderTopColor: Colors.divider,
  },
  totalLabel: {
    color: Colors.textSecondary,
    fontSize: 13,
  },
  totalValue: {
    color: Colors.textPrimary,
    fontSize: 20,
    fontWeight: '700',
  },
  bottomBar: {
    position: 'absolute',
    right: 0,
    bottom: 0,
    left: 0,
    padding: 16,
    paddingBottom: 28,
    backgroundColor: Colors.background,
    borderTopWidth: 1,
    borderTopColor: Colors.inputBorder,
  },
  trackButton: {
    width: '100%',
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.successGreen,
    borderRadius: 4,
  },
  trackText: {
    color: Colors.white,
    fontSize: 15,
    fontWeight: '700',
  },
  homeButton: {
    width: '100%',
    height: 48,
    marginTop: 8,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
  },
  homeText: {
    color: Colors.textPrimary,
    fontSize: 15,
  },
  auditLink: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 12,
    paddingVertical: 8,
  },
  auditLinkText: {
    color: '#007185',
    fontSize: 13,
    marginLeft: 6,
  },
})
