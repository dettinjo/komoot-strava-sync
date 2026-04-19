import type { Metadata } from 'next'
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui'
import { Badge } from '@/components/ui'
import { Button } from '@/components/ui'
import { CheckCircle2 } from 'lucide-react'

export const metadata: Metadata = { title: 'Billing' }

const FREE_FEATURES = [
  'Komoot → Strava sync',
  'Batch sync (up to 30-min delay)',
  '30 days activity history',
  '1 sync rule',
]

const PRO_FEATURES = [
  'Everything in Free',
  'Near-realtime sync',
  '12 months activity history',
  '5 sync rules',
  'Intervals.icu & Runalyze push',
  'API key access',
  'Priority support',
]

export default function BillingPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-heading-xl text-text-primary">Billing</h1>
        <p className="text-body text-text-secondary mt-1">
          Manage your RoutePass subscription.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6 max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>Free</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-heading-lg text-text-primary font-bold">$0</p>
            <ul className="space-y-2">
              {FREE_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2 text-body-sm text-text-primary">
                  <CheckCircle2 className="h-4 w-4 text-success flex-shrink-0" aria-hidden />
                  {f}
                </li>
              ))}
            </ul>
          </CardContent>
          <CardFooter>
            <Badge variant="neutral" className="w-full justify-center py-1.5">Current plan</Badge>
          </CardFooter>
        </Card>

        <Card className="border-primary">
          <CardHeader>
            <CardTitle>Pro</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-heading-lg text-text-primary font-bold">
              $29 <span className="text-body text-text-secondary font-normal">/ year</span>
            </p>
            <ul className="space-y-2">
              {PRO_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2 text-body-sm text-text-primary">
                  <CheckCircle2 className="h-4 w-4 text-primary flex-shrink-0" aria-hidden />
                  {f}
                </li>
              ))}
            </ul>
          </CardContent>
          <CardFooter>
            <Button className="w-full">Upgrade to Pro</Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
