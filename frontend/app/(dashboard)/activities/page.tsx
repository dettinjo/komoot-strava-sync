import type { Metadata } from 'next'
import { SkeletonRow } from '@/components/ui'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui'

export const metadata: Metadata = { title: 'Activities' }

export default function ActivitiesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-heading-xl text-text-primary">Activities</h1>
        <p className="text-body text-text-secondary mt-1">
          All synced activities across your connected platforms.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Sync history</CardTitle>
        </CardHeader>
        <CardContent className="divide-y divide-border">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonRow key={i} />
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
