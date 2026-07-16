import vue from "@vitejs/plugin-vue";
import { readFileSync } from "fs";
import { defineConfig } from "vite";
import svgLoader from "vite-svg-loader";

const packageJson = JSON.parse(readFileSync("package.json", "utf-8"));

// https://vite.dev/config/
export default defineConfig({
    plugins: [vue(), svgLoader()],
    base: "/rungoal/",
    define: {
        "import.meta.env.APP_VERSION": JSON.stringify(packageJson.version),
    },
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
                changeOrigin: true,
            },
        },
    },
    // Silence Sass deprecation warnings
    css: {
        preprocessorOptions: {
            scss: {
                silenceDeprecations: ["if-function", "import", "color-functions", "global-builtin"],
            },
        },
    },
});
