import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";
import svgLoader from 'vite-svg-loader';

// https://vite.dev/config/
export default defineConfig({
    plugins: [vue(), svgLoader()],
    server: {
        proxy: {
            // For development, Vite controls the flow. The frontend is served at the root.
            // API requests are made to "/api". Vite catches those requests here and redirects
            // them to the backend server.
            //
            // For production, FastAPI controls the flow through FastAPI.frontend() (see 
            // ../api/rungoal/main.py).
            "^/api/.*": {
                target: "http://localhost:8000/",
                changeOrigin: true
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
