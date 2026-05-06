import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy REST API calls to FastAPI
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
      // Proxy WebSocket connections — essential for dev mode
      '/ws': {
        target: process.env.VITE_WS_URL || 'ws://localhost:8000',
        changeOrigin: true,
        ws: true,          // enables WebSocket proxying
      },
    },
  },
  build: {
    // Code-split vendor chunks for better caching
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom'],
        },
      },
    },
  },
})
