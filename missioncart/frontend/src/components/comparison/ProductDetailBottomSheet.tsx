import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet'
import { Ionicons } from '@expo/vector-icons'
import { useEffect, useMemo, useRef } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'

import { Colors, getLabelColor } from '../../lib/constants'

interface ProductDetailBottomSheetProps {
  item: any | null
  visible: boolean
  onClose: () => void
}

export default function ProductDetailBottomSheet({
  item,
  visible,
  onClose,
}: ProductDetailBottomSheetProps) {
  const sheetRef = useRef<BottomSheet>(null)
  const snapPoints = useMemo(() => ['48%'], [])

  useEffect(() => {
    if (visible) {
      sheetRef.current?.snapToIndex(0)
    } else {
      sheetRef.current?.close()
    }
  }, [visible])

  if (!item) {
    return null
  }

  const palette = getLabelColor(item.need_label || item.title)
  const quantity = item.packs_quantity || 1
  const lineTotal = item.total_cost || item.price * quantity

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
          <Text style={styles.eyebrow}>
            {(item.need_label || 'PRODUCT DETAILS').toUpperCase()}
          </Text>
          <Pressable onPress={onClose} hitSlop={10}>
            <Ionicons name="close" size={20} color={Colors.textSecondary} />
          </Pressable>
        </View>
        <View style={styles.productRow}>
          <View style={[styles.placeholder, { backgroundColor: palette.bg }]}>
            <Text style={[styles.letter, { color: palette.text }]}>
              {(item.title || '?')[0].toUpperCase()}
            </Text>
          </View>
          <View style={styles.productCopy}>
            <Text style={styles.title}>{item.title}</Text>
            <Text style={styles.price}>₹{lineTotal.toLocaleString('en-IN')}</Text>
            <Text style={styles.unitCopy}>
              ₹{(item.price || 0).toLocaleString('en-IN')} × {quantity} pack
              {quantity === 1 ? '' : 's'}
            </Text>
          </View>
        </View>
        <View style={styles.factsRow}>
          <View style={styles.fact}>
            <Ionicons name="star" size={14} color={Colors.starYellow} />
            <Text style={styles.factValue}>{item.rating || '4.0'} rating</Text>
          </View>
          <View style={styles.fact}>
            <Ionicons
              name={item.amazon_now_eligible ? 'flash' : 'time-outline'}
              size={14}
              color={
                item.amazon_now_eligible
                  ? Colors.successGreen
                  : Colors.textSecondary
              }
            />
            <Text style={styles.factValue}>
              {item.amazon_now_eligible ? 'Now · 20 min' : 'Tomorrow'}
            </Text>
          </View>
        </View>
        <View style={styles.reasonBox}>
          <Text style={styles.reasonLabel}>WHY IT FITS</Text>
          <Text style={styles.reasonText}>
            {item.explanation ||
              'Selected for its quantity, delivery speed, and fit with your mission.'}
          </Text>
        </View>
      </BottomSheetScrollView>
    </BottomSheet>
  )
}

const styles = StyleSheet.create({
  sheet: {
    backgroundColor: Colors.white,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
  },
  handle: {
    width: 40,
    backgroundColor: Colors.inputBorder,
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  eyebrow: {
    color: Colors.textSecondary,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.2,
  },
  productRow: {
    marginTop: 16,
    flexDirection: 'row',
  },
  placeholder: {
    width: 76,
    height: 76,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
  },
  letter: {
    fontSize: 30,
    fontWeight: '700',
  },
  productCopy: {
    flex: 1,
    marginLeft: 14,
  },
  title: {
    color: Colors.textPrimary,
    fontSize: 17,
    fontWeight: '700',
  },
  price: {
    marginTop: 5,
    color: Colors.errorRed,
    fontSize: 20,
    fontWeight: '700',
  },
  unitCopy: {
    marginTop: 2,
    color: Colors.textSecondary,
    fontSize: 12,
  },
  factsRow: {
    marginTop: 18,
    flexDirection: 'row',
    gap: 8,
  },
  fact: {
    flex: 1,
    minHeight: 42,
    paddingHorizontal: 10,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBg,
    borderRadius: 4,
  },
  factValue: {
    marginLeft: 6,
    color: Colors.textPrimary,
    fontSize: 12,
    fontWeight: '600',
  },
  reasonBox: {
    marginTop: 16,
    padding: 12,
    backgroundColor: '#FFF8E1',
    borderLeftWidth: 3,
    borderLeftColor: Colors.primary,
    borderRadius: 4,
  },
  reasonLabel: {
    color: Colors.primaryDark,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  reasonText: {
    marginTop: 5,
    color: Colors.textPrimary,
    fontSize: 13,
    lineHeight: 19,
  },
})
