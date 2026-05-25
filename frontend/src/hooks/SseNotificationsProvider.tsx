import { ReactNode } from 'react'
import { SseNotificationsContext, useSseInternalState } from './useSseNotifications'

export function SseNotificationsProvider({ children }: { children: ReactNode }) {
  const value = useSseInternalState()
  return (
    <SseNotificationsContext.Provider value={value}>
      {children}
    </SseNotificationsContext.Provider>
  )
}
