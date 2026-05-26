import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import Keycloak from 'keycloak-js'

interface KeycloakContextValue {
  keycloak: Keycloak | null
  initialized: boolean
  locationId: string | null
}

const KeycloakContext = createContext<KeycloakContextValue>({
  keycloak: null,
  initialized: false,
  locationId: null,
})

export function useKeycloak() {
  return useContext(KeycloakContext)
}

const keycloakInstance = new Keycloak({
  url: '/',
  realm: 'bordercapcontrol',
  clientId: 'bordercapcontrol-frontend',
})

export function KeycloakProvider({ children }: { children: React.ReactNode }) {
  const [initialized, setInitialized] = useState(false)
  const [locationId, setLocationId] = useState<string | null>(null)
  const didInit = useRef(false)

  useEffect(() => {
    if (didInit.current) return
    didInit.current = true

    keycloakInstance
      .init({ onLoad: 'login-required', pkceMethod: 'S256' })
      .then((authenticated) => {
        if (authenticated) {
          const parsed = keycloakInstance.tokenParsed as Record<string, unknown> | undefined
          const roles = (parsed?.realm_access as { roles?: string[] } | undefined)?.roles ?? []
          // system-admin has no location binding — ignore location_id claim even if present
          const lid = roles.includes('system-admin')
            ? null
            : (parsed?.location_id as string | undefined) ?? null
          setLocationId(lid)
        }
        setInitialized(true)
      })
      .catch((err) => {
        console.error('Keycloak init fehler:', err)
        setInitialized(true)
      })
  }, [])

  useEffect(() => {
    if (!initialized) return
    const interval = setInterval(() => {
      keycloakInstance.updateToken(60).catch(() => {
        keycloakInstance.logout()
      })
    }, 30_000)
    return () => clearInterval(interval)
  }, [initialized])

  return (
    <KeycloakContext.Provider value={{ keycloak: keycloakInstance, initialized, locationId }}>
      {children}
    </KeycloakContext.Provider>
  )
}
