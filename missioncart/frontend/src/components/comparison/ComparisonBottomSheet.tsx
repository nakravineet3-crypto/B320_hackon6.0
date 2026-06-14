import { Ionicons } from '@expo/vector-icons'
import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet'
import * as Haptics from 'expo-haptics'
import { useCallback, useEffect, useMemo, useRef } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'

import { Colors, getLabelColor } from '../../lib/constants'
import { useMissionStore } from '../../store/mission'

function firstWords(title: string, count = 3): string {
  return (title || '')
    .split(/\s+/)
    .slice(0, count)
    .join(' ')
}

function ProductColumn({
  item,
  selected,
}: {
  item: any
  selected: boolean
}) {
  const palette = getLabelColor(item.need_label || item.title)
  const letter = (item.title || item.need_label || '?')[0].toUpperCase()

  return (
    <View style={[styles.column, selected && styles.columnSelected]}>
      <View style={[styles.placeholder, { backgroundColor: palette.bg }]}>
        <Text style={[styles.placeholderLetter, { color: palette.text }]}>
          {letter}
        </Text>
      </View>
      <Text style={styles.colTitle} numberOfLines={2}>
        {item.title}
      </Text>
      <Text style={styles.colPrice}>₹{item.price || item.total_cost}</Text>
      <View style={styles.colRatingRow}>
        <Ionicons name="star" size={11} color={Colors.primary} />
        <Text style={styles.colRating}> {item.rating || '4.0'}</Text>
      </View>
      {item.amazon_now_eligible ? (
        <View style={styles.nowBadge}>
          <Text style={styles.badgeText}>Now · 20 min</Text>
        </View>
      ) : (
        <View style={styles.tomorrowBadge}>
          <Text style={styles.badgeText}>Tomorrow</Text>
        </View>
      )}
    </View>
  )
}

export default function ComparisonBottomSheet() {
  const visible = useMissionStore((s) => s.comparisonVisible)
  const itemA = useMissionStore((s) => s.comparisonItemA)
  const itemB = useMissionStore((s) => s.comparisonItemB)
  const dismiss = useMissionStore((s) => s.dismissComparison)

  const sheetRef = useRef<BottomSheet>(null)
  const snapPoints = useMemo(() => ['65%'], [])

  useEffect(() => {
    if (visible) {
      sheetRef.current?.expand()
    } else {
      sheetRef.current?.close()
    }
  }, [visible])

  const handleClose = useCallback(() => {
    dismiss()
  }, [dismiss])

  const handlePick = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {})
    dismiss()
  }

  if (!itemA || !itemB) return null

  const insightText =
    'Option A has better ratings for the price. Option B ships faster on Amazon Now. Since your party is tomorrow, the faster delivery wins.'

  return (
    <BottomSheet
      ref={sheetRef}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={handleClose}
      backgroundStyle={styles.sheetBg}
      handleIndicatorStyle={styles.handleIndicator}
    >
      <BottomSheetScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.headerSection}>
          <View style={styles.headerRow}>
            <Text style={styles.headerTitle}>Compare</Text>
            <Pressable onPress={dismiss} hitSlop={10} accessibilityRole="button">
              <Ionicons name="close" size={20} color={Colors.textSecondary} />
            </Pressable>
          </View>
          <Text style={styles.headerSubtitle}>
            You switched between these{' '}
            <Text style={styles.headerSubtitleAccent}>3 times</Text>
          </Text>
        </View>

        {/* Two product columns */}
        <View style={styles.columnsRow}>
          <ProductColumn item={itemA} selected />
          <ProductColumn item={itemB} selected={false} />
          <View style={styles.vsDivider}>
            <Text style={styles.vsText}>vs</Text>
          </View>
        </View>

        {/* AI insight */}
        <View style={styles.insightBox}>
          <View style={styles.insightHeader}>
            <Ionicons name="analytics-outline" size={14} color={Colors.primary} />
            <Text style={styles.insightLabel}>MissionCart recommendation</Text>
          </View>
          <Text style={styles.insightText}>{insightText}</Text>
        </View>

        {/* Pick buttons */}
        <View style={styles.buttonsRow}>
          <Pressable onPress={handlePick} style={styles.pickButtonPrimary}>
            <Text style={styles.pickButtonPrimaryText}>
              {firstWords(itemA.title)}
            </Text>
          </Pressable>
          <Pressable onPress={handlePick} style={styles.pickButtonSecondary}>
            <Text style={styles.pickButtonSecondaryText}>
              {firstWords(itemB.title)}
            </Text>
          </Pressable>
        </View>
      </BottomSheetScrollView>
    </BottomSheet>
  )
}

const styles = StyleSheet.create({
  sheetBg: {
    backgroundColor: Colors.white,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
  },
  handleIndicator: {
    backgroundColor: Colors.inputBorder,
    width: 40,
  },
  scrollContent: {
    paddingBottom: 32,
  },
  headerSection: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    color: Colors.textPrimary,
    fontSize: 18,
    fontWeight: '700',
  },
  headerSubtitle: {
    marginTop: 4,
    color: Colors.textSecondary,
    fontSize: 13,
  },
  headerSubtitleAccent: {
    color: Colors.primary,
    fontSize: 13,
    fontWeight: '600',
  },
  columnsRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    marginTop: 16,
    gap: 12,
  },
  column: {
    flex: 1,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
    padding: 10,
  },
  columnSelected: {
    borderColor: Colors.primary,
    borderWidth: 2,
  },
  placeholder: {
    width: '100%',
    height: 72,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderLetter: {
    fontSize: 28,
    fontWeight: '700',
  },
  colTitle: {
    color: Colors.textPrimary,
    fontSize: 13,
    fontWeight: '600',
    marginTop: 8,
  },
  colPrice: {
    color: Colors.textPrimary,
    fontSize: 16,
    fontWeight: '700',
    marginTop: 4,
  },
  colRatingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  colRating: {
    color: Colors.textSecondary,
    fontSize: 12,
  },
  nowBadge: {
    backgroundColor: Colors.nowBadge,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 3,
    alignSelf: 'flex-start',
    marginTop: 6,
  },
  tomorrowBadge: {
    backgroundColor: Colors.textSecondary,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 3,
    alignSelf: 'flex-start',
    marginTop: 6,
  },
  badgeText: {
    color: Colors.white,
    fontSize: 10,
    fontWeight: '700',
  },
  vsDivider: {
    position: 'absolute',
    top: 36,
    left: '50%',
    marginLeft: -14,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  vsText: {
    color: Colors.textSecondary,
    fontSize: 11,
    fontWeight: '700',
  },
  insightBox: {
    marginHorizontal: 16,
    marginTop: 12,
    backgroundColor: Colors.cardBg,
    borderRadius: 4,
    borderLeftWidth: 3,
    borderLeftColor: Colors.primary,
    padding: 12,
  },
  insightHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  insightLabel: {
    color: Colors.primary,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
    marginLeft: 6,
  },
  insightText: {
    marginTop: 6,
    color: Colors.textPrimary,
    fontSize: 14,
    lineHeight: 20,
  },
  buttonsRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    marginTop: 12,
    gap: 8,
  },
  pickButtonPrimary: {
    flex: 1,
    height: 48,
    borderRadius: 4,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pickButtonPrimaryText: {
    color: Colors.white,
    fontSize: 14,
    fontWeight: '700',
  },
  pickButtonSecondary: {
    flex: 1,
    height: 48,
    borderRadius: 4,
    backgroundColor: Colors.white,
    borderWidth: 1.5,
    borderColor: Colors.inputBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pickButtonSecondaryText: {
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '400',
  },
})
