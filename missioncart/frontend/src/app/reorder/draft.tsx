import AsyncStorage from '@react-native-async-storage/async-storage'
import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import { useCallback, useEffect, useState } from 'react'
import {
  ActivityIndicator,
  FlatList,
  Image,
  Pressable,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import WhyBottomSheet from '../../components/WhyBottomSheet'
import { reorderAPI } from '../../lib/api'
import { Colors, getLabelColor } from '../../lib/constants'
import {
  type ReorderDraft,
  type ReorderItem,
  useReorderStore,
} from '../../store/reorder'

function formatInr(value: number) {
  return value.toLocaleString('en-IN')
}

function confidencePalette(label: string) {
  if (label === 'High') {
    return { backgroundColor: '#E7F5EA', color: Colors.successGreen }
  }
  if (label === 'Medium') {
    return { backgroundColor: '#FFF8E1', color: '#F57F17' }
  }
  return { backgroundColor: Colors.divider, color: Colors.textSecondary }
}

export default function ReorderDraftScreen() {
  const router = useRouter()
  const storedDraft = useReorderStore((state) => state.draft)
  const setStoredDraft = useReorderStore((state) => state.setDraft)
  const setStoredOrder = useReorderStore((state) => state.setOrder)
  const [draft, setDraft] = useState<ReorderDraft | null>(storedDraft)
  const [loading, setLoading] = useState(!storedDraft)
  const [whyItem, setWhyItem] = useState<ReorderItem | null>(null)

  const commitDraft = useCallback(
    (nextDraft: ReorderDraft) => {
      setDraft(nextDraft)
      setStoredDraft(nextDraft)
    },
    [setStoredDraft],
  )

  useEffect(() => {
    let cancelled = false

    const loadDraft = async () => {
      try {
        const existing = await AsyncStorage.getItem('removed_items')
        const removed = existing ? JSON.parse(existing) : []
        const response = await reorderAPI.getDraft(removed)
        const data = response.data?.data || response.data
        if (!cancelled && data?.items) {
          setStoredOrder(null)
          commitDraft(data)
        }
      } catch {
        // Keep any in-memory draft if the API is temporarily unavailable.
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadDraft()
    return () => {
      cancelled = true
    }
  }, [commitDraft, setStoredOrder])

  const updateQty = (item: ReorderItem, newQty: number) => {
    if (!draft || newQty < 1 || newQty > 20) {
      return
    }

    const items = draft.items.map((current) =>
      current.item_id === item.item_id
        ? {
            ...current,
            user_quantity: newQty,
            total_cost: current.price_per_unit * newQty,
          }
        : current,
    )
    commitDraft({
      ...draft,
      items,
      total_price: items.reduce((sum, current) => sum + current.total_cost, 0),
    })

    void reorderAPI
      .updateQuantity(draft.draft_id, item.item_id, newQty)
      .catch(() => {})
  }

  const removeItem = async (itemId: string) => {
    if (!draft) {
      return
    }
    const existing = await AsyncStorage.getItem('removed_items')
    const removedList: string[] = existing ? JSON.parse(existing) : []
    if (!removedList.includes(itemId)) {
      removedList.push(itemId)
      await AsyncStorage.setItem(
        'removed_items',
        JSON.stringify(removedList),
      )
    }

    const items = draft.items.filter((item) => item.item_id !== itemId)
    commitDraft({
      ...draft,
      items,
      item_count: items.length,
      total_price: items.reduce((sum, item) => sum + item.total_cost, 0),
    })
  }

  const reject = async () => {
    if (draft) {
      await reorderAPI.reject(draft.draft_id).catch(() => {})
    }
    router.back()
  }

  const renderItem = ({ item }: { item: ReorderItem }) => {
    const palette = getLabelColor(item.title)
    const confidence = confidencePalette(item.confidence.label)
    const canDecrease = item.user_quantity > 1
    const canIncrease = item.user_quantity < 20

    return (
      <View style={styles.itemCard}>
        <View style={styles.itemTopRow}>
          {item.image_url ? (
            <Image source={{ uri: item.image_url }} style={styles.letterTile} resizeMode="contain" />
          ) : (
            <View style={[styles.letterTile, { backgroundColor: palette.bg }]}>
              <Text style={[styles.letterText, { color: palette.text }]}>
                {item.title.charAt(0).toUpperCase()}
              </Text>
            </View>
          )}

          <View style={styles.itemMain}>
            <Text style={styles.itemTitle} numberOfLines={2}>
              {item.title}
            </Text>
            <View style={styles.predictionRow}>
              <View
                style={[
                  styles.confidencePill,
                  { backgroundColor: confidence.backgroundColor },
                ]}
              >
                <Text
                  style={[styles.confidenceText, { color: confidence.color }]}
                >
                  {item.confidence.label.toUpperCase()} confidence ·{' '}
                  {item.confidence.percentage}%
                </Text>
              </View>
              <Text style={styles.separator}>·</Text>
              <Text style={styles.urgencyCopy}>{item.urgency_copy}</Text>
            </View>
            <TouchableOpacity
              onPress={() => setWhyItem(item)}
              style={styles.whyLink}
            >
              <Ionicons
                name="information-circle-outline"
                size={12}
                color={Colors.linkBlue}
              />
              <Text style={styles.whyText}>Why this?</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.priceColumn}>
            <Text style={styles.itemTotal}>₹{formatInr(item.total_cost)}</Text>
            <Text style={styles.unitPrice}>
              ₹{formatInr(item.price_per_unit)}/unit
            </Text>
          </View>
        </View>

        <View style={styles.controlsRow}>
          <TouchableOpacity
            onPress={() => void removeItem(item.item_id)}
            style={styles.removeButton}
          >
            <Ionicons
              name="trash-outline"
              size={16}
              color={Colors.errorRed}
            />
            <Text style={styles.removeText}>Remove</Text>
          </TouchableOpacity>

          <View style={styles.quantityControls}>
            <TouchableOpacity
              disabled={!canDecrease}
              onPress={() => updateQty(item, item.user_quantity - 1)}
              style={[
                styles.quantityButton,
                !canDecrease && styles.quantityButtonDisabled,
              ]}
            >
              <Ionicons
                name="remove"
                size={16}
                color={canDecrease ? Colors.textPrimary : Colors.inputBorder}
              />
            </TouchableOpacity>
            <View style={styles.quantityDisplay}>
              <Text style={styles.quantityText}>{item.user_quantity}</Text>
            </View>
            <TouchableOpacity
              disabled={!canIncrease}
              onPress={() => updateQty(item, item.user_quantity + 1)}
              style={[
                styles.quantityButton,
                !canIncrease && styles.quantityButtonDisabled,
              ]}
            >
              <Ionicons
                name="add"
                size={16}
                color={canIncrease ? Colors.textPrimary : Colors.inputBorder}
              />
            </TouchableOpacity>
          </View>
        </View>

        <View
          style={[
            styles.deliveryBadge,
            {
              backgroundColor: item.amazon_now_eligible
                ? Colors.successGreen
                : Colors.textSecondary,
            },
          ]}
        >
          {item.amazon_now_eligible && (
            <Ionicons name="flash" size={10} color={Colors.white} />
          )}
          <Text style={styles.deliveryBadgeText}>
            {item.amazon_now_eligible
              ? 'Now · ~20 min'
              : 'Standard delivery'}
          </Text>
        </View>
      </View>
    )
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          style={styles.backButton}
          accessibilityRole="button"
        >
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </Pressable>
        <View>
          <Text style={styles.headerTitle}>Today&apos;s Reorder</Text>
          <Text style={styles.headerSubtitle}>
            {draft?.items.length || 0} items
          </Text>
        </View>
      </View>

      {loading ? (
        <View style={styles.loading}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      ) : (
        <FlatList
          data={draft?.items || []}
          keyExtractor={(item) => item.item_id}
          renderItem={renderItem}
          contentContainerStyle={styles.listContent}
          ListHeaderComponent={
            <>
              <View style={styles.summaryBar}>
                <View>
                  <Text style={styles.summaryTotal}>
                    ₹{formatInr(draft?.total_price || 0)}
                  </Text>
                  <Text style={styles.summaryLabel}>total</Text>
                </View>
                <View style={styles.deliverySummary}>
                  <Ionicons
                    name="flash"
                    color={Colors.successGreen}
                    size={12}
                  />
                  <Text style={styles.deliverySummaryText}>
                    {draft?.delivery_copy || 'Amazon Now · ~20 min'}
                  </Text>
                </View>
              </View>
              <View style={styles.divider} />
              <Text style={styles.sectionLabel}>YOUR REORDER</Text>
            </>
          }
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <Text style={styles.emptyTitle}>No items left in this draft</Text>
              <Text style={styles.emptyCopy}>
                Reset demo data from Discover to restore suggestions.
              </Text>
            </View>
          }
        />
      )}

      <View style={styles.bottomBar}>
        <TouchableOpacity onPress={() => void reject()} style={styles.rejectButton}>
          <Text style={styles.rejectText}>Reject</Text>
        </TouchableOpacity>
        <TouchableOpacity
          disabled={!draft || draft.items.length === 0}
          onPress={() => router.push('/reorder/review')}
          style={[
            styles.reviewOrderButton,
            (!draft || draft.items.length === 0) && styles.disabledButton,
          ]}
        >
          <Text style={styles.reviewOrderText}>Review Order →</Text>
        </TouchableOpacity>
      </View>

      <WhyBottomSheet
        visible={Boolean(whyItem)}
        item={whyItem}
        onClose={() => setWhyItem(null)}
      />
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
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.background,
  },
  listContent: {
    paddingBottom: 110,
    backgroundColor: Colors.background,
  },
  summaryBar: {
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
    borderBottomColor: Colors.inputBorder,
  },
  summaryTotal: {
    color: Colors.textPrimary,
    fontSize: 22,
    fontWeight: '700',
  },
  summaryLabel: {
    color: Colors.textSecondary,
    fontSize: 12,
  },
  deliverySummary: {
    maxWidth: '58%',
    flexDirection: 'row',
    alignItems: 'center',
  },
  deliverySummaryText: {
    marginLeft: 4,
    color: Colors.successGreen,
    fontSize: 13,
    textAlign: 'right',
  },
  divider: {
    height: 8,
    backgroundColor: Colors.divider,
  },
  sectionLabel: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    color: Colors.textSecondary,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  itemCard: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: Colors.background,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  itemTopRow: {
    flexDirection: 'row',
  },
  letterTile: {
    width: 52,
    height: 52,
    marginRight: 12,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 4,
  },
  letterText: {
    fontSize: 20,
    fontWeight: '700',
  },
  itemMain: {
    flex: 1,
  },
  itemTitle: {
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '700',
  },
  predictionRow: {
    marginTop: 4,
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  confidencePill: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 3,
  },
  confidenceText: {
    fontSize: 10,
    fontWeight: '700',
  },
  separator: {
    marginHorizontal: 5,
    color: Colors.textSecondary,
  },
  urgencyCopy: {
    color: Colors.errorRed,
    fontSize: 12,
    fontWeight: '600',
  },
  whyLink: {
    marginTop: 4,
    flexDirection: 'row',
    alignItems: 'center',
  },
  whyText: {
    marginLeft: 3,
    color: Colors.linkBlue,
    fontSize: 12,
  },
  priceColumn: {
    marginLeft: 8,
    alignItems: 'flex-end',
  },
  itemTotal: {
    color: Colors.textPrimary,
    fontSize: 16,
    fontWeight: '700',
  },
  unitPrice: {
    color: Colors.textSecondary,
    fontSize: 11,
  },
  controlsRow: {
    marginTop: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  removeButton: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  removeText: {
    marginLeft: 4,
    color: Colors.errorRed,
    fontSize: 12,
  },
  quantityControls: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  quantityButton: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
  },
  quantityButtonDisabled: {
    borderColor: Colors.divider,
  },
  quantityDisplay: {
    width: 44,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: Colors.inputBorder,
  },
  quantityText: {
    color: Colors.textPrimary,
    fontSize: 15,
    fontWeight: '700',
  },
  deliveryBadge: {
    marginTop: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 3,
  },
  deliveryBadgeText: {
    marginLeft: 3,
    color: Colors.white,
    fontSize: 10,
    fontWeight: '700',
  },
  emptyState: {
    padding: 40,
    alignItems: 'center',
  },
  emptyTitle: {
    color: Colors.textPrimary,
    fontSize: 16,
    fontWeight: '700',
  },
  emptyCopy: {
    marginTop: 6,
    color: Colors.textSecondary,
    fontSize: 13,
    textAlign: 'center',
  },
  bottomBar: {
    position: 'absolute',
    right: 0,
    bottom: 0,
    left: 0,
    padding: 12,
    paddingBottom: 28,
    flexDirection: 'row',
    gap: 8,
    backgroundColor: Colors.background,
    borderTopWidth: 1,
    borderTopColor: Colors.inputBorder,
  },
  rejectButton: {
    flex: 1,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
  },
  rejectText: {
    color: Colors.textSecondary,
    fontSize: 15,
  },
  reviewOrderButton: {
    flex: 2,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.primary,
    borderRadius: 4,
  },
  reviewOrderText: {
    color: Colors.white,
    fontSize: 15,
    fontWeight: '700',
  },
  disabledButton: {
    opacity: 0.45,
  },
})
