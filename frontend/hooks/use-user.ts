'use client'

import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api'
import { useAuthStore } from '@/store/auth'
import type { UserMe } from '@/types/api'

export function useUser() {
  const token   = useAuthStore((s) => s.token)
  const setUser = useAuthStore((s) => s.setUser)

  return useQuery<UserMe>({
    queryKey: ['user', 'me'],
    queryFn:  async () => {
      const user = await apiGet<UserMe>('/api/v1/auth/me')
      setUser(user)
      return user
    },
    enabled: !!token,
    staleTime: 60_000,
  })
}
