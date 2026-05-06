import fs from 'node:fs'
import path from 'node:path'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

const certDir = path.resolve(__dirname, 'certs')
const pfxPath = path.join(certDir, 'dev-server.pfx')
const httpsPassphrase = process.env.VITE_DEV_HTTPS_PASSPHRASE || 'detect-report-dev'
const forceHttp = ['1', 'true', 'yes', 'on'].includes(
  (process.env.VITE_DEV_FORCE_HTTP || '').trim().toLowerCase(),
)
const httpsOptions = !forceHttp && fs.existsSync(pfxPath)
  ? {
      pfx: fs.readFileSync(pfxPath),
      passphrase: httpsPassphrase,
    }
  : undefined

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router'],
    }),
    Components({
      resolvers: [ElementPlusResolver()],
    }),
  ],
  server: {
    host: '0.0.0.0',
    port: 5173,
    https: httpsOptions,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
