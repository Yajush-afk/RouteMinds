import { useEffect, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"

import { useRouteMindsAuth } from "@/auth/Auth0ProviderWithNavigate"
import { Button } from "@workspace/ui/components/button"
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@workspace/ui/components/field"
import { Input } from "@workspace/ui/components/input"
import { Separator } from "@workspace/ui/components/separator"
import { cn } from "@workspace/ui/lib/utils"
import { AlertCircle, LoaderCircle } from "lucide-react"

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18z"
      />
      <path
        fill="#34A853"
        d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17z"
      />
      <path
        fill="#FBBC05"
        d="M4.5 10.52a4.8 4.8 0 0 1 0-3.04V5.41H1.83a8 8 0 0 0 0 7.18z"
      />
      <path
        fill="#EA4335"
        d="M8.98 4.18c1.17 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.4L4.5 7.49a4.77 4.77 0 0 1 4.48-3.3z"
      />
    </svg>
  )
}

function InlineAlert({
  tone = "destructive",
  title,
  message,
}: {
  tone?: "destructive" | "warning"
  title: string
  message: string
}) {
  return (
    <div
      className={cn(
        "rounded-xl border px-3 py-2 text-sm",
        tone === "warning"
          ? "border-amber-200 bg-amber-50 text-amber-800"
          : "border-red-200 bg-red-50 text-red-700"
      )}
    >
      <p className="flex items-center gap-2 font-medium">
        <AlertCircle className="size-4" />
        {title}
      </p>
      <p className="mt-1">{message}</p>
    </div>
  )
}

export default function AuthEntryPanel() {
  const {
    configError,
    error,
    isAuthenticated,
    isConfigured,
    isLoading,
    loginWithGoogle,
    startPasswordless,
  } = useRouteMindsAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [identifierInput, setIdentifierInput] = useState("")
  const [identifierError, setIdentifierError] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<
    "continue" | "google" | null
  >(null)
  const returnTo =
    new URLSearchParams(location.search).get("returnTo")?.trim() || "/map"

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate(returnTo, { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate, returnTo])

  async function handleContinue() {
    setIdentifierError(null)
    setPendingAction("continue")

    try {
      await startPasswordless(identifierInput, returnTo)
    } catch (startError) {
      setPendingAction(null)
      setIdentifierError(
        startError instanceof Error
          ? startError.message
          : "We could not send a one-time code."
      )
    }
  }

  async function handleGoogleAuth() {
    setPendingAction("google")
    setIdentifierError(null)

    try {
      await loginWithGoogle(returnTo)
    } catch (googleError) {
      setPendingAction(null)
      setIdentifierError(
        googleError instanceof Error
          ? googleError.message
          : "Google sign-in is unavailable."
      )
    }
  }

  const intro = "Enter your phone or email"

  return (
    <div
      className="flex flex-col justify-center bg-white px-8 py-14 text-slate-900 sm:px-12 sm:py-16"
      style={{ fontFamily: "'Poppins', sans-serif" }}
    >
      <div className="mx-auto w-full max-w-sm">
        <div className="mb-8 flex flex-col gap-2">
          <h1 className="text-3xl font-medium text-[#161616]">
            Welcome to RouteMinds
          </h1>
          <p className="text-sm leading-6 text-[#5f5f5f]">{intro}</p>
        </div>

        <FieldGroup>
          <Field data-invalid={!!identifierError}>
            <FieldLabel htmlFor="identifier" className="text-[#1d1d1d]">
              Phone or email
            </FieldLabel>
            <Input
              id="identifier"
              autoComplete="email"
              inputMode="email"
              value={identifierInput}
              onChange={(event) => setIdentifierInput(event.target.value)}
              placeholder="+91 98765 43210"
              aria-invalid={!!identifierError}
              className="h-11 rounded-xl border-[#d8d8d3] bg-white px-3 text-[#151515] placeholder:text-[#8b8b85]"
            />
            <FieldDescription className="text-[#696965]">
              We&apos;ll send you a one-time code on the next secure step.
            </FieldDescription>
            <FieldError>{identifierError}</FieldError>
          </Field>

          <div className="flex flex-col gap-3">
            <Button
              type="button"
              size="lg"
              onClick={handleContinue}
              disabled={!isConfigured || isLoading || pendingAction !== null}
              className="rounded-xl"
            >
              {pendingAction === "continue" ? (
                <LoaderCircle
                  data-icon="inline-start"
                  className="animate-spin"
                />
              ) : null}
              Continue &rarr;
            </Button>
          </div>

          <div className="flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-xs text-[#8a8a84]">or</span>
            <Separator className="flex-1" />
          </div>

          <Button
            type="button"
            variant="outline"
            size="lg"
            onClick={handleGoogleAuth}
            disabled={!isConfigured || isLoading || pendingAction !== null}
            className="rounded-xl"
          >
            {pendingAction === "google" ? (
              <LoaderCircle data-icon="inline-start" className="animate-spin" />
            ) : (
              <GoogleIcon />
            )}
            Continue with Google
          </Button>

          {configError ? (
            <InlineAlert
              tone="warning"
              title="Auth0 is not configured"
              message={configError}
            />
          ) : null}

          {error ? (
            <InlineAlert
              title="Authentication failed"
              message={error.message}
            />
          ) : null}

          <p className="text-xs leading-5 text-[#6d6d66]">
            Your phone or email is used only to start Auth0&apos;s secure
            passwordless login flow.
          </p>
        </FieldGroup>

        <p className="mt-6 text-center text-sm text-[#6d675a]">
          New here? You&apos;ll be signed up automatically.
        </p>
      </div>
    </div>
  )
}
