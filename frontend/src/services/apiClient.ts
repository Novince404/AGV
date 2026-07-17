const API_PREFIX = '/api/v1'
const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

export interface ApiProblemPayload {
  type?: string
  title?: string
  status?: number
  detail?: string | Record<string, unknown>
  code?: string
  errors?: Record<string, string[]>
}

export class ApiProblem extends Error {
  status: number
  code: string | null
  requestId: string | null
  details: ApiProblemPayload | null

  constructor(message: string, options: {
    status: number
    code?: string | null
    requestId?: string | null
    details?: ApiProblemPayload | null
  }) {
    super(message)
    this.name = 'ApiProblem'
    this.status = options.status
    this.code = options.code ?? null
    this.requestId = options.requestId ?? null
    this.details = options.details ?? null
  }
}

function configuredApiBase() {
  const configured = String(import.meta.env.VITE_API_BASE ?? '').trim()
  if (configured) return configured.replace(/\/$/, '')

  if (typeof window !== 'undefined') {
    const { origin, protocol, hostname, port } = window.location
    const isDevFrontendPort = ['5173', '5174', '4173', '4174'].includes(port)
    if (origin && /^https?:$/i.test(protocol) && hostname && !isDevFrontendPort) {
      return origin.replace(/\/$/, '')
    }
  }

  return 'http://127.0.0.1:8000'
}

export const apiBase = configuredApiBase()

function stripTrailingSlash(value: string) {
  return value.replace(/\/+$/, '')
}

function apiRoot() {
  const base = stripTrailingSlash(apiBase)
  return base.endsWith(API_PREFIX) ? base : `${base}${API_PREFIX}`
}

function resolveUrl(path: string) {
  if (/^https?:\/\//i.test(path)) return path
  const normalized = path.startsWith('/') ? path : `/${path}`
  if (normalized.startsWith(API_PREFIX)) {
    const base = stripTrailingSlash(apiBase)
    return base.endsWith(API_PREFIX)
      ? `${base}${normalized.slice(API_PREFIX.length)}`
      : `${base}${normalized}`
  }
  return `${apiRoot()}${normalized}`
}

function getCookie(name: string) {
  if (typeof document === 'undefined') return ''
  const encodedName = `${encodeURIComponent(name)}=`
  const value = document.cookie
    .split(';')
    .map(item => item.trim())
    .find(item => item.startsWith(encodedName))
    ?.slice(encodedName.length)
  if (!value) return ''
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function problemMessage(payload: ApiProblemPayload | null, fallback: string) {
  if (!payload) return fallback
  if (typeof payload.detail === 'string' && payload.detail.trim()) return payload.detail
  if (payload.title?.trim()) return payload.title
  return fallback
}

async function readPayload(response: Response) {
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json') && !contentType.includes('application/problem+json')) {
    return null
  }
  try {
    return (await response.json()) as unknown
  } catch {
    return null
  }
}

function withSecurityDefaults(init: RequestInit = {}) {
  const method = String(init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers ?? {})
  if (UNSAFE_METHODS.has(method) && !headers.has('X-CSRF-Token')) {
    const csrfToken = getCookie('agv_csrf')
    if (csrfToken) headers.set('X-CSRF-Token', csrfToken)
  }
  return {
    ...init,
    headers,
    credentials: init.credentials ?? 'include'
  } satisfies RequestInit
}

function belongsToAgvApi(input: RequestInfo | URL) {
  const inputUrl = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
  const base = stripTrailingSlash(apiBase)
  if (inputUrl.startsWith(`${base}/`) || inputUrl === base) return true
  return inputUrl.startsWith('/api/') || inputUrl.startsWith('/auth/') || inputUrl.startsWith('/agv/') || inputUrl.startsWith('/task/') || inputUrl.startsWith('/schedule/') || inputUrl.startsWith('/status/') || inputUrl.startsWith('/fault/')
}

/**
 * Transitional bridge for the beta.1 workspace.  New pages use ApiClient directly;
 * legacy direct fetch calls still receive the same cookie and CSRF protection.
 */
export function installLegacyApiFetchDefaults() {
  if (typeof window === 'undefined' || window.__agvFetchDefaultsInstalled) return

  const nativeFetch = window.fetch.bind(window)
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    if (!belongsToAgvApi(input)) return nativeFetch(input, init)
    return nativeFetch(input, withSecurityDefaults(init))
  }
  window.__agvFetchDefaultsInstalled = true
}

export class ApiClient {
  url(path: string) {
    return resolveUrl(path)
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers ?? {})
    headers.set('Accept', 'application/json')
    if (init.body && !headers.has('Content-Type') && !(init.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json')
    }

    const response = await fetch(resolveUrl(path), withSecurityDefaults({ ...init, headers }))
    const payload = await readPayload(response)
    if (!response.ok) {
      const problem = payload && typeof payload === 'object' ? payload as ApiProblemPayload : null
      throw new ApiProblem(problemMessage(problem, `Request failed (${response.status})`), {
        status: response.status,
        code: problem?.code ?? null,
        requestId: response.headers.get('X-Request-ID'),
        details: problem
      })
    }
    return payload as T
  }

  get<T>(path: string, init: RequestInit = {}) {
    return this.request<T>(path, { ...init, method: 'GET' })
  }

  post<T>(path: string, body?: unknown, init: RequestInit = {}) {
    return this.request<T>(path, {
      ...init,
      method: 'POST',
      body: body === undefined ? undefined : JSON.stringify(body)
    })
  }

  put<T>(path: string, body?: unknown, init: RequestInit = {}) {
    return this.request<T>(path, {
      ...init,
      method: 'PUT',
      body: body === undefined ? undefined : JSON.stringify(body)
    })
  }

  delete<T>(path: string, init: RequestInit = {}) {
    return this.request<T>(path, { ...init, method: 'DELETE' })
  }
}

export const apiClient = new ApiClient()
