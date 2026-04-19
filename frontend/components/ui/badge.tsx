import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

// DESIGN.md §Badge / Status Pill spec.
// Use semantic variants — never hardcode colors in pages.

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full px-2 font-label text-label leading-none h-5 whitespace-nowrap',
  {
    variants: {
      variant: {
        connected:  'bg-success-light text-success',
        syncing:    'bg-info-light text-info',
        error:      'bg-error-light text-error',
        paused:     'bg-warning-light text-warning',
        free:       'bg-bg text-text-secondary border border-border',
        pro:        'bg-primary-light text-primary',
        neutral:    'bg-surface-raised text-text-secondary border border-border',
        pending:    'bg-warning-light text-warning',
        skipped:    'bg-bg text-text-disabled border border-border',
      },
    },
    defaultVariants: {
      variant: 'neutral',
    },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

// Status dot — animated for active/syncing states
const statusDotVariants = cva('inline-block w-2 h-2 rounded-full flex-shrink-0', {
  variants: {
    status: {
      active:   'bg-success animate-pulse-slow',
      syncing:  'bg-info animate-pulse-slow',
      error:    'bg-error',
      paused:   'bg-warning',
      inactive: 'bg-border-strong',
    },
  },
  defaultVariants: { status: 'inactive' },
})

export interface StatusDotProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof statusDotVariants> {}

function StatusDot({ className, status, ...props }: StatusDotProps) {
  return <span className={cn(statusDotVariants({ status }), className)} {...props} />
}

export { Badge, badgeVariants, StatusDot }
