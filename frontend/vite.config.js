import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  envDir: false,
  appType: 'spa',
  cacheDir: 'dist/.vite',
  server: {
    host: '127.0.0.1', port: 5173, strictPort: true,
    proxy: { '/api/v1': { target: 'http://127.0.0.1:5000', changeOrigin: true } },
  },
  preview: { host: '127.0.0.1', port: 5173, strictPort: true,
    proxy: { '/api/v1': { target: 'http://127.0.0.1:5000', changeOrigin: true } } },
  build: { outDir: 'dist', emptyOutDir: true },
  plugins: [{
    name: 'inventario-runtime-nativo',
    generateBundle() {
      const modules = [...this.getModuleIds()].filter((id) => !id.startsWith('\0'))
      if (modules.some((id) => /node_modules[\\/](react|react-dom|react-router|react-router-dom)[\\/]/.test(id))) {
        this.error('Runtime de interfaz ajeno al candidato nativo.')
      }
      this.emitFile({ type: 'asset', fileName: 'modulos-build.json', source: JSON.stringify(modules, null, 2) })
    },
  }],
})
