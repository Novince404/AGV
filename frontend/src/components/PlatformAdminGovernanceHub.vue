<template>
  <section class="platform-admin-governance-shell">
    <div class="platform-admin-governance-head">
      <div>
        <div class="auth-dialog-kicker">{{ t('auth_role_platform_admin') }}</div>
        <h2 class="auth-dialog-title">{{ t('platform_admin_governance_title') }}</h2>
        <p class="auth-dialog-hint">{{ t('platform_admin_governance_hint') }}</p>
      </div>
    </div>

    <div class="approval-summary-grid platform-admin-governance-grid">
      <article class="approval-summary-card platform-admin-governance-card">
        <div class="platform-admin-governance-card-head">
          <strong>{{ t('platform_admin_governance_enterprise_approval_title') }}</strong>
          <span>{{ t('platform_admin_governance_enterprise_approval_hint') }}</span>
        </div>
        <div class="platform-admin-governance-metrics">
          <span>{{ formatInlineMessage(t('platform_admin_governance_enterprise_approval_meta'), { count: enterpriseApprovalSummary.pending || 0 }) }}</span>
          <small v-if="enterpriseApprovalLastFetchedText">{{ enterpriseApprovalLastFetchedText }}</small>
        </div>
        <div class="approval-actions">
          <button class="btn-secondary" type="button" @click="openEnterpriseApprovalDialog({ status: 'pending', resetSearch: true })">
            {{ t('platform_admin_governance_enterprise_approval_action') }}
          </button>
        </div>
      </article>

      <article class="approval-summary-card platform-admin-governance-card">
        <div class="platform-admin-governance-card-head">
          <strong>{{ t('platform_admin_governance_account_title') }}</strong>
          <span>{{ t('platform_admin_governance_account_hint') }}</span>
        </div>
        <div class="platform-admin-governance-metrics">
          <span>
            {{
              formatInlineMessage(t('platform_admin_governance_account_meta'), {
                approved: accountGovernanceSummary.approved || 0,
                suspended: accountGovernanceSummary.suspended || 0,
                deactivated: accountGovernanceSummary.deactivated || 0
              })
            }}
          </span>
          <small v-if="accountGovernanceLastFetchedText">{{ accountGovernanceLastFetchedText }}</small>
        </div>
        <div class="approval-actions">
          <button class="btn-secondary" type="button" @click="openAccountGovernanceDialog({ resetSearch: true })">
            {{ t('platform_admin_governance_account_action') }}
          </button>
        </div>
      </article>

      <article class="approval-summary-card platform-admin-governance-card">
        <div class="platform-admin-governance-card-head">
          <strong>{{ t('platform_admin_governance_bug_title') }}</strong>
          <span>{{ t('platform_admin_governance_bug_hint') }}</span>
        </div>
        <div class="platform-admin-governance-metrics">
          <span>
            {{
              formatInlineMessage(t('platform_admin_governance_bug_meta'), {
                open: platformBugFeedbackSummary.open || 0,
                progressing: platformBugFeedbackSummary.in_progress || 0,
                resolved: platformBugFeedbackSummary.resolved || 0
              })
            }}
          </span>
          <small v-if="platformBugFeedbackLastFetchedText">{{ platformBugFeedbackLastFetchedText }}</small>
        </div>
        <div class="approval-actions">
          <button class="btn-secondary" type="button" @click="openPlatformBugFeedbackDialog({ status: 'open' })">
            {{ t('platform_admin_governance_bug_action') }}
          </button>
        </div>
      </article>

      <article class="approval-summary-card platform-admin-governance-card">
        <div class="platform-admin-governance-card-head">
          <strong>{{ t('platform_admin_governance_audit_title') }}</strong>
          <span>{{ t('platform_admin_governance_audit_hint') }}</span>
        </div>
        <div class="platform-admin-governance-metrics">
          <span>
            {{
              platformRecentAuditEntries.length
                ? formatInlineMessage(t('platform_admin_governance_audit_meta'), { count: platformRecentAuditEntries.length })
                : t('platform_admin_governance_audit_empty')
            }}
          </span>
          <small v-if="operationAuditLastFetchedText">{{ operationAuditLastFetchedText }}</small>
        </div>
        <div class="approval-actions">
          <button class="btn-secondary" type="button" @click="requestOperationAuditRefresh({ force: true })">
            {{ t('platform_admin_governance_audit_action') }}
          </button>
        </div>
      </article>
    </div>

    <div class="platform-admin-governance-actions">
      <div class="platform-admin-governance-actions-copy">
        <strong>{{ t('platform_admin_governance_test_title') }}</strong>
        <span>{{ t('platform_admin_governance_test_hint') }}</span>
      </div>
      <div class="approval-actions">
        <button class="btn-secondary" type="button" @click="enterPlatformAdminPersonalPreviewMode">
          {{ t('platform_admin_governance_test_personal') }}
        </button>
        <button class="btn-secondary" type="button" @click="enterPlatformAdminEnterprisePreviewMode('enterprise_admin')">
          {{ t('platform_admin_governance_test_enterprise') }}
        </button>
      </div>
    </div>

    <div class="approval-history-shell platform-admin-governance-audit-list-shell">
      <div class="approval-history-head">
        <strong>{{ t('platform_admin_governance_audit_recent_title') }}</strong>
        <span>{{ t('platform_admin_governance_audit_recent_hint') }}</span>
      </div>
      <div v-if="platformRecentAuditEntries.length" class="approval-history-list">
        <article
          v-for="entry in platformRecentAuditEntries"
          :key="`platform-admin-audit-${entry.id}`"
          class="approval-history-card"
        >
          <div class="approval-history-title-row">
            <strong>{{ formatOperationAuditTitle(entry) }}</strong>
            <small>{{ entry.timestamp || '-' }}</small>
          </div>
          <span>{{ formatOperationAuditOperator(entry) }}</span>
          <span>{{ formatOperationAuditResourceRef(entry) }}</span>
          <span v-if="formatOperationAuditMetadata(entry)" class="task-line operations-summary">
            {{ formatOperationAuditMetadata(entry) }}
          </span>
        </article>
      </div>
      <div v-else class="approval-empty">
        {{ t('platform_admin_governance_audit_empty') }}
      </div>
    </div>
  </section>
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'PlatformAdminGovernanceHub',
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
      exposed.operationAuditLastFetchedText = exposed.operationAuditLastFetchedAt
        ? exposed.formatInlineMessage?.(exposed.t?.('operations_last_updated'), {
            at: exposed.operationAuditLastFetchedAt
          }) || ''
        : ''
    })

    return exposed
  }
})
</script>
