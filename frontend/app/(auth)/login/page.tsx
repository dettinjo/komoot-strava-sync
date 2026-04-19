'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui'
import { Button } from '@/components/ui'
import { Input, FormField } from '@/components/ui'
import { Alert } from '@/components/ui'
import { apiPost } from '@/lib/api'
import { useAuthStore } from '@/store/auth'
import type { TokenResponse, UserMe } from '@/types/api'
import { useState } from 'react'

const schema = z.object({
  email:    z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})

type FormData = z.infer<typeof schema>

export default function LoginPage() {
  const router = useRouter()
  const login  = useAuthStore((s) => s.login)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormData) {
    setServerError(null)
    try {
      // FastAPI OAuth2 password flow expects form-encoded body
      const form = new FormData()
      form.append('username', data.email)
      form.append('password', data.password)

      const tokenRes = await fetch('/api/v1/auth/login', {
        method: 'POST',
        body: new URLSearchParams({ username: data.email, password: data.password }),
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      if (!tokenRes.ok) {
        const err = await tokenRes.json()
        throw new Error(err.detail ?? 'Login failed')
      }
      const { access_token } = (await tokenRes.json()) as TokenResponse

      const me = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${access_token}` },
      }).then((r) => r.json() as Promise<UserMe>)

      login(access_token, me)
      router.push('/dashboard')
    } catch (err) {
      setServerError(err instanceof Error ? err.message : 'Login failed. Try again.')
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sign in to RoutePass</CardTitle>
      </CardHeader>
      <CardContent>
        {serverError && (
          <Alert variant="error" className="mb-6">
            {serverError}
          </Alert>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <FormField label="Email" htmlFor="email" required error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              error={!!errors.email}
              {...register('email')}
            />
          </FormField>

          <FormField label="Password" htmlFor="password" required error={errors.password?.message}>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              error={!!errors.password}
              {...register('password')}
            />
          </FormField>

          <Button type="submit" className="w-full" loading={isSubmitting}>
            Sign in
          </Button>
        </form>
      </CardContent>
      <CardFooter className="justify-center">
        <p className="text-body-sm text-text-secondary">
          No account?{' '}
          <Link href="/register" className="text-primary hover:underline">
            Sign up free
          </Link>
        </p>
      </CardFooter>
    </Card>
  )
}
