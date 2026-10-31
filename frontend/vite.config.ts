/// <reference types="vitest/config" />
import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, './src') } },
  server: { proxy: { '/api': 'http://localhost:5000' } },
  test: {
    projects: [
      {
        test: {
          name: 'contract',
          include: ['tests/contract/**/*.test.ts'],
          globalSetup: ['tests/contract/globalSetup.ts'],
        },
      },
    ],
  },
})
