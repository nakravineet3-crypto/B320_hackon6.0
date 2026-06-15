import { Pressable, StyleSheet, Text, View } from 'react-native'
import Animated, { SlideInDown, SlideOutDown } from 'react-native-reanimated'

import { Colors } from '../lib/constants'
import { useMissionStore } from '../store/mission'

export default function UndoToast() {
  const undoToast = useMissionStore((state) => state.undoToast)
  const hideUndoToast = useMissionStore((state) => state.hideUndoToast)

  if (!undoToast) {
    return null
  }

  const undo = () => {
    undoToast.onUndo?.()
    hideUndoToast()
  }

  return (
    <Animated.View
      entering={SlideInDown.duration(300)}
      exiting={SlideOutDown.duration(200)}
      style={styles.toast}
    >
      <View style={styles.messageWrap}>
        <Text style={styles.message}>{undoToast.message.replace(' · Undo', '')}</Text>
      </View>
      <Pressable onPress={undo} hitSlop={8}>
        <Text style={styles.undoText}>Undo</Text>
      </Pressable>
    </Animated.View>
  )
}

const styles = StyleSheet.create({
  toast: {
    position: 'absolute',
    right: 16,
    bottom: 80,
    left: 16,
    zIndex: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.textPrimary,
    borderRadius: 8,
    elevation: 10,
  },
  messageWrap: {
    flex: 1,
  },
  message: {
    color: Colors.white,
    fontSize: 14,
  },
  undoText: {
    color: Colors.primary,
    fontSize: 14,
    fontWeight: '700',
  },
})
