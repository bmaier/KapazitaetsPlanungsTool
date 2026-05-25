import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import { useKeycloak } from '../auth/KeycloakProvider'

export interface SseNotificationsContextValue {
  count: number
  resetCount: () => void
}

export const SseNotificationsContext = createContext<SseNotificationsContextValue>({
  count: 0,
  resetCount: () => {},
})

export function useSseInternalState(): SseNotificationsContextValue {
  const { keycloak, locationId, initialized } = useKeycloak()
  const [count, setCount] = useState(0)

  const resetCount = useCallback(() => setCount(0), [])

  useEffect(() => {
    if (!initialized || !keycloak?.token) return

    const ctrl = new AbortController()
    const headers: Record<string, string> = {
      Authorization: `Bearer ${keycloak.token}`,
    }
    if (locationId) {
      headers['X-Location-Id'] = locationId
    }

    fetchEventSource('/api/notifications/stream', {
      headers,
      signal: ctrl.signal,
      onmessage() {
        setCount((n) => n + 1)
      },
      onerror(err) {
        keycloak.updateToken(60).catch(() => { ctrl.abort() })
        throw err
      },
      openWhenHidden: true,
    })

    return () => { ctrl.abort() }
  }, [initialized, keycloak?.token, locationId]) // eslint-disable-line react-hooks/exhaustive-deps

  return { count, resetCount }
}

export function useSseNotifications(): SseNotificationsContextValue {
  return useContext(SseNotificationsContext)
}
