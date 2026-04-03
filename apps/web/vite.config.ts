import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    modulePreload: {
      resolveDependencies(_filename, deps, context) {
        if (context.hostType !== "html") {
          return deps
        }

        return deps.filter(
          (dep) => !dep.includes("map-vendor") && !dep.includes("MapPage-")
        )
      },
    },
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return undefined
          }

          if (id.includes("maplibre-gl") || id.includes("react-map-gl")) {
            return "map-vendor"
          }

          if (id.includes("/motion/") || id.includes("motion/react")) {
            return "motion-vendor"
          }

          return undefined
        },
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
