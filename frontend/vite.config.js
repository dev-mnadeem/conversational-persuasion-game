import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * Dev ports are pinned so the backend's CORS allow-list and the README's
 * instructions agree with what actually starts.
 *
 * `/api` and `/healthz` are proxied to the Python server, so in development
 * the browser makes same-origin requests and CORS never applies. For a built
 * bundle pointed at a deployed backend, set VITE_API_BASE instead.
 */
const BACKEND = process.env.VITE_BACKEND_ORIGIN ?? 'http://127.0.0.1:7321';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 7322,
    strictPort: true,
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
      '/healthz': { target: BACKEND, changeOrigin: true },
    },
  },
  preview: { port: 7323, strictPort: true },
});
