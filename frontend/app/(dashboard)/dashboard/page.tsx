import type { Metadata } from 'next'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui'
import { SkeletonCard } from '@/components/ui'
import { RefreshCw, Plug, Activity } from 'lucide-react'

export const metadata: Metadata = { title: 'Dashboard' }

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-heading-xl text-text-primary">Dashboard</h1>
        <p className="text-body text-text-secondary mt-1">
          Your sync status and recent activity at a glance.
        </p>
      </div>

      <div className="space-y-6">
        <SkeletonCard />
        <div className="grid md:grid-cols-2 gap-6">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    </div>
  )
}
