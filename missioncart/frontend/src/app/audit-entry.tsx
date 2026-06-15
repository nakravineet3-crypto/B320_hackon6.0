import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { Colors } from '../lib/constants'

export default function AuditEntryScreen() {
  const router = useRouter()

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar style="light" backgroundColor={Colors.nowBlue} />

      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </Pressable>
        <View>
          <Text style={styles.headerTitle}>Cart Audit</Text>
          <Text style={styles.headerSubtitle}>Constraint-based cart analysis</Text>
        </View>
      </View>

      <ScrollView style={styles.body} contentContainerStyle={styles.bodyContent}>
        {/* CARD 1 — Demo path */}
        <View style={styles.demoCard}>
          <View style={styles.demoPill}>
            <Text style={styles.demoPillText}>FEATURED DEMO</Text>
          </View>
          <Text style={styles.cardTitle}>Sneha's Birthday Cart</Text>
          <Text style={styles.cardDescription}>
            See the full audit experience — quantity errors, missing accessories,
            sponsored blocking, and automatic repair in action.
          </Text>
          <View style={styles.statsRow}>
            <Text style={styles.statText}>4 items</Text>
            <Text style={styles.statDot}>·</Text>
            <Text style={styles.statText}>4 flags found</Text>
            <Text style={styles.statDot}>·</Text>
            <Text style={styles.statText}>₹490 saved</Text>
          </View>
          <Pressable style={styles.primaryButton} onPress={() => router.push('/audit')}>
            <Text style={styles.primaryButtonText}>Start Demo Audit →</Text>
          </Pressable>
        </View>

        {/* CARD 2 — Real path */}
        <View style={styles.realCard}>
          <Text style={styles.cardTitle}>Audit Your Own Cart</Text>
          <Text style={styles.cardDescription}>
            Add products from our catalog, tell us your occasion, and we'll find
            every issue before you checkout.
          </Text>
          <Pressable style={styles.secondaryButton} onPress={() => router.push('/audit-build')}>
            <Text style={styles.secondaryButtonText}>Try it →</Text>
          </Pressable>
        </View>

        <Text style={styles.bottomNote}>
          Demo AI layer · Bedrock-ready production architecture
        </Text>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.nowBlue },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    backgroundColor: Colors.nowBlue,
  },
  backBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center', marginRight: 8 },
  headerTitle: { color: Colors.white, fontSize: 18, fontWeight: '700' },
  headerSubtitle: { color: Colors.white, fontSize: 12, opacity: 0.85, marginTop: 1 },
  body: { flex: 1, backgroundColor: Colors.background },
  bodyContent: { padding: 16, paddingBottom: 40 },
  demoCard: {
    backgroundColor: Colors.background,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: Colors.primary,
    padding: 20,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  demoPill: {
    backgroundColor: Colors.primary,
    borderRadius: 3,
    paddingHorizontal: 8,
    paddingVertical: 3,
    alignSelf: 'flex-start',
  },
  demoPillText: { color: Colors.white, fontSize: 10, fontWeight: '700', letterSpacing: 1 },
  cardTitle: { color: Colors.textPrimary, fontSize: 18, fontWeight: '700', marginTop: 8 },
  cardDescription: { color: Colors.textSecondary, fontSize: 13, lineHeight: 19, marginTop: 6 },
  statsRow: { flexDirection: 'row', marginTop: 12, alignItems: 'center', gap: 6 },
  statText: { color: Colors.textSecondary, fontSize: 12 },
  statDot: { color: Colors.textSecondary, fontSize: 12 },
  primaryButton: {
    backgroundColor: Colors.primary,
    height: 48,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 16,
  },
  primaryButtonText: { color: Colors.white, fontSize: 15, fontWeight: '700' },
  realCard: {
    backgroundColor: Colors.background,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#D5D9D9',
    padding: 20,
    marginTop: 12,
  },
  secondaryButton: {
    backgroundColor: Colors.background,
    borderWidth: 1.5,
    borderColor: Colors.linkBlue,
    height: 48,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 16,
  },
  secondaryButtonText: { color: Colors.linkBlue, fontSize: 15, fontWeight: '700' },
  bottomNote: { color: '#9AA0A6', fontSize: 11, textAlign: 'center', marginTop: 16 },
})
