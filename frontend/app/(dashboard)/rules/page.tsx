import type { Metadata } from 'next'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui'
import { Badge } from '@/components/ui'
import { Filter } from 'lucide-react'

export const metadata: Metadata = { title: 'Rules' }

export default function RulesPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-heading-xl text-text-primary">Rules</h1>
          <p className="text-body text-text-secondary mt-1">
            Automatically filter and tag activities during sync.
          </p>
        </div>
        <Badge variant="pro">Pro</Badge>
      </div>

      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <Filter className="h-10 w-10 text-border-strong mb-4" aria-hidden />
          <h2 className="text-heading-md text-text-primary mb-2">No rules yet</h2>
          <p className="text-body text-text-secondary max-w-sm">
            Create rules to automatically skip, tag, or modify activities based on sport type,
            distance, duration, or name.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
