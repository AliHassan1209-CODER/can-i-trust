import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user:         null,
      token:        null,
      refreshToken: null,
      isAuth:       false,

      login: (user, token, refreshToken) =>
        set({ user, token, refreshToken, isAuth: true }),

      logout: () =>
        set({ user: null, token: null, refreshToken: null, isAuth: false }),

      setUser: (user) => set({ user }),
    }),
    {
      name: 'can-i-trust-auth',
      partialize: (s) => ({ token: s.token, refreshToken: s.refreshToken, user: s.user, isAuth: s.isAuth }),
    }
  )
)
