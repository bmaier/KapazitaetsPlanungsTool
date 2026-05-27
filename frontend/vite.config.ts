import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendUrl = process.env.VITE_BACKEND_URL ?? 'http://localhost:8000'
const keycloakUrl = process.env.VITE_KEYCLOAK_URL ?? 'http://localhost:8080'
const tileserverUrl = process.env.VITE_TILESERVER_URL ?? 'http://localhost:8082'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
      },
      '/realms': {
        target: keycloakUrl,
        changeOrigin: true,
      },
      '/resources': {
        target: keycloakUrl,
        changeOrigin: true,
      },
      '/tiles': {
        target: tileserverUrl,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/tiles/, ''),
      },
    },
  },
})
