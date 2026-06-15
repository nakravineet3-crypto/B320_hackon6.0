import AsyncStorage from '@react-native-async-storage/async-storage'
import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import { useState } from 'react'
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { Colors, getLabelColor } from '../../lib/constants'
import { useReorderStore } from '../../store/reorder'

type IoniconName = keyof typeof Ionicons.glyphMap

interface IdentityGroup {
  icon: IoniconName
  name: string
}

interface GoalTile {
  name: string
  members: string
  accent: string
}

interface ProductItem {
  name: string
  price: number
  rating: number
  amazonNow: boolean
  initial: string
}

const IDENTITY_GROUPS: IdentityGroup[] = [
  { icon: 'barbell-outline', name: 'Office Gym Dad' },
  { icon: 'book-outline', name: 'JEE Student' },
  { icon: 'school-outline', name: 'College Girl' },
  { icon: 'restaurant-outline', name: 'Home Chef' },
]

const GOAL_TILES: GoalTile[] = [
  { name: 'Trekking Essentials', members: '2,847 planners', accent: '#2E7D32' },
  { name: 'Party Season', members: '5,102 planners', accent: '#FF6B00' },
  { name: 'JEE Prep', members: '3,891 planners', accent: '#1565C0' },
  { name: 'New Baby', members: '1,203 planners', accent: '#6B3FA0' },
]

const PRODUCTS: ProductItem[] = [
  { name: 'Protein Shaker Bottle', price: 399, rating: 4.3, amazonNow: true, initial: 'P' },
  { name: 'Resistance Bands Set', price: 599, rating: 4.5, amazonNow: true, initial: 'R' },
  { name: 'Multivitamin 60 tabs', price: 449, rating: 4.2, amazonNow: true, initial: 'M' },
  { name: 'Water Bottle 1L', price: 299, rating: 4.4, amazonNow: true, initial: 'W' },
  { name: 'Notebook A4 Pack of 3', price: 149, rating: 4.1, amazonNow: true, initial: 'N' },
  { name: 'Wireless Earphones', price: 799, rating: 4.0, amazonNow: false, initial: 'W' },
]

const DEMO_SCREENS = [
  { label: 'Voice input', route: '/ppt/voice-input' },
  { label: 'Photo scan', route: '/ppt/photo-input' },
  { label: 'Share card', route: '/ppt/mission-share' },
  { label: 'Seller dashboard', route: '/ppt/seller-dashboard' },
] as const

export default function DiscoverScreen() {
  const router = useRouter()
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null)
  const [selectedGoal, setSelectedGoal] = useState<string | null>(null)

  const showProducts = selectedGroup !== null || selectedGoal !== null

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <Text style={styles.pageTitle}>Discover</Text>

        {/* Identity Groups */}
        <Text style={styles.sectionTitle}>For people like you</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.pillsScroll}
        >
          {IDENTITY_GROUPS.map((group) => {
            const isSelected = selectedGroup === group.name
            return (
              <TouchableOpacity
                key={group.name}
                onPress={() => {
                  setSelectedGroup(group.name)
                  setSelectedGoal(null)
                }}
                activeOpacity={0.7}
                style={[styles.groupPill, isSelected && styles.groupPillSelected]}
              >
                <Ionicons
                  name={group.icon}
                  size={16}
                  color={isSelected ? Colors.white : Colors.textPrimary}
                />
                <Text
                  style={[
                    styles.groupPillText,
                    isSelected && styles.groupPillTextSelected,
                  ]}
                >
                  {group.name}
                </Text>
              </TouchableOpacity>
            )
          })}
        </ScrollView>

        {/* Trust badge */}
        {showProducts && (
          <View style={styles.trustBadge}>
            <Ionicons
              name="shield-checkmark"
              size={14}
              color={Colors.successGreen}
            />
            <Text style={styles.trustBadgeText}>
              Zero sponsored products in this section
            </Text>
          </View>
        )}

        {/* Product grid */}
        {showProducts && (
          <View style={styles.productGrid}>
            {PRODUCTS.map((product) => {
              const palette = getLabelColor(product.name)
              return (
                <View key={product.name} style={styles.productCard}>
                  <View
                    style={[styles.productPlaceholder, { backgroundColor: palette.bg }]}
                  >
                    <Text style={[styles.productInitial, { color: palette.text }]}>
                      {product.initial}
                    </Text>
                  </View>
                  <Text style={styles.productName} numberOfLines={2}>
                    {product.name}
                  </Text>
                  <Text style={styles.productPrice}>₹{product.price}</Text>
                  <View style={styles.ratingRow}>
                    <Ionicons name="star" size={10} color={Colors.primary} />
                    <Text style={styles.ratingText}>{product.rating}</Text>
                  </View>
                  {product.amazonNow && (
                    <View style={styles.nowBadge}>
                      <Text style={styles.nowBadgeText}>NOW</Text>
                    </View>
                  )}
                </View>
              )
            })}
          </View>
        )}

        {/* Divider */}
        <View style={styles.divider} />

        {/* Popular Goals */}
        <Text style={styles.goalsTitle}>Popular goals</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.goalsScroll}
        >
          {GOAL_TILES.map((goal) => {
            const isSelected = selectedGoal === goal.name
            return (
              <TouchableOpacity
                key={goal.name}
                onPress={() => {
                  if (goal.name === 'Trekking Essentials') {
                    router.push('/community/trekking')
                    return
                  }
                  setSelectedGoal(goal.name)
                  setSelectedGroup(null)
                }}
                activeOpacity={0.7}
                style={[
                  styles.goalCard,
                  { borderLeftColor: goal.accent },
                  isSelected && styles.goalCardSelected,
                ]}
              >
                <Text style={styles.goalName}>{goal.name}</Text>
                <Text style={styles.goalMembers}>{goal.members}</Text>
                <Text style={styles.goalNoSponsored}>No sponsored</Text>
              </TouchableOpacity>
            )
          })}
        </ScrollView>

        <View style={styles.demoSection}>
          <Text style={styles.demoSectionTitle}>Preview screens</Text>
          <View style={styles.demoLinks}>
            {DEMO_SCREENS.map((screen) => (
              <TouchableOpacity
                key={screen.route}
                onPress={() => router.push(screen.route)}
                accessibilityRole="button"
              >
                <Text style={styles.demoLinkText}>{screen.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <TouchableOpacity
            onPress={async () => {
              await AsyncStorage.removeItem('removed_items')
              await AsyncStorage.removeItem('approved_orders')
              useReorderStore.getState().clear()
              Alert.alert('Demo state cleared')
            }}
            style={styles.resetDemoButton}
            accessibilityRole="button"
          >
            <Text style={styles.resetDemoButtonText}>Reset demo data</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  screen: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  content: {
    paddingBottom: 24,
  },
  pageTitle: {
    color: Colors.textPrimary,
    fontSize: 22,
    fontWeight: '700',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 16,
  },
  sectionTitle: {
    color: Colors.textPrimary,
    fontSize: 16,
    fontWeight: '700',
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  pillsScroll: {
    paddingHorizontal: 16,
  },
  groupPill: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    marginRight: 8,
  },
  groupPillSelected: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  groupPillText: {
    color: Colors.textPrimary,
    fontSize: 13,
    fontWeight: '400',
    marginLeft: 6,
  },
  groupPillTextSelected: {
    color: Colors.white,
    fontWeight: '600',
  },
  trustBadge: {
    paddingHorizontal: 16,
    marginVertical: 8,
    flexDirection: 'row',
    alignItems: 'center',
  },
  trustBadgeText: {
    color: Colors.successGreen,
    fontSize: 12,
    fontWeight: '600',
    marginLeft: 6,
  },
  productGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 16,
  },
  productCard: {
    width: '47%',
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
    padding: 10,
    margin: 4,
  },
  productPlaceholder: {
    width: '100%',
    height: 80,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  productInitial: {
    fontSize: 24,
    fontWeight: '700',
  },
  productName: {
    color: Colors.textPrimary,
    fontSize: 12,
    fontWeight: '600',
    marginTop: 8,
  },
  productPrice: {
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '700',
    marginTop: 4,
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  ratingText: {
    color: Colors.textSecondary,
    fontSize: 11,
    marginLeft: 2,
  },
  nowBadge: {
    backgroundColor: Colors.nowBadge,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 3,
    alignSelf: 'flex-start',
    marginTop: 4,
  },
  nowBadgeText: {
    color: Colors.white,
    fontSize: 9,
    fontWeight: '700',
  },
  divider: {
    height: 8,
    backgroundColor: Colors.divider,
    marginTop: 20,
  },
  goalsTitle: {
    color: Colors.textPrimary,
    fontSize: 16,
    fontWeight: '700',
    paddingHorizontal: 16,
    paddingTop: 16,
    marginBottom: 12,
  },
  goalsScroll: {
    paddingHorizontal: 16,
  },
  goalCard: {
    width: 130,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
    borderLeftWidth: 3,
    padding: 12,
    marginRight: 8,
  },
  goalCardSelected: {
    borderColor: Colors.primary,
  },
  goalName: {
    color: Colors.textPrimary,
    fontSize: 13,
    fontWeight: '700',
  },
  goalMembers: {
    color: Colors.textSecondary,
    fontSize: 11,
    marginTop: 2,
  },
  goalNoSponsored: {
    color: Colors.successGreen,
    fontSize: 10,
    fontWeight: '600',
    marginTop: 6,
  },
  demoSection: {
    marginTop: 20,
    paddingHorizontal: 16,
    paddingVertical: 20,
    borderTopWidth: 1,
    borderTopColor: '#F0F2F2',
  },
  demoSectionTitle: {
    marginBottom: 8,
    color: '#9AA0A6',
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 1,
  },
  demoLinks: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  demoLinkText: {
    color: '#007185',
    fontSize: 12,
  },
  resetDemoButton: {
    alignSelf: 'flex-start',
    marginTop: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: '#FFF5F5',
    borderWidth: 1,
    borderColor: '#CC0C39',
    borderRadius: 4,
  },
  resetDemoButtonText: {
    color: '#CC0C39',
    fontSize: 13,
  },
})
