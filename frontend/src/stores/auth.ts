import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { apiClient, ApiProblem } from '@/services/apiClient'
import type { AuthPayload, AuthSessionState, CapabilityGroups, SessionUser, UserRole } from '@/types/auth'

const EMPTY_CAPABILITIES: CapabilityGroups = {
  dispatch: false,
  fault: false,
  map: false,
  data: false,
  audit: false,
  ai: false,
  platform: false
}

function guestUser(): SessionUser {
  return {
    id: 'guest',
    username: 'guest',
    display_name: '访客',
    role: 'guest',
    active: true,
    account_status: 'guest',
    must_change_password: false,
    organization_id: null,
    organization_name: null,
    capabilities: ['dashboard.view'],
    capability_groups: { ...EMPTY_CAPABILITIES }
  }
}

function guestState(): AuthSessionState {
  return {
    authenticated: false,
    session_expires_at: null,
    capabilities: ['dashboard.view'],
    capability_groups: { ...EMPTY_CAPABILITIES },
    user: guestUser()
  }
}

function normalizeGroups(value: Partial<CapabilityGroups> | undefined): CapabilityGroups {
  return {
    dispatch: Boolean(value?.dispatch),
    fault: Boolean(value?.fault),
    map: Boolean(value?.map),
    data: Boolean(value?.data),
    audit: Boolean(value?.audit),
    ai: Boolean(value?.ai),
    platform: Boolean(value?.platform)
  }
}

function normalizeRole(value: unknown): UserRole {
  const role = String(value ?? 'guest')
  const roles: UserRole[] = ['guest', 'personal', 'enterprise_operator', 'enterprise_logistics', 'enterprise_admin', 'platform_admin']
  return roles.includes(role as UserRole) ? role as UserRole : 'guest'
}

function normalizeSession(payload: AuthPayload | null | undefined): AuthSessionState {
  if (!payload?.authenticated || !payload.user) return guestState()

  const capabilities = Array.isArray(payload.capabilities)
    ? payload.capabilities.map(item => String(item))
    : Array.isArray(payload.user.capabilities)
      ? payload.user.capabilities.map(item => String(item))
      : []
  const groups = normalizeGroups(payload.user.capability_groups ?? payload.capability_groups)
  const rawUser = payload.user

  return {
    authenticated: true,
    session_expires_at: Number.isFinite(Number(payload.session_expires_at))
      ? Number(payload.session_expires_at)
      : null,
    capabilities,
    capability_groups: groups,
    user: {
      id: String(rawUser.id ?? ''),
      username: String(rawUser.username ?? ''),
      display_name: String(rawUser.display_name ?? rawUser.username ?? ''),
      role: normalizeRole(rawUser.role),
      active: rawUser.active !== false,
      account_status: String(rawUser.account_status ?? 'approved'),
      must_change_password: rawUser.must_change_password === true,
      organization_id: rawUser.organization_id == null ? null : String(rawUser.organization_id),
      organization_name: rawUser.organization_name == null ? null : String(rawUser.organization_name),
      capabilities,
      capability_groups: groups
    }
  }
}

export const useAuthStore = defineStore('auth', () => {
  const session = ref<AuthSessionState>(guestState())
  const initialized = ref(false)
  const loading = ref(false)
  const lastError = ref<string | null>(null)

  const isAuthenticated = computed(() => session.value.authenticated)
  const currentUser = computed(() => session.value.user)
  const currentRole = computed(() => session.value.user.role)
  const displayName = computed(() => session.value.user.display_name || session.value.user.username || '访客')

  function apply(payload: AuthPayload | null | undefined) {
    session.value = normalizeSession(payload)
    return session.value
  }

  function reset() {
    lastError.value = null
    return apply(null)
  }

  function canUseGroup(group: keyof CapabilityGroups) {
    return Boolean(session.value.capability_groups[group])
  }

  async function hydrate({ force = false } = {}) {
    if (initialized.value && !force) return session.value
    loading.value = true
    lastError.value = null
    try {
      const payload = await apiClient.get<AuthPayload>('/auth/me')
      return apply(payload)
    } catch (error) {
      if (!(error instanceof ApiProblem) || ![401, 403].includes(error.status)) {
        lastError.value = error instanceof Error ? error.message : '无法读取登录状态'
      }
      return reset()
    } finally {
      initialized.value = true
      loading.value = false
    }
  }

  async function login(username: string, password: string) {
    loading.value = true
    lastError.value = null
    try {
      const payload = await apiClient.post<AuthPayload>('/auth/login', { username, password })
      initialized.value = true
      return apply(payload)
    } catch (error) {
      lastError.value = error instanceof Error ? error.message : '登录失败'
      throw error
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    loading.value = true
    try {
      await apiClient.post('/auth/logout')
    } finally {
      initialized.value = true
      reset()
      loading.value = false
    }
  }

  async function changePassword(currentPassword: string, newPassword: string) {
    loading.value = true
    lastError.value = null
    try {
      const payload = await apiClient.post<AuthPayload>('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      })
      initialized.value = true
      return apply(payload)
    } catch (error) {
      lastError.value = error instanceof Error ? error.message : 'Unable to change password'
      throw error
    } finally {
      loading.value = false
    }
  }

  return {
    session,
    initialized,
    loading,
    lastError,
    isAuthenticated,
    currentUser,
    currentRole,
    displayName,
    apply,
    reset,
    canUseGroup,
    hydrate,
    login,
    changePassword,
    logout
  }
})
