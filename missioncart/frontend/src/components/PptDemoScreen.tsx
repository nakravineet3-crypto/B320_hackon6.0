import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { Colors } from '../lib/constants'

type IoniconName = keyof typeof Ionicons.glyphMap

interface PptDemoScreenProps {
  eyebrow: string
  title: string
  description: string
  icon: IoniconName
  actionLabel: string
}

export default function PptDemoScreen({
  eyebrow,
  title,
  description,
  icon,
  actionLabel,
}: PptDemoScreenProps) {
  const router = useRouter()

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          style={styles.backButton}
          accessibilityRole="button"
          accessibilityLabel="Go back"
        >
          <Ionicons name="arrow-back" size={20} color={Colors.textPrimary} />
        </Pressable>
        <Text style={styles.headerLabel}>MissionCart preview</Text>
      </View>

      <View style={styles.content}>
        <View style={styles.iconTile}>
          <Ionicons name={icon} size={34} color={Colors.primary} />
        </View>
        <Text style={styles.eyebrow}>{eyebrow}</Text>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.description}>{description}</Text>

        <View style={styles.evidenceCard}>
          <Text style={styles.evidenceLabel}>DEMO MODE</Text>
          <Text style={styles.evidenceText}>
            This presentation screen is connected to app navigation and ready
            for the walkthrough.
          </Text>
        </View>
      </View>

      <View style={styles.footer}>
        <Pressable style={styles.actionButton} accessibilityRole="button">
          <Text style={styles.actionText}>{actionLabel}</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    height: 56,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  backButton: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerLabel: {
    marginLeft: 8,
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '600',
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 64,
  },
  iconTile: {
    width: 64,
    height: 64,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFF4E5',
    borderRadius: 4,
  },
  eyebrow: {
    marginTop: 24,
    color: Colors.textSecondary,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.2,
  },
  title: {
    marginTop: 8,
    color: Colors.textPrimary,
    fontSize: 28,
    lineHeight: 34,
    fontWeight: '700',
  },
  description: {
    marginTop: 12,
    color: Colors.textSecondary,
    fontSize: 15,
    lineHeight: 22,
  },
  evidenceCard: {
    marginTop: 32,
    padding: 16,
    backgroundColor: Colors.cardBg,
    borderLeftWidth: 4,
    borderLeftColor: Colors.primary,
    borderRadius: 4,
  },
  evidenceLabel: {
    color: Colors.textSecondary,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  evidenceText: {
    marginTop: 6,
    color: Colors.textPrimary,
    fontSize: 13,
    lineHeight: 19,
  },
  footer: {
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: Colors.divider,
  },
  actionButton: {
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.primary,
    borderRadius: 4,
  },
  actionText: {
    color: Colors.white,
    fontSize: 15,
    fontWeight: '700',
  },
})
