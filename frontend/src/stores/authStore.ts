import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthUser {
  id:    number;
  email: string;
  name:  string;
}

interface AuthState {
  isLoggedIn:   boolean;
  user:         AuthUser | null;
  showAuthGate: boolean;
  gateReason:   "favourite" | "enquiry" | null;
  setUser:      (user: AuthUser) => void;
  logout:       () => void;
  openGate:     (reason: "favourite" | "enquiry") => void;
  closeGate:    () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isLoggedIn:   false,
      user:         null,
      showAuthGate: false,
      gateReason:   null,

      setUser:   (user) => set({ user, isLoggedIn: true, showAuthGate: false }),
      logout:    ()     => {
        localStorage.removeItem("sanctuary_token");
        set({ user: null, isLoggedIn: false });
      },
      openGate:  (reason) => set({ showAuthGate: true, gateReason: reason }),
      closeGate: ()       => set({ showAuthGate: false, gateReason: null }),
    }),
    {
      name:    "sanctuary_auth",
      partialize: (s) => ({ isLoggedIn: s.isLoggedIn, user: s.user }),
    }
  )
);
