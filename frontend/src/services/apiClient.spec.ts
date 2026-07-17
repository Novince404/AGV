import { describe, expect, it } from 'vitest'
import { apiClient } from './apiClient'

describe('API client', () => {
  it('routes new endpoints through the stable v1 prefix', () => {
    expect(apiClient.url('/agvs')).toContain('/api/v1/agvs')
    expect(apiClient.url('/auth/me')).toContain('/api/v1/auth/me')
  })
})
