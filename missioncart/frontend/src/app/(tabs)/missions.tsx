import { useRouter } from 'expo-router'
import { useState } from 'react'
import {
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { Colors } from '../../lib/constants'

interface QuickChip {
  label: string
  goal: string
}

const quickChips: QuickChip[] = [
  {
    label: 'Birthday party',
    goal: 'Birthday party for 12 kids tomorrow under ₹4000',
  },
  {
    label: 'New flat setup',
    goal: 'New flat setup this weekend under ₹15000',
  },
  {
    label: 'Road trip',
    goal: 'Road trip for 4 people this weekend under ₹5000',
  },
]

export default function MissionsScreen() {
  const router = useRouter()
  const [goalText, setGoalText] = useState('')
  const [budgetText, setBudgetText] = useState('3000')
  const [goalFocused, setGoalFocused] = useState(false)
  const [showError, setShowError] = useState(false)

  const handleChipPress = (chip: QuickChip) => {
    setGoalText(chip.goal)
    setShowError(false)
  }

  const handlePlanMission = () => {
    if (!goalText.trim()) {
      setShowError(true)
      return
    }
    setShowError(false)
    router.push({
      pathname: '/cart/building',
      params: { goal: goalText.trim(), budget: budgetText || '3000' },
    })
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.title}>Missions</Text>

        {/* Quick start */}
        <Text style={styles.quickStartLabel}>Quick start</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipRow}
        >
          {quickChips.map((chip) => (
            <TouchableOpacity
              key={chip.label}
              onPress={() => handleChipPress(chip)}
              style={styles.chip}
              activeOpacity={0.7}
            >
              <Text style={styles.chipText}>{chip.label}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Main input */}
        <View style={styles.inputSection}>
          <Text style={styles.inputLabel}>Describe your goal</Text>
          <TextInput
            value={goalText}
            onChangeText={(text) => {
              setGoalText(text)
              if (showError) setShowError(false)
            }}
            onFocus={() => setGoalFocused(true)}
            onBlur={() => setGoalFocused(false)}
            placeholder="e.g. Birthday party for 20 people under ₹3000"
            placeholderTextColor={Colors.placeholder}
            style={[styles.goalInput, goalFocused && styles.goalInputFocused]}
            multiline
            textAlignVertical="top"
            accessibilityLabel="Mission goal"
          />
        </View>

        {showError && (
          <Text style={styles.errorText}>Please enter your goal first</Text>
        )}

        {/* Budget row */}
        <View style={styles.budgetRow}>
          <Text style={styles.budgetLabel}>Budget</Text>
          <View style={styles.budgetInputWrap}>
            <Text style={styles.budgetPrefix}>₹</Text>
            <TextInput
              value={budgetText}
              onChangeText={setBudgetText}
              keyboardType="numeric"
              style={styles.budgetInput}
              accessibilityLabel="Budget amount"
            />
          </View>
        </View>

        {/* CTA */}
        <TouchableOpacity
          onPress={handlePlanMission}
          style={styles.planButton}
          activeOpacity={0.8}
        >
          <Text style={styles.planButtonText}>Plan my cart</Text>
        </TouchableOpacity>
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
  title: {
    color: Colors.textPrimary,
    fontSize: 22,
    fontWeight: '700',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
  },
  quickStartLabel: {
    color: Colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
    paddingHorizontal: 16,
    marginBottom: 8,
  },
  chipRow: {
    paddingHorizontal: 16,
  },
  chip: {
    backgroundColor: Colors.divider,
    borderRadius: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginRight: 8,
  },
  chipText: {
    color: Colors.textPrimary,
    fontSize: 13,
    fontWeight: '400',
  },
  inputSection: {
    paddingHorizontal: 16,
    marginTop: 16,
  },
  inputLabel: {
    color: Colors.textPrimary,
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  goalInput: {
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: 4,
    padding: 14,
    fontSize: 15,
    color: Colors.textPrimary,
    minHeight: 88,
  },
  goalInputFocused: {
    borderColor: Colors.inputBorderFocus,
  },
  errorText: {
    color: Colors.errorRed,
    fontSize: 12,
    marginTop: 4,
    paddingHorizontal: 16,
  },
  budgetRow: {
    marginHorizontal: 16,
    marginTop: 12,
    backgroundColor: Colors.cardBg,
    borderRadius: 4,
    padding: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  budgetLabel: {
    color: Colors.textSecondary,
    fontSize: 13,
  },
  budgetInputWrap: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  budgetPrefix: {
    color: Colors.textPrimary,
    fontSize: 14,
  },
  budgetInput: {
    width: 80,
    fontSize: 14,
    fontWeight: '600',
    color: Colors.textPrimary,
    textAlign: 'right',
    paddingVertical: 0,
  },
  planButton: {
    marginHorizontal: 16,
    marginTop: 20,
    height: 52,
    backgroundColor: Colors.primary,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  planButtonText: {
    color: Colors.white,
    fontSize: 16,
    fontWeight: '700',
  },
})
