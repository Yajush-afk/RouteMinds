import { Link } from "react-router-dom"

function LandingPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-background px-6 text-center">
      <div className="space-y-4">
        <h1 className="text-3xl font-semibold text-foreground sm:text-4xl">
          Route Minds Landing Page
        </h1>
        <Link className="text-primary underline underline-offset-4" to="/map">
          Go to map
        </Link>
      </div>
    </main>
  )
}

export default LandingPage
