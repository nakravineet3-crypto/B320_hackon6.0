import React from 'react'
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native'
import Animated, { SlideInDown, SlideOutDown } from 'react-native-reanimated'
import { Ionicons } from '@expo/vector-icons'

interface Props {
  visible: boolean
  onHelp: () => void
  onDismiss: () => void
}

export default function HesitationCard({ visible, onHelp, onDismiss }: Props) {
  if (!visible) return null

  return (
    <Animated.View
      entering={SlideInDown.duration(300)}
      exiting={SlideOutDown.duration(200)}
      style={styles.container}
    >
      <View style={styles.row}>
        <Ionicons name="help-circle-outline" size={24} color="#FF9900" />
        <View style={styles.textBlock}>
          <Text style={styles.title}>Having trouble choosing?</Text>
          <Text style={styles.subtitle}>
            We can highlight the best features
          </Text>
        </View>
        <TouchableOpacity onPress={onDismiss}>
          <Text style={styles.close}>×</Text>
        </TouchableOpacity>
      </View>
      <View style={styles.buttons}>
        <TouchableOpacity style={styles.helpBtn} onPress={onHelp}>
          <Text style={styles.helpText}>Help me decide</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.browseBtn} onPress={onDismiss}>
          <Text style={styles.browseText}>Keep browsing</Text>
        </TouchableOpacity>
      </View>
    </Animated.View>
  )
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 80,
    left: 16,
    right: 16,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#D5D9D9',
    padding: 16,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    zIndex: 100,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  textBlock: {
    flex: 1,
    marginLeft: 12,
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0F1111',
  },
  subtitle: {
    fontSize: 12,
    color: '#565959',
    marginTop: 2,
  },
  close: {
    fontSize: 20,
    color: '#565959',
    paddingLeft: 8,
  },
  buttons: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 12,
  },
  helpBtn: {
    flex: 1,
    height: 40,
    backgroundColor: '#FF9900',
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  helpText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '700',
  },
  browseBtn: {
    flex: 1,
    height: 40,
    borderWidth: 1,
    borderColor: '#D5D9D9',
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  browseText: {
    color: '#565959',
    fontSize: 13,
  },
})
