import type { Metadata } from 'next'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui'
import { Badge } from '@/components/ui'
import { Key } from 'lucide-react'

export const metadata: Metadata = { title: 'API Keys' }

export default function ApiKeysPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-heading-xl text-text-primary">API Keys</h1>
          <p className="text-body text-text-secondary mt-1">
            Authenticate programmatic access to the RoutePass API.
          </p>
        </div>
        <Badge variant="pro">Pro</Badge>
      </div>

      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <Key className="h-10 w-10 text-border-strong mb-4" aria-hidden />
          <h2 className="text-heading-md text-text-primary mb-2">No API keys</h2>
          <p className="text-body text-text-secondary max-w-sm">
            Create API keys to integrate RoutePass with your own tools and workflows.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
