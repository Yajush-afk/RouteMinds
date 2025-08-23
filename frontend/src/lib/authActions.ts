import { signOut } from "firebase/auth";
import { auth } from "./firebase";

export const handleLogout = async () => {
  try {
    await signOut(auth);
    console.log("✅ User logged out");
  } catch (err) {
    console.error("Logout error:", err);
  }
};
