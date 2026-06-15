import { Ionicons } from '@expo/vector-icons'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { Colors } from '../../lib/constants'
import { ALL_PERSONAS, usePersonaStore } from '../../store/persona'

export default function ProfileScreen() {
  const { selectedPersonas, togglePersona } = usePersonaStore()

  const selectedCount = selectedPersonas.length

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.avatarCircle}>
            <Ionicons name="person" size={32} color={Colors.white} />
          </View>
          <Text style={styles.userName}>Shopper</Text>
          <Text style={styles.userSub}>Manage your personas below</Text>
        </View>

        {/* Persona selection */}
        <View style={styles.personaSection}>
          <View style={styles.personaSectionHeader}>
            <Text style={styles.personaSectionTitle}>Your Personas</Text>
            <Text style={styles.personaCount}>
              {selectedCount} selected
            </Text>
          </View>
          <Text style={styles.personaSectionSubtitle}>
            Choose the personas that describe you. Products loved by people in
            these groups will show up on your home feed.
          </Text>

          {/* Grid */}
          <View style={styles.personaGrid}>
            {ALL_PERSONAS.map((persona) => {
              const isActive = selectedPersonas.includes(persona.id)
              return (
                <Pressable
                  key={persona.id}
                  onPress={() => togglePersona(persona.id)}
                  style={[
                    styles.personaGridItem,
                    isActive && styles.personaGridItemActive,
                  ]}
                  accessibilityRole="button"
                  accessibilityLabel={`${persona.label} persona`}
                  accessibilityState={{ selected: isActive }}
                >
                  <View
                    style={[
                      styles.personaGridCircle,
                      { backgroundColor: persona.color },
                      isActive && styles.personaGridCircleActive,
                    ]}
                  >
                    <Text style={styles.personaGridEmoji}>{persona.emoji}</Text>
                  </View>
                  <Text
                    style={[
                      styles.personaGridLabel,
                      isActive && styles.personaGridLabelActive,
                    ]}
                    numberOfLines={1}
                  >
                    {persona.label}
                  </Text>
                  {isActive && (
                    <View style={styles.checkBadge}>
                      <Ionicons name="checkmark" size={10} color={Colors.white} />
                    </View>
                  )}
                </Pressable>
              )
            })}
          </View>
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
    paddingBottom: 40,
  },
  header: {
    alignItems: 'center',
    paddingTop: 24,
    paddingBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  avatarCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  userName: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.textPrimary,
  },
  userSub: {
    fontSize: 13,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  personaSection: {
    paddingHorizontal: 16,
    paddingTop: 20,
  },
  personaSectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  personaSectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.textPrimary,
  },
  personaCount: {
    fontSize: 12,
    color: '#FF9900',
    fontWeight: '600',
  },
  personaSectionSubtitle: {
    fontSize: 12,
    color: Colors.textSecondary,
    marginTop: 4,
    marginBottom: 16,
    lineHeight: 17,
  },
  personaGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  personaGridItem: {
    width: '21%',
    alignItems: 'center',
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: 'transparent',
    position: 'relative',
  },
  personaGridItemActive: {
    borderColor: '#FF9900',
    backgroundColor: '#FFF8F0',
  },
  personaGridCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  personaGridCircleActive: {
    borderColor: '#FF9900',
  },
  personaGridEmoji: {
    fontSize: 22,
  },
  personaGridLabel: {
    marginTop: 6,
    fontSize: 10,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
  personaGridLabelActive: {
    color: '#FF9900',
    fontWeight: '700',
  },
  checkBadge: {
    position: 'absolute',
    top: 6,
    right: 6,
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: '#FF9900',
    alignItems: 'center',
    justifyContent: 'center',
  },
})
