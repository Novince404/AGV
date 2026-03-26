<template>
<div class="auth-dialog-backdrop" :class="{ gate: showAuthGate }">
      <div class="auth-dialog-card">
        <div class="auth-dialog-header">
          <div>
            <div class="auth-dialog-kicker">{{ t('title') }}</div>
            <h2 class="auth-dialog-title">{{ authModalTitle }}</h2>
            <p class="auth-dialog-hint">{{ authPanelModeText }}</p>
          </div>
          <button
            v-if="dashboardUnlocked"
            class="auth-dialog-close"
            type="button"
            @click="authPanelOpen = false"
          >
            {{ t('auth_close') }}
          </button>
        </div>

        <div class="auth-dialog-current" :class="[authRoleBadgeClass, { guest: !authAuthenticated }]">
          <div class="auth-dialog-current-label">{{ t('auth_current_identity') }}</div>
          <strong>{{ authAuthenticated ? authCurrentDisplayName : t('auth_role_guest') }}</strong>
          <span>{{ authModeText }}</span>
          <small class="auth-dialog-current-hint">{{ authEntryHintText }}</small>
          <small>{{ authAuthenticated ? authCurrentUser.username : 'guest' }}</small>
          <small v-if="authAuthenticated">{{ authAccountStatusLabel }}</small>
          <small v-if="authAuthenticated && authCurrentOrganizationName">{{ authCurrentOrganizationName }}</small>
          <button
            v-if="authAuthenticated"
            class="auth-dialog-inline-action"
            type="button"
            :disabled="authLoading"
            @click="handleAuthLogout"
          >
            {{ t('auth_sign_out') }}
          </button>
        </div>

        <div
          v-if="authStatusNotice"
          class="auth-status-note"
          :class="[`tone-${authStatusNotice.tone}`]"
        >
          <strong>{{ authStatusNotice.title }}</strong>
          <span>{{ authStatusNotice.hint }}</span>
          <small v-if="authStatusNotice.meta">{{ authStatusNotice.meta }}</small>
          <p v-if="authStatusNotice.detail" class="auth-status-note-detail">{{ authStatusNotice.detail }}</p>
          <button
            v-if="authStatusNotice.actionKey === 'enterprise-approval'"
            class="auth-dialog-inline-action"
            type="button"
            :disabled="authLoading"
            @click="openEnterpriseApprovalDialog"
          >
            {{ authStatusNotice.actionLabel }}
          </button>
          <button
            v-else-if="authStatusNotice.actionKey === 'refresh-enterprise-status'"
            class="auth-dialog-inline-action"
            type="button"
            :disabled="authLoading"
            @click="refreshEnterpriseAccountStatus"
          >
            {{ authStatusNotice.actionLabel }}
          </button>
          <button
            v-else-if="authStatusNotice.actionKey === 'enterprise-settings'"
            class="auth-dialog-inline-action"
            type="button"
            :disabled="authLoading"
            @click="openEnterpriseSettingsDialog()"
          >
            {{ authStatusNotice.actionLabel }}
          </button>
        </div>

        <div
          v-if="authCanEnterpriseApprove"
          class="auth-status-note tone-platform"
        >
          <div class="auth-status-note-head">
            <div>
              <strong>{{ t('auth_platform_pending_snapshot_title') }}</strong>
              <span>{{ t('auth_platform_pending_snapshot_hint') }}</span>
            </div>
            <button
              class="auth-dialog-inline-action"
              type="button"
              :disabled="authLoading"
              @click="openEnterpriseApprovalDialog"
            >
              {{ t('enterprise_approval_entry') }}
            </button>
            <button
              class="auth-dialog-inline-action"
              type="button"
              :disabled="authLoading"
              @click="refreshEnterpriseApprovalSnapshot"
            >
              {{ t('enterprise_approval_refresh') }}
            </button>
          </div>
          <small v-if="enterpriseApprovalLastFetchedText">{{ enterpriseApprovalLastFetchedText }}</small>
          <div v-if="recentPendingEnterpriseApplications.length" class="auth-status-list">
            <button
              v-for="item in recentPendingEnterpriseApplications"
              :key="`auth-pending-${item.id}`"
              class="auth-status-list-item"
              type="button"
              @click="openEnterpriseApprovalDialogForItem(item.id, 'pending')"
            >
              <strong>{{ item.company_name }}</strong>
              <span>
                {{
                  formatInlineMessage(t('auth_platform_pending_snapshot_item'), {
                    contact: item.contact_name,
                    submittedAt: item.submitted_at || '-'
                  })
                }}
              </span>
            </button>
          </div>
          <div v-else class="auth-status-empty">
            {{ t('auth_platform_pending_snapshot_empty') }}
          </div>
        </div>

        <div
          v-if="authCanEnterpriseApprove"
          class="auth-status-note"
        >
          <div class="auth-status-note-head">
            <div>
              <strong>{{ t('auth_platform_recent_review_snapshot_title') }}</strong>
              <span>{{ t('auth_platform_recent_review_snapshot_hint') }}</span>
            </div>
            <button
              class="auth-dialog-inline-action"
              type="button"
              :disabled="authLoading"
              @click="openEnterpriseApprovalDialog({ status: 'all' })"
            >
              {{ t('enterprise_approval_entry') }}
            </button>
            <button
              class="auth-dialog-inline-action"
              type="button"
              :disabled="authLoading"
              @click="refreshEnterpriseApprovalSnapshot"
            >
              {{ t('enterprise_approval_refresh') }}
            </button>
          </div>
          <small v-if="enterpriseApprovalLastFetchedText">{{ enterpriseApprovalLastFetchedText }}</small>
          <div v-if="recentReviewedEnterpriseApplications.length" class="auth-status-list">
            <button
              v-for="item in recentReviewedEnterpriseApplications"
              :key="`auth-reviewed-${item.id}`"
              class="auth-status-list-item"
              type="button"
              @click="openEnterpriseApprovalDialogForItem(item.id, item.status)"
            >
              <strong>{{ item.company_name }}</strong>
              <span>
                {{
                  formatInlineMessage(t('auth_platform_recent_review_snapshot_item'), {
                    status: t(`enterprise_approval_status_${item.status}`),
                    reviewer: item.reviewed_by || '-',
                    reviewedAt: item.reviewed_at || item.submitted_at || '-'
                  })
                }}
              </span>
            </button>
          </div>
          <div v-else class="auth-status-empty">
            {{ t('auth_platform_recent_review_snapshot_empty') }}
          </div>
        </div>

        <div
          v-if="authIsEnterpriseRole && authEnterpriseApplicationProgressItems.length"
          class="auth-status-note"
        >
          <div class="auth-status-note-head">
            <div>
              <strong>{{ t('enterprise_application_progress_title') }}</strong>
              <span>{{ t('enterprise_settings_application_status_hint') }}</span>
            </div>
            <button
              v-if="authCurrentEnterpriseApplication?.username"
              class="auth-dialog-inline-action"
              type="button"
              :disabled="authLoading"
              @click="copyEnterpriseApplicationUsername(authCurrentEnterpriseApplication)"
            >
              {{ t('enterprise_application_copy_username') }}
            </button>
          </div>
          <div class="application-progress-grid">
            <article
              v-for="item in authEnterpriseApplicationProgressItems"
              :key="`auth-enterprise-progress-${item.key}`"
              class="application-progress-item"
              :class="`is-${item.tone}`"
            >
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </article>
          </div>
          <div class="enterprise-settings-status-grid auth-enterprise-status-grid">
            <div class="enterprise-settings-status-item">
              <span>{{ t('enterprise_register_company_name') }}</span>
              <strong>{{ authCurrentEnterpriseApplication?.company_name || authCurrentOrganizationName || '—' }}</strong>
            </div>
            <div class="enterprise-settings-status-item">
              <span>{{ t('enterprise_register_username') }}</span>
              <strong>{{ authCurrentEnterpriseApplication?.username || '—' }}</strong>
            </div>
            <div class="enterprise-settings-status-item">
              <span>{{ t('enterprise_register_contact_name') }}</span>
              <strong>{{ authCurrentEnterpriseApplication?.contact_name || '—' }}</strong>
            </div>
            <div class="enterprise-settings-status-item">
              <span>{{ t('enterprise_register_contact_email') }}</span>
              <strong>{{ authCurrentEnterpriseApplication?.contact_email || '—' }}</strong>
            </div>
          </div>
          <small v-if="authAccountStatusLastCheckedText" class="operations-last-fetched">
            {{ authAccountStatusLastCheckedText }}
          </small>
          <div v-if="authEnterpriseQuickActionItems.length" class="auth-status-subnote">
            <strong>{{ t('auth_enterprise_actions_title') }}</strong>
            <span>{{ authEnterpriseQuickActionHint }}</span>
            <div class="auth-status-actions">
              <button
                v-for="action in authEnterpriseQuickActionItems"
                :key="`auth-enterprise-action-${action.key}`"
                :class="action.tone === 'ghost' ? 'btn-ghost' : 'btn-secondary'"
                type="button"
                :disabled="authLoading"
                @click="runAuthEnterpriseQuickAction(action.key)"
              >
                {{ action.label }}
              </button>
            </div>
          </div>
        </div>

        <div class="auth-capability-panel">
          <div class="auth-dialog-divider">{{ t('auth_capabilities_title') }}</div>
          <p class="auth-dialog-hint">
            {{ authAuthenticated ? t('auth_capabilities_hint') : t('auth_capabilities_guest_hint') }}
          </p>
          <div class="auth-capability-grid">
            <article
              v-for="item in authCapabilityCards"
              :key="item.key"
              class="auth-capability-card"
              :class="{ enabled: item.enabled, disabled: !item.enabled }"
            >
              <div class="auth-capability-label-row">
                <strong>{{ item.label }}</strong>
                <span class="auth-capability-state">{{ buildAuthCapabilityStateText(item.enabled) }}</span>
              </div>
              <span>{{ item.hint }}</span>
            </article>
          </div>
        </div>

        <div class="auth-dialog-choice-grid">
          <button class="auth-dialog-choice guest" type="button" @click="enterGuestMode">
            <strong>{{ t('auth_enter_guest') }}</strong>
            <span>{{ t('auth_role_guest') }}</span>
          </button>
          <button
            v-for="account in authPrimaryAccounts"
            :key="account.role"
            class="auth-dialog-choice"
            type="button"
            :disabled="authLoading"
            @click="handleAuthQuickLogin(account)"
          >
            <strong>{{ t(`auth_role_${account.role}`) }}</strong>
            <span>{{ account.username }}</span>
          </button>
        </div>

        <div class="auth-dialog-segmented">
          <button
            class="auth-dialog-segment"
            :class="{ active: authDialogView === 'login' }"
            type="button"
            @click="switchAuthDialogView('login')"
          >
            {{ t('auth_manual_login') }}
          </button>
          <button
            class="auth-dialog-segment"
            :class="{ active: authDialogView === 'enterprise-register' }"
            type="button"
            @click="switchAuthDialogView('enterprise-register')"
          >
            {{ t('auth_enterprise_register') }}
          </button>
        </div>

        <template v-if="authDialogView === 'login'">
          <div class="auth-dialog-divider">{{ t('auth_manual_login') }}</div>

          <div v-if="authEnterpriseRegisterFollowup" class="auth-status-note tone-pending">
            <div class="auth-status-note-head">
              <div>
                <strong>{{ t('auth_enterprise_register_followup_title') }}</strong>
                <span>
                  {{
                    formatInlineMessage(t('auth_enterprise_register_followup_hint'), {
                      company: authEnterpriseRegisterFollowup.company_name,
                      username: authEnterpriseRegisterFollowup.username
                    })
                  }}
                </span>
              </div>
              <button
                class="auth-dialog-inline-action"
                type="button"
                :disabled="authLoading"
                @click="copyEnterpriseApplicationUsername(authEnterpriseRegisterFollowup)"
              >
                {{ t('enterprise_application_copy_username') }}
              </button>
            </div>
            <div class="enterprise-settings-status-grid auth-enterprise-status-grid">
              <div class="enterprise-settings-status-item">
                <span>{{ t('enterprise_register_company_name') }}</span>
                <strong>{{ authEnterpriseRegisterFollowup.company_name || '—' }}</strong>
              </div>
              <div class="enterprise-settings-status-item">
                <span>{{ t('enterprise_register_username') }}</span>
                <strong>{{ authEnterpriseRegisterFollowup.username || '—' }}</strong>
              </div>
              <div v-if="authEnterpriseRegisterFollowup.contact_email" class="enterprise-settings-status-item">
                <span>{{ t('enterprise_register_contact_email') }}</span>
                <strong>{{ authEnterpriseRegisterFollowup.contact_email }}</strong>
              </div>
            </div>
            <div class="auth-status-actions">
              <button
                v-if="authEnterpriseRegisterFollowup.contact_email"
                class="btn-ghost"
                type="button"
                :disabled="authLoading"
                @click="copyEnterpriseApplicationContactEmail(authEnterpriseRegisterFollowup)"
              >
                {{ t('enterprise_application_copy_contact_email') }}
              </button>
              <button
                class="auth-dialog-submit"
                type="button"
                :disabled="authLoading"
                @click="signInEnterpriseRegisterFollowup"
              >
                {{ authLoading ? t('auth_signing_in') : t('auth_enterprise_register_followup_action') }}
              </button>
            </div>
          </div>

          <div class="auth-dialog-form">
            <label class="auth-dialog-field">
              <span>{{ t('auth_username') }}</span>
              <input
                v-model.trim="authUsername"
                :placeholder="t('auth_username_placeholder')"
                @keydown.enter.prevent="handleAuthLogin"
              />
            </label>

            <label class="auth-dialog-field">
              <span>{{ t('auth_password') }}</span>
              <input
                v-model="authPassword"
                type="password"
                :placeholder="t('auth_password_placeholder')"
                @keydown.enter.prevent="handleAuthLogin"
              />
            </label>

            <div class="auth-dialog-actions">
              <button class="auth-dialog-submit" type="button" :disabled="authLoading" @click="handleAuthLogin">
                {{ authLoading ? t('auth_signing_in') : t('auth_sign_in') }}
              </button>
              <div class="auth-dialog-demo-label">{{ t('auth_demo_accounts') }}</div>
              <div class="auth-dialog-demo-grid">
                <button
                  v-for="account in authDemoAccounts"
                  :key="account.username"
                  class="auth-dialog-demo-button"
                  type="button"
                  @click="handleAuthDemoFill(account)"
                >
                  {{ authDemoAccountLabel(account) }}
                </button>
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="auth-dialog-divider">{{ t('auth_enterprise_register') }}</div>
          <p class="auth-dialog-hint">{{ t('auth_enterprise_register_hint') }}</p>
          <div v-if="authEnterpriseRegisterDraftHasContent" class="auth-status-note">
            <strong>{{ t('auth_enterprise_register_draft_title') }}</strong>
            <span>{{ t('auth_enterprise_register_draft_hint') }}</span>
          </div>
          <div class="auth-dialog-form">
            <label class="auth-dialog-field">
              <span>{{ t('enterprise_register_company_name') }}</span>
              <input v-model.trim="authEnterpriseRegisterForm.company_name" />
            </label>
            <label class="auth-dialog-field">
              <span>{{ t('enterprise_register_contact_name') }}</span>
              <input v-model.trim="authEnterpriseRegisterForm.contact_name" />
            </label>
            <label class="auth-dialog-field">
              <span>{{ t('enterprise_register_contact_email') }}</span>
              <input v-model.trim="authEnterpriseRegisterForm.contact_email" />
            </label>
            <label class="auth-dialog-field">
              <span>{{ t('enterprise_register_username') }}</span>
              <input v-model.trim="authEnterpriseRegisterForm.username" />
            </label>
            <label class="auth-dialog-field">
              <span>{{ t('enterprise_register_password') }}</span>
              <input
                v-model="authEnterpriseRegisterForm.password"
                type="password"
                @keydown.enter.prevent="handleEnterpriseRegister"
              />
            </label>

            <div class="auth-dialog-actions">
              <button
                class="auth-dialog-submit"
                type="button"
                :disabled="authEnterpriseRegisterLoading || !authEnterpriseRegisterValidation.valid"
                @click="handleEnterpriseRegister"
              >
                {{ authEnterpriseRegisterLoading ? t('auth_enterprise_register_submitting') : t('auth_enterprise_register_submit') }}
              </button>
              <button
                class="btn-ghost"
                type="button"
                :disabled="authEnterpriseRegisterLoading || !authEnterpriseRegisterDraftHasContent"
                @click="clearEnterpriseRegisterDraft"
              >
                {{ t('auth_enterprise_register_clear_draft') }}
              </button>
            </div>
            <p class="auth-dialog-hint auth-register-draft-hint">
              {{ t('auth_enterprise_register_draft_hint') }}
            </p>

            <div class="auth-register-sidecard">
              <div class="auth-register-sidecard-head">
                <strong>{{ t('auth_enterprise_register_panel_title') }}</strong>
                <span class="auth-register-sidecard-state" :class="{ ready: authEnterpriseRegisterValidation.valid }">
                  {{ authEnterpriseRegisterStatusText }}
                </span>
              </div>

              <div class="auth-register-checklist">
                <article
                  v-for="item in authEnterpriseRegisterValidation.items"
                  :key="item.key"
                  class="auth-register-check-item"
                  :class="{ ready: item.valid }"
                >
                  <strong>{{ item.label }}</strong>
                  <span>{{ item.valid ? t('auth_enterprise_register_requirement_complete') : item.message }}</span>
                </article>
              </div>

              <div class="auth-register-process">
                <strong>{{ t('auth_enterprise_register_process_title') }}</strong>
                <ol>
                  <li>{{ t('auth_enterprise_register_process_step_submit') }}</li>
                  <li>{{ t('auth_enterprise_register_process_step_review') }}</li>
                  <li>{{ t('auth_enterprise_register_process_step_unlock') }}</li>
                </ol>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'AuthDialog',
  props: {
    ui: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const exposed = reactive({})

    watchEffect(() => {
      Object.assign(exposed, props.ui || {})
    })

    return exposed
  }
})
</script>
