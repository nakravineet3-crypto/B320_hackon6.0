import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import { useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator,
  Animated,
  FlatList,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { communityAPI, communityGoalAPI, occasionAPI, GroupProduct, GoalPageSummary } from '../../lib/api'
import { Colors } from '../../lib/constants'
import { FALLBACK_GROUP_PRODUCTS, FALLBACK_OCCASIONS } from '../../lib/fallbacks'
import type { OccasionCard } from '../../lib/types'

type IoniconName = keyof typeof Ionicons.glyphMap

interface IdentityGroup {
  id: string
  icon: IoniconName
  name: string
  label: string
}

interface GoalTile {
  name: string
  members: string
  accent: string
}

interface CommunityActivityItem {
  icon: IoniconName
  message: string
  color: string
}

const IDENTITY_GROUPS: IdentityGroup[] = [
  { id: 'office_gym_dad', icon: 'barbell-outline', name: 'Office Gym Dad', label: 'Office Gym Dads' },
  { id: 'jee_student', icon: 'book-outline', name: 'JEE Student', label: 'JEE Students' },
  { id: 'college_girl', icon: 'school-outline', name: 'College Girl', label: 'College Girls' },
  { id: 'home_chef', icon: 'restaurant-outline', name: 'Home Chef', label: 'Home Chefs' },
]

const GOAL_TILES: GoalTile[] = [
  { name: 'Trekking Essentials', members: '2,847 planners', accent: '#2E7D32' },
  { name: 'Party Season', members: '5,102 planners', accent: '#FF6B00' },
  { name: 'JEE Prep', members: '3,891 planners', accent: '#1565C0' },
  { name: 'New Baby', members: '1,203 planners', accent: '#6B3FA0' },
]

const COMMUNITY_ACTIVITY: CommunityActivityItem[] = [
  { icon: 'people-outline', message: '42 people in Bangalore planning Diwali this week', color: '#FF6B00' },
  { icon: 'trending-up-outline', message: 'Birthday party carts up 38% this month', color: '#007185' },
  { icon: 'checkmark-circle-outline', message: '94% coverage rate among Weekend Adventurers', color: '#007600' },
]

const URGENCY_COLORS = {
  discovery: '#5C6BC0',
  preparation: '#FF6B00',
  urgent: '#E53935',
  emergency: '#B71C1C',
} as const

function formatInr(value: number) {
  return value.toLocaleString('en-IN')
}

export default function DiscoverScreen() {
  const router = useRouter()
  const [selectedGroup, setSelectedGroup] = useState<IdentityGroup | null>(null)
  const [occasions, setOccasions] = useState<OccasionCard[]>(FALLBACK_OCCASIONS)
  const [groupProducts, setGroupProducts] = useState<GroupProduct[]>([])
  const [loadingGroupProducts, setLoadingGroupProducts] = useState(false)
  const [communityGoals, setCommunityGoals] = useState<GoalPageSummary[]>([])

  // Animation values
  const pillScales = useRef<Record<string, Animated.Value>>({})
  IDENTITY_GROUPS.forEach((g) => {
    if (!pillScales.current[g.id]) {
      pillScales.current[g.id] = new Animated.Value(1)
    }
  })
  const gridOpacity = useRef(new Animated.Value(0)).current

  function animatePillSelect(groupId: string) {
    const scale = pillScales.current[groupId]
    if (!scale) return
    Animated.sequence([
      Animated.spring(scale, { toValue: 1.05, useNativeDriver: true, speed: 300, bounciness: 0 }),
      Animated.spring(scale, { toValue: 1.0, useNativeDriver: true, speed: 300, bounciness: 0 }),
    ]).start()
  }

  function animateGridIn() {
    gridOpacity.setValue(0)
    Animated.timing(gridOpacity, {
      toValue: 1,
      duration: 250,
      useNativeDriver: true,
    }).start()
  }

  useEffect(() => {
    occasionAPI
      .getFeed('U001')
      .then((feed) => {
        if (Array.isArray(feed) && feed.length > 0) {
          setOccasions(feed)
        }
      })
      .catch(() => {
        // Keep fallback occasions
      })

    communityGoalAPI
      .listGoals()
      .then((goals) => {
        if (Array.isArray(goals) && goals.length > 0) {
          setCommunityGoals(goals)
        }
      })
      .catch(() => {
        // Goals section stays hidden if fetch fails
      })
  }, [])

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
            const isSelected = selectedGroup?.id === group.id
            const scale = pillScales.current[group.id] ?? new Animated.Value(1)
            return (
              <Animated.View key={group.id} style={{ transform: [{ scale }] }}>
                <TouchableOpacity
                  onPress={() => {
                    if (isSelected) {
                      setSelectedGroup(null)
                      setGroupProducts([])
                    } else {
                      animatePillSelect(group.id)
                      setSelectedGroup(group)
                      setLoadingGroupProducts(true)
                      setGroupProducts([])
                      communityAPI
                        .getGroupProducts(group.id)
                        .then((data) => {
                          const products =
                            data.products.length > 0
                              ? data.products
                              : (FALLBACK_GROUP_PRODUCTS[group.id] ?? [])
                          setGroupProducts(products)
                          setLoadingGroupProducts(false)
                          animateGridIn()
                        })
                        .catch(() => {
                          setGroupProducts(FALLBACK_GROUP_PRODUCTS[group.id] ?? [])
                          setLoadingGroupProducts(false)
                          animateGridIn()
                        })
                    }
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
              </Animated.View>
            )
          })}
        </ScrollView>

        {/* Trust badge — shown immediately when a group is selected, before products load */}
        {selectedGroup !== null && (
          <View style={styles.trustBadgeTile}>
            <Ionicons name="shield-checkmark" size={18} color="#007600" />
            <View style={styles.trustBadgeTextBlock}>
              <Text style={styles.trustBadgeTitle}>Zero sponsored products</Text>
              <Text style={styles.trustBadgeSubtitle}>
                Only what {selectedGroup.label} actually buys
              </Text>
            </View>
          </View>
        )}

        {/* Product grid — visible when a group is selected */}
        {selectedGroup !== null && (
          <Animated.View style={[styles.groupProductGrid, { opacity: gridOpacity }]}>
            {loadingGroupProducts ? (
              <View style={styles.groupProductLoading}>
                <ActivityIndicator size="small" color={Colors.primary} />
                <Text style={styles.groupProductLoadingText}>Loading picks...</Text>
              </View>
            ) : groupProducts.length > 0 ? (
              <>
                <Text style={styles.groupProductGridTitle}>
                  What {selectedGroup.name} actually buy
                </Text>
                <FlatList
                  data={groupProducts}
                  keyExtractor={(item) => item.asin}
                  numColumns={2}
                  scrollEnabled={false}
                  columnWrapperStyle={styles.groupProductRow}
                  renderItem={({ item }) => (
                    <View style={styles.groupProductCard}>
                      {item.image_url ? (
                        <Image
                          source={{ uri: item.image_url }}
                          style={styles.groupProductImage}
                          resizeMode="cover"
                        />
                      ) : (
                        <View
                          style={[
                            styles.groupProductImage,
                            { backgroundColor: item.image_placeholder },
                          ]}
                        />
                      )}
                      <View style={styles.groupProductInfo}>
                        <Text style={styles.groupProductName} numberOfLines={2}>
                          {item.title}
                        </Text>
                        <Text style={styles.groupProductPrice}>
                          ₹{item.price_inr.toLocaleString('en-IN')}
                        </Text>
                        <View style={styles.ratingRow}>
                          <Ionicons name="star" size={12} color="#FF9500" />
                          <Text style={styles.ratingText}>{item.rating.toFixed(1)}</Text>
                          {item.amazon_now_eligible && (
                            <Text style={styles.groupProductNow}>Now</Text>
                          )}
                        </View>
                        {item.adoption_copy && (
                          <Text style={styles.adoptionCopy} numberOfLines={1}>
                            {item.adoption_copy}
                          </Text>
                        )}
                      </View>
                    </View>
                  )}
                />
              </>
            ) : (
              <Text style={styles.groupProductEmpty}>
                Community picks coming soon
              </Text>
            )}
          </Animated.View>
        )}

        {/* Divider */}
        <View style={styles.divider} />

        {/* COMMUNITY GOALS */}
        {communityGoals.length > 0 && (
          <>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionHeading}>COMMUNITY GOALS</Text>
            </View>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.communityGoalsScroll}
            >
              {communityGoals.map((goal) => {
                const daysUrgent = goal.days_until >= 0 && goal.days_until <= 3
                const daysLabel =
                  goal.days_until < 0
                    ? 'Past'
                    : goal.days_until === 0
                    ? 'Today'
                    : goal.days_until === 1
                    ? 'Tomorrow'
                    : `${goal.days_until} days`
                return (
                  <TouchableOpacity
                    key={goal.goal_id}
                    style={styles.communityGoalCard}
                    activeOpacity={0.75}
                    onPress={() =>
                      router.push({
                        pathname: '/community/goal',
                        params: { id: goal.goal_id },
                      })
                    }
                  >
                    <View style={styles.goalCardTop}>
                      <Text style={styles.goalCardEmoji}>{goal.occasion_emoji}</Text>
                      <View
                        style={[
                          styles.goalDaysBadge,
                          daysUrgent && styles.goalDaysBadgeUrgent,
                        ]}
                      >
                        <Text
                          style={[
                            styles.goalDaysText,
                            daysUrgent && styles.goalDaysTextUrgent,
                          ]}
                        >
                          {daysLabel}
                        </Text>
                      </View>
                    </View>
                    <Text style={styles.communityGoalTitle} numberOfLines={2}>
                      {goal.title}
                    </Text>
                    <Text style={styles.goalParticipants}>
                      {goal.participant_count}{' '}
                      {goal.participant_count === 1 ? 'person' : 'people'} coordinating
                    </Text>
                    {/* Progress bar */}
                    <View style={styles.goalProgressBar}>
                      <View
                        style={[
                          styles.goalProgressFill,
                          { width: `${goal.coverage_pct}%` as `${number}%` },
                        ]}
                      />
                    </View>
                    <Text style={styles.goalProgressLabel}>
                      {goal.items_claimed}/{goal.items_total} items claimed
                    </Text>
                  </TouchableOpacity>
                )
              })}
            </ScrollView>
            <View style={styles.divider} />
          </>
        )}

        {/* UPCOMING OCCASIONS */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionHeading}>UPCOMING OCCASIONS</Text>
        </View>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.occasionList}
        >
          {occasions.map((occasion) => (
            <Pressable
              key={occasion.occasion_type}
              onPress={() =>
                router.push({
                  pathname: '/cart/building',
                  params: {
                    goal: occasion.tap_goal,
                    budget: String(occasion.estimated_budget),
                    headcount: String(occasion.headcount),
                    occasion_type: occasion.occasion_type,
                  },
                })
              }
              style={[
                styles.occasionCard,
                { borderLeftColor: URGENCY_COLORS[occasion.urgency_state] },
              ]}
            >
              <View style={styles.occasionCardTop}>
                <Text style={styles.occasionEmoji}>{occasion.emoji}</Text>
                <View
                  style={[
                    styles.urgencyPill,
                    { backgroundColor: URGENCY_COLORS[occasion.urgency_state] },
                  ]}
                >
                  <Text style={styles.urgencyPillText}>{occasion.urgency_label}</Text>
                </View>
              </View>
              <Text style={styles.occasionTitle} numberOfLines={2}>
                {occasion.title}
              </Text>
              <Text style={styles.occasionBudget}>
                ~₹{formatInr(occasion.estimated_budget)} · {occasion.headcount} people
              </Text>
              <Text style={styles.occasionSignal} numberOfLines={2}>
                {occasion.community_signal}
              </Text>
              <TouchableOpacity
                style={styles.startCartBtn}
                onPress={() =>
                  router.push({
                    pathname: '/cart/building',
                    params: {
                      goal: occasion.tap_goal,
                      budget: String(occasion.estimated_budget),
                      headcount: String(occasion.headcount),
                      occasion_type: occasion.occasion_type,
                    },
                  })
                }
                activeOpacity={0.85}
              >
                <Text style={styles.startCartBtnText}>
                  {occasion.urgency_state === 'emergency' ? 'Order Now · 20 min' : 'Start Cart'}
                </Text>
              </TouchableOpacity>
            </Pressable>
          ))}
        </ScrollView>

        {/* Divider */}
        <View style={styles.divider} />

        {/* POPULAR GOALS THIS WEEK */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionHeading}>POPULAR GOALS THIS WEEK</Text>
        </View>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.goalsScroll}
        >
          {GOAL_TILES.map((goal) => (
            <TouchableOpacity
              key={goal.name}
              onPress={() =>
                router.push({
                  pathname: '/cart/building',
                  params: { goal: goal.name },
                })
              }
              activeOpacity={0.7}
              style={[styles.goalCard, { borderLeftColor: goal.accent }]}
            >
              <Text style={styles.goalName}>{goal.name}</Text>
              <Text style={styles.goalMembers}>{goal.members}</Text>
              <Text style={styles.goalNoSponsored}>No sponsored</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Divider */}
        <View style={styles.divider} />

        {/* COMMUNITY ACTIVITY */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionHeading}>COMMUNITY ACTIVITY</Text>
        </View>
        <View style={styles.communityList}>
          {COMMUNITY_ACTIVITY.map((item, idx) => (
            <View key={idx} style={styles.communityRow}>
              <Ionicons name={item.icon} size={20} color={item.color} />
              <Text style={styles.communityMessage}>{item.message}</Text>
            </View>
          ))}
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
    paddingBottom: 32,
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
    paddingBottom: 4,
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
  trustBadgeTile: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F0FFF4',
    borderColor: '#007600',
    borderWidth: 1,
    borderRadius: 6,
    padding: 12,
    marginHorizontal: 16,
    marginTop: 10,
    marginBottom: 2,
    gap: 10,
  },
  trustBadgeTextBlock: {
    flex: 1,
  },
  trustBadgeTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#007600',
  },
  trustBadgeSubtitle: {
    fontSize: 12,
    fontWeight: '400',
    color: '#2D6A4F',
    marginTop: 2,
  },
  divider: {
    height: 8,
    backgroundColor: Colors.divider,
    marginTop: 16,
  },
  sectionHeader: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
  },
  sectionHeading: {
    color: Colors.textSecondary,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  // Occasion cards
  occasionList: {
    paddingLeft: 16,
    paddingRight: 8,
  },
  occasionCard: {
    width: 160,
    marginRight: 8,
    padding: 12,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
    borderLeftWidth: 3,
  },
  occasionTitle: {
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '700',
    lineHeight: 18,
  },
  occasionDays: {
    marginTop: 2,
    color: Colors.textSecondary,
    fontSize: 12,
    lineHeight: 16,
  },
  occasionBudget: {
    marginTop: 4,
    color: Colors.successGreen,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '600',
  },
  planText: {
    marginTop: 8,
    color: Colors.linkBlue,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '600',
  },
  occasionCardTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  occasionEmoji: {
    fontSize: 22,
    lineHeight: 28,
  },
  urgencyPill: {
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  urgencyPillText: {
    color: Colors.white,
    fontSize: 10,
    fontWeight: '700',
    lineHeight: 14,
  },
  occasionSignal: {
    marginTop: 6,
    color: Colors.textSecondary,
    fontSize: 11,
    lineHeight: 15,
  },
  startCartBtn: {
    marginTop: 10,
    backgroundColor: Colors.primary,
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  startCartBtnText: {
    color: Colors.white,
    fontSize: 13,
    fontWeight: '600',
  },
  // Goal tiles
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
  // Community activity
  communityList: {
    paddingHorizontal: 16,
  },
  communityRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
    gap: 12,
  },
  communityMessage: {
    flex: 1,
    color: Colors.textPrimary,
    fontSize: 13,
    lineHeight: 18,
  },
  // Identity group product grid
  groupProductGrid: {
    marginTop: 12,
    marginBottom: 4,
  },
  groupProductLoading: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  groupProductLoadingText: {
    fontSize: 13,
    color: Colors.textSecondary,
  },
  groupProductGridTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.textSecondary,
    marginBottom: 10,
    paddingHorizontal: 16,
  },
  groupProductRow: {
    paddingHorizontal: 16,
    gap: 10,
    marginBottom: 10,
  },
  groupProductCard: {
    flex: 1,
    backgroundColor: Colors.white,
    borderRadius: 8,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: Colors.inputBorder,
  },
  groupProductImage: {
    height: 88,
    width: '100%',
  },
  groupProductInfo: {
    padding: 8,
  },
  groupProductName: {
    fontSize: 13,
    fontWeight: '600',
    color: '#0F1111',
    marginTop: 6,
    lineHeight: 18,
  },
  groupProductPrice: {
    fontSize: 13,
    fontWeight: '700',
    color: Colors.textPrimary,
    marginBottom: 2,
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    marginTop: 4,
  },
  ratingText: {
    fontSize: 12,
    fontWeight: '500',
    color: '#0F1111',
  },
  groupProductNow: {
    fontSize: 9,
    fontWeight: '700',
    color: Colors.successGreen,
  },
  adoptionCopy: {
    fontSize: 11,
    fontWeight: '400',
    color: '#007600',
    marginTop: 3,
    fontStyle: 'italic',
  },
  groupProductEmpty: {
    fontSize: 13,
    color: Colors.textSecondary,
    textAlign: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  // Community Goals section
  communityGoalsScroll: {
    paddingLeft: 16,
    paddingRight: 8,
    paddingBottom: 4,
  },
  communityGoalCard: {
    width: 168,
    marginRight: 8,
    padding: 12,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
    borderTopWidth: 3,
    borderTopColor: Colors.primary,
  },
  goalCardTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  goalCardEmoji: {
    fontSize: 20,
    lineHeight: 26,
  },
  goalDaysBadge: {
    backgroundColor: Colors.divider,
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 3,
  },
  goalDaysBadgeUrgent: {
    backgroundColor: '#E53935',
  },
  goalDaysText: {
    fontSize: 10,
    fontWeight: '700',
    color: Colors.textSecondary,
  },
  goalDaysTextUrgent: {
    color: Colors.white,
  },
  communityGoalTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: Colors.textPrimary,
    lineHeight: 18,
    marginBottom: 4,
  },
  goalParticipants: {
    fontSize: 11,
    color: Colors.textSecondary,
    marginBottom: 8,
  },
  goalProgressBar: {
    height: 5,
    backgroundColor: Colors.divider,
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 4,
  },
  goalProgressFill: {
    height: 5,
    backgroundColor: Colors.successGreen,
    borderRadius: 3,
  },
  goalProgressLabel: {
    fontSize: 10,
    color: Colors.successGreen,
    fontWeight: '600',
  },
})
