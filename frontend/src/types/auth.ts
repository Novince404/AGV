export type UserRole =
  | 'guest'
  | 'personal'
  | 'enterprise_operator'
  | 'enterprise_logistics'
  | 'enterprise_admin'
  | 'platform_admin'

export interface CapabilityGroups {
  dispatch: boolean
  fault: boolean
  map: boolean
  data: boolean
  audit: boolean
  ai: boolean
  platform: boolean
}

export interface SessionUser {
  id: string
  username: string
  display_name: string
  role: UserRole
  active: boolean
  account_status: string
  must_change_password: boolean
  organization_id: string | null
  organization_name: string | null
  capabilities: string[]
  capability_groups: CapabilityGroups
}

export interface AuthPayload {
  authenticated?: boolean
  session_expires_at?: number | null
  capabilities?: string[]
  capability_groups?: Partial<CapabilityGroups>
  user?: Partial<SessionUser>
}

export interface AuthSessionState {
  authenticated: boolean
  session_expires_at: number | null
  capabilities: string[]
  capability_groups: CapabilityGroups
  user: SessionUser
}
