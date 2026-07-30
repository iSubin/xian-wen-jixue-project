import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const devApiTarget = env.VITE_DEV_API_TARGET || 'http://127.0.0.1:8000'
  const packageJsonPath = resolve(process.cwd(), 'package.json')
  const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8')) as { version?: string }
  const appVersion = packageJson.version || '0.0.0'

  return {
    plugins: [vue()],
    define: {
      __APP_VERSION__: JSON.stringify(appVersion),
    },
    server: {
      proxy: {
        '/tasks': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/upload': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/local-path': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/local-folder': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/articles': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/collections': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/folders': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/library': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/git': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/providers': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/connected-accounts': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/bilibili': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/task-assets': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/prewarm': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/version': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/llm': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/transcription': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/summarization': {
          target: devApiTarget,
          changeOrigin: true,
        },
        '/ws': {
          target: devApiTarget,
          ws: true,
          changeOrigin: true,
        },
      },
    },
  }
})
