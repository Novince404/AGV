<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const errorMessage = ref('')

async function submit() {
  errorMessage.value = ''
  try {
    const session = await auth.login(username.value.trim(), password.value)
    if (session.user.must_change_password) {
      await router.replace({ name: 'change-password' })
      return
    }
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/overview'
    await router.replace(redirect)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '登录失败，请检查账号或服务状态。'
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-card" aria-labelledby="login-title">
      <p class="login-kicker">AGV DISPATCH · ENTERPRISE TRIAL</p>
      <h1 id="login-title">登录工作台</h1>
      <p class="login-description">登录状态由安全 Cookie 保持，浏览器不会保存可复用的会话令牌。</p>

      <form class="login-form" @submit.prevent="submit">
        <label>
          <span>账号</span>
          <input v-model="username" autocomplete="username" required :disabled="auth.loading" />
        </label>
        <label>
          <span>密码</span>
          <input v-model="password" type="password" autocomplete="current-password" required :disabled="auth.loading" />
        </label>
        <p v-if="errorMessage" class="login-error" role="alert">{{ errorMessage }}</p>
        <button class="login-submit" type="submit" :disabled="auth.loading">
          {{ auth.loading ? '正在登录…' : '登录' }}
        </button>
      </form>

      <RouterLink class="login-guest-link" to="/overview">先以访客方式查看总览</RouterLink>
    </section>
  </main>
</template>

<style scoped>
.login-page { display: grid; min-height: 100vh; place-items: center; padding: var(--agv-space-5); background: radial-gradient(circle at 20% 10%, rgba(67, 182, 255, .18), transparent 32%), var(--agv-bg-canvas); }.login-card { width: min(100%, 430px); padding: 42px; border: 1px solid var(--agv-border); border-radius: var(--agv-radius-lg); background: rgba(13, 27, 45, .92); box-shadow: var(--agv-shadow-lg); }.login-kicker { margin: 0 0 10px; color: var(--agv-brand); font-size: 12px; letter-spacing: .1em; }.login-card h1 { margin: 0; font-size: 28px; }.login-description { margin: 12px 0 28px; color: var(--agv-text-secondary); line-height: 1.6; }.login-form { display: grid; gap: var(--agv-space-4); }.login-form label { display: grid; gap: 7px; color: var(--agv-text-secondary); font-size: 14px; }.login-form input { width: 100%; padding: 11px 12px; border: 1px solid var(--agv-border); border-radius: var(--agv-radius-sm); outline: none; color: var(--agv-text-primary); background: var(--agv-bg-canvas); }.login-form input:focus { border-color: var(--agv-brand); box-shadow: 0 0 0 3px rgba(67, 182, 255, .15); }.login-submit { padding: 12px 16px; border: 0; border-radius: var(--agv-radius-sm); color: #06111d; background: var(--agv-brand); font-weight: 700; }.login-submit:disabled { cursor: wait; opacity: .65; }.login-error { margin: 0; color: var(--agv-danger); font-size: 14px; }.login-guest-link { display: inline-block; margin-top: 22px; color: var(--agv-brand); font-size: 14px; }
</style>
