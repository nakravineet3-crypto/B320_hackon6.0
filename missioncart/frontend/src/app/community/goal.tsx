import { Ionicons } from '@expo/vector-icons'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { useEffect, useState } from 'react'
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { communityGoalAPI } from '../../lib/api'
import { Colors } from '../../lib/constants'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface GoalItem {
  item_id: string
  asin: string
  title: string
  price_inr: number
  category: string
  claimed_by: string | null
  claimed_by_name: string | null
  status: 'claimed' | 'unclaimed'
}

interface GoalPageDetail {
  goal_id: string
  title: string
  occasion_type: string
  occasion_emoji: string
  created_by: string
  participants: string[]
  participant_names: string[]
  target_date: string
  budget_total: number
  budget_per_person: number
  items: GoalItem[]
  items_total: number
  items_claimed: number
  coverage_pct: number
  days_until: number
  community_signal: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const AVATAR_COLORS = ['#FF9900', '#007185', '#007600', '#C45500', '#5C6BC0', '#2E7D32', '#AB47BC', '#E53935']

function getAvatarColor(idx: number): string {
  return AVATAR_COLORS[idx % AVATAR_COLORS.length]
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function formatDaysLabel(days: number): string {
  if (days < 0) return 'Past'
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  return `${days} days`
}

function formatInr(value: number): string {
  return value.toLocaleString('en-IN')
}

// ---------------------------------------------------------------------------
// Main screen
// ---------------------------------------------------------------------------
export default function CommunityGoalScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const router = useRouter()

  const [goal, setGoal] = useState<GoalPageDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [claimedLocally, setClaimedLocally] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!id) {
      setError('No goal ID provided')
      setLoading(false)
      return
    }
    communityGoalAPI
      .getGoal(id)
      .then((data) => {
        setGoal(data)
        setLoading(false)
      })
      .catch(() => {
        setError('Could not load goal page')
        setLoading(false)
      })
  }, [id])

  function handleClaim(itemId: string) {
    setClaimedLocally((prev) => {
      const next = new Set(prev)
      next.add(itemId)
      return next
    })
  }

  function handleAddToCart() {
    if (!goal) return
    const unclaimed = goal.items.filter(
      (it) => it.status === 'unclaimed' && !claimedLocally.has(it.item_id),
    )
    const goalText =
      unclaimed.length > 0
        ? `Community goal items for ${goal.title}`
        : goal.title
    router.push({
      pathname: '/cart/building',
      params: {
        goal: goalText,
        budget: String(goal.budget_per_person),
        occasion_type: goal.occasion_type,
      },
    })
  }

  // ── Loading state ──
  if (loading) {
    return (
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Loading goal page...</Text>
        </View>
      </SafeAreaView>
    )
  }

  // ── Error state ──
  if (error || !goal) {
    return (
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <View style={styles.centered}>
          <Ionicons name="alert-circle-outline" size={40} color={Colors.errorRed} />
          <Text style={styles.errorText}>{error ?? 'Goal not found'}</Text>
          <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
            <Text style={styles.backBtnText}>Go Back</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    )
  }

  const claimedCount =
    goal.items.filter((it) => it.status === 'claimed' || claimedLocally.has(it.item_id)).length
  const totalCount = goal.items_total
  const coveragePct = totalCount > 0 ? Math.round((claimedCount / totalCount) * 100) : 0
  const daysLabel = formatDaysLabel(goal.days_until)
  const daysUrgent = goal.days_until >= 0 && goal.days_until <= 3

  const unclaimedItems = goal.items.filter(
    (it) => it.status === 'unclaimed' && !claimedLocally.has(it.item_id),
  )
  const claimedItems = goal.items.filter(
    (it) => it.status === 'claimed' || claimedLocally.has(it.item_id),
  )

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Back nav */}
        <TouchableOpacity style={styles.navBack} onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={20} color={Colors.textPrimary} />
          <Text style={styles.navBackText}>Discover</Text>
        </TouchableOpacity>

        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerEmoji}>{goal.occasion_emoji}</Text>
          <View style={styles.headerText}>
            <Text style={styles.goalTitle} numberOfLines={2}>
              {goal.title}
            </Text>
            <View style={styles.urgencyRow}>
              <View style={[styles.daysBadge, daysUrgent && styles.daysBadgeUrgent]}>
                <Ionicons
                  name="calendar-outline"
                  size={12}
                  color={daysUrgent ? Colors.white : Colors.textSecondary}
                />
                <Text style={[styles.daysText, daysUrgent && styles.daysTextUrgent]}>
                  {daysLabel}
                </Text>
              </View>
              <Text style={styles.budgetLabel}>
                ₹{formatInr(goal.budget_total)} total · ₹{formatInr(goal.budget_per_person)}/person
              </Text>
            </View>
          </View>
        </View>

        {/* Progress section */}
        <View style={styles.progressCard}>
          <View style={styles.progressHeader}>
            <Text style={styles.progressTitle}>
              {claimedCount} of {totalCount} items claimed
            </Text>
            <Text style={styles.progressPct}>{coveragePct}%</Text>
          </View>
          <View style={styles.progressBar}>
            <View style={[styles.progressFill, { width: `${coveragePct}%` }]} />
          </View>
          <Text style={styles.communitySignal}>{goal.community_signal}</Text>
        </View>

        {/* Participants */}
        <View style={styles.sectionBlock}>
          <Text style={styles.sectionLabel}>
            {goal.participant_names.length}{' '}
            {goal.participant_names.length === 1 ? 'person' : 'people'} coordinating
          </Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.avatarRow}>
            {goal.participant_names.map((name, idx) => (
              <View key={idx} style={styles.avatarWrap}>
                <View style={[styles.avatar, { backgroundColor: getAvatarColor(idx) }]}>
                  <Text style={styles.avatarInitials}>{getInitials(name)}</Text>
                </View>
                <Text style={styles.avatarName} numberOfLines={1}>
                  {name}
                </Text>
              </View>
            ))}
          </ScrollView>
        </View>

        {/* Unclaimed items */}
        {unclaimedItems.length > 0 && (
          <View style={styles.sectionBlock}>
            <Text style={styles.sectionLabel}>Needs someone to bring</Text>
            {unclaimedItems.map((item) => (
              <View key={item.item_id} style={styles.itemRow}>
                <View style={styles.itemInfo}>
                  <Text style={styles.itemTitle} numberOfLines={2}>
                    {item.title}
                  </Text>
                  <Text style={styles.itemPrice}>₹{formatInr(item.price_inr)}</Text>
                </View>
                <TouchableOpacity
                  style={styles.claimBtn}
                  onPress={() => handleClaim(item.item_id)}
                  activeOpacity={0.8}
                >
                  <Text style={styles.claimBtnText}>I'll bring it</Text>
                </TouchableOpacity>
              </View>
            ))}
          </View>
        )}

        {/* Claimed items */}
        {claimedItems.length > 0 && (
          <View style={styles.sectionBlock}>
            <Text style={styles.sectionLabel}>Already claimed</Text>
            {claimedItems.map((item) => {
              const isLocal = claimedLocally.has(item.item_id)
              const claimerName = isLocal ? 'You' : (item.claimed_by_name ?? 'Someone')
              return (
                <View key={item.item_id} style={[styles.itemRow, styles.itemRowClaimed]}>
                  <Ionicons name="checkmark-circle" size={18} color={Colors.successGreen} />
                  <View style={[styles.itemInfo, { marginLeft: 10 }]}>
                    <Text style={[styles.itemTitle, styles.itemTitleClaimed]} numberOfLines={2}>
                      {item.title}
                    </Text>
                    <Text style={styles.claimedBy}>{claimerName} is bringing this</Text>
                  </View>
                  <Text style={styles.itemPriceClaimed}>₹{formatInr(item.price_inr)}</Text>
                </View>
              )
            })}
          </View>
        )}

        {/* Add to Cart CTA */}
        <View style={styles.ctaBlock}>
          <TouchableOpacity style={styles.addToCartBtn} onPress={handleAddToCart} activeOpacity={0.85}>
            <Ionicons name="cart-outline" size={18} color={Colors.white} />
            <Text style={styles.addToCartText}>
              {unclaimedItems.length > 0
                ? `Build cart for ${unclaimedItems.length} unclaimed items`
                : 'Build your contribution cart'}
            </Text>
          </TouchableOpacity>
          <Text style={styles.ctaSubtext}>
            Opens Goal Cart Build pre-filled with occasion · Amazon Now delivery
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------
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
    paddingBottom: 40,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    gap: 12,
  },
  loadingText: {
    color: Colors.textSecondary,
    fontSize: 14,
  },
  errorText: {
    color: Colors.textPrimary,
    fontSize: 14,
    textAlign: 'center',
  },
  backBtn: {
    marginTop: 8,
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: Colors.primary,
    borderRadius: 4,
  },
  backBtnText: {
    color: Colors.white,
    fontSize: 14,
    fontWeight: '600',
  },
  // Nav
  navBack: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 8,
  },
  navBackText: {
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '500',
  },
  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 12,
  },
  headerEmoji: {
    fontSize: 36,
    lineHeight: 44,
  },
  headerText: {
    flex: 1,
  },
  goalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: Colors.textPrimary,
    lineHeight: 26,
  },
  urgencyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginTop: 6,
    flexWrap: 'wrap',
  },
  daysBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: Colors.divider,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  daysBadgeUrgent: {
    backgroundColor: '#E53935',
  },
  daysText: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.textSecondary,
  },
  daysTextUrgent: {
    color: Colors.white,
  },
  budgetLabel: {
    fontSize: 12,
    color: Colors.textSecondary,
  },
  // Progress
  progressCard: {
    marginHorizontal: 16,
    padding: 14,
    backgroundColor: Colors.cardBg,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    marginBottom: 4,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  progressTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.textPrimary,
  },
  progressPct: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.successGreen,
  },
  progressBar: {
    height: 8,
    backgroundColor: Colors.divider,
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 10,
  },
  progressFill: {
    height: 8,
    backgroundColor: Colors.successGreen,
    borderRadius: 4,
  },
  communitySignal: {
    fontSize: 12,
    color: Colors.textSecondary,
    fontStyle: 'italic',
    lineHeight: 16,
  },
  // Section blocks
  sectionBlock: {
    marginTop: 20,
    paddingHorizontal: 16,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: Colors.textSecondary,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    marginBottom: 12,
  },
  // Avatars
  avatarRow: {
    gap: 16,
    paddingBottom: 4,
  },
  avatarWrap: {
    alignItems: 'center',
    gap: 4,
    width: 52,
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarInitials: {
    color: Colors.white,
    fontSize: 14,
    fontWeight: '700',
  },
  avatarName: {
    fontSize: 10,
    color: Colors.textSecondary,
    textAlign: 'center',
    width: 52,
  },
  // Items
  itemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
    gap: 10,
  },
  itemRowClaimed: {
    opacity: 0.85,
  },
  itemInfo: {
    flex: 1,
  },
  itemTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.textPrimary,
    lineHeight: 18,
  },
  itemTitleClaimed: {
    color: Colors.textSecondary,
  },
  itemPrice: {
    fontSize: 13,
    fontWeight: '700',
    color: Colors.textPrimary,
    marginTop: 2,
  },
  itemPriceClaimed: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.textSecondary,
    minWidth: 50,
    textAlign: 'right',
  },
  claimedBy: {
    fontSize: 11,
    color: Colors.successGreen,
    marginTop: 2,
    fontWeight: '500',
  },
  claimBtn: {
    backgroundColor: Colors.primary,
    borderRadius: 4,
    paddingHorizontal: 14,
    paddingVertical: 8,
    minWidth: 90,
    alignItems: 'center',
  },
  claimBtnText: {
    color: Colors.white,
    fontSize: 12,
    fontWeight: '700',
  },
  // CTA
  ctaBlock: {
    marginTop: 28,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  addToCartBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: Colors.primary,
    borderRadius: 8,
    paddingVertical: 14,
    paddingHorizontal: 24,
    width: '100%',
    justifyContent: 'center',
  },
  addToCartText: {
    color: Colors.white,
    fontSize: 14,
    fontWeight: '700',
  },
  ctaSubtext: {
    marginTop: 8,
    fontSize: 11,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
})
