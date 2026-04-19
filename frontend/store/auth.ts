// RoutePass — Auth store (Zustand)
// Stores the JWT in memory (never localStorage/sessionStorage — XSS risk).
// The token is also sent as an httpOnly cookie for SSR requests via the
// Next.js route handler at /api/auth/session.
//
// Consumers:
//   const { token, user, login, logout } = useAuthStore()

import { create } from 'zustand'
import type { UserMe } from '@/types/api'
import { registerTokenAccessor } from '@/lib/api'

interface AuthState {
  token: string | null
  user:  UserMe | null
  login:  (token: string, user: UserMe) => void
  logout: () => void
  setUser: (user: UserMe) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user:  null,

  login(token, user) {
    set({ token, user })
  },

  logout() {
    set({ token: null, user: null })
    // Clear the httpOnly session cookie via the Next.js route handler
    fetch('/api/auth/logout', { method: 'POST' }).catch(() => null)
  },

  setUser(user) {
    set({ user })
  },
}))

// Wire the auth store into the API client so apiGet/apiPost auto-attach the JWT
registerTokenAccessor(() => useAuthStore.getState().token)
