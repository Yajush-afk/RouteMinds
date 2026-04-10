import { apiFetch } from "@/lib/api/client"

export type AuthSessionResponse = {
  claims: Record<string, unknown>
  permissions: string[]
  scope: string[]
  subject: string
}

export function fetchAuthSession() {
  return apiFetch<AuthSessionResponse>("/api/v1/auth/me", {
    auth: true,
  })
}
