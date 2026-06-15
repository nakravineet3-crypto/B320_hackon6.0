import { Ionicons } from '@expo/vector-icons'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { Colors } from '../../lib/constants'

export default function HiveConfirmationScreen() {
  const router = useRouter()
  const params = useLocalSearchParams()
  const orderId = (params.orderId as string) || 'HIVE-847291'
  const total = params.total as string || '3720'
  const perPerson = params.perPerson as string || '930'

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar style="light" backgroundColor={Colors.successGreen} />
      <View style={styles.greenHeader}>
        <Ionicons name="checkmark-circle" size={24} color={Colors.white} />
        <Text style={styles.greenHeaderTitle}>Hive Order Placed!</Text>
      </View>

      <View style={styles.body}>
        <View style={styles.checkCircle}>
          <Ionicons name="checkmark" size={44} color={Colors.white} />
        </View>

        <Text style={styles.orderId}>Order {orderId}</Text>

        <View style={styles.deliveryCard}>
          <Text style={styles.deliveryTitle}>All 4 members</Text>
          <Text style={styles.deliveryEta}>Arriving in ~20 min ⚡</Text>
        </View>

        <Text style={styles.splitLabel}>Each person owes</Text>
        <Text style={styles.splitAmount}>₹{Math.round(Number(perPerson))}</Text>
        <Text style={styles.splitSub}>Birthday Party Squad · ₹{total} total</Text>

        <Pressable style={styles.homeBtn} onPress={() => router.replace('/')}>
          <Text style={styles.homeBtnText}>Back to Home</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.successGreen },
  greenHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 16, backgroundColor: Colors.successGreen, gap: 8 },
  greenHeaderTitle: { color: Colors.white, fontSize: 20, fontWeight: '700' },
  body: { flex: 1, backgroundColor: Colors.background, alignItems: 'center', paddingTop: 48 },
  checkCircle: { width: 80, height: 80, borderRadius: 40, backgroundColor: Colors.successGreen, alignItems: 'center', justifyContent: 'center' },
  orderId: { color: Colors.textPrimary, fontSize: 16, fontWeight: '700', marginTop: 24 },
  deliveryCard: { backgroundColor: '#E7F5EA', borderRadius: 8, padding: 12, paddingHorizontal: 20, marginTop: 16, alignItems: 'center' },
  deliveryTitle: { color: Colors.successGreen, fontSize: 14, fontWeight: '600' },
  deliveryEta: { color: Colors.successGreen, fontSize: 13, marginTop: 2 },
  splitLabel: { color: Colors.textSecondary, fontSize: 13, marginTop: 32 },
  splitAmount: { color: Colors.textPrimary, fontSize: 28, fontWeight: '700', marginTop: 4 },
  splitSub: { color: Colors.textSecondary, fontSize: 13, marginTop: 4 },
  homeBtn: { marginTop: 48, borderWidth: 1, borderColor: '#D5D9D9', borderRadius: 4, paddingHorizontal: 32, paddingVertical: 12 },
  homeBtnText: { color: Colors.textPrimary, fontSize: 15 },
})
