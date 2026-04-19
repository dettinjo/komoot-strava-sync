import type { Metadata } from 'next'
import { SkeletonCard } from '@/components/ui'

export const metadata: Metadata = { title: 'Connections' }

export default function ConnectionsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-heading-xl text-text-primary">Connections</h1>
        <p className="text-body text-text-secondary mt-1">
          Connect RoutePass to your training platforms.
        </p>
      </div>

      <div className="grid gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  )
}
