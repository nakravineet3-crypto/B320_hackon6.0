import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet'
import { Ionicons } from '@expo/vector-icons'
import { useEffect, useMemo, useRef } from 'react'
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native'

import { Colors } from '../lib/constants'
import type { ReorderItem } from '../store/reorder'

interface WhyBottomSheetProps {
  visible: boolean
  item: ReorderItem | null
  onClose: () => void
}

const ROWS = [
  {
    icon: 'repeat-outline',
    label: 'Purchase pattern',
    value: (item: ReorderItem) => item.explanation.pattern,
    color: Colors.linkBlue,
  },
  {
    icon: 'calendar-outline',
    label: 'Last purchased',
    value: (item: ReorderItem) =>
      `${item.explanation.last_purchased} · ${item.explanation.days_since} days ago`,
    color: Colors.linkBlue,
  },
  {
    icon: 'time-outline',
    label: 'Expected to run out',
    value: (item: ReorderItem) => item.urgency_copy,
    color: Colors.errorRed,
  },
  {
    icon: 'bar-chart-outline',
    label: 'Purchase history',
    value: (item: ReorderItem) =>
      `${item.explanation.purchase_count} times in last 6 months`,
    color: Colors.linkBlue,
  },
  {
    icon: 'flash-outline',
    label: 'Availability',
    value: (item: ReorderItem) => item.explanation.availability,
    color: Colors.successGreen,
  },
] as const

export default function WhyBottomSheet({
  visible,
  item,
  onClose,
}: WhyBottomSheetProps) {
  const sheetRef = useRef<BottomSheet>(null)
  const snapPoints = useMemo(() => ['45%'], [])

  useEffect(() => {
    if (visible) {
      sheetRef.current?.snapToIndex(0)
    } else {
      sheetRef.current?.close()
    }
  }, [visible])

  const confidenceColor =
    item?.confidence.label === 'High'
      ? Colors.successGreen
      : item?.confidence.label === 'Medium'
        ? Colors.primary
        : Colors.textSecondary

  return (
    <BottomSheet
      ref={sheetRef}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={onClose}
      backgroundStyle={styles.sheet}
      handleIndicatorStyle={styles.handle}
    >
      <BottomSheetScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <View style={styles.headerCopy}>
            <Text style={styles.title}>Why this item?</Text>
            <Text style={styles.subtitle}>{item?.title || ''}</Text>
          </View>
          <TouchableOpacity onPress={onClose} hitSlop={10}>
            <Ionicons name="close" size={20} color={Colors.textSecondary} />
          </TouchableOpacity>
        </View>

        {item &&
          ROWS.map((row) => (
            <View key={row.label} style={styles.row}>
              <Ionicons
                name={row.icon}
                size={16}
                color={row.color}
                style={styles.rowIcon}
              />
              <View style={styles.rowCopy}>
                <Text style={styles.rowLabel}>{row.label}</Text>
                <Text style={[styles.rowValue, { color: row.color }]}>
                  {row.value(item)}
                </Text>
              </View>
            </View>
          ))}

        {item && (
          <View style={styles.confidenceSection}>
            <Text style={styles.confidenceLabel}>Prediction confidence</Text>
            <View style={styles.confidenceTrack}>
              <View
                style={[
                  styles.confidenceFill,
                  {
                    width: `${item.confidence.percentage}%`,
                    backgroundColor: confidenceColor,
                  },
                ]}
              />
            </View>
            <Text style={styles.confidenceCopy}>
              {item.confidence.percentage}% · {item.confidence.label} confidence
            </Text>
          </View>
        )}
      </BottomSheetScrollView>
    </BottomSheet>
  )
}

const styles = StyleSheet.create({
  sheet: {
    backgroundColor: Colors.background,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
  },
  handle: {
    width: 40,
    backgroundColor: Colors.inputBorder,
  },
  content: {
    paddingHorizontal: 16,
    paddingBottom: 28,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  headerCopy: {
    flex: 1,
  },
  title: {
    color: Colors.textPrimary,
    fontSize: 18,
    fontWeight: '700',
  },
  subtitle: {
    marginTop: 2,
    color: Colors.textSecondary,
    fontSize: 13,
  },
  row: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  rowIcon: {
    marginRight: 12,
  },
  rowCopy: {
    flex: 1,
  },
  rowLabel: {
    color: Colors.textSecondary,
    fontSize: 11,
  },
  rowValue: {
    marginTop: 2,
    fontSize: 13,
    fontWeight: '700',
  },
  confidenceSection: {
    marginTop: 16,
  },
  confidenceLabel: {
    color: Colors.textSecondary,
    fontSize: 12,
  },
  confidenceTrack: {
    height: 6,
    marginTop: 8,
    overflow: 'hidden',
    backgroundColor: Colors.divider,
    borderRadius: 3,
  },
  confidenceFill: {
    height: 6,
    borderRadius: 3,
  },
  confidenceCopy: {
    marginTop: 4,
    color: Colors.textSecondary,
    fontSize: 12,
  },
})
