import { Ionicons } from '@expo/vector-icons'
import * as Haptics from 'expo-haptics'
import { useRouter } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useEffect, useRef, useState } from 'react'
import {
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import HesitationCard from '../components/HesitationCard'
import ProductDetailSheet from '../components/ProductDetailSheet'
import ComparisonBottomSheet from '../components/comparison/ComparisonBottomSheet'
import { searchAPI } from '../lib/api'
import { Colors } from '../lib/constants'
import { useMissionStore } from '../store/mission'

interface ProductResult {
  asin: string
  title: string
  category: string
  price: number
  pack_size: number
  rating: number
  return_risk: number
  amazon_now_eligible: boolean
  delivery_eta: string
  sponsored: boolean
  stock_available: boolean
  safety_tags: string[]
  badge?: {
    badge_type: string
    badge_label: string
    badge_reason: string
    colors?: { bg: string; text: string }
    simulated_data?: boolean
  }
}

export default function SearchScreen() {
  const router = useRouter()
  const inputRef = useRef<TextInput>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ProductResult[]>([])
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  // Product detail
  const [selectedProduct, setSelectedProduct] = useState<any>(null)
  const [showDetailSheet, setShowDetailSheet] = useState(false)

  // Hesitation on search list
  const [showHesitationCard, setShowHesitationCard] = useState(false)
  const [hesitationShown, setHesitationShown] = useState(false)
  const [hasScrolled, setHasScrolled] = useState(false)
  const lastScrollTimeRef = useRef<number>(0)
  const hesitationTimerRef = useRef<ReturnType<typeof setInterval>>()

  // Switching detection
  const [viewHistory, setViewHistory] = useState<
    Array<{ asin: string; category: string; time: number }>
  >([])
  const [showCompareChip, setShowCompareChip] = useState(false)
  const [compareItemA, setCompareItemA] = useState<any>(null)
  const [compareItemB, setCompareItemB] = useState<any>(null)

  // Session cart
  const [sessionCart, setSessionCart] = useState<any[]>([])

  // Badge mode
  const [badgeMode, setBadgeMode] = useState(false)

  // Zustand store
  const setComparisonItems = useMissionStore((s) => s.setComparisonItems)

  // Focus input after screen transition
  useEffect(() => {
    const timer = setTimeout(() => {
      inputRef.current?.focus()
    }, 300)
    return () => clearTimeout(timer)
  }, [])

  // Load initial suggestions
  useEffect(() => {
    searchAPI
      .suggest('')
      .then((res) => {
        if (res.data?.data?.suggestions) {
          setSuggestions(res.data.data.suggestions)
        }
      })
      .catch(() => {})
  }, [])

  // Hesitation detection: fires when user scrolled but stops for 5s
  useEffect(() => {
    hesitationTimerRef.current = setInterval(() => {
      if (
        hasScrolled &&
        !hesitationShown &&
        !showHesitationCard &&
        results.length > 0 &&
        Date.now() - lastScrollTimeRef.current > 5000 &&
        lastScrollTimeRef.current > 0
      ) {
        setShowHesitationCard(true)
      }
    }, 1000)
    return () => {
      if (hesitationTimerRef.current) {
        clearInterval(hesitationTimerRef.current)
      }
    }
  }, [hasScrolled, hesitationShown, showHesitationCard, results.length])

  const handleSearch = async (text: string) => {
    setQuery(text)

    if (!text.trim()) {
      setResults([])
      setHasSearched(false)
      searchAPI
        .suggest('')
        .then((res) => {
          if (res.data?.data?.suggestions) {
            setSuggestions(res.data.data.suggestions)
          }
        })
        .catch(() => {})
      return
    }

    if (text.length >= 2) {
      searchAPI
        .suggest(text)
        .then((res) => {
          if (res.data?.data?.suggestions) {
            setSuggestions(res.data.data.suggestions)
          }
        })
        .catch(() => {})
    }

    if (text.length >= 2) {
      setLoading(true)
      setHasSearched(true)
      try {
        const res = await searchAPI.search(text)
        if (res.data?.data?.products) {
          setResults(res.data.data.products)
        }
      } catch {
        setResults([])
      }
      setLoading(false)
    }
  }

  const handleSuggestionTap = (suggestion: string) => {
    setQuery(suggestion)
    handleSearch(suggestion)
  }

  const handleScroll = () => {
    if (!hasScrolled) setHasScrolled(true)
    lastScrollTimeRef.current = Date.now()
  }

  const handleProductTap = (product: any) => {
    const now = Date.now()
    setViewHistory((prev) => {
      const updated = [
        ...prev,
        { asin: product.asin, category: product.category, time: now },
      ].slice(-10)

      // Check for switching pattern within last 60 seconds
      const recent = updated.filter((v) => now - v.time < 60000).slice(-6)
      const uniqueAsins = [...new Set(recent.map((v) => v.asin))]

      if (uniqueAsins.length === 2) {
        const bothSameCategory = recent.every(
          (v) => v.category === product.category,
        )
        const countA = recent.filter((v) => v.asin === uniqueAsins[0]).length
        const countB = recent.filter((v) => v.asin === uniqueAsins[1]).length

        if (countA >= 3 && countB >= 3 && bothSameCategory) {
          const prodA = results.find((p) => p.asin === uniqueAsins[0])
          const prodB = results.find((p) => p.asin === uniqueAsins[1])
          if (prodA && prodB) {
            setComparisonItems(prodA, prodB)
            setShowCompareChip(false)
            return []
          }
        }

        if (countA >= 2 && countB >= 1 && bothSameCategory) {
          const prodA = results.find((p) => p.asin === uniqueAsins[0])
          const prodB = results.find((p) => p.asin === uniqueAsins[1])
          if (prodA && prodB) {
            setCompareItemA(prodA)
            setCompareItemB(prodB)
            setShowCompareChip(true)
          }
        }
      }

      return updated
    })

    // Open product detail
    setSelectedProduct(product)
    setShowDetailSheet(true)
  }

  const handleAddToCart = (product: any) => {
    setSessionCart((prev) => {
      const existing = prev.find((p) => p.asin === product.asin)
      if (existing) {
        return prev.map((p) =>
          p.asin === product.asin
            ? { ...p, quantity: p.quantity + 1 }
            : p,
        )
      }
      return [...prev, { ...product, quantity: 1 }]
    })
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium)
  }

  const handleCompareFromDetail = (productA: any, productB: any) => {
    setShowDetailSheet(false)
    setComparisonItems(productA, productB)
    setViewHistory([])
    setShowCompareChip(false)
  }

  const renderProduct = ({ item }: { item: ProductResult }) => (
    <TouchableOpacity
      onPress={() => handleProductTap(item)}
      activeOpacity={0.8}
      style={styles.productRow}
    >
      <View style={styles.productLetter}>
        <Text style={styles.productLetterText}>
          {item.title[0].toUpperCase()}
        </Text>
      </View>
      <View style={styles.productInfo}>
        <Text style={styles.productTitle} numberOfLines={1}>
          {item.title}
        </Text>
        <View style={styles.productMeta}>
          <Text style={styles.productPrice}>₹{item.price}</Text>
          <Text style={styles.productRating}>⭐ {item.rating}</Text>
          {item.amazon_now_eligible && (
            <View style={styles.nowBadge}>
              <Text style={styles.nowBadgeText}>⚡ Now</Text>
            </View>
          )}
          {item.sponsored && (
            <View style={styles.sponsoredBadge}>
              <Text style={styles.sponsoredText}>Sponsored</Text>
            </View>
          )}
        </View>
        {item.badge?.badge_label && (
          <View
            style={[
              styles.badgePill,
              { backgroundColor: item.badge.colors?.bg || '#007185' },
            ]}
          >
            <Text
              style={[
                styles.badgePillText,
                { color: item.badge.colors?.text || '#FFFFFF' },
              ]}
            >
              {item.badge.badge_label}
            </Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  )

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar style="dark" backgroundColor={Colors.background} />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => router.back()}
            style={styles.backBtn}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons name="arrow-back" size={22} color={Colors.textPrimary} />
          </TouchableOpacity>
          <View style={styles.inputContainer}>
            <Ionicons name="search" size={18} color="#9AA0A6" />
            <TextInput
              ref={inputRef}
              style={styles.input}
              value={query}
              onChangeText={handleSearch}
              placeholder="Search products..."
              placeholderTextColor="#9AA0A6"
              returnKeyType="search"
              autoCapitalize="none"
              autoCorrect={false}
              clearButtonMode="while-editing"
            />
            {query.length > 0 && (
              <TouchableOpacity onPress={() => handleSearch('')} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                <Ionicons name="close-circle" size={18} color="#9AA0A6" />
              </TouchableOpacity>
            )}
          </View>
        </View>

        {/* SUGGESTIONS */}
        {!hasSearched && suggestions.length > 0 && (
          <View style={styles.suggestionsSection}>
            <Text style={styles.suggestionsLabel}>
              {query.length >= 2 ? 'Suggestions' : 'Popular categories'}
            </Text>
            {suggestions.map((s, idx) => (
              <TouchableOpacity
                key={idx}
                style={styles.suggestionRow}
                onPress={() => handleSuggestionTap(s)}
              >
                <Ionicons name="search-outline" size={16} color="#9AA0A6" />
                <Text style={styles.suggestionText}>{s.replace(/_/g, ' ')}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* LOADING */}
        {loading && (
          <View style={styles.loadingContainer}>
            <Text style={styles.loadingText}>Searching...</Text>
          </View>
        )}

        {/* RESULTS */}
        {!loading && hasSearched && (
          <>
            {/* Compare chip */}
            {showCompareChip && compareItemA && compareItemB && (
              <TouchableOpacity
                style={styles.compareChip}
                onPress={() => {
                  setComparisonItems(compareItemA, compareItemB)
                  setShowCompareChip(false)
                  setViewHistory([])
                }}
              >
                <Ionicons name="git-compare-outline" size={14} color="#FF9900" />
                <Text style={styles.compareChipText}>Compare these two</Text>
                <TouchableOpacity
                  onPress={() => {
                    setShowCompareChip(false)
                    setViewHistory([])
                  }}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                  <Text style={styles.compareChipClose}>×</Text>
                </TouchableOpacity>
              </TouchableOpacity>
            )}

            <FlatList
              data={results}
              keyExtractor={(item) => item.asin}
              renderItem={renderProduct}
              style={styles.resultsList}
              contentContainerStyle={styles.resultsContent}
              keyboardShouldPersistTaps="handled"
              onScroll={handleScroll}
              scrollEventThrottle={500}
              ListEmptyComponent={
                <View style={styles.emptyContainer}>
                  <Ionicons name="search-outline" size={48} color="#D5D9D9" />
                  <Text style={styles.emptyText}>
                    No products found for "{query}"
                  </Text>
                  <Text style={styles.emptyHint}>
                    Try a different search term
                  </Text>
                </View>
              }
              ListHeaderComponent={
                results.length > 0 ? (
                  <Text style={styles.resultsCount}>
                    {results.length} results
                  </Text>
                ) : null
              }
            />
          </>
        )}
      </KeyboardAvoidingView>

      {/* Hesitation card */}
      <HesitationCard
        visible={showHesitationCard}
        onHelp={() => {
          setHesitationShown(true)
          setShowHesitationCard(false)
          setBadgeMode(true)
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light)
        }}
        onDismiss={() => {
          setShowHesitationCard(false)
          setHesitationShown(true)
        }}
      />

      {/* Product detail sheet */}
      <ProductDetailSheet
        visible={showDetailSheet}
        product={selectedProduct}
        allProducts={results}
        occasionType="general"
        onClose={() => setShowDetailSheet(false)}
        onAddToCart={handleAddToCart}
        onCompare={handleCompareFromDetail}
      />

      {/* Comparison bottom sheet */}
      <ComparisonBottomSheet />

      {/* Floating cart button */}
      {sessionCart.length > 0 && (
        <TouchableOpacity
          style={styles.floatingCart}
          onPress={() => {
            const store = useMissionStore.getState()
            store.setCart(
              sessionCart.map((item) => ({
                cart_item_id: item.asin,
                need_id: item.category,
                need_label: item.category.replace(/_/g, ' '),
                asin: item.asin,
                title: item.title,
                price: item.price,
                pack_size: item.pack_size || 10,
                packs_quantity: item.quantity,
                units_total: item.quantity * (item.pack_size || 10),
                total_cost: item.price * item.quantity,
                delivery_eta: item.delivery_eta || 'now_20min',
                prime: true,
                amazon_now_eligible: item.amazon_now_eligible,
                rating: item.rating,
                explanation: item.badge?.badge_reason || '',
                is_sponsored: item.sponsored || false,
                was_repaired: false,
                repair_reason: null,
                compatibility_flags: [],
                community_adoption_score: 0.75,
                sessions_analyzed: 3847,
                quantity_basis: 'selected from search',
              })) as any,
            )
            router.push('/cart/result')
          }}
        >
          <Ionicons name="cart" size={20} color="#FFFFFF" />
          <Text style={styles.floatingCartText}>
            {sessionCart.length} item{sessionCart.length > 1 ? 's' : ''}
          </Text>
          <Text style={styles.floatingCartSep}>·</Text>
          <Text style={styles.floatingCartTotal}>
            ₹{sessionCart.reduce((s, i) => s + i.price * i.quantity, 0)}
          </Text>
        </TouchableOpacity>
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  flex: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F2F2',
  },
  backBtn: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 4,
  },
  inputContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    height: 40,
    backgroundColor: '#F3F3F3',
    borderRadius: 4,
    paddingHorizontal: 10,
  },
  input: {
    flex: 1,
    marginLeft: 8,
    fontSize: 15,
    color: Colors.textPrimary,
    paddingVertical: 0,
  },
  suggestionsSection: { paddingHorizontal: 16, paddingTop: 16 },
  suggestionsLabel: {
    color: Colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  suggestionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F2F2',
    gap: 10,
  },
  suggestionText: { color: Colors.textPrimary, fontSize: 14 },
  loadingContainer: { padding: 32, alignItems: 'center' },
  loadingText: { color: Colors.textSecondary, fontSize: 14 },
  resultsList: { flex: 1 },
  resultsContent: { paddingBottom: 100 },
  resultsCount: {
    color: Colors.textSecondary,
    fontSize: 12,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  productRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F2F2',
  },
  productLetter: {
    width: 48,
    height: 48,
    borderRadius: 4,
    backgroundColor: '#F3F3F3',
    alignItems: 'center',
    justifyContent: 'center',
  },
  productLetterText: {
    color: Colors.textSecondary,
    fontSize: 20,
    fontWeight: '700',
  },
  productInfo: { flex: 1, marginLeft: 12 },
  productTitle: { color: Colors.textPrimary, fontSize: 14, fontWeight: '600' },
  productMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
    gap: 8,
  },
  productPrice: { color: Colors.textPrimary, fontSize: 14, fontWeight: '700' },
  productRating: { color: Colors.textSecondary, fontSize: 12 },
  nowBadge: {
    backgroundColor: Colors.successGreen,
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 6,
  },
  nowBadgeText: { color: Colors.white, fontSize: 9, fontWeight: '700' },
  sponsoredBadge: {
    backgroundColor: '#F0F0F0',
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 6,
  },
  sponsoredText: { color: Colors.textSecondary, fontSize: 9 },
  badgePill: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    marginTop: 4,
  },
  badgePillText: { fontSize: 10, fontWeight: '700' },
  emptyContainer: { padding: 48, alignItems: 'center' },
  emptyText: {
    color: Colors.textPrimary,
    fontSize: 15,
    fontWeight: '600',
    marginTop: 12,
  },
  emptyHint: { color: Colors.textSecondary, fontSize: 13, marginTop: 4 },
  compareChip: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'center',
    backgroundColor: '#FFF3E0',
    borderWidth: 1,
    borderColor: '#FF9900',
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    marginBottom: 8,
    marginTop: 4,
    gap: 6,
    elevation: 3,
  },
  compareChipText: {
    fontSize: 13,
    color: '#FF9900',
    fontWeight: '600',
    flex: 1,
  },
  compareChipClose: { fontSize: 16, color: '#FF9900', marginLeft: 4 },
  floatingCart: {
    position: 'absolute',
    bottom: 24,
    right: 16,
    backgroundColor: '#FF9900',
    borderRadius: 28,
    paddingVertical: 14,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
    elevation: 6,
    gap: 6,
  },
  floatingCartText: { color: '#FFFFFF', fontWeight: '700', fontSize: 14 },
  floatingCartSep: { color: '#FFFFFF', fontSize: 14 },
  floatingCartTotal: { color: '#FFFFFF', fontWeight: '700', fontSize: 14 },
})
