import { Navigate, useLocation } from "react-router-dom"

export default function LegacyAuthRedirect() {
  const location = useLocation()
  const target = location.search ? `/auth${location.search}` : "/auth"

  return <Navigate replace to={target} />
}
