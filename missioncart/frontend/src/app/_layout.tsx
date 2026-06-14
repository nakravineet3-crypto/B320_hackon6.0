import '../../global.css'

import * as Notifications from 'expo-notifications'
import { router, Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useEffect } from 'react'
import { StyleSheet } from 'react-native'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import { SafeAreaProvider } from 'react-native-safe-area-context'

import { Colors } from '../lib/constants'
import {
  registerForPushNotifications,
  scheduleMorningNotification,
} from '../lib/notifications'

export default function RootLayout() {
  useEffect(() => {
    // Register and schedule on first launch
    registerForPushNotifications().then((granted) => {
      if (granted) {
        scheduleMorningNotification()
      }
    })

    // Handle notification tap — navigate to home
    const subscription =
      Notifications.addNotificationResponseReceivedListener((response) => {
        const data = response.notification.request.content.data
        if (data?.screen === 'home') {
          router.push('/')
        }
      })

    return () => subscription.remove()
  }, [])

  return (
    <GestureHandlerRootView style={styles.root}>
      <SafeAreaProvider>
        <StatusBar style="dark" backgroundColor={Colors.background} />
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="audit" />
          <Stack.Screen name="cart" />
          <Stack.Screen name="community" />
          <Stack.Screen
            name="ppt/voice-input"
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="ppt/photo-input"
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="ppt/mission-share"
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="ppt/seller-dashboard"
            options={{ headerShown: false }}
          />
        </Stack>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
})
