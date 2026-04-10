import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"

import "@/assets/Bespoke Slab/Fonts/WEB/css/bespoke-slab.css"
import "@/assets/Poppins/Fonts/WEB/css/poppins.css"
import "@workspace/ui/globals.css"
import SupabaseAuthProvider from "@/auth/SupabaseAuthProvider.tsx"
import App from "./App.tsx"
import { ThemeProvider } from "@/components/theme-provider.tsx"

import { TooltipProvider } from "@workspace/ui/components/tooltip"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <SupabaseAuthProvider>
        <ThemeProvider>
          <TooltipProvider>
            <App />
          </TooltipProvider>
        </ThemeProvider>
      </SupabaseAuthProvider>
    </BrowserRouter>
  </StrictMode>
)
