<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { workbenchRoutes } from '@/router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const navigation = computed(() =>
  workbenchRoutes.filter(item => {
    if (!item.meta?.nav || item.meta.legacy) return Boolean(item.meta?.legacy && auth.canUseGroup('dispatch'))
    if (item.meta?.roles && !item.meta.roles.includes(auth.currentRole)) return false
    if (item.meta?.capabilityGroup && !auth.canUseGroup(item.meta.capabilityGroup)) return false
    return !item.meta?.requiresAuth || auth.isAuthenticated
  })
)

const pageTitle = computed(() => String(route.meta.title ?? 'AGV 工作台'))
const accountLabel = computed(() => auth.isAuthenticated ? auth.displayName : '访客模式')

async function signOut() {
  await auth.logout()
  await router.push({ name: 'login' })
}
</script>

<template>
  <div class="app-shell">
    <aside class="app-sidebar" aria-label="主导航">
      <RouterLink class="app-brand" to="/overview">
        <span class="app-brand-mark">A</span>
        <span>
          <strong>AGV Dispatch</strong>
          <small>Enterprise Trial</small>
        </span>
      </RouterLink>

      <nav class="app-nav">
        <RouterLink
          v-for="item in navigation"
          :key="String(item.name)"
          :to="item.path"
          class="app-nav-link"
          active-class="is-active"
        >
          {{ item.meta?.title }}
        </RouterLink>
      </nav>

      <div class="app-account">
        <span class="app-account-name">{{ accountLabel }}</span>
        <small>{{ auth.currentRole }}</small>
        <button v-if="auth.isAuthenticated" type="button" class="app-text-button" @click="signOut">
          退出登录
        </button>
        <RouterLink v-else to="/login" class="app-text-button">登录</RouterLink>
      </div>
    </aside>

    <main class="app-main">
      <header class="app-header">
        <div>
          <p class="app-eyebrow">AGV v3.0.0 企业试用版</p>
          <h1>{{ pageTitle }}</h1>
        </div>
        <span class="app-environment">{{ auth.isAuthenticated ? '已连接' : '未登录' }}</span>
      </header>
      <section class="app-content">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<style scoped>
.app-shell { display: grid; grid-template-columns: var(--agv-sidebar-width) minmax(0, 1fr); min-height: 100vh; }
.app-sidebar { display: flex; flex-direction: column; gap: var(--agv-space-5); padding: var(--agv-space-5) var(--agv-space-3); background: var(--agv-bg-surface); border-right: 1px solid var(--agv-border); }
.app-brand { display: flex; align-items: center; gap: var(--agv-space-3); padding: 0 var(--agv-space-2); text-decoration: none; }
.app-brand-mark { display: grid; width: 34px; height: 34px; place-items: center; border-radius: 10px; color: #06111d; background: var(--agv-brand); font-weight: 800; }
.app-brand strong, .app-brand small { display: block; }.app-brand small { color: var(--agv-text-muted); font-size: 11px; letter-spacing: .06em; text-transform: uppercase; }
.app-nav { display: grid; gap: var(--agv-space-1); }.app-nav-link { padding: 10px 12px; border-radius: var(--agv-radius-sm); color: var(--agv-text-secondary); text-decoration: none; }.app-nav-link:hover { background: var(--agv-bg-hover); color: var(--agv-text-primary); }.app-nav-link.is-active { color: var(--agv-text-primary); background: color-mix(in srgb, var(--agv-brand) 18%, transparent); box-shadow: inset 2px 0 0 var(--agv-brand); }
.app-account { display: grid; gap: 4px; margin-top: auto; padding: var(--agv-space-3); border: 1px solid var(--agv-border); border-radius: var(--agv-radius-md); }.app-account-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.app-account small { color: var(--agv-text-muted); }.app-text-button { padding: 0; border: 0; color: var(--agv-brand); background: transparent; text-align: left; text-decoration: none; font-size: 13px; }
.app-main { min-width: 0; }.app-header { display: flex; align-items: center; justify-content: space-between; gap: var(--agv-space-4); min-height: 96px; padding: var(--agv-space-5) var(--agv-space-6); border-bottom: 1px solid var(--agv-border); background: rgba(13, 27, 45, .78); }.app-header h1, .app-header p { margin: 0; }.app-header h1 { font-size: 24px; }.app-eyebrow { color: var(--agv-text-muted); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; }.app-environment { padding: 6px 10px; border: 1px solid var(--agv-border-strong); border-radius: 999px; color: var(--agv-brand); font-size: 13px; }.app-content { padding: var(--agv-space-6); }
@media (max-width: 900px) { .app-shell { grid-template-columns: 1fr; }.app-sidebar { position: sticky; top: 0; z-index: 3; flex-direction: row; align-items: center; overflow-x: auto; padding: var(--agv-space-2); border-right: 0; border-bottom: 1px solid var(--agv-border); }.app-brand { min-width: max-content; }.app-nav { display: flex; }.app-nav-link { white-space: nowrap; }.app-account { display: none; }.app-header { min-height: 78px; padding: var(--agv-space-4); }.app-content { padding: var(--agv-space-4); } }
</style>
