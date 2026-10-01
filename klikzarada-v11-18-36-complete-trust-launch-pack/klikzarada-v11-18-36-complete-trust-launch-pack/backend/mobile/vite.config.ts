import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  base: '/mobile-ui/',
  plugins: [react(), tailwindcss()],
  build: { sourcemap: false },
});
