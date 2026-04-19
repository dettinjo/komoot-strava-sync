import Link from 'next/link'
import type { Metadata } from 'next'
import { CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui'

export const metadata: Metadata = {
  title: 'RoutePass — Your routes, everywhere you train',
}

const FEATURES = [
  { title: 'Automatic sync',      body: 'Activities flow from Komoot to Strava without lifting a finger.' },
  { title: 'Multi-platform',      body: 'Push to Intervals.icu and Runalyze in the same sync run.' },
  { title: 'Rate-limit safe',     body: 'Shared Strava quota managed across all users — Pro users always get priority.' },
  { title: 'Self-hostable',       body: 'Run the full stack on your own server. MIT open-source, no licence key needed.' },
  { title: 'Sync rules',          body: 'Filter by sport type, distance, or name. Skip what you do not want.' },
  { title: 'Open API',            body: 'API key access for Pro users. Integrate with your own tools.' },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg font-sans">
      {/* Nav */}
      <header className="flex items-center justify-between px-6 py-4 max-w-5xl mx-auto">
        <span className="text-heading-sm font-semibold text-primary">RoutePass</span>
        <div className="flex items-center gap-4">
          <Link href="/login"    className="text-body-sm text-text-secondary hover:text-primary">Sign in</Link>
          <Button asChild size="sm">
            <Link href="/register">Get started free</Link>
          </Button>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-primary text-text-inverse py-24 px-6 text-center">
        <h1 className="text-display font-bold mb-4">Your routes, everywhere you train.</h1>
        <p className="text-body-lg opacity-80 mb-8 max-w-lg mx-auto">
          RoutePass automatically syncs your Komoot activities to Strava, Intervals.icu, Runalyze,
          and more — so your training data is always complete.
        </p>
        <div className="flex gap-3 justify-center">
          <Button asChild variant="secondary" size="lg">
            <Link href="/register">Get started free</Link>
          </Button>
          <Button asChild variant="ghost" size="lg" className="text-text-inverse hover:bg-primary-hover hover:text-text-inverse">
            <a href="#features">See how it works</a>
          </Button>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 px-6 max-w-5xl mx-auto">
        <h2 className="text-heading-xl text-text-primary text-center mb-12">
          Everything your training data needs
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div key={f.title} className="bg-surface border border-border rounded-lg p-6 shadow-sm">
              <CheckCircle2 className="h-5 w-5 text-accent mb-3" aria-hidden />
              <h3 className="text-heading-sm text-text-primary mb-1">{f.title}</h3>
              <p className="text-body-sm text-text-secondary">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20 px-6 bg-surface border-y border-border">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-heading-xl text-text-primary mb-4">Simple pricing</h2>
          <p className="text-body text-text-secondary mb-12">Free to start. Upgrade when you need more.</p>
          <div className="grid sm:grid-cols-2 gap-6 text-left">
            <div className="border border-border rounded-lg p-6">
              <p className="text-heading-sm text-text-primary mb-1">Free</p>
              <p className="text-heading-lg font-bold text-text-primary mb-4">$0</p>
              <ul className="space-y-2 text-body-sm text-text-secondary">
                <li>Komoot → Strava sync</li>
                <li>30-day history</li>
                <li>1 sync rule</li>
              </ul>
            </div>
            <div className="border-2 border-primary rounded-lg p-6">
              <p className="text-heading-sm text-primary mb-1">Pro</p>
              <p className="text-heading-lg font-bold text-text-primary mb-4">$29<span className="text-body font-normal text-text-secondary"> / year</span></p>
              <ul className="space-y-2 text-body-sm text-text-secondary">
                <li>Near-realtime sync</li>
                <li>12-month history</li>
                <li>5 sync rules + API keys</li>
                <li>Intervals.icu &amp; Runalyze push</li>
              </ul>
              <Button asChild className="w-full mt-6">
                <Link href="/register">Upgrade to Pro</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 text-center text-caption text-text-secondary">
        © {new Date().getFullYear()} RoutePass ·{' '}
        <Link href="/privacy" className="hover:text-primary">Privacy</Link>
        {' · '}
        <Link href="/terms"   className="hover:text-primary">Terms</Link>
        {' · '}
        <a href="https://github.com/dettinjo/komoot-strava-sync" className="hover:text-primary" target="_blank" rel="noopener noreferrer">GitHub</a>
      </footer>
    </div>
  )
}
