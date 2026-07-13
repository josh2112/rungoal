import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";
import svgLoader from 'vite-svg-loader';

const baseUrl = "/rungoal/";

// https://vite.dev/config/
export default defineConfig({
    base: baseUrl,
    plugins: [vue(), svgLoader()],
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
                    "if-function",
                    "import",
                    "color-functions",
                    "global-builtin",
                ],
            },
        },
    },
});
