# RoutePass Frontend — AI Implementation Guide

> Read this file first before writing any frontend code. It is the single source of truth for
> implementation order, component patterns, naming conventions, and file placement.
> Design tokens and visual specs live in `../DESIGN.md`. This file covers *how to build*, not *what it looks like*.

---

## Stack (locked — do not change without updating this file)

| Layer | Package | Version |
|-------|---------|---------|
| Framework | Next.js App Router | 14.x |
| Language | TypeScript | 5.x strict |
| Styling | Tailwind CSS | 3.x |
| Component primitives | shadcn/ui (Radix) | — |
| Icons | Lucide React | latest |
| Data fetching | TanStack Query v5 | 5.x |
| Forms | React Hook Form + Zod | 7.x + 3.x |
| Auth state | Zustand | 5.x |
| Charts | Recharts | 2.x |
| Fonts | next/font/google — Inter + JetBrains Mono | — |

---

## Rules Every AI Agent Must Follow

1. **Never hardcode color values** (`#16533A`, `text-[#111827]`, etc.). Use Tailwind tokens from `tailwind.config.ts` only.
2. **Never add a new color** to a component. Extend `tailwind.config.ts → theme.extend.colors` if a token is genuinely missing, then update `DESIGN.md`.
3. **Every page is a Server Component by default.** Add `'use client'` only when you need browser APIs, hooks, or event handlers.
4. **Use `cn()` from `@/lib/utils`** for all className merging. Never concatenate classnames with template literals.
5. **Import UI components from `@/components/ui`** (the barrel). Never import from deep paths like `@/components/ui/button`.
6. **Form validation lives in Zod schemas** co-located with the form component. Never validate inside `onChange` handlers.
7. **API calls go through `apiGet/apiPost/apiPut/apiDelete`** from `@/lib/api`. Never call `fetch()` directly in components.
8. **Data fetching uses TanStack Query.** Never `useEffect` + `fetch`. Query keys follow the pattern `[resource, { filters }]`.
9. **Auth token lives in Zustand** (`useAuthStore`). Never `localStorage.getItem('token')`.
10. **All text sizes come from the type scale** in `tailwind.config.ts`. Never `text-[13px]`.
11. **Spacing is always a multiple of 4px.** Use `space-*`, `p-*`, `gap-*` with Tailwind tokens. Never `mt-[7px]`.
12. **`'use client'` components must not do data-fetching via fetch.** Use the hook layer (`hooks/`) instead.

---

## Directory Structure (do not reorganise)

```
frontend/
├── app/
│   ├── (auth)/              ← login, register — minimal centered layout
│   │   ├── layout.tsx
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── (dashboard)/         ← authenticated app — sidebar + topbar shell
│   │   ├── layout.tsx
│   │   ├── dashboard/page.tsx
│   │   ├── activities/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── connections/page.tsx
│   │   ├── rules/page.tsx
│   │   ├── api-keys/page.tsx
│   │   ├── settings/page.tsx
│   │   └── billing/page.tsx
│   ├── (landing)/           ← public marketing page
│   │   └── page.tsx
│   ├── globals.css          ← CSS custom properties + Tailwind directives
│   └── layout.tsx           ← root: fonts, <Providers>, metadata
├── components/
│   ├── ui/                  ← design system atoms (Button, Card, Badge …)
│   │   └── index.ts         ← barrel — always import from here
│   ├── layout/              ← Topbar, Sidebar, MobileNav
│   ├── connections/         ← ConnectionCard, PlatformIcons
│   ├── activities/          ← ActivityTable, ActivityRow
│   └── sync/                ← SyncStatusCard, SyncNowButton
├── hooks/                   ← TanStack Query wrappers (use-user, use-activities …)
├── lib/
│   ├── api.ts               ← fetch wrapper (apiGet, apiPost, apiPut, apiDelete)
│   └── utils.ts             ← cn(), formatRelative, formatDistance …
├── store/
│   └── auth.ts              ← Zustand auth store (token + user)
├── types/
│   └── api.ts               ← TypeScript mirror of backend Pydantic schemas
├── public/                  ← static assets (logo SVG goes here)
├── tailwind.config.ts       ← ALL design tokens live here
├── next.config.ts
├── tsconfig.json
├── components.json          ← shadcn/ui config
└── package.json
```

---

## What Is Already Built

| File | Status | Notes |
|------|--------|-------|
| `tailwind.config.ts` | ✅ Complete | All design tokens wired |
| `app/globals.css` | ✅ Complete | CSS custom properties + base styles |
| `app/layout.tsx` | ✅ Complete | Fonts + Providers |
| `app/(auth)/layout.tsx` | ✅ Complete | Minimal centered auth shell |
| `app/(auth)/login/page.tsx` | ✅ Complete | Login form (RHF + Zod) |
| `app/(dashboard)/layout.tsx` | ✅ Complete | App shell: Topbar + Sidebar + MobileNav |
| `app/(dashboard)/dashboard/page.tsx` | 🟡 Stub | Skeleton placeholders only |
| `components/providers.tsx` | ✅ Complete | QueryClient |
| `components/ui/button.tsx` | ✅ Complete | All 5 variants + loading state |
| `components/ui/card.tsx` | ✅ Complete | Card + header/content/footer |
| `components/ui/badge.tsx` | ✅ Complete | All semantic variants + StatusDot |
| `components/ui/input.tsx` | ✅ Complete | Input, Textarea, Label, FormField |
| `components/ui/alert.tsx` | ✅ Complete | 4 semantic variants with icons |
| `components/ui/skeleton.tsx` | ✅ Complete | Shimmer variants |
| `components/ui/index.ts` | ✅ Complete | Barrel export |
| `components/layout/topbar.tsx` | ✅ Complete | Logo + user menu |
| `components/layout/sidebar.tsx` | ✅ Complete | Collapsible + active state |
| `components/layout/mobile-nav.tsx` | ✅ Complete | 5-item bottom nav |
| `lib/api.ts` | ✅ Complete | fetch wrapper + ApiRequestError |
| `lib/utils.ts` | ✅ Complete | cn, formatters, sportLabel |
| `store/auth.ts` | ✅ Complete | Zustand + token accessor wired |
| `types/api.ts` | ✅ Complete | All backend response types |
| `hooks/use-user.ts` | ✅ Complete | |
| `hooks/use-activities.ts` | ✅ Complete | |

---

## Build Order — What to Implement Next

Work top-to-bottom. Do not skip ahead — later steps depend on earlier ones being correct.

### Step A — Register Page
**File:** `app/(auth)/register/page.tsx`

Mirror `login/page.tsx`. Differences:
- Fields: `email`, `password`, `confirmPassword` (Zod `.refine()` that passwords match)
- POST to `/api/v1/auth/register` with `{ email, password }` JSON body (not form-encoded)
- On success: auto-login (POST `/api/v1/auth/login` to get token), redirect to `/dashboard`
- Footer link: "Already have an account? Sign in"

### Step B — SyncStatusCard component
**File:** `components/sync/sync-status-card.tsx`

Props: `state: SyncState` (from `types/api.ts`)

Layout (full-width card):
- Left: `<StatusDot status={…}>` + heading "Sync status" + sub-text (e.g. "Last synced 2 hours ago — Morning Ride")
- Right: `<Button variant="secondary" size="sm">Sync now</Button>` — calls POST `/api/v1/sync/trigger`
- Below (conditional, free tier only): usage bar
  - `<div>` progress bar from 0→1, filled with `bg-accent`, track `bg-border`
  - Label: "{used} / {limit} daily Strava calls used"
  - If > 80%: show `<Alert variant="warning">` beneath

Data hook: `useSyncState` in `hooks/use-sync-state.ts`
- queryKey: `['sync', 'state']`
- queryFn: `apiGet<SyncState>('/api/v1/sync/status')`
- refetchInterval: 15_000 (poll every 15s when syncing)

### Step C — Activities page
**File:** `app/(dashboard)/activities/page.tsx`
**File:** `components/activities/activity-table.tsx`
**File:** `components/activities/activity-row.tsx`

`ActivityTable` props: `activities: Activity[]`, `loading: boolean`

Table columns: name | sport type (icon + label) | date | duration | distance | status badge | GPX button

- Sport icon: map `sportType` to a Lucide icon (Bike → `Bike`, Run → `Footprints`, Hike → `Mountain`, default → `Activity`)
- Status badge: use `<Badge variant={…}>` with variant matching activity status (`synced→connected`, `failed→error`, `pending→syncing`, `skipped→neutral`)
- GPX button: only rendered when `activity.gpx_available`. Ghost button with `Download` icon. href: `/api/v1/activities/{id}/gpx` (direct download, sets the auth header via the Next.js rewrite)
- Pagination: render `<Pagination>` below table. New component `components/ui/pagination.tsx` — previous / page numbers / next, using Ghost button variant.

`app/(dashboard)/activities/page.tsx`:
- Search input (filter by name, client-side on the current page)
- `useActivities({ page, pageSize: 25 })` hook
- Pass `loading` + `activities` to `ActivityTable`
- Render `SkeletonRow` × 5 while loading

### Step D — Activity detail page
**File:** `app/(dashboard)/activities/[id]/page.tsx`

- Fetch: `apiGet<Activity>('/api/v1/activities/${id}')`
- Layout: two-column on md+
  - Left: activity metadata (name, date, sport, distance, duration, elevation)
  - Right: map placeholder (grey rounded box, "Map coming soon" caption) + GPX download button
- Back link: "← Back to Activities" (Ghost button or plain link)

### Step E — Connections page
**File:** `app/(dashboard)/connections/page.tsx`
**File:** `components/connections/connection-card.tsx`

`ConnectionCard` props:
```ts
interface ConnectionCardProps {
  platform:     string            // 'Komoot' | 'Strava' | 'Intervals.icu' | …
  icon:         React.ElementType // Lucide icon
  description:  string
  connected:    boolean
  comingSoon?:  boolean
  onConnect:    () => void
  onDisconnect: () => void
  children?:    React.ReactNode   // rendered inside card when connected (e.g. form fields)
}
```

States:
- Not connected: muted card. Primary "Connect" button.
- Connected: green `<Badge variant="connected">Connected</Badge>` in card header. Secondary "Disconnect" danger button.
- Coming soon: neutral badge "Coming soon". All buttons disabled.
- Error: red badge + `<Alert variant="error">` with the error message.

Platforms to render (in order):
1. Komoot — `Map` icon — POST `/api/v1/auth/komoot/connect` with `{ email, password }` form fields rendered in card
2. Strava — `Activity` icon — redirect to `/api/v1/auth/strava/connect` (OAuth)
3. Intervals.icu — `BarChart3` icon — POST connect with `{ api_key, athlete_id }` (Phase 6)
4. Runalyze — `TrendingUp` icon — POST connect with `{ token }` (Phase 6)
5. Polar — `Heart` icon — OAuth redirect (Phase 7) — "Coming soon"
6. Outdooractive — `Compass` icon — OAuth redirect (Phase 7) — "Coming soon"

User connection status comes from `useUser()` hook (`user.komoot_connected`, etc.).

### Step F — Billing page
**File:** `app/(dashboard)/billing/page.tsx`

- Two plan cards side by side (Free / Pro), matching the pricing from PROJECT.md
  - Free card: current features list, "Your current plan" badge if on free
  - Pro card: additional features, "Upgrade — $29/year" primary button → POST `/api/v1/billing/checkout` → redirect to Stripe URL in response
- If already Pro: show `<Alert variant="success">` and "Manage subscription" button → POST `/api/v1/billing/portal` → redirect to Stripe portal
- Usage section below: Strava daily calls bar (same component as SyncStatusCard)

### Step G — Settings page
**File:** `app/(dashboard)/settings/page.tsx`

Tabs (Radix `@radix-ui/react-tabs`):
- **Profile**: email display (read-only), password change form
- **Sync**: poll interval slider/select (15/30/60/120 min), sync direction toggles
- **Notifications**: webhook URL input (Pro only)
- **Danger zone**: "Delete account" button → confirmation dialog before DELETE `/api/v1/auth/me`

### Step H — Rules page (Pro gate)
**File:** `app/(dashboard)/rules/page.tsx`

- If free tier: full-page upsell card with "Upgrade to Pro" CTA. Do not show rule list.
- If Pro: rule list table + "Add rule" button that opens a slide-over drawer
- Drawer contains: name input + condition builder (field select + operator select + value input) + action select
- CRUD via `apiPost/apiPut/apiDelete` on `/api/v1/rules`

### Step I — API Keys page (Pro gate)
**File:** `app/(dashboard)/api-keys/page.tsx`

- Same Pro gate pattern as Rules
- Table: name | prefix | created | last used | [Revoke button]
- "Create key" button → dialog → name input → POST `/api/v1/api-keys` → show `raw_key` ONCE in a monospace alert box with copy button. Warn the user it won't be shown again.
- Revoke: DELETE `/api/v1/api-keys/{id}` — confirm dialog first

### Step J — Landing page
**File:** `app/(landing)/page.tsx`

Sections (top to bottom):
1. **Hero**: headline "Your routes, everywhere you train." Sub: one sentence value prop. CTA: "Get started free" (primary) + "See how it works" (ghost, scrolls to #features). Background: full-width primary color block, white text.
2. **Platform logos**: horizontal strip — Komoot, Strava, Intervals.icu, Runalyze logos (SVG, greyscale, coloured on hover)
3. **Features** `#features`: 3-column grid of feature cards (icon + heading + body text)
4. **Pricing**: Free card + Pro card. Annual/monthly toggle. Same data as billing page.
5. **FAQ**: accordion, 5–7 questions
6. **Footer**: links + copyright

---

## Pattern Reference

### Adding a new page

```tsx
// app/(dashboard)/example/page.tsx
import type { Metadata } from 'next'

export const metadata: Metadata = { title: 'Example' }

export default function ExamplePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-heading-xl text-text-primary">Example</h1>
        <p className="text-body text-text-secondary mt-1">Page description.</p>
      </div>
      {/* content */}
    </div>
  )
}
```

### Adding a new data hook

```ts
// hooks/use-example.ts
'use client'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api'
import type { ExampleType } from '@/types/api'

export function useExample(id: string) {
  return useQuery<ExampleType>({
    queryKey: ['example', id],
    queryFn:  () => apiGet(`/api/v1/example/${id}`),
    enabled:  !!id,
  })
}
```

### Adding a new UI component

```tsx
// components/ui/example.tsx
import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const exampleVariants = cva('base-classes', {
  variants: { variant: { default: 'variant-classes' } },
  defaultVariants: { variant: 'default' },
})

export interface ExampleProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof exampleVariants> {}

function Example({ className, variant, ...props }: ExampleProps) {
  return <div className={cn(exampleVariants({ variant }), className)} {...props} />
}

export { Example, exampleVariants }
```

Then add to `components/ui/index.ts`.

### Handling a Pro-only page

```tsx
'use client'
import { useUser } from '@/hooks/use-user'
import { Card, CardContent, Button } from '@/components/ui'
import Link from 'next/link'

export default function ProOnlyPage() {
  const { data: user, isLoading } = useUser()

  if (isLoading) return <SkeletonCard />

  if (user?.tier !== 'pro') {
    return (
      <Card>
        <CardContent className="text-center py-12">
          <h2 className="text-heading-md text-text-primary mb-2">Pro feature</h2>
          <p className="text-body text-text-secondary mb-6">
            Upgrade to RoutePass Pro to access this feature.
          </p>
          <Button asChild>
            <Link href="/billing">Upgrade to Pro</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return <div>{/* actual page content */}</div>
}
```

### Mutation with optimistic invalidation

```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiDelete } from '@/lib/api'

function useDeleteApiKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiDelete(`/api/v1/api-keys/${id}`),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['api-keys'] }),
  })
}
```

---

## Token Cheat Sheet (most used)

| What you need | Class to use |
|--------------|-------------|
| Primary green text | `text-primary` |
| Primary green background | `bg-primary` |
| Accent mint | `bg-accent` / `text-accent` |
| App background | `bg-bg` |
| White card | `bg-surface` |
| Default border | `border-border` |
| Body copy | `text-text-primary text-body` |
| Muted text | `text-text-secondary` |
| Error text/border | `text-error` / `border-error` |
| Success text | `text-success` |
| Card border+shadow | `border border-border rounded-lg shadow-md` |
| Card padding | `p-6` |
| Section gap | `space-y-8` |
| Card header gap | `px-6 py-4 border-b border-border` |
| Smooth transition | `transition-colors duration-150` |
| Focus ring | `focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2` |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Dev only | FastAPI backend URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_APP_URL` | Yes | App base URL for OAuth callbacks and metadata |

Copy `.env.local.example` → `.env.local` before running `npm run dev`.

---

## Dev Commands

```bash
# From repo root:
make frontend-install   # npm install
make frontend-dev       # npm run dev  →  http://localhost:3000
make frontend-check     # lint + typecheck

# From frontend/ directory:
npm run dev
npm run build
npm run check           # lint + typecheck
```

---

## Adding a New Platform Integration (pattern)

When a new platform (e.g. Polar) is added to the backend:

1. Add connection fields to `UserMe` in `types/api.ts` (`polar_connected: boolean`)
2. Add `polar` to the connections page list in `connections/page.tsx` — remove "Coming soon"
3. Add the connect/disconnect API endpoints to `lib/api.ts` if they need special handling (OAuth redirects are just `window.location.href = '/api/v1/auth/polar/connect'`)
4. Update `hooks/use-user.ts` — no change needed (it fetches the whole `UserMe`)
5. Test: connect flow → verify `user.polar_connected` becomes `true` → disconnect → verify `false`
