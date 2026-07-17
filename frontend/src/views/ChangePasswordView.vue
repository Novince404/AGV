<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const errorMessage = ref('')

async function submit() {
  errorMessage.value = ''
  if (newPassword.value.length < 12) {
    errorMessage.value = 'Use a password with at least 12 characters.'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = 'The new passwords do not match.'
    return
  }

  try {
    await auth.changePassword(currentPassword.value, newPassword.value)
    await router.replace('/overview')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to change password.'
  }
}
</script>

<template>
  <main class="password-page">
    <section class="password-card" aria-labelledby="password-title">
      <p class="password-kicker">AGV DISPATCH · SECURITY REQUIRED</p>
      <h1 id="password-title">Choose a new password</h1>
      <p class="password-description">
        This account must use a personal password before it can access the workbench.
      </p>

      <form class="password-form" @submit.prevent="submit">
        <label>
          <span>Current password</span>
          <input v-model="currentPassword" type="password" autocomplete="current-password" required :disabled="auth.loading" />
        </label>
        <label>
          <span>New password</span>
          <input v-model="newPassword" type="password" autocomplete="new-password" minlength="12" required :disabled="auth.loading" />
        </label>
        <label>
          <span>Confirm new password</span>
          <input v-model="confirmPassword" type="password" autocomplete="new-password" minlength="12" required :disabled="auth.loading" />
        </label>
        <p v-if="errorMessage" class="password-error" role="alert">{{ errorMessage }}</p>
        <button class="password-submit" type="submit" :disabled="auth.loading">
          {{ auth.loading ? 'Saving…' : 'Save password' }}
        </button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.password-page { display: grid; min-height: 100vh; place-items: center; padding: var(--agv-space-5); background: radial-gradient(circle at 20% 10%, rgba(67, 182, 255, .18), transparent 32%), var(--agv-bg-canvas); }
.password-card { width: min(100%, 430px); padding: 42px; border: 1px solid var(--agv-border); border-radius: var(--agv-radius-lg); background: rgba(13, 27, 45, .92); box-shadow: var(--agv-shadow-lg); }
.password-kicker { margin: 0 0 10px; color: var(--agv-brand); font-size: 12px; letter-spacing: .1em; }
.password-card h1 { margin: 0; font-size: 28px; }
.password-description { margin: 12px 0 28px; color: var(--agv-text-secondary); line-height: 1.6; }
.password-form { display: grid; gap: var(--agv-space-4); }
.password-form label { display: grid; gap: 7px; color: var(--agv-text-secondary); font-size: 14px; }
.password-form input { width: 100%; padding: 11px 12px; border: 1px solid var(--agv-border); border-radius: var(--agv-radius-sm); outline: none; color: var(--agv-text-primary); background: var(--agv-bg-canvas); }
.password-form input:focus { border-color: var(--agv-brand); box-shadow: 0 0 0 3px rgba(67, 182, 255, .15); }
.password-submit { padding: 12px 16px; border: 0; border-radius: var(--agv-radius-sm); color: #06111d; background: var(--agv-brand); font-weight: 700; }
.password-submit:disabled { cursor: wait; opacity: .65; }
.password-error { margin: 0; color: var(--agv-danger); font-size: 14px; }
</style>
