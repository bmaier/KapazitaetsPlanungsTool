import { useCallback, useEffect, useMemo, useRef } from 'react'
import { useKeycloak } from '../auth/KeycloakProvider'

function buildHeaders(token: string | undefined, locationId: string | null): HeadersInit {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (locationId) headers['X-Location-Id'] = locationId
  return headers
}

// Stabile API-Funktionen über Refs — vermeidet unendliche useEffect-Loops
export function useApiClient() {
  const { keycloak, locationId } = useKeycloak()
  const kcRef = useRef(keycloak)
  const locRef = useRef(locationId)

  useEffect(() => { kcRef.current = keycloak }, [keycloak])
  useEffect(() => { locRef.current = locationId }, [locationId])

  const get = useCallback(async <T>(path: string): Promise<T> => {
    const kc = kcRef.current
    await kc?.updateToken(60).catch((e: unknown) => { kc?.logout(); throw e })
    const r = await fetch(path, { headers: buildHeaders(kc?.token, locRef.current) })
    if (!r.ok) throw new Error(`GET ${path}: ${r.status}`)
    return r.json() as Promise<T>
  }, [])

  const post = useCallback(async <T>(path: string, body: unknown): Promise<T> => {
    const kc = kcRef.current
    await kc?.updateToken(60).catch((e: unknown) => { kc?.logout(); throw e })
    const r = await fetch(path, {
      method: 'POST',
      headers: buildHeaders(kc?.token, locRef.current),
      body: JSON.stringify(body),
    })
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }))
      throw Object.assign(new Error(`POST ${path}: ${r.status}`), { status: r.status, detail: err })
    }
    return r.json() as Promise<T>
  }, [])

  const patch = useCallback(async <T>(path: string, body: unknown): Promise<T> => {
    const kc = kcRef.current
    await kc?.updateToken(60).catch((e: unknown) => { kc?.logout(); throw e })
    const r = await fetch(path, {
      method: 'PATCH',
      headers: buildHeaders(kc?.token, locRef.current),
      body: JSON.stringify(body),
    })
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }))
      throw Object.assign(new Error(`PATCH ${path}: ${r.status}`), { status: r.status, detail: err })
    }
    return r.json() as Promise<T>
  }, [])

  const del = useCallback(async (path: string): Promise<void> => {
    const kc = kcRef.current
    await kc?.updateToken(60).catch((e: unknown) => { kc?.logout(); throw e })
    const r = await fetch(path, {
      method: 'DELETE',
      headers: buildHeaders(kc?.token, locRef.current),
    })
    if (!r.ok) throw new Error(`DELETE ${path}: ${r.status}`)
  }, [])

  return useMemo(() => ({ get, post, patch, del }), [get, post, patch, del])
}
