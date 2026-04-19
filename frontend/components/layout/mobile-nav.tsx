'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, Activity, Plug, Settings2, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'

// Mobile bottom navigation — 4 primary destinations.
// Shown below md breakpoint only. Sidebar is hidden at that size.

const MOBILE_NAV = [
  { href: '/dashboard',   label: 'Dashboard',   icon: LayoutDashboard },
  { href: '/activities',  label: 'Activities',  icon: Activity },
  { href: '/sync',        label: 'Sync',        icon: RefreshCw },
  { href: '/connections', label: 'Connect',     icon: Plug },
  { href: '/settings',    label: 'Settings',    icon: Settings2 },
]

export function MobileNav() {
  const pathname = usePathname()

  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-surface border-t border-border flex"
      aria-label="Mobile navigation"
    >
      {MOBILE_NAV.map((item) => {
        const Icon   = item.icon
        const active = pathname.startsWith(item.href)

        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex-1 flex flex-col items-center justify-center gap-1 py-3',
              'text-caption transition-colors duration-150',
              active
                ? 'text-primary'
                : 'text-text-secondary hover:text-text-primary',
            )}
            aria-current={active ? 'page' : undefined}
          >
            <Icon className={cn('h-5 w-5', active && 'stroke-[2]')} aria-hidden />
            <span>{item.label}</span>
          </Link>
        )
      })}
    </nav>
  )
}
