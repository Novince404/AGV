import { createMemoryHistory, createRouter, createWebHistory, type RouteMeta, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { CapabilityGroups, UserRole } from '@/types/auth'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    description?: string
    nav?: boolean
    legacy?: boolean
    public?: boolean
    requiresAuth?: boolean
    roles?: UserRole[]
    capabilityGroup?: keyof CapabilityGroups
    standalone?: boolean
  }
}

const placeholder = () => import('@/views/WorkspacePlaceholder.vue')

export const workbenchRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true, title: '登录' }
  },
  {
    path: '/change-password',
    name: 'change-password',
    component: () => import('@/views/ChangePasswordView.vue'),
    meta: {
      title: 'Change password',
      requiresAuth: true,
      standalone: true
    }
  },
  {
    path: '/overview',
    alias: '/',
    name: 'overview',
    component: placeholder,
    meta: {
      nav: true,
      title: '运行总览',
      description: '用统一工作台查看当前运行状态、待处理事项和系统健康度。'
    }
  },
  {
    path: '/dispatch',
    name: 'dispatch',
    component: () => import('@/views/LegacyWorkspace.vue'),
    meta: {
      nav: true,
      legacy: true,
      title: '实时调度',
      description: 'beta.1 调度工作区，后续将按领域逐页迁移。',
      capabilityGroup: 'dispatch'
    }
  },
  {
    path: '/tasks',
    name: 'tasks',
    component: placeholder,
    meta: {
      nav: true,
      title: '任务中心',
      description: '任务队列、执行进度与异常原因将在此处统一呈现。',
      requiresAuth: true
    }
  },
  {
    path: '/agvs',
    name: 'agvs',
    component: placeholder,
    meta: {
      nav: true,
      title: '车辆管理',
      description: '车辆状态、健康信息与控制指令将在此处统一呈现。',
      requiresAuth: true,
      capabilityGroup: 'dispatch'
    }
  },
  {
    path: '/maps',
    name: 'maps',
    component: placeholder,
    meta: {
      nav: true,
      title: '地图与拓扑',
      description: '编辑、校验、预览和发布地图拓扑，避免运行态被直接改写。',
      requiresAuth: true,
      capabilityGroup: 'map'
    }
  },
  {
    path: '/faults',
    name: 'faults',
    component: placeholder,
    meta: {
      nav: true,
      title: '故障中心',
      description: '聚合告警、恢复记录与人工处置流程。',
      requiresAuth: true,
      capabilityGroup: 'fault'
    }
  },
  {
    path: '/reports',
    name: 'reports',
    component: placeholder,
    meta: {
      nav: true,
      title: '报表与审计',
      description: '按数据范围查看运行报表与可追溯审计事件。',
      requiresAuth: true,
      capabilityGroup: 'data'
    }
  },
  {
    path: '/admin/users',
    name: 'admin-users',
    component: placeholder,
    meta: {
      nav: true,
      title: '成员与权限',
      description: '管理组织成员、角色、外部身份绑定和权限审批。',
      requiresAuth: true,
      roles: ['enterprise_admin', 'platform_admin']
    }
  },
  {
    path: '/admin/organizations',
    name: 'admin-organizations',
    component: placeholder,
    meta: {
      nav: true,
      title: '组织治理',
      description: '平台管理员可管理组织申请、隔离边界和跨组织审计。',
      requiresAuth: true,
      roles: ['platform_admin'],
      capabilityGroup: 'platform'
    }
  },
  {
    path: '/settings',
    name: 'settings',
    component: placeholder,
    meta: {
      nav: true,
      title: '个人设置',
      description: '管理个人偏好、语言和登录方式。',
      requiresAuth: true
    }
  },
  { path: '/:pathMatch(.*)*', redirect: '/overview' }
]

export const router = createRouter({
  // Memory history lets route metadata be tested in Node without changing the
  // browser's normal URL behavior.
  history: typeof window === 'undefined' ? createMemoryHistory() : createWebHistory(),
  routes: workbenchRoutes
})

function routeAllowed(meta: RouteMeta, role: UserRole, canUseGroup: (group: keyof CapabilityGroups) => boolean) {
  if (meta.roles && !meta.roles.includes(role)) return false
  if (meta.capabilityGroup && role !== 'guest' && !canUseGroup(meta.capabilityGroup)) return false
  return true
}

router.beforeEach(async to => {
  const auth = useAuthStore()
  if (!auth.initialized) await auth.hydrate()

  if (to.meta.public && auth.isAuthenticated) return { name: 'overview' }
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (auth.isAuthenticated && auth.currentUser.must_change_password && to.name !== 'change-password') {
    return { name: 'change-password' }
  }
  if (!routeAllowed(to.meta, auth.currentRole, auth.canUseGroup)) return { name: 'overview' }
  return true
})
