// RoutePass — API response types
// These mirror the Pydantic response schemas from backend/app/api/v1/*.py.
// Keep in sync when the backend schema changes.

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
}

export interface UserMe {
  id: string
  email: string
  created_at: string
  // Connection status
  komoot_connected: boolean
  strava_connected: boolean
  intervals_connected: boolean
  runalyze_connected: boolean
  polar_connected: boolean
  outdooractive_connected: boolean
  // Subscription
  tier: 'free' | 'pro'
  subscription?: Subscription
}

// ── Subscription ──────────────────────────────────────────────────────────────

export interface Subscription {
  id: string
  tier: 'free' | 'pro'
  status: 'active' | 'trialing' | 'past_due' | 'canceled'
  current_period_end: string | null
  stripe_customer_id: string | null
}

// ── Sync ──────────────────────────────────────────────────────────────────────

export type SyncStatus = 'idle' | 'syncing' | 'error' | 'paused'
export type SyncDirection =
  | 'komoot_to_strava'
  | 'strava_to_komoot'
  | 'komoot_to_intervals'
  | 'strava_to_intervals'
  | 'komoot_to_runalyze'

export interface SyncState {
  status: SyncStatus
  last_synced_at: string | null
  last_activity_name: string | null
  last_activity_id: string | null
  error_message: string | null
  daily_strava_calls_used: number
  daily_strava_calls_limit: number
}

// ── Activities ────────────────────────────────────────────────────────────────

export type ActivityStatus = 'synced' | 'pending' | 'failed' | 'skipped'

export interface Activity {
  id: string
  komoot_tour_id: string | null
  strava_activity_id: string | null
  name: string
  sport_type: string
  distance_metres: number | null
  duration_seconds: number | null
  elevation_gain_metres: number | null
  started_at: string | null
  sync_direction: SyncDirection
  status: ActivityStatus
  error_message: string | null
  synced_at: string
  gpx_available: boolean
}

export interface PaginatedActivities {
  items: Activity[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

// ── Rules ─────────────────────────────────────────────────────────────────────

export interface SyncRule {
  id: string
  name: string
  enabled: boolean
  conditions: RuleCondition[]
  action: 'sync' | 'skip' | 'tag'
  action_value: string | null
  created_at: string
}

export interface RuleCondition {
  field: 'sport_type' | 'distance_km' | 'duration_min' | 'name'
  operator: 'eq' | 'neq' | 'gt' | 'lt' | 'contains'
  value: string
}

// ── API Keys ──────────────────────────────────────────────────────────────────

export interface ApiKey {
  id: string
  name: string
  prefix: string        // first 8 chars of the key, for display
  created_at: string
  last_used_at: string | null
  expires_at: string | null
}

export interface ApiKeyCreated extends ApiKey {
  raw_key: string       // returned once at creation, never again
}

// ── Billing ───────────────────────────────────────────────────────────────────

export interface BillingInfo {
  subscription: Subscription | null
  checkout_url: string | null
  portal_url: string | null
}

// ── Generic ───────────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string
}

export interface MessageResponse {
  message: string
}
