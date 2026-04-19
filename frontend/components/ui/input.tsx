import * as React from 'react'
import { cn } from '@/lib/utils'

// DESIGN.md §Input spec.
// Always pair with <Label> and optionally <FieldError> — never render standalone.

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        'flex h-9 w-full rounded-md border bg-surface px-3 text-body text-text-primary',
        'placeholder:text-text-disabled',
        'transition-colors duration-150',
        'focus-visible:outline-none focus-visible:border-accent focus-visible:shadow-inner',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        error
          ? 'border-error focus-visible:border-error'
          : 'border-border focus-visible:border-accent',
        className,
      )}
      {...props}
    />
  ),
)
Input.displayName = 'Input'

// Textarea follows the same token set as Input
export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        'flex min-h-[80px] w-full rounded-md border bg-surface px-3 py-2 text-body text-text-primary',
        'placeholder:text-text-disabled',
        'transition-colors duration-150 resize-vertical',
        'focus-visible:outline-none focus-visible:border-accent focus-visible:shadow-inner',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        error
          ? 'border-error focus-visible:border-error'
          : 'border-border focus-visible:border-accent',
        className,
      )}
      {...props}
    />
  ),
)
Textarea.displayName = 'Textarea'

// Label — always use instead of raw <label>
export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean
}

const Label = React.forwardRef<HTMLLabelElement, LabelProps>(
  ({ className, required, children, ...props }, ref) => (
    <label
      ref={ref}
      className={cn('block text-label font-medium text-text-secondary mb-1.5', className)}
      {...props}
    >
      {children}
      {required && <span className="text-error ml-0.5" aria-hidden>*</span>}
    </label>
  ),
)
Label.displayName = 'Label'

// Field error message — rendered below the input
function FieldError({ message, id }: { message?: string; id?: string }) {
  if (!message) return null
  return (
    <p id={id} role="alert" className="mt-1 text-caption text-error">
      {message}
    </p>
  )
}

// Helper text — rendered below the input (non-error)
function FieldHint({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-1 text-caption text-text-secondary">{children}</p>
  )
}

// FormField — convenience wrapper: label + input + optional error
interface FormFieldProps {
  label: string
  htmlFor: string
  required?: boolean
  error?: string
  hint?: string
  children: React.ReactNode
  className?: string
}

function FormField({ label, htmlFor, required, error, hint, children, className }: FormFieldProps) {
  const errorId = error ? `${htmlFor}-error` : undefined
  return (
    <div className={cn('space-y-0', className)}>
      <Label htmlFor={htmlFor} required={required}>
        {label}
      </Label>
      {children}
      {hint && !error && <FieldHint>{hint}</FieldHint>}
      {error && <FieldError message={error} id={errorId} />}
    </div>
  )
}

export { Input, Textarea, Label, FieldError, FieldHint, FormField }
