export type IdentifierKind = "email" | "sms"

export type ParsedIdentifier = {
  kind: IdentifierKind
  value: string
}

function isEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
}

function normalizeIndianPhone(rawValue: string) {
  const trimmed = rawValue.trim()
  const hasPlusPrefix = trimmed.startsWith("+")
  const digits = trimmed.replace(/\D/g, "")

  if (hasPlusPrefix) {
    if (!digits.startsWith("91") || digits.length !== 12) {
      throw new Error("Enter a valid Indian mobile number with country code.")
    }

    return `+${digits}`
  }

  if (digits.length === 10) {
    return `+91${digits}`
  }

  if (digits.length === 11 && digits.startsWith("0")) {
    return `+91${digits.slice(1)}`
  }

  if (digits.length === 12 && digits.startsWith("91")) {
    return `+${digits}`
  }

  throw new Error("Enter a valid Indian mobile number.")
}

export function parseIdentifier(rawValue: string): ParsedIdentifier {
  const trimmed = rawValue.trim()

  if (!trimmed) {
    throw new Error("Enter your phone number or email address.")
  }

  if (isEmail(trimmed)) {
    return {
      kind: "email",
      value: trimmed.toLowerCase(),
    }
  }

  return {
    kind: "sms",
    value: normalizeIndianPhone(trimmed),
  }
}

export function maskIdentifier(identifier: ParsedIdentifier) {
  if (identifier.kind === "email") {
    const [localPart, domain = ""] = identifier.value.split("@")
    const localVisible = localPart.slice(0, 2)
    return `${localVisible}${"*".repeat(Math.max(localPart.length - 2, 2))}@${domain}`
  }

  return `${identifier.value.slice(0, 3)} ${"*".repeat(4)} ${identifier.value.slice(-3)}`
}
