import type { Metadata } from 'next'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui'

export const metadata: Metadata = { title: 'Settings' }

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-heading-xl text-text-primary">Settings</h1>
        <p className="text-body text-text-secondary mt-1">
          Manage your account, sync preferences, and notifications.
        </p>
      </div>

      <div className="space-y-4 max-w-xl">
        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-body text-text-secondary">Account details and password.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sync preferences</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-body text-text-secondary">
              Poll interval, sync direction, and activity defaults.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Notifications</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-body text-text-secondary">Webhook URL and alert thresholds.</p>
          </CardContent>
        </Card>

        <Card className="border-error">
          <CardHeader>
            <CardTitle className="text-error">Danger zone</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-body text-text-secondary">Delete your account and all data.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
