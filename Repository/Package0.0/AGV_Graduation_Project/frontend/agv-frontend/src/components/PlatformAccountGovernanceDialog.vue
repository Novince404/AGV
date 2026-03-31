<template>
  <div class="auth-dialog-backdrop">
    <div class="approval-dialog-card account-governance-dialog-card">
      <div class="auth-dialog-header">
        <div>
          <div class="auth-dialog-kicker">{{ t('auth_role_platform_admin') }}</div>
          <h2 class="auth-dialog-title">{{ t('account_governance_title') }}</h2>
          <p class="auth-dialog-hint">{{ t('account_governance_hint') }}</p>
        </div>
        <button class="auth-dialog-close" type="button" @click="closeAccountGovernanceDialog">
          {{ t('auth_close') }}
        </button>
      </div>

      <div class="approval-summary-grid account-governance-summary-grid">
        <button
          class="approval-summary-card"
          :class="{ active: accountGovernanceRoleFilter === 'all' }"
          type="button"
          @click="accountGovernanceRoleFilter = 'all'"
        >
          <strong>{{ accountGovernanceSummary.all || 0 }}</strong>
          <span>{{ t('account_governance_role_all') }}</span>
        </button>
        <button
          class="approval-summary-card"
          :class="{ active: accountGovernanceRoleFilter === 'personal' }"
          type="button"
          @click="accountGovernanceRoleFilter = 'personal'"
        >
          <strong>{{ accountGovernanceSummary.personal || 0 }}</strong>
          <span>{{ t('account_governance_role_personal') }}</span>
        </button>
        <button
          class="approval-summary-card"
          :class="{ active: accountGovernanceRoleFilter === 'enterprise' }"
          type="button"
          @click="accountGovernanceRoleFilter = 'enterprise'"
        >
          <strong>{{ accountGovernanceSummary.enterprise || 0 }}</strong>
          <span>{{ t('account_governance_role_enterprise') }}</span>
        </button>
        <button
          class="approval-summary-card"
          :class="{ active: accountGovernanceRoleFilter === 'platform_admin' }"
          type="button"
          @click="accountGovernanceRoleFilter = 'platform_admin'"
        >
          <strong>{{ accountGovernanceSummary.platform_admin || 0 }}</strong>
          <span>{{ t('account_governance_role_platform_admin') }}</span>
        </button>
      </div>

      <div class="approval-summary-grid account-governance-summary-grid account-governance-summary-grid-status">
        <button
          class="approval-summary-card"
          :class="{ active: accountGovernanceStatusFilter === 'approved' }"
          type="button"
          @click="accountGovernanceStatusFilter = 'approved'"
        >
          <strong>{{ accountGovernanceSummary.approved || 0 }}</strong>
          <span>{{ t('account_governance_status_approved') }}</span>
        </button>
        <button
          class="approval-summary-card"
          :class="{ active: accountGovernanceStatusFilter === 'pending' }"
          type="button"
          @click="accountGovernanceStatusFilter = 'pending'"
        >
          <strong>{{ accountGovernanceSummary.pending || 0 }}</strong>
          <span>{{ t('account_governance_status_pending') }}</span>
        </button>
        <button
          class="approval-summary-card"
          :class="{ active: accountGovernanceStatusFilter === 'rejected' }"
          type="button"
          @click="accountGovernanceStatusFilter = 'rejected'"
        >
          <strong>{{ accountGovernanceSummary.rejected || 0 }}</strong>
          <span>{{ t('account_governance_status_rejected') }}</span>
        </button>
        <button
          class="approval-summary-card"
          :class="{ active: accountGovernanceStatusFilter === 'suspended' }"
          type="button"
          @click="accountGovernanceStatusFilter = 'suspended'"
        >
          <strong>{{ accountGovernanceSummary.suspended || 0 }}</strong>
          <span>{{ t('account_governance_status_suspended') }}</span>
        </button>
        <button
          class="approval-summary-card"
          :class="{ active: accountGovernanceStatusFilter === 'deactivated' }"
          type="button"
          @click="accountGovernanceStatusFilter = 'deactivated'"
        >
          <strong>{{ accountGovernanceSummary.deactivated || 0 }}</strong>
          <span>{{ t('account_governance_status_deactivated') }}</span>
        </button>
      </div>

      <div class="approval-toolbar">
        <div class="task-line operations-last-fetched approval-filter-summary">
          {{ accountGovernanceFilterSummaryText }}
        </div>
        <label class="auth-dialog-field">
          <span>{{ t('account_governance_filter_role') }}</span>
          <select v-model="accountGovernanceRoleFilter">
            <option value="all">{{ t('account_governance_role_all') }}</option>
            <option value="personal">{{ t('account_governance_role_personal') }}</option>
            <option value="enterprise">{{ t('account_governance_role_enterprise') }}</option>
            <option value="platform_admin">{{ t('account_governance_role_platform_admin') }}</option>
          </select>
        </label>
        <label class="auth-dialog-field">
          <span>{{ t('account_governance_filter_status') }}</span>
          <select v-model="accountGovernanceStatusFilter">
            <option value="all">{{ t('account_governance_status_all') }}</option>
            <option value="approved">{{ t('account_governance_status_approved') }}</option>
            <option value="pending">{{ t('account_governance_status_pending') }}</option>
            <option value="rejected">{{ t('account_governance_status_rejected') }}</option>
            <option value="suspended">{{ t('account_governance_status_suspended') }}</option>
            <option value="deactivated">{{ t('account_governance_status_deactivated') }}</option>
          </select>
        </label>
        <label class="auth-dialog-field account-governance-search-field">
          <span>{{ t('account_governance_filter_search') }}</span>
          <input
            v-model.trim="accountGovernanceSearch"
            type="text"
            :placeholder="t('account_governance_filter_search_placeholder')"
            @keyup.enter="fetchManagedUserAccounts({ forceSelectFirst: true })"
          />
        </label>
        <div v-if="accountGovernanceLastFetchedText" class="task-line operations-last-fetched">
          {{ accountGovernanceLastFetchedText }}
        </div>
        <button
          class="auth-dialog-inline-action"
          type="button"
          :disabled="accountGovernanceLoading"
          @click="fetchManagedUserAccounts({ forceSelectFirst: false })"
        >
          {{ accountGovernanceLoading ? `${t('account_governance_refresh')}...` : t('account_governance_refresh') }}
        </button>
        <button class="btn-ghost" type="button" @click="resetAccountGovernanceFilters">
          {{ t('account_governance_reset_filters') }}
        </button>
        <button class="btn-ghost" type="button" @click="exportManagedUserAccounts('json')">
          {{ t('account_governance_export_json') }}
        </button>
        <button class="btn-ghost" type="button" @click="exportManagedUserAccounts('csv')">
          {{ t('account_governance_export_csv') }}
        </button>
      </div>

      <div class="approval-layout">
        <div class="approval-list">
          <div v-if="accountGovernanceLoading && managedUserAccounts.length === 0" class="approval-empty">
            {{ t('account_governance_loading') }}
          </div>
          <button
            v-for="item in managedUserAccounts"
            :key="item.id"
            class="approval-list-item account-governance-list-item"
            :class="{ active: String(selectedManagedUserId || '') === String(item.id || '') }"
            type="button"
            @click="selectedManagedUserId = String(item.id || '')"
          >
            <strong>{{ item.display_name || item.username }}</strong>
            <span class="managed-user-item-meta">{{ buildManagedUserMeta(item) }}</span>
            <div class="approval-list-meta">
              <small>{{ managedUserStatusLabel(item.account_status) }}</small>
              <span v-if="item.builtin" class="point-badge approval-draft-badge">
                {{ t('account_governance_builtin_badge') }}
              </span>
            </div>
          </button>
          <div v-if="!accountGovernanceLoading && managedUserAccounts.length === 0" class="approval-empty">
            <strong>{{ t('account_governance_empty') }}</strong>
            <span>{{ accountGovernanceEmptyHint }}</span>
            <div class="approval-actions approval-empty-actions">
              <button class="btn-secondary" type="button" @click="resetAccountGovernanceFilters">
                {{ t('account_governance_reset_filters') }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="selectedManagedUser" class="approval-detail account-governance-detail">
          <div class="approval-detail-toolbar">
            <div>
              <strong>{{ t('account_governance_detail_title') }}</strong>
            </div>
            <div class="approval-actions approval-detail-actions">
              <span class="point-badge">{{ managedUserRoleLabel(selectedManagedUser.role) }}</span>
              <span class="point-badge">{{ managedUserStatusLabel(selectedManagedUser.account_status) }}</span>
            </div>
          </div>

          <div class="approval-detail-grid">
            <div>
              <strong>{{ t('account_governance_field_username') }}</strong>
              <span>{{ selectedManagedUser.username || '-' }}</span>
            </div>
            <div>
              <strong>{{ t('account_governance_field_display_name') }}</strong>
              <span>{{ selectedManagedUser.display_name || '-' }}</span>
            </div>
            <div>
              <strong>{{ t('account_governance_field_role') }}</strong>
              <span>{{ managedUserRoleLabel(selectedManagedUser.role) }}</span>
            </div>
            <div>
              <strong>{{ t('account_governance_field_status') }}</strong>
              <span>{{ managedUserStatusLabel(selectedManagedUser.account_status) }}</span>
            </div>
            <div>
              <strong>{{ t('account_governance_field_organization') }}</strong>
              <span>{{ selectedManagedUser.organization_name || '-' }}</span>
            </div>
            <div>
              <strong>{{ t('account_governance_field_created_at') }}</strong>
              <span>{{ selectedManagedUser.created_at || '-' }}</span>
            </div>
            <div>
              <strong>{{ t('account_governance_field_last_login_at') }}</strong>
              <span>{{ selectedManagedUser.last_login_at || '-' }}</span>
            </div>
            <div>
              <strong>{{ t('account_governance_field_governance_updated_at') }}</strong>
              <span>{{ selectedManagedUser.governance_updated_at || '-' }}</span>
            </div>
            <div v-if="selectedManagedUser.suspended_at">
              <strong>{{ t('account_governance_field_suspended_at') }}</strong>
              <span>{{ selectedManagedUser.suspended_at }}</span>
            </div>
            <div v-if="selectedManagedUser.suspended_by">
              <strong>{{ t('account_governance_field_suspended_by') }}</strong>
              <span>{{ selectedManagedUser.suspended_by }}</span>
            </div>
            <div v-if="selectedManagedUser.suspended_until">
              <strong>{{ t('account_governance_field_suspended_until') }}</strong>
              <span>{{ selectedManagedUser.suspended_until }}</span>
            </div>
            <div v-if="selectedManagedUser.deactivated_at">
              <strong>{{ t('account_governance_field_deactivated_at') }}</strong>
              <span>{{ selectedManagedUser.deactivated_at }}</span>
            </div>
            <div v-if="selectedManagedUser.deactivated_by">
              <strong>{{ t('account_governance_field_deactivated_by') }}</strong>
              <span>{{ selectedManagedUser.deactivated_by }}</span>
            </div>
          </div>
          <div
            v-if="selectedManagedUser.suspension_reason || selectedManagedUser.suspension_note"
            class="approval-existing-note"
          >
            <strong>{{ t('account_governance_suspension_title') }}</strong>
            <p v-if="selectedManagedUser.suspension_reason">
              <strong>{{ t('account_governance_suspension_reason') }}</strong>
              <span> {{ selectedManagedUser.suspension_reason }}</span>
            </p>
            <p v-if="selectedManagedUser.suspension_note">
              <strong>{{ t('account_governance_suspension_note') }}</strong>
              <span> {{ selectedManagedUser.suspension_note }}</span>
            </p>
          </div>

          <div v-if="selectedManagedUser.enterprise_application" class="approval-existing-note">
            <strong>{{ t('account_governance_enterprise_application') }}</strong>
            <p>
              <strong>{{ t('enterprise_register_company_name') }}</strong>
              <span> {{ selectedManagedUser.enterprise_application.company_name || '-' }}</span>
            </p>
            <p>
              <strong>{{ t('account_governance_contact_email') }}</strong>
              <span> {{ selectedManagedUser.enterprise_application.contact_email || '-' }}</span>
            </p>
            <p v-if="selectedManagedUser.enterprise_application.review_note">
              <strong>{{ t('account_governance_review_note') }}</strong>
              <span> {{ selectedManagedUser.enterprise_application.review_note }}</span>
            </p>
          </div>

          <div
            v-if="selectedManagedUser.account_status !== 'deactivated'"
            class="approval-existing-note account-governance-action-box"
          >
            <strong>{{ t('account_governance_action_title') }}</strong>
            <p>{{ t('account_governance_action_hint') }}</p>

            <template v-if="selectedManagedUser.account_status === 'suspended'">
              <div class="approval-actions">
                <button
                  class="btn-secondary"
                  type="button"
                  :disabled="accountGovernanceActionLoading"
                  @click="unsuspendManagedUserAccount"
                >
                  {{
                    accountGovernanceActionLoading
                      ? `${t('account_governance_unsuspend_submit')}...`
                      : t('account_governance_unsuspend_submit')
                  }}
                </button>
              </div>
            </template>

            <template v-else>
              <div class="approval-detail-grid">
                <label class="auth-dialog-field">
                  <span>{{ t('account_governance_suspension_reason') }}</span>
                  <input
                    v-model.trim="accountGovernanceSuspendReason"
                    type="text"
                    :placeholder="t('account_governance_suspend_reason_placeholder')"
                  />
                </label>
                <label class="auth-dialog-field">
                  <span>{{ t('account_governance_suspend_duration') }}</span>
                  <select v-model="accountGovernanceSuspendDurationPreset">
                    <option value="1d">{{ t('account_governance_suspend_duration_1d') }}</option>
                    <option value="7d">{{ t('account_governance_suspend_duration_7d') }}</option>
                    <option value="30d">{{ t('account_governance_suspend_duration_30d') }}</option>
                    <option value="permanent">{{ t('account_governance_suspend_duration_permanent') }}</option>
                  </select>
                </label>
              </div>
              <label class="auth-dialog-field">
                <span>{{ t('account_governance_suspension_note') }}</span>
                <textarea
                  v-model.trim="accountGovernanceSuspendNote"
                  rows="3"
                  :placeholder="t('account_governance_suspend_note_placeholder')"
                ></textarea>
              </label>

              <div class="approval-actions">
                <button
                  class="btn-secondary"
                  type="button"
                  :disabled="accountGovernanceActionLoading"
                  @click="suspendManagedUserAccount"
                >
                  {{
                    accountGovernanceActionLoading
                      ? `${t('account_governance_suspend_submit')}...`
                      : t('account_governance_suspend_submit')
                  }}
                </button>
                <button
                  class="btn-delete"
                  type="button"
                  :disabled="accountGovernanceActionLoading"
                  @click="deactivateManagedUserAccount"
                >
                  {{
                    accountGovernanceActionLoading
                      ? `${t('account_governance_deactivate_submit')}...`
                      : t('account_governance_deactivate_submit')
                  }}
                </button>
              </div>
            </template>
          </div>

          <div v-else class="approval-existing-note account-governance-action-box">
            <strong>{{ t('account_governance_deactivated_title') }}</strong>
            <p>{{ t('account_governance_deactivated_hint') }}</p>
          </div>
        </div>

        <div v-else class="approval-detail-empty">
          {{ t('account_governance_select_hint') }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'PlatformAccountGovernanceDialog',
  props: {
    ui: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const exposed = reactive({
      buildManagedUserMeta(item) {
        if (!item) return ''
        const parts = [
          exposed.managedUserRoleLabel?.(item.role) || item.role || '-',
          item.username || '-'
        ]
        if (item.organization_name) {
          parts.push(item.organization_name)
        }
        return parts.join(' · ')
      },
      managedUserRoleLabel(role) {
        return exposed.t?.(`auth_role_${role || 'guest'}`) || String(role || 'guest')
      },
      managedUserStatusLabel(status) {
        return exposed.t?.(`account_governance_status_${status || 'approved'}`) || String(status || 'approved')
      }
    })

    watchEffect(() => {
      Object.assign(exposed, props.ui || {})
    })

    return exposed
  }
})
</script>


