/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'


// https://vitejs.dev/config/
export default defineConfig({
  envDir: '..',
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true,
    },
    proxy: {
      '/auth-api': {
        target: process.env.VITE_PROXY_TARGET || 'http://backend:8000',
        changeOrigin: true,
      },
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://backend:8000',
        changeOrigin: true,
      },
      '/social-api': {
        target: process.env.VITE_PROXY_TARGET || 'http://backend:8000',
        changeOrigin: true,
      },
      '/media': {
        target: process.env.VITE_PROXY_TARGET || 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    include: ['react-router-dom']
  }
})
