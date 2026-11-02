import { API } from "../api/client"

// One plain sentence for each failure code the callback can send back.
export const SIGN_IN_MESSAGES: Record<string, string> = {
  not_allowed: "That Google account isn't on the list of people who can use Talent Scout. Ask for it to be added.",
  unverified_email: "Google hasn't verified that email address, so it can't be used to sign in.",
  bad_state: "The sign-in took too long or was started in another tab. Please try again.",
  google_failed: "Google didn't complete the sign-in. Please try again.",
}

export function SignIn() {
  const code = new URLSearchParams(location.search).get("signin")
  return (
    <main className="sign-in">
      <div className="card">
        <h1>Talent Scout</h1>
        {code && <p className="error" role="alert">{SIGN_IN_MESSAGES[code] ?? SIGN_IN_MESSAGES.google_failed}</p>}
        {/* A full navigation, not fetch: Google's pages and the cookie both need the browser. */}
        <a className="start" href={`${API}/auth/google`}>Sign in with Google</a>
      </div>
    </main>
  )
}
