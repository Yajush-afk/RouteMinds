import { createServerClient, parseCookieHeader, serializeCookieHeader } from '@supabase/ssr'
import { getSupabaseServerEnv } from './config'

export function createClient(request: Request) {
  const headers = new Headers()
  const { publishableKey, url } = getSupabaseServerEnv()

  const supabase = createServerClient(
    url,
    publishableKey,
    {
      cookies: {
        getAll() {
          return parseCookieHeader(request.headers.get('Cookie') ?? '') as {
            name: string
            value: string
          }[]
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            headers.append('Set-Cookie', serializeCookieHeader(name, value, options))
          )
        },
      },
    }
  )

  return { supabase, headers }
}
