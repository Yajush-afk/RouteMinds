declare module "auth0-js" {
  export type Auth0Error = {
    error?: string
    errorDescription?: string
    description?: string
    message?: string
  }

  export type AuthResult = {
    accessToken?: string | null
    idToken?: string | null
    idTokenPayload?: {
      sub?: string
      email?: string
      name?: string
      picture?: string
    } | null
    appState?: unknown
    expiresIn?: number | null
    tokenType?: string | null
    scope?: string | null
  }

  export type PasswordlessStartOptions = {
    connection: string
    send: "code" | "link"
    email?: string
    phoneNumber?: string
    authParams?: Record<string, unknown>
  }

  export type PasswordlessLoginOptions = {
    connection: string
    email?: string
    phoneNumber?: string
    verificationCode: string
    appState?: unknown
    onRedirecting?: (done: () => void) => void
  }

  export type AuthorizeOptions = {
    connection?: string
    appState?: unknown
  }

  export type LogoutOptions = {
    clientID?: string
    returnTo?: string
  }

  export type ParseHashOptions = {
    hash?: string
  }

  export type CheckSessionOptions = {
    responseType?: string
    scope?: string
    audience?: string
  }

  export type WebAuthOptions = {
    domain: string
    clientID: string
    redirectUri: string
    responseType: string
    scope: string
    audience?: string
  }

  export class WebAuth {
    constructor(options: WebAuthOptions)
    authorize(options?: AuthorizeOptions): void
    checkSession(
      options: CheckSessionOptions,
      callback: (error: Auth0Error | null, result?: AuthResult | null) => void
    ): void
    logout(options?: LogoutOptions): void
    parseHash(
      options: ParseHashOptions,
      callback: (error: Auth0Error | null, result?: AuthResult | null) => void
    ): void
    passwordlessLogin(
      options: PasswordlessLoginOptions,
      callback: (error: Auth0Error | null) => void
    ): void
    passwordlessStart(
      options: PasswordlessStartOptions,
      callback: (error: Auth0Error | null) => void
    ): void
  }

  const auth0: {
    WebAuth: typeof WebAuth
  }

  export default auth0
}
