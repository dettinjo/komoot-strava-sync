// RoutePass — Tailwind CSS configuration
// All values map 1:1 to the tokens in DESIGN.md.
// Never add one-off colors inline — extend this config instead.

import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'], // reserved — dark mode ships later
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    // ── Override (not extend) the default container so it centers automatically
    container: {
      center: true,
      padding: '2rem',
      screens: { '2xl': '1400px' },
    },

    extend: {
      // ── Brand Colors ────────────────────────────────────────────────────────
      colors: {
        // Primary — forest green
        primary: {
          DEFAULT: '#16533A',
          hover:   '#124430',
          light:   '#E8F5F0',
        },
        // Accent — trail mint
        accent: {
          DEFAULT: '#3ECFAF',
          hover:   '#2EB89A',
        },
        // Backgrounds
        bg:      '#F5F7F5',
        surface: {
          DEFAULT: '#FFFFFF',
          raised:  '#FAFAFA',
        },
        // Borders
        border: {
          DEFAULT: '#E2E8E4',
          strong:  '#C8D4CE',
        },
        // Text
        text: {
          primary:   '#111827',
          secondary: '#6B7280',
          disabled:  '#9CA3AF',
          inverse:   '#FFFFFF',
        },
        // Semantic
        success: {
          DEFAULT: '#059669',
          light:   '#ECFDF5',
        },
        warning: {
          DEFAULT: '#D97706',
          light:   '#FFFBEB',
        },
        error: {
          DEFAULT: '#DC2626',
          light:   '#FEF2F2',
        },
        info: {
          DEFAULT: '#2563EB',
          light:   '#EFF6FF',
        },
      },

      // ── Border Radius ────────────────────────────────────────────────────────
      // Matches DESIGN.md exactly. Never use raw px values in components.
      borderRadius: {
        sm:   '4px',
        md:   '8px',
        lg:   '12px',
        xl:   '16px',
        full: '9999px',
      },

      // ── Box Shadows ──────────────────────────────────────────────────────────
      boxShadow: {
        sm:    '0 1px 2px rgba(0,0,0,0.06)',
        md:    '0 4px 12px rgba(0,0,0,0.08)',
        lg:    '0 8px 24px rgba(0,0,0,0.10)',
        inner: 'inset 0 2px 4px rgba(0,0,0,0.04)',
      },

      // ── Typography ───────────────────────────────────────────────────────────
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains-mono)', 'monospace'],
      },
      fontSize: {
        // DESIGN.md type scale
        'display':    ['36px', { lineHeight: '1.2',  fontWeight: '700' }],
        'heading-xl': ['30px', { lineHeight: '1.25', fontWeight: '700' }],
        'heading-lg': ['24px', { lineHeight: '1.3',  fontWeight: '600' }],
        'heading-md': ['20px', { lineHeight: '1.35', fontWeight: '600' }],
        'heading-sm': ['16px', { lineHeight: '1.4',  fontWeight: '600' }],
        'body-lg':    ['16px', { lineHeight: '1.6',  fontWeight: '400' }],
        'body':       ['14px', { lineHeight: '1.6',  fontWeight: '400' }],
        'body-sm':    ['13px', { lineHeight: '1.5',  fontWeight: '400' }],
        'caption':    ['12px', { lineHeight: '1.4',  fontWeight: '400' }],
        'label':      ['12px', { lineHeight: '1.0',  fontWeight: '500' }],
        'mono':       ['13px', { lineHeight: '1.5',  fontWeight: '400' }],
      },

      // ── Spacing ──────────────────────────────────────────────────────────────
      // 4px base unit. All values from DESIGN.md.
      spacing: {
        'space-1':  '4px',
        'space-2':  '8px',
        'space-3':  '12px',
        'space-4':  '16px',
        'space-5':  '20px',
        'space-6':  '24px',
        'space-8':  '32px',
        'space-10': '40px',
        'space-12': '48px',
        'space-16': '64px',
      },

      // ── Animations ───────────────────────────────────────────────────────────
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
        'slide-in-right': {
          '0%':   { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)',    opacity: '1' },
        },
        'scale-in': {
          '0%':   { transform: 'scale(0.97)', opacity: '0' },
          '100%': { transform: 'scale(1)',    opacity: '1' },
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.4' },
        },
      },
      animation: {
        shimmer:          'shimmer 1.5s ease-in-out infinite',
        'slide-in-right': 'slide-in-right 200ms ease-out',
        'scale-in':       'scale-in 200ms ease-out',
        'pulse-slow':     'pulse 2s infinite',
      },
    },
  },
  plugins: [],
}

export default config
