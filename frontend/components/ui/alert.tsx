import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

// DESIGN.md §Alert spec.
// Border-left accent, semantic background, icon left-aligned.

const alertVariants = cva(
  'relative flex gap-3 rounded-md border-l-[3px] p-4',
  {
    variants: {
      variant: {
        success: 'bg-success-light border-success text-success',
        warning: 'bg-warning-light border-warning text-warning',
        error:   'bg-error-light border-error text-error',
        info:    'bg-info-light border-info text-info',
      },
    },
    defaultVariants: { variant: 'info' },
  },
)

const ICONS = {
  success: CheckCircle2,
  warning: AlertTriangle,
  error:   XCircle,
  info:    Info,
} as const

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  title?: string
}

function Alert({ className, variant = 'info', title, children, ...props }: AlertProps) {
  const Icon = ICONS[variant ?? 'info']

  return (
    <div role="alert" className={cn(alertVariants({ variant }), className)} {...props}>
      <Icon className="h-4 w-4 mt-0.5 flex-shrink-0" aria-hidden />
      <div className="flex-1 min-w-0">
        {title && (
          <p className="text-body-sm font-semibold mb-0.5">{title}</p>
        )}
        <div className="text-body-sm text-text-primary">{children}</div>
      </div>
    </div>
  )
}

export { Alert, alertVariants }
