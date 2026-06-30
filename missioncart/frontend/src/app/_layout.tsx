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

    // Handle notification action buttons and taps
    const subscription =
      Notifications.addNotificationResponseReceivedListener((response) => {
        const actionId = response.actionIdentifier
        const data = response.notification.request.content.data

        // User tapped "Checkout Now" button or the notification body itself
        // Navigate directly to the checkout/review page
        if (
          actionId === 'checkout_now' ||
          actionId === Notifications.DEFAULT_ACTION_IDENTIFIER
        ) {
          if (data?.screen === 'reorder_checkout') {
            router.push('/reorder/review')
          } else {
            router.push('/reorder/review')
          }
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
          <Stack.Screen name="audit-entry" />
          <Stack.Screen name="audit-build" />
          <Stack.Screen name="audit-result" />
          <Stack.Screen name="search" options={{ animation: 'slide_from_right' }} />
          <Stack.Screen name="hive/index" options={{ headerShown: false }} />
          <Stack.Screen name="hive/confirmation" options={{ headerShown: false }} />
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
          <Stack.Screen name="reorder/draft" options={{ headerShown: false }} />
          <Stack.Screen name="reorder/review" options={{ headerShown: false }} />
          <Stack.Screen
            name="reorder/placing"
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="reorder/confirmation"
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="reorder/tracking"
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
