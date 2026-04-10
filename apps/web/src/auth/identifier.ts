export type ParsedIdentifier = {
  kind: "email" | "sms"
  value: string
}

export function parseIdentifier(value: string): ParsedIdentifier {
  const normalized = value.trim()

  if (!normalized) {
    throw new Error("Enter your phone number or email.")
  }

  if (normalized.includes("@")) {
    return { kind: "email", value: normalized.toLowerCase() }
  }

  const digits = normalized.replace(/[^\d+]/g, "")

  if (digits.length < 10) {
    throw new Error("Enter a valid phone number or email.")
  }

  return { kind: "sms", value: digits }
}

export function maskIdentifier({ kind, value }: ParsedIdentifier) {
  if (kind === "email") {
    const [local, domain] = value.split("@")

    if (!local || !domain) {
      return value
    }

    const visibleLocal = local.slice(0, 2)
    return `${visibleLocal}${"*".repeat(Math.max(local.length - 2, 2))}@${domain}`
  }

  const suffix = value.slice(-4)
  return `${"*".repeat(Math.max(value.length - 4, 6))}${suffix}`
}
