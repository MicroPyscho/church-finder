import { create } from "zustand";

interface AuthState {
  isLoggedIn:    boolean;
  user:          any | null;
  showAuthGate:  boolean;
  gateReason:    "favourite" | "enquiry" | null;
  setUser:       (user: any) => void;
  logout:        () => void;
  openGate:      (reason: "favourite" | "enquiry") => void;
  closeGate:     () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isLoggedIn:   false,
  user:         null,
  showAuthGate: false,
  gateReason:   null,

  setUser: (user) => set({ user, isLoggedIn: true, showAuthGate: false }),
  logout:  ()     => set({ user: null, isLoggedIn: false }),
  openGate:  (reason) => set({ showAuthGate: true, gateReason: reason }),
  closeGate: ()       => set({ showAuthGate: false, gateReason: null }),
}));
