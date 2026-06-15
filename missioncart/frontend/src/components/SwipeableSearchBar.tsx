import { Ionicons } from '@expo/vector-icons'
import { useCallback, useEffect, useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { Gesture, GestureDetector } from 'react-native-gesture-handler'
import Animated, {
  Easing,
  interpolate,
  interpolateColor,
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withSpring,
  withTiming,
} from 'react-native-reanimated'

import { Colors } from '../lib/constants'

const SWIPE_THRESHOLD = 50
const SPRING_CONFIG = { damping: 18, stiffness: 180 }
const ACCENT_BLUE = '#2196F3'

type Mode = 'search' | 'mission'

interface SwipeableSearchBarProps {
  search: string
  onSearchChange: (text: string) => void
  goal: string
  onGoalChange: (text: string) => void
  onBuildCart: () => void
  onSearchFocus?: () => void
}

export function SwipeableSearchBar({
  search,
  onSearchChange,
  goal,
  onGoalChange,
  onBuildCart,
  onSearchFocus,
}: SwipeableSearchBarProps) {
  const [mode, setMode] = useState<Mode>('search')
  const progress = useSharedValue(0)

  // Animated arrows hint
  const arrow1 = useSharedValue(0)
  const arrow2 = useSharedValue(0)
  const arrow3 = useSharedValue(0)

  useEffect(() => {
    const duration = 600
    const stagger = 150

    arrow1.value = withDelay(
      800,
      withRepeat(
        withSequence(
          withTiming(1, { duration, easing: Easing.out(Easing.ease) }),
          withTiming(0, { duration: 300, easing: Easing.in(Easing.ease) }),
          withDelay(2200, withTiming(0, { duration: 0 }))
        ),
        -1,
        false
      )
    )

    arrow2.value = withDelay(
      800 + stagger,
      withRepeat(
        withSequence(
          withTiming(1, { duration, easing: Easing.out(Easing.ease) }),
          withTiming(0, { duration: 300, easing: Easing.in(Easing.ease) }),
          withDelay(2200 - stagger, withTiming(0, { duration: 0 }))
        ),
        -1,
        false
      )
    )

    arrow3.value = withDelay(
      800 + stagger * 2,
      withRepeat(
        withSequence(
          withTiming(1, { duration, easing: Easing.out(Easing.ease) }),
          withTiming(0, { duration: 300, easing: Easing.in(Easing.ease) }),
          withDelay(2200 - stagger * 2, withTiming(0, { duration: 0 }))
        ),
        -1,
        false
      )
    )
  }, [])

  const switchToMission = useCallback(() => {
    setMode('mission')
  }, [])

  const switchToSearch = useCallback(() => {
    setMode('search')
  }, [])

  const panGesture = Gesture.Pan()
    .activeOffsetX([-20, 20])
    .onEnd((event) => {
      if (mode === 'search' && event.translationX > SWIPE_THRESHOLD) {
        progress.value = withSpring(1, SPRING_CONFIG)
        runOnJS(switchToMission)()
      } else if (mode === 'mission' && event.translationX < -SWIPE_THRESHOLD) {
        progress.value = withSpring(0, SPRING_CONFIG)
        runOnJS(switchToSearch)()
      }
    })

  const barBorderStyle = useAnimatedStyle(() => ({
    borderColor: interpolateColor(
      progress.value,
      [0, 1],
      [Colors.inputBorder, '#FF9900']
    ),
    backgroundColor: interpolateColor(
      progress.value,
      [0, 1],
      [Colors.background, '#FFF8F0']
    ),
  }))

  const searchAnimatedStyle = useAnimatedStyle(() => ({
    opacity: interpolate(progress.value, [0, 0.4], [1, 0]),
    transform: [
      { translateX: interpolate(progress.value, [0, 1], [0, -80]) },
    ],
  }))

  const missionAnimatedStyle = useAnimatedStyle(() => ({
    opacity: interpolate(progress.value, [0.4, 1], [0, 1]),
    transform: [
      { translateX: interpolate(progress.value, [0, 1], [80, 0]) },
    ],
  }))

  const arrow1Style = useAnimatedStyle(() => ({
    opacity: interpolate(arrow1.value, [0, 0.5, 1], [0.2, 1, 0.2]),
    transform: [
      { translateX: interpolate(arrow1.value, [0, 1], [0, 6]) },
    ],
  }))

  const arrow2Style = useAnimatedStyle(() => ({
    opacity: interpolate(arrow2.value, [0, 0.5, 1], [0.2, 1, 0.2]),
    transform: [
      { translateX: interpolate(arrow2.value, [0, 1], [0, 6]) },
    ],
  }))

  const arrow3Style = useAnimatedStyle(() => ({
    opacity: interpolate(arrow3.value, [0, 0.5, 1], [0.2, 1, 0.2]),
    transform: [
      { translateX: interpolate(arrow3.value, [0, 1], [0, 6]) },
    ],
  }))

  const handleModeToggle = () => {
    if (mode === 'search') {
      progress.value = withSpring(1, SPRING_CONFIG)
      switchToMission()
    } else {
      progress.value = withSpring(0, SPRING_CONFIG)
      switchToSearch()
    }
  }

  return (
    <View style={styles.container}>
      <GestureDetector gesture={panGesture}>
        <Animated.View style={[styles.barWrapper, barBorderStyle]}>
          {/* Search mode */}
          <Animated.View
            style={[styles.barContent, searchAnimatedStyle]}
            pointerEvents={mode === 'search' ? 'auto' : 'none'}
          >
            {/* Static search icon + animated directional arrows */}
            <View style={styles.searchIconWrap}>
              <Ionicons name="search" size={18} color={ACCENT_BLUE} />
            </View>
            <View style={styles.arrowsWrap}>
              <Animated.Text style={[styles.arrowChar, arrow1Style]}>›</Animated.Text>
              <Animated.Text style={[styles.arrowChar, arrow2Style]}>›</Animated.Text>
              <Animated.Text style={[styles.arrowChar, arrow3Style]}>›</Animated.Text>
            </View>

            <Pressable onPress={onSearchFocus} style={styles.inputPressable}>
              <Text style={styles.inputPlaceholder}>
                Search groceries, snacks...
              </Text>
            </Pressable>
            <Pressable
              onPress={handleModeToggle}
              hitSlop={10}
              style={styles.toggleButton}
              accessibilityLabel="Switch to goal-based cart builder"
              accessibilityRole="button"
            >
              <Ionicons name="rocket" size={18} color="#FF9900" />
            </Pressable>
          </Animated.View>

          {/* Mission mode */}
          <Animated.View
            style={[styles.barContent, styles.barContentAbsolute, missionAnimatedStyle]}
            pointerEvents={mode === 'mission' ? 'auto' : 'none'}
          >
            <Ionicons name="rocket" size={18} color="#FF9900" />
            <TextInput
              value={goal}
              onChangeText={onGoalChange}
              placeholder="e.g. Birthday party for 20 people under ₹3000"
              placeholderTextColor={Colors.placeholder}
              style={styles.missionInput}
              returnKeyType="done"
              onSubmitEditing={onBuildCart}
              accessibilityLabel="Mission goal"
            />
            <Pressable
              onPress={onBuildCart}
              style={styles.buildButton}
              accessibilityLabel="Build cart from goal"
              accessibilityRole="button"
            >
              <Text style={styles.buildButtonText}>Build</Text>
            </Pressable>
            <Pressable
              onPress={handleModeToggle}
              hitSlop={10}
              style={styles.backButton}
              accessibilityLabel="Switch back to search"
              accessibilityRole="button"
            >
              <Ionicons name="close" size={18} color={Colors.textSecondary} />
            </Pressable>
          </Animated.View>
        </Animated.View>
      </GestureDetector>

      {/* Hint text */}
      <View style={styles.hintRow}>
        {mode === 'search' ? (
          <Text style={styles.hintText}>
            Swipe right  →  to build cart by goal
          </Text>
        ) : (
          <Text style={styles.hintTextMission}>
            ← Swipe left to go back to search
          </Text>
        )}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 16,
  },
  barWrapper: {
    height: 46,
    borderWidth: 1.5,
    borderRadius: 10,
    overflow: 'hidden',
    position: 'relative',
  },
  barContent: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    height: 44,
  },
  barContentAbsolute: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  // Search icon + arrows
  searchIconWrap: {
    width: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  arrowsWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 1,
    width: 32,
  },
  arrowChar: {
    fontSize: 22,
    fontWeight: '900',
    color: ACCENT_BLUE,
    marginHorizontal: -1,
  },
  input: {
    flex: 1,
    height: 42,
    marginLeft: 6,
    marginRight: 8,
    paddingVertical: 0,
    color: Colors.textPrimary,
    fontSize: 14,
  },
  inputPressable: {
    flex: 1,
    height: 42,
    marginLeft: 6,
    marginRight: 8,
    justifyContent: 'center',
  },
  inputPlaceholder: {
    color: Colors.placeholder,
    fontSize: 14,
  },
  missionInput: {
    flex: 1,
    height: 42,
    marginHorizontal: 8,
    paddingVertical: 0,
    color: Colors.textPrimary,
    fontSize: 14,
  },
  buildButton: {
    backgroundColor: '#FF9900',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
  },
  buildButtonText: {
    color: Colors.white,
    fontSize: 13,
    fontWeight: '700',
  },
  toggleButton: {
    padding: 6,
  },
  backButton: {
    marginLeft: 8,
    padding: 6,
  },
  hintRow: {
    marginTop: 6,
    alignItems: 'center',
  },
  hintText: {
    fontSize: 11,
    color: Colors.textSecondary,
    letterSpacing: 0.2,
  },
  hintTextMission: {
    fontSize: 11,
    color: '#FF9900',
    letterSpacing: 0.2,
  },
})
