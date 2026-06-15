import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useEffect, useState } from 'react'
import {
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { api, catalogAPI } from '../lib/api'
import { Colors } from '../lib/constants'
import { useMissionStore } from '../store/mission'

interface CatalogProduct {
  asin: string
  title: string
  category: string
  price: number
  pack_size: number
  amazon_now_eligible: boolean
  sponsored: boolean
  rating: number
  delivery_eta: string
  safety_tags?: string[]
}

interface CartItem extends CatalogProduct {
  quantity: number
}

const OCCASIONS = [
  'Birthday party',
  'Home setup',
  'Trek',
  'Office event',
  'Daily grocery',
  'Other',
]

const HEADCOUNT_OPTIONS = [5, 10, 12, 15, 20, 25]

export default function AuditBuildScreen() {
  const router = useRouter()
  const [catalog, setCatalog] = useState<CatalogProduct[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<CatalogProduct[]>([])
  const [cartItems, setCartItems] = useState<CartItem[]>([])
  const [selectedOccasion, setSelectedOccasion] = useState<string | null>(null)
  const [headcount, setHeadcount] = useState(12)
  const [budget, setBudget] = useState('4000')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    catalogAPI.getProducts().then((res) => {
      if (res.data?.data) setCatalog(res.data.data)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      return
    }
    const q = searchQuery.toLowerCase()
    const results = catalog.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        p.category.toLowerCase().includes(q),
    )
    setSearchResults(results.slice(0, 15))
  }, [searchQuery, catalog])

  const addToCart = (product: CatalogProduct) => {
    const existing = cartItems.find((i) => i.asin === product.asin)
    if (existing) {
      setCartItems((prev) =>
        prev.map((i) => (i.asin === product.asin ? { ...i, quantity: i.quantity + 1 } : i)),
      )
    } else {
      setCartItems((prev) => [...prev, { ...product, quantity: 1 }])
    }
    setSearchQuery('')
  }

  const updateQuantity = (asin: string, delta: number) => {
    setCartItems((prev) =>
      prev
        .map((i) => (i.asin === asin ? { ...i, quantity: Math.max(0, i.quantity + delta) } : i))
        .filter((i) => i.quantity > 0),
    )
  }

  const removeFromCart = (asin: string) => {
    setCartItems((prev) => prev.filter((i) => i.asin !== asin))
  }

  const cartTotal = cartItems.reduce((sum, i) => sum + i.price * i.quantity, 0)

  const runAudit = async () => {
    setLoading(true)
    try {
      const payload = {
        cart_items: cartItems.map((i) => ({
          asin: i.asin,
          title: i.title,
          category: i.category,
          price_inr: i.price,
          quantity: i.quantity,
          pack_size: i.pack_size || 10,
          amazon_now_eligible: i.amazon_now_eligible,
          sponsored: i.sponsored,
          safety_tags: i.safety_tags || [],
          delivery_eta: i.delivery_eta || 'now_20min',
        })),
        headcount,
        occasion: selectedOccasion || 'birthday',
        budget_max: parseFloat(budget) || 4000,
        deadline_hours: selectedOccasion === 'Birthday party' ? 18 : 24,
        safety_context: selectedOccasion === 'Birthday party' ? 'child_safe' : 'general',
      }

      const res = await api.post('/api/mission/audit', payload)
      const data = res.data?.data || res.data

      // Store audit result and navigate
      useMissionStore.getState().setAuditResult(data)
      router.push('/audit-result')
    } catch {
      // Navigate with empty result
      useMissionStore.getState().setAuditResult({ flags: [], repaired_cart: [], original_total: cartTotal, repaired_total: cartTotal, coverage_score: '0/0' })
      router.push('/audit-result')
    }
    setLoading(false)
  }

  const showContextInputs = selectedOccasion === 'Birthday party' || selectedOccasion === 'Other'

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar style="light" backgroundColor={Colors.nowBlue} />

      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </Pressable>
        <Text style={styles.headerTitle}>Build Cart to Audit</Text>
        <Text style={styles.headerCount}>{cartItems.length} items</Text>
      </View>

      <ScrollView style={styles.body} contentContainerStyle={styles.bodyContent} keyboardShouldPersistTaps="handled">
        {/* Occasion section */}
        <View style={styles.occasionSection}>
          <Text style={styles.sectionLabel}>What is this cart for?</Text>
          <View style={styles.chipsRow}>
            {OCCASIONS.map((occ) => (
              <TouchableOpacity
                key={occ}
                style={[styles.chip, selectedOccasion === occ && styles.chipSelected]}
                onPress={() => setSelectedOccasion(occ)}
              >
                <Text style={[styles.chipText, selectedOccasion === occ && styles.chipTextSelected]}>{occ}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {showContextInputs && (
            <View style={styles.contextInputs}>
              <Text style={styles.contextLabel}>For how many people?</Text>
              <View style={styles.headcountRow}>
                {HEADCOUNT_OPTIONS.map((n) => (
                  <TouchableOpacity
                    key={n}
                    style={[styles.headcountPill, headcount === n && styles.headcountPillSelected]}
                    onPress={() => setHeadcount(n)}
                  >
                    <Text style={[styles.headcountPillText, headcount === n && styles.headcountPillTextSelected]}>{n}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              <Text style={styles.contextLabel}>Budget (₹)</Text>
              <TextInput
                style={styles.budgetInput}
                value={budget}
                onChangeText={setBudget}
                keyboardType="numeric"
                placeholder="4000"
                placeholderTextColor="#999"
              />
            </View>
          )}
        </View>

        {/* Search bar */}
        <View style={styles.searchBar}>
          <Ionicons name="search-outline" size={18} color="#9AA0A6" />
          <TextInput
            style={styles.searchInput}
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholder="Search products..."
            placeholderTextColor="#9AA0A6"
          />
        </View>

        {/* Search results */}
        {searchResults.length > 0 && (
          <View style={styles.resultsSection}>
            {searchResults.map((product) => (
              <View key={product.asin} style={styles.resultRow}>
                <View style={styles.resultLetter}>
                  <Text style={styles.resultLetterText}>{product.title[0]}</Text>
                </View>
                <View style={styles.resultInfo}>
                  <Text style={styles.resultTitle} numberOfLines={1}>{product.title}</Text>
                  <Text style={styles.resultCategory}>{product.category.replace(/_/g, ' ')}</Text>
                  <View style={styles.resultMeta}>
                    <Text style={styles.resultPrice}>₹{product.price}</Text>
                    {product.amazon_now_eligible && (
                      <View style={styles.nowBadge}><Text style={styles.nowBadgeText}>NOW</Text></View>
                    )}
                    {product.sponsored && (
                      <View style={styles.sponsoredBadge}><Text style={styles.sponsoredBadgeText}>Sponsored</Text></View>
                    )}
                  </View>
                </View>
                <TouchableOpacity style={styles.addBtn} onPress={() => addToCart(product)}>
                  <Text style={styles.addBtnText}>Add</Text>
                </TouchableOpacity>
              </View>
            ))}
          </View>
        )}

        {/* Cart preview */}
        {cartItems.length > 0 && (
          <View style={styles.cartSection}>
            <Text style={styles.cartSectionTitle}>Your cart ({cartItems.length} items)</Text>
            {cartItems.map((item) => (
              <View key={item.asin} style={styles.cartRow}>
                <Text style={styles.cartItemTitle} numberOfLines={1}>{item.title}</Text>
                <View style={styles.stepper}>
                  <TouchableOpacity style={styles.stepperBtn} onPress={() => updateQuantity(item.asin, -1)}>
                    <Text style={styles.stepperBtnText}>−</Text>
                  </TouchableOpacity>
                  <View style={styles.stepperCount}>
                    <Text style={styles.stepperCountText}>{item.quantity}</Text>
                  </View>
                  <TouchableOpacity style={styles.stepperBtn} onPress={() => updateQuantity(item.asin, 1)}>
                    <Text style={styles.stepperBtnText}>+</Text>
                  </TouchableOpacity>
                </View>
                <Text style={styles.cartItemTotal}>₹{item.price * item.quantity}</Text>
                <TouchableOpacity onPress={() => removeFromCart(item.asin)} hitSlop={8}>
                  <Ionicons name="close-circle" size={16} color={Colors.errorRed} />
                </TouchableOpacity>
              </View>
            ))}
            <View style={styles.cartTotalRow}>
              <Text style={styles.cartTotalLabel}>Total</Text>
              <Text style={styles.cartTotalValue}>₹{cartTotal}</Text>
            </View>
          </View>
        )}
      </ScrollView>

      {/* Bottom button */}
      {cartItems.length > 0 && (
        <View style={styles.bottomBar}>
          <Pressable style={styles.analyzeButton} onPress={runAudit} disabled={loading}>
            <Text style={styles.analyzeButtonText}>
              {loading ? 'Analyzing...' : `Analyze Cart (${cartItems.length} items)`}
            </Text>
          </Pressable>
        </View>
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.nowBlue },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 14, backgroundColor: Colors.nowBlue },
  backBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center', marginRight: 8 },
  headerTitle: { flex: 1, color: Colors.white, fontSize: 18, fontWeight: '700' },
  headerCount: { color: Colors.white, fontSize: 12, opacity: 0.85 },
  body: { flex: 1, backgroundColor: Colors.background },
  bodyContent: { paddingBottom: 100 },
  occasionSection: { padding: 16, borderBottomWidth: 1, borderBottomColor: '#D5D9D9' },
  sectionLabel: { color: Colors.textPrimary, fontSize: 14, fontWeight: '700', marginBottom: 8 },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { borderWidth: 1, borderColor: '#D5D9D9', borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6 },
  chipSelected: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  chipText: { color: Colors.textSecondary, fontSize: 13 },
  chipTextSelected: { color: Colors.white, fontWeight: '600' },
  contextInputs: { marginTop: 12 },
  contextLabel: { color: Colors.textSecondary, fontSize: 13, marginTop: 8, marginBottom: 6 },
  headcountRow: { flexDirection: 'row', gap: 8 },
  headcountPill: { paddingHorizontal: 14, paddingVertical: 6, borderWidth: 1, borderColor: '#D5D9D9', borderRadius: 16 },
  headcountPillSelected: { borderColor: Colors.primary, backgroundColor: '#FFF8F0' },
  headcountPillText: { color: Colors.textSecondary, fontSize: 13 },
  headcountPillTextSelected: { color: Colors.primary, fontWeight: '700' },
  budgetInput: { borderWidth: 1, borderColor: '#D5D9D9', borderRadius: 4, height: 40, paddingHorizontal: 12, fontSize: 15, color: Colors.textPrimary, marginTop: 4 },
  searchBar: { flexDirection: 'row', alignItems: 'center', marginHorizontal: 16, marginTop: 12, paddingHorizontal: 12, height: 44, borderWidth: 1, borderColor: '#D5D9D9', borderRadius: 4 },
  searchInput: { flex: 1, marginLeft: 8, fontSize: 14, color: Colors.textPrimary },
  resultsSection: { marginTop: 4 },
  resultRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#F0F2F2' },
  resultLetter: { width: 44, height: 44, borderRadius: 4, backgroundColor: '#F3F3F3', alignItems: 'center', justifyContent: 'center' },
  resultLetterText: { color: Colors.textSecondary, fontSize: 18, fontWeight: '700' },
  resultInfo: { flex: 1, marginLeft: 12 },
  resultTitle: { color: Colors.textPrimary, fontSize: 14, fontWeight: '700' },
  resultCategory: { color: Colors.textSecondary, fontSize: 12, marginTop: 1 },
  resultMeta: { flexDirection: 'row', alignItems: 'center', marginTop: 4, gap: 8 },
  resultPrice: { color: Colors.textPrimary, fontSize: 14, fontWeight: '700' },
  nowBadge: { backgroundColor: Colors.successGreen, paddingHorizontal: 6, paddingVertical: 1, borderRadius: 6 },
  nowBadgeText: { color: Colors.white, fontSize: 9, fontWeight: '700' },
  sponsoredBadge: { backgroundColor: '#F0F0F0', paddingHorizontal: 6, paddingVertical: 1, borderRadius: 6 },
  sponsoredBadgeText: { color: Colors.textSecondary, fontSize: 9 },
  addBtn: { backgroundColor: Colors.primary, borderRadius: 4, paddingHorizontal: 10, paddingVertical: 6 },
  addBtnText: { color: Colors.white, fontSize: 13, fontWeight: '700' },
  cartSection: { marginTop: 16, marginHorizontal: 16 },
  cartSectionTitle: { color: Colors.textPrimary, fontSize: 14, fontWeight: '700', marginBottom: 8 },
  cartRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#F0F2F2', gap: 8 },
  cartItemTitle: { flex: 1, color: Colors.textPrimary, fontSize: 13 },
  stepper: { flexDirection: 'row', alignItems: 'center' },
  stepperBtn: { width: 28, height: 28, borderWidth: 1, borderColor: '#D5D9D9', borderRadius: 4, alignItems: 'center', justifyContent: 'center' },
  stepperBtnText: { fontSize: 16, color: Colors.textPrimary },
  stepperCount: { width: 36, height: 28, borderTopWidth: 1, borderBottomWidth: 1, borderColor: '#D5D9D9', alignItems: 'center', justifyContent: 'center' },
  stepperCountText: { fontSize: 14, fontWeight: '700', color: Colors.textPrimary },
  cartItemTotal: { color: Colors.textPrimary, fontSize: 13, fontWeight: '700', marginLeft: 8 },
  cartTotalRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 12, borderTopWidth: 2, borderTopColor: '#D5D9D9', marginTop: 4 },
  cartTotalLabel: { color: Colors.textPrimary, fontSize: 16, fontWeight: '700' },
  cartTotalValue: { color: Colors.textPrimary, fontSize: 16, fontWeight: '700' },
  bottomBar: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: 16, paddingBottom: 28, backgroundColor: Colors.background, borderTopWidth: 1, borderTopColor: '#D5D9D9' },
  analyzeButton: { backgroundColor: Colors.primary, height: 52, borderRadius: 4, alignItems: 'center', justifyContent: 'center' },
  analyzeButtonText: { color: Colors.white, fontSize: 16, fontWeight: '700' },
})
