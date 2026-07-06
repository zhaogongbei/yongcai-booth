import { defineConfig } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import packageJson from './package.json' with { type: 'json' }


function figmaAssetResolver() {
  return {
    name: 'figma-asset-resolver',
    resolveId(id) {
      if (id.startsWith('figma:asset/')) {
        const filename = id.replace('figma:asset/', '')
        return path.resolve(__dirname, 'src/assets', filename)
      }
    },
  }
}

export default defineConfig({
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(packageJson.version),
  },
  plugins: [
    figmaAssetResolver(),
    // The React and Tailwind plugins are both required for Make, even if
    // Tailwind is not being actively used – do not remove them
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      // Alias @ to the src directory
      '@': path.resolve(__dirname, './src'),
    },
  },

  // File types to support raw imports. Never add .css, .tsx, or .ts files to this.
  assetsInclude: ['**/*.svg', '**/*.csv'],

  // Exclude user data directories from Vite processing
  build: {
    // Modern-browser target (the booth runs on current Chromium); lets Vite
    // emit smaller/faster output without transpiling modern syntax down.
    target: 'es2022',
    rollupOptions: {
      external: [/src\/imports\/.*/],
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react/jsx-runtime', 'react-dom', 'react-dom/client'],
          charts: ['recharts'],
          motion: ['motion'],
          radix: [
            '@radix-ui/react-slider',
          ],
        },
      },
    },
  },
})
