import vue from '@vitejs/plugin-vue';
import { defineConfig } from 'vite';

const baseUrl = "/runtracker/";

// https://vite.dev/config/
export default defineConfig({
  base: baseUrl,
  plugins: [vue()],
  server: {
    proxy: {
      "^/.*/api/.*": {
        target: "http://localhost:8000/",
        changeOrigin: true,
        rewrite: (path) => path.replace(baseUrl, ""),
      },
    },
  },
  // Silence Sass deprecation warnings
  css: {
    preprocessorOptions: {
      scss: {
        silenceDeprecations: [
          'import',
          'mixed-decls',
          'color-functions',
          'global-builtin',
        ],
      },
    },
  },
})
