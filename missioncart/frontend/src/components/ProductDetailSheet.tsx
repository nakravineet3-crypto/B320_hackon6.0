import React, { useEffect, useRef, useState } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
  Dimensions,
  ScrollView,
} from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import * as Haptics from 'expo-haptics'

interface Props {
  visible: boolean
  product: any | null
  allProducts: any[]
  occasionType: string
  onClose: () => void
  onAddToCart: (product: any) => void
  onCompare: (productA: any, productB: any) => void
}

export default function ProductDetailSheet({
  visible,
  product,
  allProducts,
  occasionType,
  onClose,
  onAddToCart,
  onCompare,
}: Props) {
  const [showSimilar, setShowSimilar] = useState(false)
  const [hesitationFired, setHesitationFired] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  // Reset state when product changes
  useEffect(() => {
    setShowSimilar(false)
    setHesitationFired(false)
  }, [product?.asin])

  // 10-second hesitation timer
  useEffect(() => {
    if (visible && product) {
      timerRef.current = setTimeout(() => {
        if (!hesitationFired) {
          setHesitationFired(true)
          setShowSimilar(true)
        }
      }, 10000)
    }
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
    }
  }, [visible, product?.asin])

  if (!visible || !product) return null

  const similarProducts = allProducts
    .filter((p) => p.category === product.category && p.asin !== product.asin)
    .slice(0, 3)

  const getColor = (category: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      plates: { bg: '#FFF3E0', text: '#E65100' },
      cups: { bg: '#E3F2FD', text: '#1565C0' },
      balloon_set: { bg: '#F3E5F5', text: '#6A1B9A' },
      backpack: { bg: '#E8F5E9', text: '#2E7D32' },
      first_aid: { bg: '#FFEBEE', text: '#B71C1C' },
      water_bottle: { bg: '#E0F7FA', text: '#006064' },
    }
    return colors[category] || { bg: '#F7F8F8', text: '#565959' }
  }

  const color = getColor(product.category)
  const firstLetter = (product.category || product.title || '?')[0].toUpperCase()

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <TouchableOpacity
        style={styles.backdrop}
        activeOpacity={1}
        onPress={onClose}
      />
      <View style={styles.sheet}>
        <View style={styles.handle} />

        <View style={styles.header}>
          <TouchableOpacity onPress={onClose}>
            <Ionicons name="close" size={22} color="#565959" />
          </TouchableOpacity>
          <Text style={styles.headerTitle} numberOfLines={1}>
            {product.title}
          </Text>
          <TouchableOpacity
            onPress={() => {
              if (similarProducts.length > 0) {
                onCompare(product, similarProducts[0])
              }
            }}
          >
            <Text style={styles.compareLink}>Compare</Text>
          </TouchableOpacity>
        </View>

        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.content}
        >
          <View style={styles.productRow}>
            <View style={[styles.placeholder, { backgroundColor: color.bg }]}>
              <Text style={[styles.placeholderText, { color: color.text }]}>
                {firstLetter}
              </Text>
            </View>
            <View style={styles.productInfo}>
              <Text style={styles.price}>₹{product.price}</Text>
              <Text style={styles.packInfo}>
                {product.pack_size} units per pack
              </Text>
              <View style={styles.ratingRow}>
                <Ionicons name="star" size={12} color="#FF9900" />
                <Text style={styles.rating}>{product.rating}</Text>
              </View>
            </View>
          </View>

          {product.badge && (
            <View style={styles.badgeRow}>
              <View
                style={[
                  styles.badge,
                  {
                    backgroundColor:
                      product.badge.colors?.bg || '#F7F8F8',
                  },
                ]}
              >
                <Text
                  style={[
                    styles.badgeText,
                    {
                      color:
                        product.badge.colors?.text || '#565959',
                    },
                  ]}
                >
                  {product.badge.badge_label}
                </Text>
              </View>
              <Text style={styles.badgeReason}>
                {product.badge.badge_reason}
              </Text>
            </View>
          )}

          <View style={styles.specsRow}>
            <View style={styles.spec}>
              <Ionicons
                name="flash"
                size={14}
                color={product.amazon_now_eligible ? '#007600' : '#565959'}
              />
              <Text style={styles.specValue}>
                {product.amazon_now_eligible ? '20 min' : 'Tomorrow'}
              </Text>
              <Text style={styles.specLabel}>Delivery</Text>
            </View>
            <View style={styles.spec}>
              <Ionicons name="cube-outline" size={14} color="#565959" />
              <Text style={styles.specValue}>{product.pack_size} units</Text>
              <Text style={styles.specLabel}>Per pack</Text>
            </View>
            <View style={styles.spec}>
              <Ionicons name="refresh-outline" size={14} color="#565959" />
              <Text style={styles.specValue}>
                {((product.return_risk || 0) * 100).toFixed(0)}%
              </Text>
              <Text style={styles.specLabel}>Returns</Text>
            </View>
          </View>

          {similarProducts.length > 0 && (
            <View style={styles.similarSection}>
              <View style={styles.similarHeader}>
                {showSimilar ? (
                  <>
                    <Ionicons name="sparkles" size={14} color="#FF9900" />
                    <Text style={styles.similarTitle}>
                      Similar options to compare
                    </Text>
                  </>
                ) : (
                  <Text style={styles.similarTitle}>Similar products</Text>
                )}
              </View>
              {similarProducts.map((similar) => {
                const simColor = getColor(similar.category)
                const simLetter = (
                  similar.category ||
                  similar.title ||
                  '?'
                )[0].toUpperCase()
                return (
                  <TouchableOpacity
                    key={similar.asin}
                    style={[
                      styles.similarCard,
                      showSimilar && styles.similarCardHighlighted,
                    ]}
                    onPress={() => onCompare(product, similar)}
                  >
                    <View
                      style={[
                        styles.simPlaceholder,
                        { backgroundColor: simColor.bg },
                      ]}
                    >
                      <Text
                        style={[
                          styles.simPlaceholderText,
                          { color: simColor.text },
                        ]}
                      >
                        {simLetter}
                      </Text>
                    </View>
                    <View style={styles.simInfo}>
                      <Text style={styles.simTitle} numberOfLines={1}>
                        {similar.title}
                      </Text>
                      <Text style={styles.simPrice}>₹{similar.price}</Text>
                      {similar.badge && (
                        <View
                          style={[
                            styles.simBadge,
                            {
                              backgroundColor:
                                similar.badge.colors?.bg || '#F7F8F8',
                            },
                          ]}
                        >
                          <Text
                            style={[
                              styles.simBadgeText,
                              {
                                color:
                                  similar.badge.colors?.text || '#565959',
                              },
                            ]}
                          >
                            {similar.badge.badge_label}
                          </Text>
                        </View>
                      )}
                    </View>
                    <View style={styles.compareBtn}>
                      <Text style={styles.compareBtnText}>Compare</Text>
                    </View>
                  </TouchableOpacity>
                )
              })}
            </View>
          )}
        </ScrollView>

        <View style={styles.bottomButtons}>
          <TouchableOpacity
            style={styles.addBtn}
            onPress={() => {
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium)
              onAddToCart(product)
              onClose()
            }}
          >
            <Text style={styles.addBtnText}>Add to cart</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  )
}

const { height } = Dimensions.get('window')

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' },
  sheet: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    maxHeight: height * 0.8,
    paddingBottom: 32,
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: '#D5D9D9',
    borderRadius: 2,
    alignSelf: 'center',
    marginTop: 8,
    marginBottom: 4,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F2F2',
  },
  headerTitle: {
    flex: 1,
    fontSize: 15,
    fontWeight: '700',
    color: '#0F1111',
    marginHorizontal: 12,
  },
  compareLink: { fontSize: 13, color: '#007185', fontWeight: '600' },
  content: { padding: 16 },
  productRow: { flexDirection: 'row', marginBottom: 16 },
  placeholder: {
    width: 72,
    height: 72,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderText: { fontSize: 28, fontWeight: '700' },
  productInfo: { flex: 1, marginLeft: 12, justifyContent: 'center' },
  price: { fontSize: 24, fontWeight: '700', color: '#CC0C39' },
  packInfo: { fontSize: 12, color: '#565959', marginTop: 4 },
  ratingRow: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
  rating: { fontSize: 12, color: '#565959', marginLeft: 4 },
  badgeRow: { marginBottom: 16 },
  badge: {
    alignSelf: 'flex-start',
    borderRadius: 3,
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginBottom: 4,
  },
  badgeText: { fontSize: 11, fontWeight: '700' },
  badgeReason: { fontSize: 12, color: '#565959' },
  specsRow: { flexDirection: 'row', gap: 8, marginBottom: 20 },
  spec: {
    flex: 1,
    backgroundColor: '#F7F8F8',
    borderRadius: 4,
    padding: 10,
    alignItems: 'center',
  },
  specValue: {
    fontSize: 13,
    fontWeight: '700',
    color: '#0F1111',
    marginTop: 4,
  },
  specLabel: { fontSize: 10, color: '#565959', marginTop: 2 },
  similarSection: {
    borderTopWidth: 1,
    borderTopColor: '#F0F2F2',
    paddingTop: 16,
  },
  similarHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  similarTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0F1111',
    marginLeft: 6,
  },
  similarCard: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F2F2',
  },
  similarCardHighlighted: {
    backgroundColor: '#FFFBF0',
    borderRadius: 4,
    paddingHorizontal: 8,
    borderBottomWidth: 0,
    marginBottom: 4,
  },
  simPlaceholder: {
    width: 44,
    height: 44,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  simPlaceholderText: { fontSize: 18, fontWeight: '700' },
  simInfo: { flex: 1, marginLeft: 10 },
  simTitle: { fontSize: 13, fontWeight: '600', color: '#0F1111' },
  simPrice: { fontSize: 13, color: '#CC0C39', marginTop: 2 },
  simBadge: {
    alignSelf: 'flex-start',
    borderRadius: 3,
    paddingHorizontal: 6,
    paddingVertical: 2,
    marginTop: 4,
  },
  simBadgeText: { fontSize: 10, fontWeight: '700' },
  compareBtn: {
    borderWidth: 1.5,
    borderColor: '#007185',
    borderRadius: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  compareBtnText: { fontSize: 12, color: '#007185', fontWeight: '600' },
  bottomButtons: {
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#F0F2F2',
  },
  addBtn: {
    backgroundColor: '#FF9900',
    height: 48,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  addBtnText: { color: '#FFFFFF', fontSize: 15, fontWeight: '700' },
})
