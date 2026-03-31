import { computed, ref } from 'vue'

function buildGuestState() {
  return {
    authenticated: false,
    session_expires_at: null,
    capabilities: ['dashboard.view'],
    capability_groups: {
      dispatch: false,
      fault: false,
      map: false,
      data: false,
      audit: false,
      ai: false,
      platform: false
    },
    user: {
      id: 'guest',
      username: 'guest',
      display_name: 'Guest',
      role: 'guest',
      active: true,
      builtin: true,
      account_status: 'guest',
      organization_id: null,
      organization_name: null,
      suspension_reason: null,
      suspension_note: null,
      suspended_at: null,
      suspended_until: null,
      suspended_by: null,
      deactivated_at: null,
      deactivated_by: null,
      created_at: null,
      last_login_at: null,
      governance_updated_at: null,
      enterprise_application: null,
      capabilities: ['dashboard.view'],
      capability_groups: {
        dispatch: false,
        fault: false,
        map: false,
        data: false,
        audit: false,
        ai: false,
        platform: false
      }
    }
  }
}

function normalizeAuthPayload(payload) {
  if (!payload?.authenticated || !payload?.user) {
    return buildGuestState()
  }

  return {
    authenticated: true,
    session_token: typeof payload.session_token === 'string' ? payload.session_token : '',
    session_expires_at: Number.isFinite(Number(payload.session_expires_at))
      ? Number(payload.session_expires_at)
      : null,
    capabilities: Array.isArray(payload.capabilities) ? payload.capabilities.map(item => String(item)) : [],
    capability_groups:
      payload.capability_groups && typeof payload.capability_groups === 'object'
        ? {
            dispatch: Boolean(payload.capability_groups.dispatch),
            fault: Boolean(payload.capability_groups.fault),
            map: Boolean(payload.capability_groups.map),
            data: Boolean(payload.capability_groups.data),
            audit: Boolean(payload.capability_groups.audit),
            ai: Boolean(payload.capability_groups.ai),
            platform: Boolean(payload.capability_groups.platform)
          }
        : buildGuestState().capability_groups,
    user: {
      id: String(payload.user.id ?? ''),
      username: String(payload.user.username ?? ''),
      display_name: String(payload.user.display_name ?? payload.user.username ?? ''),
      role: String(payload.user.role ?? 'guest'),
      active: payload.user.active !== false,
      builtin: payload.user.builtin !== false,
      account_status: String(payload.user.account_status ?? 'approved'),
      organization_id: payload.user.organization_id == null ? null : String(payload.user.organization_id),
      organization_name: payload.user.organization_name == null ? null : String(payload.user.organization_name),
      suspension_reason: payload.user.suspension_reason == null ? null : String(payload.user.suspension_reason),
      suspension_note: payload.user.suspension_note == null ? null : String(payload.user.suspension_note),
      suspended_at: payload.user.suspended_at == null ? null : String(payload.user.suspended_at),
      suspended_until: payload.user.suspended_until == null ? null : String(payload.user.suspended_until),
      suspended_by: payload.user.suspended_by == null ? null : String(payload.user.suspended_by),
      deactivated_at: payload.user.deactivated_at == null ? null : String(payload.user.deactivated_at),
      deactivated_by: payload.user.deactivated_by == null ? null : String(payload.user.deactivated_by),
      created_at: payload.user.created_at == null ? null : String(payload.user.created_at),
      last_login_at: payload.user.last_login_at == null ? null : String(payload.user.last_login_at),
      governance_updated_at: payload.user.governance_updated_at == null ? null : String(payload.user.governance_updated_at),
      enterprise_application:
        payload.user.enterprise_application && typeof payload.user.enterprise_application === 'object'
          ? {
              id: Number.isFinite(Number(payload.user.enterprise_application.id))
                ? Number(payload.user.enterprise_application.id)
                : null,
              company_name: String(payload.user.enterprise_application.company_name ?? ''),
              contact_name: String(payload.user.enterprise_application.contact_name ?? ''),
              contact_email: String(payload.user.enterprise_application.contact_email ?? ''),
              username: String(payload.user.enterprise_application.username ?? ''),
              user_id: String(payload.user.enterprise_application.user_id ?? ''),
              status: String(payload.user.enterprise_application.status ?? ''),
              submitted_at: String(payload.user.enterprise_application.submitted_at ?? ''),
              reviewed_at: String(payload.user.enterprise_application.reviewed_at ?? ''),
              reviewed_by: String(payload.user.enterprise_application.reviewed_by ?? ''),
              review_note: String(payload.user.enterprise_application.review_note ?? ''),
              organization_id: payload.user.enterprise_application.organization_id == null
                ? null
                : String(payload.user.enterprise_application.organization_id)
            }
          : null,
      capabilities: Array.isArray(payload.user.capabilities)
        ? payload.user.capabilities.map(item => String(item))
        : Array.isArray(payload.capabilities)
          ? payload.capabilities.map(item => String(item))
          : [],
      capability_groups:
        payload.user.capability_groups && typeof payload.user.capability_groups === 'object'
          ? {
              dispatch: Boolean(payload.user.capability_groups.dispatch),
              fault: Boolean(payload.user.capability_groups.fault),
              map: Boolean(payload.user.capability_groups.map),
              data: Boolean(payload.user.capability_groups.data),
              audit: Boolean(payload.user.capability_groups.audit),
              ai: Boolean(payload.user.capability_groups.ai),
              platform: Boolean(payload.user.capability_groups.platform)
            }
          : payload.capability_groups && typeof payload.capability_groups === 'object'
            ? {
                dispatch: Boolean(payload.capability_groups.dispatch),
                fault: Boolean(payload.capability_groups.fault),
                map: Boolean(payload.capability_groups.map),
                data: Boolean(payload.capability_groups.data),
                audit: Boolean(payload.capability_groups.audit),
                ai: Boolean(payload.capability_groups.ai),
                platform: Boolean(payload.capability_groups.platform)
              }
            : buildGuestState().capability_groups
    }
  }
}

function readStoredToken(storageKey) {
  if (typeof window === 'undefined') return ''
  try {
    return String(window.localStorage.getItem(storageKey) ?? '')
  } catch {
    return ''
  }
}

function writeStoredToken(storageKey, token) {
  if (typeof window === 'undefined') return
  try {
    if (token) {
      window.localStorage.setItem(storageKey, token)
    } else {
      window.localStorage.removeItem(storageKey)
    }
  } catch {
    // Ignore localStorage failures and keep in-memory auth usable.
  }
}

export function useAuthSession(options) {
  const {
    API_BASE,
    createApiError,
    storageKey = 'agv_auth_session_token'
  } = options

  const authPanelOpen = ref(false)
  const authLoading = ref(false)
  const authInitialized = ref(false)
  const authUsername = ref('')
  const authPassword = ref('')
  const sessionToken = ref(readStoredToken(storageKey))
  const authState = ref(buildGuestState())
  const authLastFetchedAt = ref('')
  const demoAccounts = [
    { role: 'personal', username: 'personal_demo', password: 'personal123' },
    { role: 'enterprise_admin', username: 'enterprise_demo', password: 'enterprise123' },
    { role: 'enterprise_operator', username: 'enterprise_operator_demo', password: 'operator123' },
    { role: 'enterprise_logistics', username: 'enterprise_logistics_demo', password: 'logistics123' },
    { role: 'platform_admin', username: 'admin_demo', password: 'admin123' }
  ]

  function applyAuthPayload(payload) {
    const normalized = normalizeAuthPayload(payload)
    authState.value = normalized
    sessionToken.value = normalized.authenticated ? normalized.session_token || sessionToken.value : ''
    writeStoredToken(storageKey, sessionToken.value)
    return normalized
  }

  function buildAuthHeaders(baseHeaders = {}) {
    const headers = { ...baseHeaders }
    if (sessionToken.value) {
      headers.Authorization = `Bearer ${sessionToken.value}`
    }
    return headers
  }

  async function readJsonResponse(response) {
    try {
      return await response.json()
    } catch {
      return null
    }
  }

  async function fetchAuthMe({ silent = true } = {}) {
    authLoading.value = true
    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: buildAuthHeaders()
      })
      const data = await readJsonResponse(response)
      if (!response.ok) {
        throw createApiError(data, 'Auth status request failed')
      }
      authLastFetchedAt.value = new Date().toISOString()
      return applyAuthPayload(data)
    } catch (error) {
      applyAuthPayload(null)
      if (!silent) throw error
      return authState.value
    } finally {
      authInitialized.value = true
      authLoading.value = false
    }
  }

  async function login(username = authUsername.value, password = authPassword.value) {
    authLoading.value = true
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: String(username ?? ''),
          password: String(password ?? '')
        })
      })
      const data = await readJsonResponse(response)
      if (!response.ok) {
        const error = createApiError(data, 'Login failed')
        error.detail = data?.detail ?? null
        throw error
      }
      authPassword.value = ''
      authLastFetchedAt.value = new Date().toISOString()
      return applyAuthPayload(data)
    } finally {
      authInitialized.value = true
      authLoading.value = false
    }
  }

  async function registerPersonal({
    username,
    password,
    display_name
  }) {
    authLoading.value = true
    try {
      const response = await fetch(`${API_BASE}/auth/register-personal`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: String(username ?? ''),
          password: String(password ?? ''),
          display_name: display_name == null ? null : String(display_name)
        })
      })
      const data = await readJsonResponse(response)
      if (!response.ok) {
        throw createApiError(data, 'Personal registration failed')
      }
      authPassword.value = ''
      authLastFetchedAt.value = new Date().toISOString()
      return applyAuthPayload(data)
    } finally {
      authInitialized.value = true
      authLoading.value = false
    }
  }

  async function logout() {
    authLoading.value = true
    try {
      const response = await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: buildAuthHeaders()
      })
      const data = await readJsonResponse(response)
      if (!response.ok) {
        throw createApiError(data, 'Logout failed')
      }
      authPassword.value = ''
      authLastFetchedAt.value = new Date().toISOString()
      return applyAuthPayload(data)
    } finally {
      authInitialized.value = true
      authLoading.value = false
    }
  }

  function fillDemoAccount(account) {
    authUsername.value = String(account?.username ?? '')
    authPassword.value = String(account?.password ?? '')
    authPanelOpen.value = true
  }

  const isAuthenticated = computed(() => Boolean(authState.value?.authenticated))
  const currentUser = computed(() => authState.value?.user ?? buildGuestState().user)
  const currentRole = computed(() => currentUser.value?.role || 'guest')
  const currentDisplayName = computed(
    () => currentUser.value?.display_name || currentUser.value?.username || 'Guest'
  )
  const currentAccountStatus = computed(() => currentUser.value?.account_status || 'approved')
  const currentOrganizationName = computed(() => currentUser.value?.organization_name || '')
  const currentEnterpriseApplication = computed(() => currentUser.value?.enterprise_application || null)
  const currentCapabilities = computed(() => authState.value?.capabilities ?? [])
  const currentCapabilityGroups = computed(() => authState.value?.capability_groups ?? buildGuestState().capability_groups)

  return {
    authPanelOpen,
    authLoading,
    authInitialized,
    authUsername,
    authPassword,
    authState,
    authLastFetchedAt,
    sessionToken,
    demoAccounts,
    isAuthenticated,
    currentUser,
    currentRole,
    currentDisplayName,
    currentAccountStatus,
    currentOrganizationName,
    currentEnterpriseApplication,
    currentCapabilities,
    currentCapabilityGroups,
    buildAuthHeaders,
    applyAuthPayload,
    fetchAuthMe,
    login,
    registerPersonal,
    logout,
    fillDemoAccount
  }
}
