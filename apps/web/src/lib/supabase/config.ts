const MISSING_ENV_MESSAGE =
  "Missing Supabase env. Add VITE_SUPABASE_URL and either VITE_SUPABASE_PUBLISHABLE_KEY or VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY to apps/web/.env.local."

function readClientEnv(name: string) {
  const value = import.meta.env[name]
  return typeof value === "string" ? value.trim() : ""
}

function readServerEnv(name: string) {
  const value = process.env[name]
  return typeof value === "string" ? value.trim() : ""
}

export function getSupabaseClientEnv() {
  const url = readClientEnv("VITE_SUPABASE_URL")
  const publishableKey =
    readClientEnv("VITE_SUPABASE_PUBLISHABLE_KEY") ||
    readClientEnv("VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY")

  if (!url || !publishableKey) {
    throw new Error(MISSING_ENV_MESSAGE)
  }

  return { publishableKey, url }
}

export function getSupabaseServerEnv() {
  const url = readServerEnv("VITE_SUPABASE_URL")
  const publishableKey =
    readServerEnv("VITE_SUPABASE_PUBLISHABLE_KEY") ||
    readServerEnv("VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY")

  if (!url || !publishableKey) {
    throw new Error(MISSING_ENV_MESSAGE)
  }

  return { publishableKey, url }
}
