import axios from 'axios'
import * as Notifications from 'expo-notifications'
import { Platform } from 'react-native'

import { API_BASE } from './constants'

// Notification category ID for reorder notifications
const REORDER_CATEGORY = 'morning_reorder'

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
})

export async function registerForPushNotifications(): Promise<boolean> {
  const { status: existingStatus } = await Notifications.getPermissionsAsync()
  let finalStatus = existingStatus

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync()
    finalStatus = status
  }

  if (finalStatus !== 'granted') {
    return false
  }

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('morning-reorder', {
      name: 'Morning Reorder',
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#FF9900',
      sound: 'default',
    })
  }

  // Register notification category with action button
  await Notifications.setNotificationCategoryAsync(REORDER_CATEGORY, [
    {
      identifier: 'checkout_now',
      buttonTitle: '🛒 Checkout Now',
      options: {
        opensAppToForeground: true,
      },
    },
  ])

  return true
}

export async function scheduleMorningNotification(): Promise<void> {
  await Notifications.cancelAllScheduledNotificationsAsync()

  let title = '🛒 Your reorder cart is ready for checkout'
  let body =
    'Amul Milk, Surf Excel, Parle-G — Tap to review & place your order ⚡'

  try {
    const res = await axios.get(
      `${API_BASE}/api/demo/notification-content`,
      { timeout: 3000 },
    )
    const data = res.data?.data
    if (data?.title) title = data.title
    if (data?.body) body = data.body
  } catch {
    // Use the defaults above when the API is unavailable.
  }

  await Notifications.scheduleNotificationAsync({
    content: {
      title,
      body,
      data: { screen: 'reorder_checkout', action: 'open_checkout' },
      sound: 'default',
      badge: 1,
      color: '#FF9900',
      categoryIdentifier: REORDER_CATEGORY,
    },
    trigger: {
      hour: 7,
      minute: 0,
      repeats: true,
      channelId: 'morning-reorder',
    },
  })
}

export async function scheduleTestNotification(): Promise<void> {
  let title = '🛒 Your reorder cart is ready for checkout'
  let body =
    'Amul Milk, Surf Excel, Parle-G — Tap to review & place your order ⚡'

  try {
    const res = await axios.get(
      `${API_BASE}/api/demo/notification-content`,
      { timeout: 3000 },
    )
    const data = res.data?.data
    if (data?.title) title = data.title
    if (data?.body) body = data.body
  } catch {
    // Use the defaults above when the API is unavailable.
  }

  await Notifications.scheduleNotificationAsync({
    content: {
      title,
      body,
      data: { screen: 'reorder_checkout', action: 'open_checkout' },
      sound: 'default',
      color: '#FF9900',
      categoryIdentifier: REORDER_CATEGORY,
    },
    trigger: { seconds: 5 },
  })
}

/**
 * @deprecated No longer approving orders directly from notification.
 * Users are now routed to the checkout page instead.
 */
export async function handleApproveFromNotification(): Promise<void> {
  // No-op — kept for backward compatibility
}
