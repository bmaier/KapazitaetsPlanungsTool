/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BACKEND_URL: string
  readonly VITE_KEYCLOAK_URL: string
  readonly VITE_TILESERVER_URL: string
  readonly VITE_SUPPORT_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
