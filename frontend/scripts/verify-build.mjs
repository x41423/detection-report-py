import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { build } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const rootDir = path.resolve(__dirname, '..')
const certDir = path.resolve(rootDir, 'certs')
const pfxPath = path.join(certDir, 'dev-server.pfx')
const httpsPassphrase = process.env.VITE_DEV_HTTPS_PASSPHRASE || 'detect-report-dev'
const httpsOptions = fs.existsSync(pfxPath)
  ? {
      pfx: fs.readFileSync(pfxPath),
      passphrase: httpsPassphrase,
    }
  : undefined

await build({
  configFile: false,
  root: rootDir,
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
