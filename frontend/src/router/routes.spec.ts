import { describe, expect, it } from 'vitest'
import { workbenchRoutes } from './index'

describe('v3 workbench routes', () => {
  it('exposes every planned desktop workspace route', () => {
    const paths = new Set(workbenchRoutes.map(route => route.path))
    for (const path of [
      '/login',
      '/change-password',
      '/overview',
      '/dispatch',
      '/tasks',
      '/agvs',
      '/maps',
      '/faults',
      '/reports',
      '/admin/users',
      '/admin/organizations',
      '/settings'
    ]) {
      expect(paths).toContain(path)
    }
  })
})
