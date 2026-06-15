import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet'
import { Ionicons } from '@expo/vector-icons'
import * as Haptics from 'expo-haptics'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native'

import { comparisonAPI } from '../../lib/api'
import { Colors, getLabelColor } from '../../lib/constants'
import { useMissionStore } from '../../store/mission'

type Choice = 'a' | 'b'

const FALLBACK_WEIGHTS = {
  delivery: 0.3,
  price: 0.3,
  quantity: 0.25,
  quality: 0.15,
}

function firstWords(title: string, count = 3) {
  return (title || 'Choose item').split(/\s+/).slice(0, count).join(' ')
}

function numericValue(value: unknown, fallback = 0) {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

function overallScore(score: any, item: any) {
  if (score?.eliminated) {
    return 0
  }
  return numericValue(
    score?.mission_fit_score ??
      score?.total_score ??
      score?.total ??
      score?.score ??
      item?.mission_fit_score,
  )
}

function dimensionScore(score: any, dimension: string) {
  const aliases: Record<string, string[]> = {
    delivery: ['delivery', 'delivery_speed', 'delivery_score'],
    price: ['price', 'price_value', 'price_score'],
    quantity: ['quantity', 'quantity_fit', 'quantity_score'],
    quality: ['quality', 'quality_score'],
  }
  const breakdown = score?.breakdown || score?.score_breakdown || score || {}

  for (const key of aliases[dimension] || [dimension]) {
    const value = breakdown[key]
    if (typeof value === 'object' && value !== null) {
      return numericValue(value.score ?? value.value)
    }
    if (value !== undefined) {
      return numericValue(value)
    }
  }
  return 0
}

function scorePercent(score: number) {
  return `${Math.round(score * 100)}%`
}

function ProductColumn({
  item,
  score,
  choice,
  winner,
  nearTie,
}: {
  item: any
  score: any
  choice: Choice
  winner: Choice | null
  nearTie: boolean
}) {
  const isWinner = !nearTie && winner === choice
  const palette = getLabelColor(item.need_label || item.title)
  const letter = (item.title || item.need_label || '?')[0].toUpperCase()
  const price = item.price ?? item.total_cost ?? 0
  const missionScore = overallScore(score, item)

  return (
    <View style={[styles.productColumn, isWinner && styles.winnerColumn]}>
      {isWinner && (
        <View style={styles.winnerBadge}>
          <Text style={styles.winnerBadgeText}>
            Best match · {scorePercent(missionScore)}
          </Text>
        </View>
      )}
      <View style={[styles.productPlaceholder, { backgroundColor: palette.bg }]}>
        <Text style={[styles.productLetter, { color: palette.text }]}>
          {letter}
        </Text>
      </View>
      <Text style={styles.productTitle} numberOfLines={2}>
        {item.title}
      </Text>
      <Text style={styles.productPrice}>₹{price.toLocaleString('en-IN')}</Text>
      <View style={styles.ratingRow}>
        <Ionicons name="star" size={11} color={Colors.starYellow} />
        <Text style={styles.ratingText}>{item.rating || '4.0'}</Text>
      </View>
      <View style={styles.productMetaRow}>
        <View
          style={[
            styles.deliveryBadge,
            item.amazon_now_eligible
              ? styles.nowDelivery
              : styles.tomorrowDelivery,
          ]}
        >
          <Text style={styles.deliveryText}>
            {item.amazon_now_eligible ? 'Now' : 'Tomorrow'}
          </Text>
        </View>
        <View style={styles.scorePill}>
          <Text style={styles.scorePillText}>
            {score?.eliminated ? 'Eliminated' : scorePercent(missionScore)}
          </Text>
        </View>
      </View>
    </View>
  )
}

function SkeletonRows() {
  return (
    <View style={styles.rowsWrap}>
      {[0, 1, 2].map((row) => (
        <View key={row} style={styles.comparisonRow}>
          <View style={[styles.skeleton, styles.skeletonLabel]} />
          <View style={[styles.skeleton, styles.skeletonValue]} />
          <View style={[styles.skeleton, styles.skeletonValue]} />
        </View>
      ))}
    </View>
  )
}

function ScoreTraceModal({
  visible,
  onClose,
  comparison,
  missionSpec,
}: {
  visible: boolean
  onClose: () => void
  comparison: any
  missionSpec: any
}) {
  const scoreA = comparison?.score_a || {}
  const scoreB = comparison?.score_b || {}
  const weights =
    comparison?.weights_applied ||
    comparison?.weights ||
    comparison?.classification?.weights ||
    scoreA?.calculation_trace?.weights_applied ||
    scoreB?.calculation_trace?.weights_applied ||
    scoreA?.weights ||
    FALLBACK_WEIGHTS
  const missionType =
    comparison?.mission_type ||
    comparison?.classification?.mission_type ||
    missionSpec?.mission_type ||
    missionSpec?.domain ||
    'balanced'
  const dimensions = [
    { key: 'delivery', label: 'Delivery' },
    { key: 'price', label: 'Price' },
    { key: 'quantity', label: 'Quantity' },
    { key: 'quality', label: 'Quality' },
  ]
  const evidenceA = numericValue(
    scoreA?.evidence?.modifier ??
      comparison?.evidence?.a?.modifier ??
      comparison?.evidence_modifier_a,
    1,
  )
  const evidenceB = numericValue(
    scoreB?.evidence?.modifier ??
      comparison?.evidence?.b?.modifier ??
      comparison?.evidence_modifier_b,
    1,
  )

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.modalBackdrop}>
        <View style={styles.traceCard}>
          <View style={styles.traceHeader}>
            <View>
              <Text style={styles.traceTitle}>Score trace</Text>
              <Text style={styles.traceSubtitle}>
                Mission type: {String(missionType).replace(/_/g, ' ')}
              </Text>
            </View>
            <Pressable onPress={onClose} hitSlop={10}>
              <Ionicons name="close" size={20} color={Colors.textSecondary} />
            </Pressable>
          </View>

          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={styles.traceTable}>
              <View style={[styles.traceRow, styles.traceHeadingRow]}>
                <Text style={[styles.traceCell, styles.traceDimension]}>
                  Dimension
                </Text>
                <Text style={styles.traceCell}>Product A</Text>
                <Text style={styles.traceCell}>Product B</Text>
                <Text style={styles.traceCell}>Weight</Text>
              </View>
              {dimensions.map((dimension) => (
                <View key={dimension.key} style={styles.traceRow}>
                  <Text style={[styles.traceCell, styles.traceDimension]}>
                    {dimension.label}
                  </Text>
                  <Text style={styles.traceCell}>
                    {scoreA?.eliminated
                      ? 'Eliminated'
                      : dimensionScore(scoreA, dimension.key).toFixed(2)}
                  </Text>
                  <Text style={styles.traceCell}>
                    {scoreB?.eliminated
                      ? 'Eliminated'
                      : dimensionScore(scoreB, dimension.key).toFixed(2)}
                  </Text>
                  <Text style={styles.traceCell}>
                    {numericValue(weights[dimension.key]).toFixed(2)}
                  </Text>
                </View>
              ))}
              <View style={[styles.traceRow, styles.traceScoreRow]}>
                <Text style={[styles.traceCell, styles.traceDimension]}>
                  Score
                </Text>
                <Text style={styles.traceCell}>
                  {scoreA?.eliminated
                    ? 'Eliminated'
                    : overallScore(scoreA, {}).toFixed(2)}
                </Text>
                <Text style={styles.traceCell}>
                  {scoreB?.eliminated
                    ? 'Eliminated'
                    : overallScore(scoreB, {}).toFixed(2)}
                </Text>
                <Text style={styles.traceCell}>
                  Winner: {String(comparison?.winner || '').toUpperCase()}
                </Text>
              </View>
            </View>
          </ScrollView>

          <View style={styles.traceNotes}>
            <Text style={styles.traceNote}>
              Evidence modifier: A {evidenceA.toFixed(2)} · B{' '}
              {evidenceB.toFixed(2)}
            </Text>
            <Text style={styles.traceNote}>
              Confidence logic:{' '}
              {comparison?.near_tie
                ? 'Score gap is below the near-tie threshold.'
                : `${comparison?.confidence || 'moderate'} confidence from the weighted score gap.`}
            </Text>
            {comparison?.eliminations?.length ? (
              <Text style={styles.traceNote}>
                Eliminations:{' '}
                {comparison.eliminations
                  .map((entry: any) => {
                    const reasons = (entry.reasons || [])
                      .map((reason: any) => reason.reason || reason.rule)
                      .join('; ')
                    return `${String(entry.product).toUpperCase()}: ${reasons}`
                  })
                  .join(' · ')}
              </Text>
            ) : null}
          </View>
        </View>
      </View>
    </Modal>
  )
}

export default function ComparisonBottomSheet() {
  const visible = useMissionStore((state) => state.comparisonVisible)
  const itemA = useMissionStore((state) => state.comparisonItemA)
  const itemB = useMissionStore((state) => state.comparisonItemB)
  const dismiss = useMissionStore((state) => state.dismissComparison)
  const buildResult = useMissionStore((state) => state.currentBuildResult)
  const [comparison, setComparison] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [traceVisible, setTraceVisible] = useState(false)
  const sheetRef = useRef<BottomSheet>(null)
  const snapPoints = useMemo(() => ['76%'], [])

  const missionSpec = useMemo(
    () =>
      buildResult?.mission_spec ||
      buildResult?.spec || {
        goal: buildResult?.goal || 'Shopping mission',
        domain: buildResult?.domain || 'general',
        occasion_type: buildResult?.occasion_type || buildResult?.domain || 'general',
        headcount: buildResult?.headcount || 1,
        budget_max:
          buildResult?.budget_max ??
          numericValue(buildResult?.total_cost) +
            numericValue(buildResult?.budget_remaining),
        budget_remaining: buildResult?.budget_remaining || 0,
        deadline_hours: buildResult?.deadline_hours,
        safety_context: buildResult?.safety_context || 'general',
      },
    [buildResult],
  )

  useEffect(() => {
    if (visible) {
      sheetRef.current?.snapToIndex(0)
    } else {
      sheetRef.current?.close()
      setTraceVisible(false)
    }
  }, [visible])

  useEffect(() => {
    let cancelled = false
    if (!visible || !itemA || !itemB) {
      return
    }

    setComparison(null)
    setLoading(true)
    comparisonAPI
      .evaluate(itemA, itemB, missionSpec)
      .then((response) => {
        if (!cancelled) {
          setComparison(response.data?.data || null)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setComparison(null)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [itemA, itemB, missionSpec, visible])

  if (!itemA || !itemB) {
    return null
  }

  const winner: Choice | null =
    comparison?.winner === 'a' || comparison?.winner === 'b'
      ? comparison.winner
      : null
  const nearTie = comparison?.near_tie === true
  const rows = comparison?.comparison_rows || []
  const explanation =
    typeof comparison?.explanation === 'string'
      ? comparison.explanation
      : comparison?.explanation?.summary ||
        comparison?.explanation?.text ||
        'The recommendation uses delivery, total cost, quantity fit, and quality.'
  const costWinner =
    rows.find((row: any) => /cost|price/i.test(row.label))?.winner || 'a'
  const alternativeRow = rows.find(
    (row: any) =>
      row.winner &&
      row.winner !== 'tie' &&
      row.winner !== costWinner,
  )
  const tradeoffA =
    costWinner === 'a'
      ? 'Pick A for lower total cost.'
      : `Pick A for ${alternativeRow?.label?.toLowerCase() || 'its product fit'}.`
  const tradeoffB =
    costWinner === 'b'
      ? 'Pick B for lower total cost.'
      : `Pick B for ${alternativeRow?.label?.toLowerCase() || 'its product fit'}.`

  const pickProduct = (choice: Choice) => {
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {})

    const chosenItem = choice === 'a' ? itemA : itemB
    const replacedItem = choice === 'a' ? itemB : itemA
    const store = useMissionStore.getState()
    const originalCart = [...(store.currentCart || store.cart || [])]
    const originalBuildResult = store.currentBuildResult
    const updatedCart = originalCart.map((item) =>
      item.cart_item_id === replacedItem.cart_item_id
        ? { ...chosenItem, cart_item_id: replacedItem.cart_item_id }
        : item,
    )
    const newTotal = updatedCart.reduce(
      (sum, item) => sum + numericValue(item.total_cost),
      0,
    )

    store.setCart(updatedCart)
    if (originalBuildResult) {
      store.setBuildResult({ ...originalBuildResult, total_cost: newTotal })
    }
    dismiss()
    store.showUndoToast({
      message: 'Cart updated · Undo',
      onUndo: () => {
        store.setCart(originalCart)
        if (originalBuildResult) {
          store.setBuildResult(originalBuildResult)
        }
      },
      duration: 4000,
    })
  }

  return (
    <>
      <BottomSheet
        ref={sheetRef}
        index={-1}
        snapPoints={snapPoints}
        enablePanDownToClose
        onClose={dismiss}
        backgroundStyle={styles.sheetBackground}
        handleIndicatorStyle={styles.handleIndicator}
      >
        <BottomSheetScrollView contentContainerStyle={styles.content}>
          <View style={styles.header}>
            <View style={styles.headerRow}>
              <Text style={styles.headerTitle}>
                {nearTie
                  ? "Both are close — here's the tradeoff"
                  : 'Need help choosing?'}
              </Text>
              <Pressable onPress={dismiss} hitSlop={10}>
                <Ionicons name="close" size={20} color={Colors.textSecondary} />
              </Pressable>
            </View>
            <Text style={styles.headerSubtitle}>
              Goal-aware · Deterministic scoring
            </Text>
          </View>

          <View style={styles.productsRow}>
            <ProductColumn
              item={itemA}
              score={comparison?.score_a}
              choice="a"
              winner={winner}
              nearTie={nearTie}
            />
            <ProductColumn
              item={itemB}
              score={comparison?.score_b}
              choice="b"
              winner={winner}
              nearTie={nearTie}
            />
            <View style={styles.vsCircle}>
              <Text style={styles.vsText}>vs</Text>
            </View>
          </View>

          {loading ? (
            <SkeletonRows />
          ) : (
            <View style={styles.rowsWrap}>
              {rows.slice(0, 3).map((row: any) => (
                <View key={row.label} style={styles.comparisonRow}>
                  <Text style={styles.rowLabel}>{row.label}</Text>
                  <Text
                    style={[
                      styles.rowValue,
                      row.winner === 'a' && styles.rowWinner,
                    ]}
                  >
                    {row.a_value}
                  </Text>
                  <Text
                    style={[
                      styles.rowValue,
                      row.winner === 'b' && styles.rowWinner,
                    ]}
                  >
                    {row.b_value}
                  </Text>
                </View>
              ))}
            </View>
          )}

          {!loading && comparison ? (
            <View style={styles.factorWrap}>
              {comparison?.dominant_factor ? (
                <Text style={styles.factorBadge}>
                  Decided by:{' '}
                  {String(comparison.dominant_factor).replace(/_/g, ' ')}
                </Text>
              ) : null}
              <Text
                style={[
                  styles.confidenceBadge,
                  nearTie && styles.nearTieConfidenceBadge,
                ]}
              >
                {nearTie
                  ? 'Near tie'
                  : `${String(comparison.confidence || 'moderate').replace(/_/g, ' ')} confidence`}
              </Text>
            </View>
          ) : null}

          <View style={[styles.insightBox, nearTie && styles.nearTieBox]}>
            {nearTie ? (
              <>
                <Text style={styles.nearTieTitle}>
                  These products are very close.
                </Text>
                <Text style={styles.tradeoffText}>{tradeoffA}</Text>
                <Text style={styles.tradeoffText}>{tradeoffB}</Text>
              </>
            ) : (
              <>
                <View style={styles.insightHeader}>
                  <Ionicons
                    name="analytics-outline"
                    size={12}
                    color={Colors.primary}
                  />
                  <Text style={styles.insightLabel}>
                    MissionCart recommendation
                  </Text>
                </View>
                <Text
                  style={[styles.insightText, loading && styles.loadingInsight]}
                >
                  {loading ? 'Calculating deterministic scores...' : explanation}
                </Text>
              </>
            )}
          </View>

          <View style={styles.buttonsRow}>
            <Pressable
              onPress={() => pickProduct('a')}
              style={[
                styles.pickButton,
                !nearTie && winner === 'a'
                  ? styles.winnerButton
                  : styles.standardButton,
              ]}
            >
              <Text
                style={[
                  styles.pickButtonText,
                  !nearTie && winner === 'a' && styles.winnerButtonText,
                ]}
                numberOfLines={1}
              >
                {nearTie
                  ? costWinner === 'a'
                    ? 'Pick for cost'
                    : 'Pick for quality'
                  : firstWords(itemA.title)}
              </Text>
            </Pressable>
            <Pressable
              onPress={() => pickProduct('b')}
              style={[
                styles.pickButton,
                !nearTie && winner === 'b'
                  ? styles.winnerButton
                  : styles.standardButton,
              ]}
            >
              <Text
                style={[
                  styles.pickButtonText,
                  !nearTie && winner === 'b' && styles.winnerButtonText,
                ]}
                numberOfLines={1}
              >
                {nearTie
                  ? costWinner === 'b'
                    ? 'Pick for cost'
                    : 'Pick for quality'
                  : firstWords(itemB.title)}
              </Text>
            </Pressable>
          </View>

          {!loading && comparison ? (
            <Pressable
              onPress={() => setTraceVisible(true)}
              style={styles.traceButton}
            >
              <Text style={styles.traceButtonText}>View score trace →</Text>
            </Pressable>
          ) : null}
        </BottomSheetScrollView>
      </BottomSheet>

      <ScoreTraceModal
        visible={traceVisible}
        onClose={() => setTraceVisible(false)}
        comparison={comparison}
        missionSpec={missionSpec}
      />
    </>
  )
}

const styles = StyleSheet.create({
  sheetBackground: {
    backgroundColor: Colors.white,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
  },
  handleIndicator: {
    width: 40,
    backgroundColor: Colors.inputBorder,
  },
  content: {
    paddingBottom: 32,
  },
  header: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  headerTitle: {
    flex: 1,
    marginRight: 12,
    color: Colors.textPrimary,
    fontSize: 18,
    fontWeight: '700',
  },
  headerSubtitle: {
    marginTop: 2,
    color: Colors.textSecondary,
    fontSize: 12,
  },
  productsRow: {
    marginTop: 16,
    paddingHorizontal: 16,
    flexDirection: 'row',
    gap: 8,
  },
  productColumn: {
    flex: 1,
    minHeight: 202,
    padding: 10,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 8,
  },
  winnerColumn: {
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  winnerBadge: {
    position: 'absolute',
    top: 6,
    right: 6,
    zIndex: 2,
    paddingHorizontal: 6,
    paddingVertical: 2,
    backgroundColor: Colors.primary,
    borderRadius: 3,
  },
  winnerBadgeText: {
    color: Colors.white,
    fontSize: 9,
    fontWeight: '700',
  },
  productPlaceholder: {
    width: 60,
    height: 60,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 4,
  },
  productLetter: {
    fontSize: 24,
    fontWeight: '700',
  },
  productTitle: {
    minHeight: 34,
    marginTop: 8,
    color: Colors.textPrimary,
    fontSize: 13,
    fontWeight: '600',
  },
  productPrice: {
    marginTop: 4,
    color: Colors.errorRed,
    fontSize: 16,
    fontWeight: '700',
  },
  ratingRow: {
    marginTop: 3,
    flexDirection: 'row',
    alignItems: 'center',
  },
  ratingText: {
    marginLeft: 3,
    color: Colors.textSecondary,
    fontSize: 11,
  },
  productMetaRow: {
    marginTop: 6,
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 4,
  },
  deliveryBadge: {
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 3,
  },
  nowDelivery: {
    backgroundColor: Colors.successGreen,
  },
  tomorrowDelivery: {
    backgroundColor: Colors.textSecondary,
  },
  deliveryText: {
    color: Colors.white,
    fontSize: 10,
    fontWeight: '700',
  },
  scorePill: {
    paddingHorizontal: 6,
    paddingVertical: 3,
    backgroundColor: Colors.cardBg,
    borderRadius: 3,
  },
  scorePillText: {
    color: Colors.textSecondary,
    fontSize: 10,
  },
  vsCircle: {
    position: 'absolute',
    top: 42,
    left: '50%',
    zIndex: 3,
    width: 28,
    height: 28,
    marginLeft: -14,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 14,
  },
  vsText: {
    color: Colors.textSecondary,
    fontSize: 10,
    fontWeight: '700',
  },
  rowsWrap: {
    marginHorizontal: 16,
    marginTop: 12,
  },
  comparisonRow: {
    minHeight: 50,
    paddingVertical: 8,
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  rowLabel: {
    width: 90,
    color: Colors.textSecondary,
    fontSize: 12,
  },
  rowValue: {
    flex: 1,
    paddingHorizontal: 4,
    color: Colors.textPrimary,
    fontSize: 12,
  },
  rowWinner: {
    color: Colors.successGreen,
    fontWeight: '700',
  },
  skeleton: {
    height: 10,
    backgroundColor: Colors.divider,
    borderRadius: 3,
  },
  skeletonLabel: {
    width: 76,
    marginRight: 14,
  },
  skeletonValue: {
    flex: 1,
    marginHorizontal: 4,
  },
  factorWrap: {
    marginTop: 8,
    marginHorizontal: 16,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    alignItems: 'flex-start',
  },
  factorBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    overflow: 'hidden',
    color: Colors.textSecondary,
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.5,
    backgroundColor: Colors.divider,
    borderRadius: 3,
  },
  confidenceBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    overflow: 'hidden',
    color: Colors.successGreen,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
    backgroundColor: '#E7F5EA',
    borderRadius: 3,
    textTransform: 'capitalize',
  },
  nearTieConfidenceBadge: {
    color: Colors.textSecondary,
    backgroundColor: Colors.divider,
  },
  insightBox: {
    marginHorizontal: 16,
    marginVertical: 12,
    padding: 12,
    backgroundColor: Colors.cardBg,
    borderLeftWidth: 3,
    borderLeftColor: Colors.primary,
    borderRadius: 4,
  },
  nearTieBox: {
    borderLeftColor: Colors.textSecondary,
  },
  insightHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  insightLabel: {
    marginLeft: 4,
    color: Colors.primary,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  insightText: {
    marginTop: 6,
    color: Colors.textPrimary,
    fontSize: 14,
    lineHeight: 20,
  },
  loadingInsight: {
    color: Colors.textSecondary,
    fontStyle: 'italic',
  },
  nearTieTitle: {
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '700',
  },
  tradeoffText: {
    marginTop: 5,
    color: Colors.textPrimary,
    fontSize: 13,
    lineHeight: 18,
  },
  buttonsRow: {
    marginHorizontal: 16,
    marginTop: 12,
    flexDirection: 'row',
    gap: 8,
  },
  pickButton: {
    flex: 1,
    height: 48,
    paddingHorizontal: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 4,
  },
  winnerButton: {
    backgroundColor: Colors.primary,
  },
  standardButton: {
    backgroundColor: Colors.white,
    borderWidth: 1.5,
    borderColor: Colors.inputBorder,
  },
  pickButtonText: {
    color: Colors.textPrimary,
    fontSize: 13,
    fontWeight: '600',
  },
  winnerButtonText: {
    color: Colors.white,
    fontWeight: '700',
  },
  traceButton: {
    alignSelf: 'center',
    marginTop: 14,
    padding: 8,
  },
  traceButtonText: {
    color: Colors.linkBlue,
    fontSize: 11,
  },
  modalBackdrop: {
    flex: 1,
    padding: 20,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(15,17,17,0.48)',
  },
  traceCard: {
    width: '100%',
    maxHeight: '80%',
    padding: 16,
    backgroundColor: Colors.white,
    borderRadius: 8,
    elevation: 12,
  },
  traceHeader: {
    marginBottom: 14,
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  traceTitle: {
    color: Colors.textPrimary,
    fontSize: 18,
    fontWeight: '700',
  },
  traceSubtitle: {
    marginTop: 2,
    color: Colors.textSecondary,
    fontSize: 12,
  },
  traceTable: {
    minWidth: 460,
  },
  traceRow: {
    minHeight: 38,
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  traceHeadingRow: {
    backgroundColor: Colors.cardBg,
  },
  traceScoreRow: {
    borderTopWidth: 2,
    borderTopColor: Colors.inputBorder,
  },
  traceCell: {
    width: 95,
    paddingHorizontal: 8,
    color: Colors.textPrimary,
    fontSize: 12,
    textAlign: 'center',
  },
  traceDimension: {
    width: 130,
    color: Colors.textSecondary,
    textAlign: 'left',
  },
  traceNotes: {
    marginTop: 14,
    padding: 10,
    backgroundColor: Colors.cardBg,
    borderRadius: 4,
  },
  traceNote: {
    marginVertical: 2,
    color: Colors.textSecondary,
    fontSize: 11,
    lineHeight: 16,
  },
})
