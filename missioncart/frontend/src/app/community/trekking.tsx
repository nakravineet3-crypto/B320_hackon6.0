import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import {
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { Colors, getLetterColor } from '../../lib/constants'

interface TrekProduct {
  id: string
  category: string
  title: string
  price: number
  rating: number
  reviews: number
  adoption: number
  amazon_now: boolean
  quote: string
}

const TREK_PRODUCTS: TrekProduct[] = [
  {
    id: '1',
    category: 'water_bottle',
    title: 'Stainless Steel Water Bottle 1L',
    price: 399,
    rating: 4.4,
    reviews: 2847,
    adoption: 93,
    amazon_now: true,
    quote: 'Essential for every Himalayan trek',
  },
  {
    id: '2',
    category: 'first_aid',
    title: 'Compact First Aid Kit 25pc',
    price: 299,
    rating: 4.3,
    reviews: 1203,
    adoption: 81,
    amazon_now: true,
    quote: 'Never skip this — saved me twice',
  },
  {
    id: '3',
    category: 'trekking_socks',
    title: 'Merino Wool Trekking Socks 5 pairs',
    price: 349,
    rating: 4.2,
    reviews: 891,
    adoption: 74,
    amazon_now: true,
    quote: 'Prevents blisters on long trails',
  },
  {
    id: '4',
    category: 'backpack',
    title: 'Wildcraft Trailblazer 40L Backpack',
    price: 1499,
    rating: 4.3,
    reviews: 3241,
    adoption: 89,
    amazon_now: false,
    quote: 'Perfect for 3-day trek with full gear',
  },
  {
    id: '5',
    category: 'energy_bar',
    title: 'RiteBite Max Protein Bar Pack of 6',
    price: 299,
    rating: 4.1,
    reviews: 567,
    adoption: 68,
    amazon_now: true,
    quote: 'Keeps energy up on steep climbs',
  },
  {
    id: '6',
    category: 'torch',
    title: 'Headlamp LED 200 Lumens',
    price: 499,
    rating: 4.5,
    reviews: 1892,
    adoption: 77,
    amazon_now: true,
    quote: 'Hands-free — must have for night camps',
  },
  {
    id: '7',
    category: 'rain_jacket',
    title: 'Wildcraft Ultralight Rain Jacket',
    price: 1299,
    rating: 4.2,
    reviews: 743,
    adoption: 71,
    amazon_now: false,
    quote: 'Packs into its own pocket, very light',
  },
  {
    id: '8',
    category: 'trekking_poles',
    title: 'Aluminium Trekking Poles Pair',
    price: 799,
    rating: 4.1,
    reviews: 1124,
    adoption: 65,
    amazon_now: false,
    quote: 'Reduces knee strain on descents',
  },
]

function formatInr(value: number) {
  return value.toLocaleString('en-IN')
}

export default function TrekkingScreen() {
  const router = useRouter()

  const renderItem = ({ item, index }: { item: TrekProduct; index: number }) => {
    const palette = getLetterColor(item.category)
    const rank = index + 1
    const isTopThree = rank <= 3

    return (
      <View style={styles.productRow}>
        <Text style={[styles.rankText, isTopThree ? styles.rankTop : styles.rankRest]}>
          {rank}
        </Text>

        <View style={[styles.letterTile, { backgroundColor: palette.bg }]}>
          <Text style={[styles.letterTileText, { color: palette.text }]}>
            {item.category[0].toUpperCase()}
          </Text>
        </View>

        <View style={styles.middle}>
          <Text style={styles.title} numberOfLines={2}>
            {item.title}
          </Text>

          <View style={styles.ratingRow}>
            <Ionicons name="star" size={10} color={Colors.primary} />
            <Text style={styles.ratingText}>
              {' '}
              {item.rating} · {formatInr(item.reviews)} reviews
            </Text>
          </View>

          <View style={styles.quoteChip}>
            <Text style={styles.quoteText}>"{item.quote}"</Text>
          </View>

          <View style={styles.bottomRow}>
            <View style={styles.adoptionPill}>
              <Text style={styles.adoptionText}>{item.adoption}% of trekkers</Text>
            </View>
            {item.amazon_now && (
              <View style={styles.nowBadge}>
                <Text style={styles.nowBadgeText}>Now</Text>
              </View>
            )}
          </View>
        </View>

        <Text style={styles.price}>₹{formatInr(item.price)}</Text>
      </View>
    )
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar style="light" backgroundColor={Colors.nowBlue} />

      {/* Header */}
      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          style={styles.backButton}
          hitSlop={10}
          accessibilityRole="button"
          accessibilityLabel="Go back"
        >
          <Ionicons name="arrow-back" size={24} color={Colors.white} />
        </Pressable>
        <View style={styles.headerCopy}>
          <Text style={styles.headerTitle}>Trekking Essentials</Text>
          <Text style={styles.headerSubtitle}>
            What 2,847 trekkers actually bought
          </Text>
        </View>
      </View>

      <FlatList
        data={TREK_PRODUCTS}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        style={styles.list}
        showsVerticalScrollIndicator={false}
        ListHeaderComponent={
          <>
            {/* Banner */}
            <View style={styles.banner}>
              <View style={styles.bannerLeft}>
                <Text style={styles.bannerBig}>2,847 trekkers</Text>
                <Text style={styles.bannerSub}>verified these essentials</Text>
              </View>
              <View style={styles.bannerRight}>
                <Text style={styles.bannerMeta}>Last updated</Text>
                <Text style={styles.bannerMeta}>June 2026</Text>
              </View>
            </View>

            {/* Trust badge */}
            <View style={styles.trustBadge}>
              <Ionicons
                name="shield-checkmark"
                size={14}
                color={Colors.successGreen}
              />
              <Text style={styles.trustBadgeText}>
                Zero sponsored products — only what trekkers actually bought
              </Text>
            </View>

            {/* 8px divider */}
            <View style={styles.divider} />

            {/* Section label */}
            <View style={styles.sectionLabelRow}>
              <Text style={styles.sectionLabel}>MOST BOUGHT</Text>
            </View>
          </>
        }
      />

      {/* Bottom CTA */}
      <View style={styles.ctaBar}>
        <Pressable style={styles.ctaButton} accessibilityRole="button">
          <Text style={styles.ctaButtonText}>Add all to cart · ₹5,343</Text>
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
    paddingVertical: 8,
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
  headerCopy: {
    flex: 1,
  },
  headerTitle: {
    color: Colors.white,
    fontSize: 18,
    fontWeight: '700',
  },
  headerSubtitle: {
    marginTop: 1,
    color: Colors.white,
    fontSize: 12,
  },
  list: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  // Banner
  banner: {
    height: 120,
    paddingHorizontal: 16,
    paddingVertical: 20,
    backgroundColor: '#2E7D32',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  bannerLeft: {
    flex: 1,
    justifyContent: 'center',
  },
  bannerBig: {
    color: Colors.white,
    fontSize: 28,
    fontWeight: '700',
  },
  bannerSub: {
    marginTop: 4,
    color: Colors.white,
    fontSize: 14,
    opacity: 0.8,
  },
  bannerRight: {
    alignItems: 'flex-end',
    justifyContent: 'flex-start',
  },
  bannerMeta: {
    color: Colors.white,
    fontSize: 10,
    opacity: 0.6,
  },
  // Trust badge
  trustBadge: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: '#E7F5EA',
    borderBottomWidth: 1,
    borderBottomColor: Colors.inputBorder,
    flexDirection: 'row',
    alignItems: 'center',
  },
  trustBadgeText: {
    color: Colors.successGreen,
    fontSize: 12,
    fontWeight: '600',
    marginLeft: 6,
    flex: 1,
  },
  divider: {
    height: 8,
    backgroundColor: Colors.divider,
  },
  sectionLabelRow: {
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  sectionLabel: {
    color: Colors.textSecondary,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  // Product row
  productRow: {
    backgroundColor: Colors.background,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
    paddingHorizontal: 16,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  rankText: {
    width: 24,
    fontSize: 16,
    fontWeight: '700',
    paddingTop: 12,
  },
  rankTop: {
    color: Colors.primary,
  },
  rankRest: {
    color: Colors.inputBorder,
  },
  letterTile: {
    width: 44,
    height: 44,
    marginLeft: 8,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  letterTileText: {
    fontSize: 18,
    fontWeight: '700',
  },
  middle: {
    flex: 1,
    marginLeft: 12,
  },
  title: {
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '600',
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  ratingText: {
    color: Colors.textSecondary,
    fontSize: 11,
  },
  quoteChip: {
    backgroundColor: Colors.cardBg,
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    alignSelf: 'flex-start',
    marginTop: 6,
  },
  quoteText: {
    color: Colors.textSecondary,
    fontSize: 11,
    fontStyle: 'italic',
  },
  bottomRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 6,
  },
  adoptionPill: {
    backgroundColor: '#FFF8E1',
    borderRadius: 3,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  adoptionText: {
    color: '#F57F17',
    fontSize: 10,
    fontWeight: '600',
  },
  nowBadge: {
    backgroundColor: Colors.nowBadge,
    borderRadius: 3,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  nowBadgeText: {
    color: Colors.white,
    fontSize: 10,
    fontWeight: '700',
  },
  price: {
    color: Colors.textPrimary,
    fontSize: 15,
    fontWeight: '700',
    marginLeft: 8,
    paddingTop: 12,
  },
  // CTA
  ctaBar: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: Colors.inputBorder,
    backgroundColor: Colors.background,
  },
  ctaButton: {
    width: '100%',
    height: 48,
    backgroundColor: Colors.primary,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaButtonText: {
    color: Colors.white,
    fontSize: 15,
    fontWeight: '700',
  },
})
