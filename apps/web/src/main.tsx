import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"

import "@workspace/ui/globals.css"
import { TooltipProvider } from "@workspace/ui/components/tooltip"
import SupabaseAuthProvider from "@/auth/SupabaseAuthProvider.tsx"
import App from "./App.tsx"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <SupabaseAuthProvider>
        <TooltipProvider>
          <App />
        </TooltipProvider>
      </SupabaseAuthProvider>
    </BrowserRouter>
  </StrictMode>
)
