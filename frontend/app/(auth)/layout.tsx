// Minimal centered layout for login / register pages.
// No sidebar, no topbar — just the RoutePass wordmark and a centered card.

import Link from 'next/link'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-bg flex flex-col">
      {/* Minimal header */}
      <header className="flex items-center justify-center py-8">
        <Link
          href="/"
          className="text-heading-sm font-semibold text-primary hover:opacity-80 transition-opacity"
        >
          RoutePass
        </Link>
      </header>

      {/* Centered form area */}
      <main className="flex-1 flex items-start justify-center px-4 pt-4 pb-16">
        <div className="w-full max-w-sm">
          {children}
        </div>
      </main>

      <footer className="py-6 text-center text-caption text-text-secondary">
        © {new Date().getFullYear()} RoutePass ·{' '}
        <Link href="/privacy" className="hover:text-primary">Privacy</Link>
        {' · '}
        <Link href="/terms" className="hover:text-primary">Terms</Link>
      </footer>
    </div>
  )
}
