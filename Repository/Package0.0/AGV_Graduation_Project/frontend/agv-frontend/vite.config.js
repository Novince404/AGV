import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (/[\\/]node_modules[\\/]vue[\\/]/.test(id)) {
            return 'vendor-vue'
          }
          if (/[\\/]src[\\/]locales[\\/]/.test(id)) {
            return 'i18n-bundle'
          }
          if (/[\\/]src[\\/]utils[\\/]comfyWorkflowTemplates\.js$/.test(id)) {
            return 'comfy-templates'
          }
          return undefined
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
