import { defineConfig } from 'vite';

export default defineConfig({
  root: 'src',
  resolve: {
    // Empêche l'import de multiples instances de Three
    dedupe: ['three']
  },
  optimizeDeps: {
    include: ['three']
  },
  server: {
    port: 5173,
    strictPort: true
  },
  build: {
    outDir: '../dist',
    emptyOutDir: true
  }
});