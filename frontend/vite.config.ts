import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

/**
 * In development the app is served by Vite and the API by uvicorn, so /api is proxied
 * across - including the WebSocket, which needs ws:true or the stream never upgrades.
 * In production there is no proxy: FastAPI serves the built app out of frontend/dist,
 * and the same relative paths resolve on their own. So the client never needs a base
 * URL, in either mode.
 */
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})