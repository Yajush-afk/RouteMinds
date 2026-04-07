import { createBrowserClient } from '@supabase/ssr'
import { getSupabaseClientEnv } from './config'

export function createClient() {
  const { publishableKey, url } = getSupabaseClientEnv()

  return createBrowserClient(url, publishableKey)
}
