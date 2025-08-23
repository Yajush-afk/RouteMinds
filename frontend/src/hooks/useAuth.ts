import { useEffect, useState } from "react";
import { onIdTokenChanged, getIdToken, type User } from "firebase/auth";
import { auth } from "@/lib/firebase";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsub = onIdTokenChanged(auth, async (u) => {
      setUser(u);
      if (u) {
        const t = await getIdToken(u, true); // get fresh JWT
        setToken(t);
      } else {
        setToken(null);
      }
      setLoading(false);
    });

    return () => unsub();
  }, []);

  return { user, token, loading };
}
