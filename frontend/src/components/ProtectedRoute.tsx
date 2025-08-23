// src/components/ProtectedRoute.tsx
import type { JSX } from "react";
import { Navigate } from "react-router-dom";

type ProtectedRouteProps = {
  user: any;
  children: JSX.Element;
};

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ user, children }) => {
  if (!user) return <Navigate to="/login" />;
  return children;
};

export default ProtectedRoute;
