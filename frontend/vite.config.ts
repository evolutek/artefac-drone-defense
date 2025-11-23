import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react(),
  ],
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react/jsx-runtime',
      'react-router',
      'react-router-dom',
      'fast-deep-equal',
      '@turf/turf',
      'three',
      '@react-three/fiber',
      '@react-three/drei',
    ],
    esbuildOptions: {
      define: { global: 'globalThis' },
    },
  },
  build: {
    commonjsOptions: {
      include: [
        /node_modules/,
        /fast-deep-equal/,
      ],
      transformMixedEsModules: true,
    },
  },
  server: {
    host: true,
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/ws': {
        target: 'ws://backend:8000',
        ws: true,
      },
    },
  },
})
