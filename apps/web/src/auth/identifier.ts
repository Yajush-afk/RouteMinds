export type ParsedIdentifier = {
  kind: "email"
  value: string
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function parseIdentifier(value: string): ParsedIdentifier {
  const normalized = value.trim()

  if (!normalized) {
    throw new Error("Enter your email address.")
  }

  const normalizedEmail = normalized.toLowerCase()

  if (!EMAIL_PATTERN.test(normalizedEmail)) {
    if (!normalized.includes("@")) {
      throw new Error(
        "Phone number sign-in is no longer available. Use your email address instead."
      )
    }

    throw new Error("Enter a valid email address.")
  }

  return { kind: "email", value: normalizedEmail }
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
