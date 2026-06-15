import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useEffect, useState } from 'react'
import {
  FlatList,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { hiveAPI } from '../../lib/api'
import { Colors } from '../../lib/constants'

type Tab = 'cart' | 'chat' | 'budget' | 'split'

export default function HiveScreen() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<Tab>('cart')
  const [hive, setHive] = useState<any>(null)
  const [cart, setCart] = useState<any>(null)
  const [messages, setMessages] = useState<any[]>([])
  const [budgetStatus, setBudgetStatus] = useState<any>(null)
  const [splitPreview, setSplitPreview] = useState<any>(null)
  const [splitMethod, setSplitMethod] = useState('equal')
  const [optimizing, setOptimizing] = useState(false)
  const [showOptimizeSheet, setShowOptimizeSheet] = useState(false)
  const [optimizeResult, setOptimizeResult] = useState<any>(null)

  useEffect(() => {
    hiveAPI.getDemo().then((res) => {
      const d = res.data.data
      setHive(d.hive)
      setCart(d.cart)
      setMessages(d.messages)
      setBudgetStatus(d.budget_status)
      setSplitPreview(d.split_preview)
    }).catch(() => {})
  }, [])

  const handleVote = (item: any, value: number) => {
    setCart((prev: any) => ({
      ...prev,
      items: prev.items.map((i: any) =>
        i.item_id === item.item_id
          ? {
              ...i,
              votes: [...i.votes.filter((v: any) => v.user_id !== 'U001'), { user_id: 'U001', value }],
              vote_score: i.votes.filter((v: any) => v.user_id !== 'U001').reduce((s: number, v: any) => s + v.value, 0) + value,
            }
          : i,
      ),
    }))
    hiveAPI.vote(cart.cart_id, item.item_id, 'U001', value as 1 | -1).catch(() => {})
  }

  const handleOptimize = () => {
    setOptimizing(true)
    hiveAPI.optimize(cart.cart_id).then((res) => {
      setOptimizeResult(res.data.data)
      setShowOptimizeSheet(true)
      hiveAPI.getDemo().then((r) => {
        const d = r.data.data
        setCart(d.cart)
        setBudgetStatus(d.budget_status)
      })
    }).finally(() => setOptimizing(false))
  }

  const handleSplitMethodChange = (method: string) => {
    setSplitMethod(method)
    hiveAPI.getSplit(cart?.cart_id || '', method).then((res) => {
      setSplitPreview(res.data.data)
    }).catch(() => {})
  }

  const handlePlaceOrder = () => {
    hiveAPI.placeOrder(cart?.cart_id || '', splitMethod).then((res) => {
      const d = res.data.data
      router.push({ pathname: '/hive/confirmation', params: { orderId: d.order_id, total: String(d.total), perPerson: String(d.per_person) } })
    }).catch(() => {})
  }

  if (!cart) return <View style={styles.loading}><Text style={styles.loadingText}>Loading Hive...</Text></View>

  const userVoted = (item: any, val: number) => item.votes?.some((v: any) => v.user_id === 'U001' && v.value === val)

  // ── RENDER TABS ─────────────────────────────────────────
  const renderCartTab = () => (
    <View style={{ flex: 1 }}>
      {/* Budget bar */}
      <View style={styles.budgetCard}>
        <View style={styles.budgetRow}>
          <Text style={styles.budgetTotal}>₹{budgetStatus?.total || 0}</Text>
          <Text style={styles.budgetCap}>of ₹{budgetStatus?.cap || 4000} budget</Text>
        </View>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${Math.min(budgetStatus?.percentage || 0, 100)}%`, backgroundColor: budgetStatus?.over_budget ? Colors.errorRed : Colors.successGreen }]} />
        </View>
        {budgetStatus?.over_budget && (
          <Text style={styles.overBudgetText}>₹{budgetStatus.over_by} over budget — tap Optimize</Text>
        )}
      </View>

      <FlatList
        data={cart.items}
        keyExtractor={(item: any) => item.item_id}
        contentContainerStyle={{ paddingBottom: 80 }}
        renderItem={({ item }) => (
          <View style={styles.itemCard}>
            <View style={styles.itemTop}>
              <View style={[styles.memberAvatar, { backgroundColor: item.added_by_color }]}>
                <Text style={styles.memberAvatarText}>{item.added_by_letter}</Text>
              </View>
              <View style={styles.itemInfo}>
                <Text style={styles.itemTitle} numberOfLines={1}>{item.title}</Text>
                <Text style={styles.itemPrice}>₹{item.price} × {item.quantity} = <Text style={{ fontWeight: '700' }}>₹{item.price * item.quantity}</Text></Text>
                {item.note ? <Text style={styles.itemNote}>{item.note}</Text> : null}
              </View>
              <View style={styles.voteCol}>
                <TouchableOpacity style={[styles.voteBtn, userVoted(item, 1) && styles.voteBtnUp]} onPress={() => handleVote(item, 1)}>
                  <Ionicons name="thumbs-up" size={14} color={userVoted(item, 1) ? Colors.successGreen : Colors.textSecondary} />
                </TouchableOpacity>
                <Text style={[styles.voteScore, { color: item.vote_score > 0 ? Colors.successGreen : item.vote_score < 0 ? Colors.errorRed : Colors.textSecondary }]}>{item.vote_score}</Text>
                <TouchableOpacity style={[styles.voteBtn, userVoted(item, -1) && styles.voteBtnDown]} onPress={() => handleVote(item, -1)}>
                  <Ionicons name="thumbs-down" size={14} color={userVoted(item, -1) ? Colors.errorRed : Colors.textSecondary} />
                </TouchableOpacity>
              </View>
            </View>
            <View style={[styles.statusPill, item.status === 'approved' && styles.statusApproved, item.status === 'rejected' && styles.statusRejected, item.status === 'pending' && styles.statusPending]}>
              <Text style={[styles.statusText, item.status === 'approved' && { color: '#007600' }, item.status === 'rejected' && { color: '#CC0C39' }, item.status === 'pending' && { color: '#F57F17' }]}>
                {item.status === 'approved' ? '✓ Approved' : item.status === 'rejected' ? '✕ Low votes' : '· Pending'}
              </Text>
            </View>
          </View>
        )}
      />

      <View style={styles.fixedBottom}>
        <Pressable style={styles.optimizeBtn} onPress={handleOptimize} disabled={optimizing}>
          <Ionicons name="sparkles" size={18} color={Colors.white} />
          <Text style={styles.optimizeBtnText}>{optimizing ? 'Optimizing...' : 'Optimize Hive Cart'}</Text>
        </Pressable>
      </View>
    </View>
  )

  const renderChatTab = () => (
    <FlatList
      data={[...messages].reverse()}
      keyExtractor={(m: any) => m.msg_id}
      inverted
      contentContainerStyle={{ padding: 12 }}
      renderItem={({ item: m }) => {
        if (m.type === 'system') return (
          <View style={styles.sysMsg}><Text style={styles.sysMsgText}>{m.text}</Text></View>
        )
        return (
          <View style={styles.chatRow}>
            <View style={[styles.chatAvatar, { backgroundColor: m.color }]}><Text style={styles.chatAvatarText}>{m.letter}</Text></View>
            <View style={styles.chatBubble}>
              <Text style={styles.chatName}>{m.name}</Text>
              <Text style={styles.chatText}>{m.text}</Text>
              <Text style={styles.chatTime}>{m.timestamp}</Text>
            </View>
          </View>
        )
      }}
    />
  )

  const renderBudgetTab = () => (
    <ScrollView contentContainerStyle={{ padding: 12 }}>
      <View style={styles.budgetHeaderCard}>
        <Text style={styles.budgetHeaderLabel}>Hive Budget</Text>
        <Text style={[styles.budgetHeaderTotal, { color: budgetStatus?.over_budget ? Colors.errorRed : Colors.successGreen }]}>₹{budgetStatus?.total || 0}</Text>
        <Text style={styles.budgetHeaderCap}>of ₹{budgetStatus?.cap || 4000} budget</Text>
        <View style={[styles.progressTrack, { height: 12, marginTop: 12 }]}>
          <View style={[styles.progressFill, { height: 12, width: `${Math.min(budgetStatus?.percentage || 0, 100)}%`, backgroundColor: budgetStatus?.over_budget ? Colors.errorRed : Colors.successGreen }]} />
        </View>
        <Text style={styles.budgetPercentage}>{budgetStatus?.percentage || 0}% used</Text>
      </View>
      <Text style={styles.sectionTitle}>By category</Text>
      {Object.entries(
        (cart?.items || []).reduce((acc: any, i: any) => { acc[i.category] = (acc[i.category] || 0) + i.price * i.quantity; return acc }, {})
      ).sort((a: any, b: any) => b[1] - a[1]).map(([cat, cost]: any) => (
        <View key={cat} style={styles.catRow}>
          <Text style={styles.catName}>{cat.replace(/_/g, ' ')}</Text>
          <Text style={styles.catCost}>₹{cost}</Text>
        </View>
      ))}
    </ScrollView>
  )

  const renderSplitTab = () => (
    <ScrollView contentContainerStyle={{ padding: 12, paddingBottom: 100 }}>
      <View style={styles.splitToggle}>
        <TouchableOpacity style={[styles.splitPill, splitMethod === 'equal' && styles.splitPillActive]} onPress={() => handleSplitMethodChange('equal')}>
          <Text style={[styles.splitPillText, splitMethod === 'equal' && styles.splitPillTextActive]}>Equal split</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.splitPill, splitMethod === 'by_contribution' && styles.splitPillActive]} onPress={() => handleSplitMethodChange('by_contribution')}>
          <Text style={[styles.splitPillText, splitMethod === 'by_contribution' && styles.splitPillTextActive]}>By contribution</Text>
        </TouchableOpacity>
      </View>
      {(splitPreview?.splits || []).map((s: any) => (
        <View key={s.user_id} style={styles.splitCard}>
          <View style={[styles.splitAvatar, { backgroundColor: s.color }]}><Text style={styles.splitAvatarText}>{s.letter}</Text></View>
          <View style={styles.splitInfo}>
            <Text style={styles.splitName}>{s.name}</Text>
            <Text style={styles.splitAmount}>₹{Math.round(s.amount)}</Text>
            <Text style={styles.splitLabel}>to pay</Text>
          </View>
        </View>
      ))}
      <View style={styles.splitTotalRow}>
        <Text style={styles.splitTotalLabel}>Total: ₹{splitPreview?.total || 0}</Text>
        <Text style={styles.splitTotalSub}>4 members</Text>
      </View>
      {!budgetStatus?.over_budget ? (
        <Pressable style={styles.placeOrderBtn} onPress={handlePlaceOrder}>
          <Text style={styles.placeOrderText}>Place Hive Order · ₹{splitPreview?.total || 0}</Text>
        </Pressable>
      ) : (
        <View style={styles.placeOrderDisabled}><Text style={styles.placeOrderDisabledText}>Optimize first to place order</Text></View>
      )}
    </ScrollView>
  )

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar style="light" backgroundColor="#1A3A5C" />
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </Pressable>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>{hive?.name || 'Birthday Party Squad'}</Text>
          <Text style={styles.headerSub}>{hive?.member_count || 4} members · Birthday Party</Text>
        </View>
        <View style={styles.avatarStack}>
          {(hive?.members || MEMBERS_FALLBACK).slice(0, 3).map((m: any, i: number) => (
            <View key={m.user_id} style={[styles.stackAvatar, { backgroundColor: m.color, marginLeft: i > 0 ? -8 : 0, zIndex: 3 - i }]}>
              <Text style={styles.stackAvatarText}>{m.letter}</Text>
            </View>
          ))}
        </View>
      </View>
      {/* Tab bar */}
      <View style={styles.tabBar}>
        {(['cart', 'chat', 'budget', 'split'] as Tab[]).map((tab) => (
          <TouchableOpacity key={tab} style={styles.tab} onPress={() => setActiveTab(tab)}>
            <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>{tab.charAt(0).toUpperCase() + tab.slice(1)}</Text>
            {activeTab === tab && <View style={styles.tabUnderline} />}
          </TouchableOpacity>
        ))}
      </View>
      {/* Content */}
      <View style={{ flex: 1, backgroundColor: Colors.background }}>
        {activeTab === 'cart' && renderCartTab()}
        {activeTab === 'chat' && renderChatTab()}
        {activeTab === 'budget' && renderBudgetTab()}
        {activeTab === 'split' && renderSplitTab()}
      </View>
      {/* Optimize Result Modal */}
      <Modal visible={showOptimizeSheet} transparent animationType="slide" onRequestClose={() => setShowOptimizeSheet(false)}>
        <Pressable style={styles.modalBackdrop} onPress={() => setShowOptimizeSheet(false)} />
        <View style={styles.modalSheet}>
          <View style={styles.modalHandle} />
          <Text style={styles.modalTitle}>Hive Optimizer Results</Text>
          <View style={styles.savingsRow}>
            <Text style={styles.originalPrice}>₹{optimizeResult?.original_total}</Text>
            <Text style={styles.arrow}> → </Text>
            <Text style={styles.optimizedPrice}>₹{optimizeResult?.optimized_total}</Text>
          </View>
          <View style={styles.savedPill}><Text style={styles.savedPillText}>Saved ₹{optimizeResult?.total_saved}</Text></View>
          <View style={styles.divider} />
          <Text style={styles.actionsTitle}>Actions taken</Text>
          {(optimizeResult?.actions || []).map((a: any, i: number) => (
            <View key={i} style={styles.actionRow}>
              <Ionicons name={a.icon as any} size={18} color={a.action_type === 'remove' ? '#CC0C39' : '#007185'} />
              <View style={styles.actionInfo}>
                <Text style={styles.actionTitle} numberOfLines={1}>{a.title}</Text>
                <Text style={styles.actionReason}>{a.reason}</Text>
              </View>
              <Text style={styles.actionSaved}>−₹{a.saved}</Text>
            </View>
          ))}
          <Pressable style={styles.gotItBtn} onPress={() => setShowOptimizeSheet(false)}>
            <Text style={styles.gotItText}>Got it — apply savings</Text>
          </Pressable>
        </View>
      </Modal>
    </SafeAreaView>
  )
}

const MEMBERS_FALLBACK = [
  { user_id: 'U001', letter: 'S', color: '#FF9900' },
  { user_id: 'U002', letter: 'R', color: '#007185' },
  { user_id: 'U003', letter: 'A', color: '#007600' },
]

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#1A3A5C' },
  loading: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: Colors.background },
  loadingText: { color: Colors.textSecondary, fontSize: 14 },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#1A3A5C' },
  backBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  headerCenter: { flex: 1, marginLeft: 8 },
  headerTitle: { color: Colors.white, fontSize: 18, fontWeight: '700' },
  headerSub: { color: Colors.white, fontSize: 12, opacity: 0.8, marginTop: 1 },
  avatarStack: { flexDirection: 'row' },
  stackAvatar: { width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: '#1A3A5C' },
  stackAvatarText: { color: Colors.white, fontSize: 11, fontWeight: '700' },
  tabBar: { flexDirection: 'row', backgroundColor: '#1A3A5C', paddingHorizontal: 16 },
  tab: { flex: 1, alignItems: 'center', paddingVertical: 10 },
  tabText: { color: Colors.white, fontSize: 13, opacity: 0.6 },
  tabTextActive: { opacity: 1, fontWeight: '700' },
  tabUnderline: { position: 'absolute', bottom: 0, width: '60%', height: 2, backgroundColor: Colors.white, borderRadius: 1 },
  // Cart tab
  budgetCard: { margin: 12, padding: 12, backgroundColor: Colors.background, borderRadius: 8, borderWidth: 1, borderColor: '#F0F2F2' },
  budgetRow: { flexDirection: 'row', alignItems: 'baseline', gap: 6 },
  budgetTotal: { color: Colors.textPrimary, fontSize: 18, fontWeight: '700' },
  budgetCap: { color: Colors.textSecondary, fontSize: 13 },
  progressTrack: { height: 8, marginTop: 8, backgroundColor: '#F0F2F2', borderRadius: 4, overflow: 'hidden' },
  progressFill: { height: 8, borderRadius: 4 },
  overBudgetText: { color: Colors.errorRed, fontSize: 12, fontWeight: '600', marginTop: 4 },
  itemCard: { marginHorizontal: 12, marginVertical: 4, padding: 12, backgroundColor: Colors.background, borderRadius: 4, borderWidth: 1, borderColor: '#F0F2F2' },
  itemTop: { flexDirection: 'row', alignItems: 'flex-start' },
  memberAvatar: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  memberAvatarText: { color: Colors.white, fontSize: 14, fontWeight: '700' },
  itemInfo: { flex: 1, marginLeft: 8 },
  itemTitle: { color: Colors.textPrimary, fontSize: 14, fontWeight: '700' },
  itemPrice: { color: Colors.textSecondary, fontSize: 12, marginTop: 2 },
  itemNote: { color: Colors.textSecondary, fontSize: 11, fontStyle: 'italic', marginTop: 2 },
  voteCol: { alignItems: 'center', gap: 2 },
  voteBtn: { width: 32, height: 32, borderRadius: 16, backgroundColor: '#F7F8F8', alignItems: 'center', justifyContent: 'center' },
  voteBtnUp: { backgroundColor: '#E7F5EA' },
  voteBtnDown: { backgroundColor: '#FFEBEE' },
  voteScore: { fontSize: 13, fontWeight: '700' },
  statusPill: { alignSelf: 'flex-start', marginTop: 6, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 3 },
  statusApproved: { backgroundColor: '#E7F5EA' },
  statusRejected: { backgroundColor: '#FFEBEE' },
  statusPending: { backgroundColor: '#FFF8E1' },
  statusText: { fontSize: 10, fontWeight: '700' },
  fixedBottom: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: 12, backgroundColor: Colors.background, borderTopWidth: 1, borderTopColor: '#F0F2F2' },
  optimizeBtn: { backgroundColor: Colors.primary, height: 52, borderRadius: 4, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  optimizeBtnText: { color: Colors.white, fontSize: 16, fontWeight: '700' },
  // Chat tab
  sysMsg: { alignSelf: 'center', backgroundColor: '#F7F8F8', borderRadius: 12, paddingHorizontal: 12, paddingVertical: 4, margin: 4 },
  sysMsgText: { color: Colors.textSecondary, fontSize: 12, textAlign: 'center' },
  chatRow: { flexDirection: 'row', margin: 8, marginHorizontal: 12 },
  chatAvatar: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  chatAvatarText: { color: Colors.white, fontSize: 13, fontWeight: '700' },
  chatBubble: { flex: 1, marginLeft: 8, backgroundColor: Colors.background, borderRadius: 8, padding: 8, paddingHorizontal: 12, borderWidth: 1, borderColor: '#F0F2F2' },
  chatName: { color: Colors.textSecondary, fontSize: 11, fontWeight: '700' },
  chatText: { color: Colors.textPrimary, fontSize: 14, marginTop: 2 },
  chatTime: { color: '#9AA0A6', fontSize: 10, marginTop: 2 },
  // Budget tab
  budgetHeaderCard: { backgroundColor: Colors.background, borderRadius: 8, padding: 16, borderWidth: 1, borderColor: '#D5D9D9', marginBottom: 16 },
  budgetHeaderLabel: { color: Colors.textPrimary, fontSize: 16, fontWeight: '700' },
  budgetHeaderTotal: { fontSize: 32, fontWeight: '700', marginTop: 4 },
  budgetHeaderCap: { color: Colors.textSecondary, fontSize: 14 },
  budgetPercentage: { color: Colors.textSecondary, fontSize: 12, marginTop: 4 },
  sectionTitle: { color: Colors.textPrimary, fontSize: 14, fontWeight: '700', marginTop: 16, marginBottom: 8 },
  catRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#F0F2F2' },
  catName: { color: Colors.textPrimary, fontSize: 13, textTransform: 'capitalize' },
  catCost: { color: Colors.textPrimary, fontSize: 13, fontWeight: '700' },
  // Split tab
  splitToggle: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  splitPill: { flex: 1, height: 36, borderRadius: 18, borderWidth: 1, borderColor: '#D5D9D9', alignItems: 'center', justifyContent: 'center' },
  splitPillActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  splitPillText: { color: Colors.textSecondary, fontSize: 13 },
  splitPillTextActive: { color: Colors.white, fontWeight: '700' },
  splitCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.background, borderRadius: 8, padding: 16, borderWidth: 1, borderColor: '#D5D9D9', marginBottom: 8 },
  splitAvatar: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
  splitAvatarText: { color: Colors.white, fontSize: 18, fontWeight: '700' },
  splitInfo: { marginLeft: 12 },
  splitName: { color: Colors.textPrimary, fontSize: 16, fontWeight: '700' },
  splitAmount: { color: Colors.errorRed, fontSize: 22, fontWeight: '700', marginTop: 2 },
  splitLabel: { color: Colors.textSecondary, fontSize: 12 },
  splitTotalRow: { padding: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  splitTotalLabel: { color: Colors.textPrimary, fontSize: 16, fontWeight: '700' },
  splitTotalSub: { color: Colors.textSecondary, fontSize: 13 },
  placeOrderBtn: { backgroundColor: Colors.successGreen, height: 52, borderRadius: 4, alignItems: 'center', justifyContent: 'center', margin: 12 },
  placeOrderText: { color: Colors.white, fontSize: 16, fontWeight: '700' },
  placeOrderDisabled: { backgroundColor: '#D5D9D9', height: 52, borderRadius: 4, alignItems: 'center', justifyContent: 'center', margin: 12 },
  placeOrderDisabledText: { color: Colors.textSecondary, fontSize: 16 },
  // Modal
  modalBackdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' },
  modalSheet: { position: 'absolute', bottom: 0, left: 0, right: 0, backgroundColor: Colors.background, borderTopLeftRadius: 16, borderTopRightRadius: 16, padding: 16, paddingBottom: 32 },
  modalHandle: { width: 40, height: 4, backgroundColor: '#D5D9D9', borderRadius: 2, alignSelf: 'center', marginBottom: 16 },
  modalTitle: { color: Colors.textPrimary, fontSize: 18, fontWeight: '700' },
  savingsRow: { flexDirection: 'row', alignItems: 'center', marginTop: 12 },
  originalPrice: { color: Colors.textSecondary, fontSize: 18, textDecorationLine: 'line-through' },
  arrow: { color: Colors.textSecondary, fontSize: 16 },
  optimizedPrice: { color: Colors.successGreen, fontSize: 22, fontWeight: '700' },
  savedPill: { backgroundColor: '#E7F5EA', alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 4, marginTop: 8 },
  savedPillText: { color: Colors.successGreen, fontSize: 13, fontWeight: '700' },
  divider: { height: 1, backgroundColor: '#F0F2F2', marginVertical: 16 },
  actionsTitle: { color: Colors.textPrimary, fontSize: 14, fontWeight: '700', marginBottom: 8 },
  actionRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F0F2F2' },
  actionInfo: { flex: 1, marginLeft: 10 },
  actionTitle: { color: Colors.textPrimary, fontSize: 14 },
  actionReason: { color: Colors.textSecondary, fontSize: 12, marginTop: 2 },
  actionSaved: { color: Colors.successGreen, fontSize: 14, fontWeight: '700' },
  gotItBtn: { backgroundColor: Colors.primary, height: 48, borderRadius: 4, alignItems: 'center', justifyContent: 'center', marginTop: 16 },
  gotItText: { color: Colors.white, fontSize: 15, fontWeight: '700' },
})
