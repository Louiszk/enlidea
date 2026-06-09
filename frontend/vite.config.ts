import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
  server: {
    proxy: {
      '/media': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    include: ['react-router-dom']
  }
})
