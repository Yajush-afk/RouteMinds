import { useEffect, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"

import {
  maskIdentifier,
  parseIdentifier,
  type ParsedIdentifier,
} from "@/auth/identifier"
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
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSeparator,
  InputOTPSlot,
} from "@workspace/ui/components/input-otp"
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
  tone?: "destructive" | "warning" | "success"
  title: string
  message: string
}) {
  return (
    <div
      className={cn(
        "rounded-xl border px-3 py-2 text-sm",
        tone === "warning"
          ? "border-amber-200 bg-amber-50 text-amber-800"
          : tone === "success"
            ? "border-emerald-200 bg-emerald-50 text-emerald-800"
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

function buildPendingIdentifier(
  value: string,
  kind: "email" | "sms"
): ParsedIdentifier {
  return { kind, value }
}

function buildCodeSentMessage(identifier: ParsedIdentifier) {
  return `We sent a 6-digit code to ${maskIdentifier(identifier)}.`
}

export default function AuthEntryPanel() {
  const {
    clearPendingIdentifier,
    configError,
    error,
    isAuthenticated,
    isConfigured,
    isLoading,
    loginWithGoogle,
    pendingIdentifier,
    pendingIdentifierKind,
    startPasswordless,
    verifyOneTimePassword,
  } = useRouteMindsAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [identifierInput, setIdentifierInput] = useState(pendingIdentifier ?? "")
  const [identifierError, setIdentifierError] = useState<string | null>(null)
  const [otpValue, setOtpValue] = useState("")
  const [otpError, setOtpError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<
    "continue" | "google" | "verify" | "resend" | null
  >(null)
  const returnTo =
    new URLSearchParams(location.search).get("returnTo")?.trim() || "/map"
  const hasPendingOtp = !!pendingIdentifier && !!pendingIdentifierKind

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate(returnTo, { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate, returnTo])

  useEffect(() => {
    if (!pendingIdentifier || !pendingIdentifierKind) {
      return
    }

    setIdentifierInput(pendingIdentifier)
    setNotice(
      `We sent a 6-digit code to ${maskIdentifier(
        buildPendingIdentifier(pendingIdentifier, pendingIdentifierKind)
      )}.`
    )
  }, [pendingIdentifier, pendingIdentifierKind])

  async function handleContinue() {
    setIdentifierError(null)
    setOtpError(null)
    setNotice(null)
    setPendingAction("continue")

    try {
      await startPasswordless(identifierInput, returnTo)
      setOtpValue("")
      setNotice(buildCodeSentMessage(parseIdentifier(identifierInput)))
    } catch (startError) {
      setIdentifierError(
        startError instanceof Error
          ? startError.message
          : "We could not send a one-time code."
      )
    } finally {
      setPendingAction(null)
    }
  }

  async function handleVerifyCode() {
    setOtpError(null)
    setPendingAction("verify")

    try {
      await verifyOneTimePassword(otpValue)
    } catch (verifyError) {
      setOtpError(
        verifyError instanceof Error
          ? verifyError.message
          : "We could not verify that code."
      )
    } finally {
      setPendingAction(null)
    }
  }

  async function handleResendCode() {
    if (!pendingIdentifier) {
      return
    }

    setOtpError(null)
    setIdentifierError(null)
    setNotice(null)
    setPendingAction("resend")

    try {
      await startPasswordless(pendingIdentifier, returnTo)
      setNotice(
        buildCodeSentMessage(
          buildPendingIdentifier(pendingIdentifier, pendingIdentifierKind)
        )
      )
    } catch (resendError) {
      setOtpError(
        resendError instanceof Error
          ? resendError.message
          : "We could not resend the code."
      )
    } finally {
      setPendingAction(null)
    }
  }

  async function handleGoogleAuth() {
    setPendingAction("google")
    setIdentifierError(null)
    setOtpError(null)

    try {
      await loginWithGoogle(returnTo)
    } catch (googleError) {
      setIdentifierError(
        googleError instanceof Error
          ? googleError.message
          : "Google sign-in is unavailable."
      )
    } finally {
      setPendingAction(null)
    }
  }

  function handleUseAnotherIdentifier() {
    clearPendingIdentifier()
    setIdentifierInput("")
    setOtpValue("")
    setOtpError(null)
    setNotice(null)
  }

  const intro = hasPendingOtp
    ? "Enter the one-time code we just sent to finish signing in."
    : "Enter your phone or email to receive a one-time code."

  return (
    <div
      className="flex flex-col justify-center border border-white/70 bg-white px-8 py-14 text-slate-900 shadow-[0_24px_60px_rgba(37,28,18,0.12)] sm:px-12 sm:py-16"
      style={{ fontFamily: "'Poppins', sans-serif" }}
    >
      <div className="mx-auto w-full max-w-sm">
        <div className="mb-8 flex flex-col gap-2">
          <h1 className="text-3xl font-medium text-[#161616]">
            {hasPendingOtp ? "Confirm your code" : "Welcome to RouteMinds"}
          </h1>
          <p className="text-sm leading-6 text-[#5f5f5f]">{intro}</p>
        </div>

        <FieldGroup>
          {!hasPendingOtp ? (
            <>
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
                  placeholder="+91 98765 43210 or name@example.com"
                  aria-invalid={!!identifierError}
                  className="h-11 rounded-xl border-[#d8d8d3] bg-white px-3 text-[#151515] placeholder:text-[#8b8b85]"
                />
                <FieldDescription className="text-[#696965]">
                  We&apos;ll send a 6-digit sign-in code. New users are created
                  automatically.
                </FieldDescription>
                <FieldError>{identifierError}</FieldError>
              </Field>

              <div className="flex flex-col gap-3">
                <Button
                  type="button"
                  size="lg"
                  onClick={handleContinue}
                  disabled={!isConfigured || isLoading || pendingAction !== null}
                  className="cursor-pointer rounded-xl"
                >
                  {pendingAction === "continue" ? (
                    <LoaderCircle
                      data-icon="inline-start"
                      className="animate-spin"
                    />
                  ) : null}
                  Continue
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
                className="cursor-pointer rounded-xl border-[#cfcfc8] bg-white text-[#151515] shadow-[inset_0_0_0_1px_rgba(207,207,200,0.95)] hover:border-[#bdbdb5] hover:bg-[#f8f8f6] hover:text-[#151515]"
              >
                {pendingAction === "google" ? (
                  <LoaderCircle
                    data-icon="inline-start"
                    className="animate-spin"
                  />
                ) : (
                  <GoogleIcon />
                )}
                Continue with Google
              </Button>
            </>
          ) : (
            <>
              <Field data-invalid={!!otpError}>
                <FieldLabel htmlFor="otp" className="text-[#1d1d1d]">
                  Verification code
                </FieldLabel>
                <InputOTP
                  id="otp"
                  maxLength={6}
                  value={otpValue}
                  onChange={setOtpValue}
                  aria-invalid={!!otpError}
                >
                  <InputOTPGroup>
                    <InputOTPSlot index={0} />
                    <InputOTPSlot index={1} />
                    <InputOTPSlot index={2} />
                  </InputOTPGroup>
                  <InputOTPSeparator />
                  <InputOTPGroup>
                    <InputOTPSlot index={3} />
                    <InputOTPSlot index={4} />
                    <InputOTPSlot index={5} />
                  </InputOTPGroup>
                </InputOTP>
                <FieldDescription className="text-[#696965]">
                  {pendingIdentifier
                    ? `Enter the code sent to ${maskIdentifier(
                        buildPendingIdentifier(
                          pendingIdentifier,
                          pendingIdentifierKind
                        )
                      )}.`
                    : "Enter the 6-digit code we sent you."}
                </FieldDescription>
                <FieldError>{otpError}</FieldError>
              </Field>

              <div className="flex flex-col gap-3">
                <Button
                  type="button"
                  size="lg"
                  onClick={handleVerifyCode}
                  disabled={
                    !isConfigured ||
                    isLoading ||
                    pendingAction !== null ||
                    otpValue.trim().length !== 6
                  }
                  className="cursor-pointer rounded-xl"
                >
                  {pendingAction === "verify" ? (
                    <LoaderCircle
                      data-icon="inline-start"
                      className="animate-spin"
                    />
                  ) : null}
                  Verify code
                </Button>

                <Button
                  type="button"
                  variant="outline"
                  size="lg"
                  onClick={handleResendCode}
                  disabled={!isConfigured || isLoading || pendingAction !== null}
                  className="cursor-pointer rounded-xl"
                >
                  {pendingAction === "resend" ? (
                    <LoaderCircle
                      data-icon="inline-start"
                      className="animate-spin"
                    />
                  ) : null}
                  Resend code
                </Button>

                <Button
                  type="button"
                  variant="ghost"
                  size="lg"
                  onClick={handleUseAnotherIdentifier}
                  disabled={pendingAction !== null}
                  className="cursor-pointer rounded-xl text-[#6d675a]"
                >
                  Use a different phone or email
                </Button>
              </div>
            </>
          )}

          {notice ? (
            <InlineAlert
              tone="success"
              title="Code sent"
              message={notice}
            />
          ) : null}

          {configError ? (
            <InlineAlert
              tone="warning"
              title="Supabase is not configured"
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
            RouteMinds uses Supabase Auth for Google sign-in and one-time codes
            over email or SMS.
          </p>
        </FieldGroup>

        <p className="mt-6 text-center text-sm text-[#6d675a]">
          New here? You&apos;ll be signed up automatically.
        </p>
      </div>
    </div>
  )
}
