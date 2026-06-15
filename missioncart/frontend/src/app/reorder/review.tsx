import { Ionicons } from '@expo/vector-icons'
import * as Haptics from 'expo-haptics'
import { useRouter } from 'expo-router'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { Colors } from '../../lib/constants'
import { useReorderStore } from '../../store/reorder'

function formatInr(value: number) {
  return value.toLocaleString('en-IN')
}

export default function ReorderReviewScreen() {
  const router = useRouter()
  const draft = useReorderStore((state) => state.draft)
  const items = draft?.items || []
  const total = draft?.total_price || 0

  const placeOrder = () => {
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy).catch(() => {})
    router.push('/reorder/placing')
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </Pressable>
        <View>
          <Text style={styles.headerTitle}>Review Order</Text>
          <Text style={styles.headerSubtitle}>Check before placing</Text>
        </View>
      </View>

      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.summaryCard}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardHeaderText}>ORDER SUMMARY</Text>
          </View>
          {items.map((item) => (
            <View key={item.item_id} style={styles.itemRow}>
              <Text style={styles.itemTitle} numberOfLines={2}>
                {item.title}
              </Text>
              <Text style={styles.itemQuantity}>{item.user_quantity} ×</Text>
              <Text style={styles.itemPrice}>
                ₹{formatInr(item.total_cost)}
              </Text>
            </View>
          ))}
          <View style={styles.cardDivider} />
          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Total</Text>
            <Text style={styles.totalValue}>₹{formatInr(total)}</Text>
          </View>
        </View>

        <View style={styles.infoCard}>
          <View style={styles.infoTitleRow}>
            <Ionicons
              name="flash"
              color={Colors.successGreen}
              size={16}
            />
            <Text style={styles.infoTitle}>Amazon Now delivery</Text>
          </View>
          <Text style={styles.infoCopy}>Estimated arrival: ~20 minutes</Text>
        </View>

        <View style={styles.infoCard}>
          <View style={styles.infoTitleRow}>
            <Ionicons
              name="wallet-outline"
              color={Colors.linkBlue}
              size={16}
            />
            <Text style={styles.infoTitle}>Pay on delivery</Text>
          </View>
          <Text style={styles.infoCopy}>Cash or UPI at doorstep</Text>
        </View>

        <View style={styles.cancellationRow}>
          <Ionicons
            name="warning-outline"
            size={14}
            color={Colors.textSecondary}
          />
          <Text style={styles.cancellationText}>
            Orders can be cancelled within 2 minutes of placing
          </Text>
        </View>
      </ScrollView>

      <View style={styles.bottomBar}>
        <Pressable
          disabled={items.length === 0}
          onPress={placeOrder}
          style={[
            styles.placeButton,
            items.length === 0 && styles.disabledButton,
          ]}
        >
          <Text style={styles.placeText}>
            Place Order · ₹{formatInr(total)}
          </Text>
        </Pressable>
      </View>
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
    fontSize: 12,
  },
  screen: {
    flex: 1,
    backgroundColor: Colors.secondaryBg,
  },
  content: {
    paddingBottom: 100,
  },
  summaryCard: {
    margin: 16,
    overflow: 'hidden',
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 8,
    elevation: 2,
  },
  cardHeader: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  cardHeaderText: {
    color: Colors.textSecondary,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  itemRow: {
    minHeight: 44,
    paddingHorizontal: 12,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
  },
  itemTitle: {
    flex: 1,
    color: Colors.textPrimary,
    fontSize: 14,
  },
  itemQuantity: {
    marginHorizontal: 10,
    color: Colors.textSecondary,
    fontSize: 12,
  },
  itemPrice: {
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '700',
  },
  cardDivider: {
    height: 1,
    backgroundColor: Colors.divider,
  },
  totalRow: {
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  totalLabel: {
    color: Colors.textPrimary,
    fontSize: 16,
    fontWeight: '700',
  },
  totalValue: {
    color: Colors.textPrimary,
    fontSize: 20,
    fontWeight: '700',
  },
  infoCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 12,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 8,
  },
  infoTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  infoTitle: {
    marginLeft: 8,
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '700',
  },
  infoCopy: {
    marginTop: 4,
    marginLeft: 24,
    color: Colors.textSecondary,
    fontSize: 12,
  },
  cancellationRow: {
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
  },
  cancellationText: {
    marginLeft: 6,
    color: Colors.textSecondary,
    fontSize: 12,
  },
  bottomBar: {
    position: 'absolute',
    right: 0,
    bottom: 0,
    left: 0,
    padding: 12,
    paddingBottom: 28,
    backgroundColor: Colors.background,
    borderTopWidth: 1,
    borderTopColor: Colors.inputBorder,
  },
  placeButton: {
    width: '100%',
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.primary,
    borderRadius: 4,
  },
  placeText: {
    color: Colors.white,
    fontSize: 16,
    fontWeight: '700',
  },
  disabledButton: {
    opacity: 0.45,
  },
})
