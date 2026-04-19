'use client'

import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api'
import type { PaginatedActivities } from '@/types/api'

interface UseActivitiesParams {
  page?:      number
  pageSize?:  number
  sportType?: string
  status?:    string
}

export function useActivities({
  page     = 1,
  pageSize = 25,
  sportType,
  status,
}: UseActivitiesParams = {}) {
  const params = new URLSearchParams({
    page:      String(page),
    page_size: String(pageSize),
    ...(sportType ? { sport_type: sportType } : {}),
    ...(status    ? { status }                : {}),
  })

  return useQuery<PaginatedActivities>({
    queryKey: ['activities', { page, pageSize, sportType, status }],
    queryFn:  () => apiGet(`/api/v1/activities?${params}`),
  })
}
