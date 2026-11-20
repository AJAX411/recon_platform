import { defineConfig } from 'vitest/config'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  envDir: false,
  cacheDir: 'dist/.vitest',
  test: {
    // El patrón propio evita que el runner React padre descubra estas suites.
    environment: 'jsdom', include: ['tests/**/*.check.js'],
    setupFiles: ['./tests/setup.js'], maxWorkers: 1,
    env: {}, coverage: { enabled: false },
  },
})
