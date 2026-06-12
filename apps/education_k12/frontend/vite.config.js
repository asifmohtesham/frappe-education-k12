import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'

export default defineConfig({
  plugins: [
    frappeui({
      frappeProxy: false,
      jinjaBootData: false,
      buildConfig: false,
    }),
    vue(),
  ],
  server: {
    port: 8080,
    proxy: {
      '^/(app|api|assets|files|login|logout)': {
        target: 'http://localhost:8002',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../education_k12/public/frontend',
    emptyOutDir: true,
    target: 'es2015',
  },
})
