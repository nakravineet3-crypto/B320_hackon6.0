import { Ionicons } from '@expo/vector-icons'
import { Tabs } from 'expo-router'
import { StyleSheet } from 'react-native'

import { Colors } from '../../lib/constants'

type IconName = React.ComponentProps<typeof Ionicons>['name']

const tabIcons: Record<
  'index' | 'discover' | 'profile',
  { active: IconName; inactive: IconName }
> = {
  index: { active: 'home', inactive: 'home-outline' },
  discover: { active: 'compass', inactive: 'compass-outline' },
  profile: { active: 'person', inactive: 'person-outline' },
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={({ route }) => {
        const routeName = route.name as keyof typeof tabIcons
        const icons = tabIcons[routeName]

        return {
          headerShown: false,
          tabBarActiveTintColor: Colors.primary,
          tabBarInactiveTintColor: Colors.textSecondary,
          tabBarStyle: styles.tabBar,
          tabBarLabelStyle: styles.tabLabel,
          tabBarIcon: ({ color, focused, size }) => (
            <Ionicons
              name={focused ? icons.active : icons.inactive}
              size={size}
              color={color}
            />
          ),
        }
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Home' }} />
      <Tabs.Screen name="missions" options={{ href: null }} />
      <Tabs.Screen name="discover" options={{ title: 'Discover' }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile' }} />
    </Tabs>
  )
}

const styles = StyleSheet.create({
  tabBar: {
    height: 60,
    paddingTop: 5,
    paddingBottom: 5,
    backgroundColor: Colors.background,
    borderTopColor: Colors.border,
    borderTopWidth: 1,
  },
  tabLabel: {
    fontSize: 10,
    fontWeight: '600',
  },
})
