<template>
<div class="auth-dialog-backdrop" :class="{ gate: showAuthGate }">
      <div class="auth-dialog-stage">
        <aside class="auth-dialog-side-panel auth-dialog-side-panel-capabilities">
          <div class="auth-capability-panel">
            <div class="auth-dialog-divider">{{ t('auth_capabilities_title') }}</div>
            <strong class="auth-side-preview-title">{{ authPreviewIdentityLabel }}</strong>
            <p class="auth-dialog-hint">
              {{ authPreviewCapabilityHint }}
            </p>
            <div class="auth-capability-grid">
              <article
                v-for="item in authPreviewCapabilityCards"
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
        </aside>

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
          <div v-if="authStatusNotice.actionLabel || authStatusNotice.secondaryActionLabel" class="auth-status-actions">
            <button
              v-if="authStatusNotice.actionLabel"
              class="auth-dialog-inline-action"
              type="button"
              :disabled="authLoading"
              @click="runAuthStatusNoticeAction(authStatusNotice.actionKey)"
            >
              {{ authStatusNotice.actionLabel }}
            </button>
            <button
              v-if="authStatusNotice.secondaryActionLabel"
              class="btn-ghost"
              type="button"
              :disabled="authLoading"
              @click="runAuthStatusNoticeAction(authStatusNotice.secondaryActionKey)"
            >
              {{ authStatusNotice.secondaryActionLabel }}
            </button>
          </div>
        </div>

        <div
          v-if="authEnterpriseStatusFollowupVisible"
          class="auth-status-note"
          :class="[`tone-${authEnterpriseStatusFollowup.status}`]"
        >
          <div class="auth-status-note-head">
            <div>
              <strong>{{ authEnterpriseStatusFollowupTitle }}</strong>
              <span>{{ authEnterpriseStatusFollowupHint }}</span>
            </div>
            <button
              class="btn-ghost"
              type="button"
              :disabled="authLoading"
              @click="runEnterpriseStatusFollowupAction('dismiss')"
            >
              {{ t('auth_enterprise_status_followup_dismiss') }}
            </button>
          </div>
          <div class="enterprise-settings-status-grid auth-enterprise-status-grid">
            <div class="enterprise-settings-status-item">
              <span>{{ t('enterprise_register_company_name') }}</span>
              <strong>{{ authEnterpriseStatusFollowup.company_name || '—' }}</strong>
            </div>
            <div class="enterprise-settings-status-item">
              <span>{{ t('enterprise_register_username') }}</span>
              <strong>{{ authEnterpriseStatusFollowup.username || '—' }}</strong>
            </div>
            <div class="enterprise-settings-status-item">
              <span>{{ t('enterprise_settings_summary_status') }}</span>
              <strong>{{ t(`auth_account_status_${authEnterpriseStatusFollowup.status}`) }}</strong>
            </div>
            <div class="enterprise-settings-status-item">
              <span>{{ t('enterprise_settings_application_reviewed_at') }}</span>
              <strong>{{ authEnterpriseStatusFollowup.reviewed_at || '—' }}</strong>
            </div>
          </div>
          <div class="application-progress-grid">
            <article
              v-for="item in authEnterpriseStatusFollowupProgressItems"
              :key="`auth-status-followup-progress-${item.key}`"
              class="application-progress-item"
              :class="`is-${item.tone}`"
            >
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </article>
          </div>
          <small v-if="authEnterpriseStatusFollowupUpdatedText" class="operations-last-fetched">
            {{ authEnterpriseStatusFollowupUpdatedText }}
          </small>
          <div v-if="authEnterpriseStatusFollowup.review_note" class="auth-status-subnote">
            <strong>{{ t('enterprise_settings_application_review_note') }}</strong>
            <span>{{ authEnterpriseStatusFollowup.review_note }}</span>
          </div>
          <div class="auth-status-subnote">
            <strong>{{ t('auth_enterprise_status_followup_next_step_title') }}</strong>
            <span>{{ authEnterpriseStatusFollowupNextStepText }}</span>
          </div>
          <div class="auth-status-actions">
            <button
              v-if="authEnterpriseStatusFollowup.status === 'approved'"
              class="auth-dialog-inline-action"
              type="button"
              :disabled="authLoading"
              @click="runEnterpriseStatusFollowupAction('open-enterprise-settings')"
            >
              {{ t('enterprise_settings_entry') }}
            </button>
            <button
              v-if="authEnterpriseStatusFollowup.status === 'approved'"
              class="btn-secondary"
              type="button"
              :disabled="authLoading"
              @click="runEnterpriseStatusFollowupAction('apply-workspace')"
            >
              {{ t('enterprise_settings_apply_workspace_preset') }}
            </button>
            <button
              v-if="authEnterpriseStatusFollowup.status === 'rejected'"
              class="auth-dialog-inline-action"
              type="button"
              :disabled="authLoading"
              @click="runEnterpriseStatusFollowupAction('resume-registration')"
            >
              {{ t('enterprise_application_resume_registration') }}
            </button>
            <button
              v-if="authEnterpriseStatusFollowup.status === 'rejected' && authEnterpriseStatusFollowup.review_note"
              class="btn-ghost"
              type="button"
              :disabled="authLoading"
              @click="runEnterpriseStatusFollowupAction('copy-review-note')"
            >
              {{ t('enterprise_application_copy_review_note') }}
            </button>
            <button
              class="btn-ghost"
              type="button"
              :disabled="authLoading"
              @click="runEnterpriseStatusFollowupAction('copy-summary')"
            >
              {{ t('enterprise_application_copy_summary') }}
            </button>
          </div>
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
              @click="openEnterpriseApprovalDialog({ status: 'pending', resetSearch: true })"
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
          v-if="enterpriseApprovalReviewFollowupVisible"
          class="auth-status-note tone-platform"
        >
          <div class="auth-status-note-head">
            <div>
              <strong>{{ t('enterprise_approval_followup_title') }}</strong>
              <span>{{ t('enterprise_approval_followup_hint') }}</span>
            </div>
            <button
              class="btn-ghost"
              type="button"
              :disabled="authLoading"
              @click="runEnterpriseApprovalFollowupAction('dismiss')"
            >
              {{ t('enterprise_approval_followup_dismiss') }}
            </button>
          </div>
          <div class="enterprise-settings-status-grid auth-enterprise-status-grid">
            <div class="enterprise-settings-status-item">
              <span>{{ t('enterprise_register_company_name') }}</span>
              <strong>{{ enterpriseApprovalReviewFollowup.company_name || '—' }}</strong>
            </div>
            <div class="enterprise-settings-status-item">
              <span>{{ t('enterprise_register_username') }}</span>
              <strong>{{ enterpriseApprovalReviewFollowup.username || '—' }}</strong>
            </div>
            <div class="enterprise-settings-status-item">
              <span>{{ t('enterprise_approval_status_label') }}</span>
              <strong>{{ t(`enterprise_approval_status_${enterpriseApprovalReviewFollowup.status || 'pending'}`) }}</strong>
            </div>
            <div class="enterprise-settings-status-item">
              <span>{{ t('enterprise_approval_reviewed_at') }}</span>
              <strong>{{ enterpriseApprovalReviewFollowup.reviewed_at || enterpriseApprovalReviewFollowup.submitted_at || '—' }}</strong>
            </div>
          </div>
          <div class="application-progress-grid">
            <article
              v-for="item in enterpriseApprovalReviewFollowupProgressItems"
              :key="`auth-approval-followup-progress-${item.key}`"
              class="application-progress-item"
              :class="`is-${item.tone}`"
            >
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </article>
          </div>
          <small v-if="enterpriseApprovalReviewFollowupUpdatedText" class="operations-last-fetched">
            {{ enterpriseApprovalReviewFollowupUpdatedText }}
          </small>
          <div class="auth-status-subnote">
            <strong>{{ t('enterprise_approval_next_step_title') }}</strong>
            <span>{{ enterpriseApprovalReviewFollowupNextStepText }}</span>
          </div>
          <div class="auth-status-subnote">
            <strong>{{ t('enterprise_approval_history_reviewed_meta_label') }}</strong>
            <span>{{ enterpriseApprovalReviewFollowupMetaText }}</span>
          </div>
          <div v-if="enterpriseApprovalReviewFollowup.review_note" class="auth-status-subnote">
            <strong>{{ t('enterprise_settings_application_review_note') }}</strong>
            <span>{{ enterpriseApprovalReviewFollowup.review_note }}</span>
          </div>
          <div class="auth-status-actions">
            <button
              class="auth-dialog-inline-action"
              type="button"
              :disabled="authLoading"
              @click="runEnterpriseApprovalFollowupAction('open-detail')"
            >
              {{ t('enterprise_approval_followup_open_detail') }}
            </button>
            <button
              class="btn-secondary"
              type="button"
              :disabled="authLoading"
              @click="runEnterpriseApprovalFollowupAction('focus-pending')"
            >
              {{ t('enterprise_approval_focus_pending') }}
            </button>
            <button
              v-if="enterpriseApprovalReviewFollowup.username"
              class="btn-ghost"
              type="button"
              :disabled="authLoading"
              @click="runEnterpriseApprovalFollowupAction('copy-username')"
            >
              {{ t('enterprise_application_copy_username') }}
            </button>
            <button
              v-if="enterpriseApprovalReviewFollowup.contact_email"
              class="btn-ghost"
              type="button"
              :disabled="authLoading"
              @click="runEnterpriseApprovalFollowupAction('copy-contact-email')"
            >
              {{ t('enterprise_application_copy_contact_email') }}
            </button>
            <button
              class="btn-ghost"
              type="button"
              :disabled="authLoading"
              @click="runEnterpriseApprovalFollowupAction('copy-summary')"
            >
              {{ t('enterprise_application_copy_summary') }}
            </button>
          </div>
        </div>

        <div
          v-if="authCanEnterpriseApprove"
          class="auth-status-note"
        >
          <div class="auth-status-note-head">
            <div>
              <strong>{{ t('auth_platform_draft_snapshot_title') }}</strong>
              <span>{{ t('auth_platform_draft_snapshot_hint') }}</span>
            </div>
            <button
              class="auth-dialog-inline-action"
              type="button"
              :disabled="authLoading"
              @click="openEnterpriseApprovalDraftWorkspace()"
            >
              {{ t('enterprise_approval_filter_draft_only') }}
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
          <small>{{ enterpriseApprovalDraftSummaryText }}</small>
          <div v-if="recentEnterpriseApprovalDraftApplications.length" class="auth-status-list">
            <button
              v-for="item in recentEnterpriseApprovalDraftApplications"
              :key="`auth-draft-${item.id}`"
              class="auth-status-list-item"
              type="button"
              @click="openEnterpriseApprovalDraftWorkspace(item.id)"
            >
              <strong>{{ item.company_name }}</strong>
              <span>
                {{
                  formatInlineMessage(t('auth_platform_draft_snapshot_item'), {
                    contact: item.contact_name,
                    username: item.username
                  })
                }}
              </span>
            </button>
          </div>
          <div v-else class="auth-status-empty">
            {{ t('auth_platform_draft_snapshot_empty') }}
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
          <div v-if="authCurrentEnterpriseApplication?.review_note" class="auth-status-subnote">
            <strong>{{ t('enterprise_settings_application_review_note') }}</strong>
            <span>{{ authCurrentEnterpriseApplication.review_note }}</span>
            <div class="auth-status-actions">
              <button
                class="btn-ghost"
                type="button"
                :disabled="authLoading"
                @click="copyEnterpriseApplicationReviewNote(authCurrentEnterpriseApplication)"
              >
                {{ t('enterprise_application_copy_review_note') }}
              </button>
            </div>
          </div>
          <div class="auth-status-subnote">
            <strong>{{ t('enterprise_settings_application_next_step_title') }}</strong>
            <span>{{ enterpriseApplicationNextStepText }}</span>
          </div>
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
          <div
            v-if="showEnterpriseWorkspaceBanner && enterpriseRoleWorkspaceActionItems.length"
            class="auth-status-subnote"
          >
            <strong>{{ enterpriseRoleFocus.title }}</strong>
            <span>{{ enterpriseRoleScopeText }}</span>
            <div class="auth-status-chip-list">
              <span
                v-for="label in enterpriseWorkspaceSectionLabels"
                :key="`auth-enterprise-workspace-${label}`"
                class="point-badge enterprise-settings-chip enterprise-settings-chip-muted"
              >
                {{ label }}
              </span>
            </div>
            <div class="auth-status-actions">
                <button
                  class="btn-secondary"
                  type="button"
                  :disabled="authLoading"
                  @click="applyEnterpriseWorkspaceFromAuth"
                >
                  {{ t('enterprise_settings_apply_workspace_preset') }}
                </button>
              <button
                v-for="action in enterpriseRoleWorkspaceActionItems"
                :key="`auth-enterprise-workspace-action-${action.key}`"
                :class="action.tone === 'ghost' ? 'btn-ghost' : 'btn-secondary'"
                type="button"
                :disabled="authLoading"
                @click="runEnterpriseWorkspaceAction(action.key, { closeAuth: true })"
              >
                {{ action.label }}
              </button>
            </div>
          </div>
        </div>

        <div class="auth-dialog-entry-shell">
          <div class="auth-dialog-choice-grid auth-dialog-choice-grid-identities">
            <button
              v-for="account in authPreviewIdentityOptions"
              :key="account.key"
              class="auth-dialog-choice"
              :class="[{ guest: account.role === 'guest' }, { 'is-selected': authSelectedPreviewRole === account.role }]"
              type="button"
              :disabled="authLoading"
              @click="selectAuthIdentityPreview(account)"
              @dblclick="activateAuthIdentityPreview(account)"
            >
              <strong>{{ account.label }}</strong>
              <span>{{ account.meta }}</span>
            </button>
          </div>
          <p class="auth-dialog-hint">{{ t('auth_identity_preview_hint') }}</p>

          <div class="auth-dialog-divider">{{ t('auth_entry_modes_title') }}</div>
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
              :class="{ active: authDialogView === 'personal-register' }"
              type="button"
              @click="switchAuthDialogView('personal-register')"
            >
              {{ t('auth_personal_register') }}
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
        </div>

        <template v-if="authDialogView === 'login'">
          <div class="auth-dialog-workspace">
          <div class="auth-dialog-divider">{{ t('auth_login_workspace_title') }}</div>

          <div
            v-if="authLoginRestrictionNotice"
            class="auth-status-note"
            :class="[`tone-${authLoginRestrictionNotice.tone}`]"
          >
            <strong>{{ authLoginRestrictionNotice.title }}</strong>
            <span>{{ authLoginRestrictionNotice.hint }}</span>
            <small v-if="authLoginRestrictionNotice.meta">{{ authLoginRestrictionNotice.meta }}</small>
            <p v-if="authLoginRestrictionNotice.detail" class="auth-status-note-detail">
              {{ authLoginRestrictionNotice.detail }}
            </p>
          </div>

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
            <div class="application-progress-grid">
              <article
                v-for="item in authEnterpriseRegisterFollowupProgressItems"
                :key="`auth-followup-progress-${item.key}`"
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
                <strong>{{ authEnterpriseRegisterFollowup.company_name || '—' }}</strong>
              </div>
              <div class="enterprise-settings-status-item">
                <span>{{ t('enterprise_register_username') }}</span>
                <strong>{{ authEnterpriseRegisterFollowup.username || '—' }}</strong>
              </div>
              <div v-if="authEnterpriseRegisterFollowup.contact_name" class="enterprise-settings-status-item">
                <span>{{ t('enterprise_register_contact_name') }}</span>
                <strong>{{ authEnterpriseRegisterFollowup.contact_name }}</strong>
              </div>
              <div v-if="authEnterpriseRegisterFollowup.contact_email" class="enterprise-settings-status-item">
                <span>{{ t('enterprise_register_contact_email') }}</span>
                <strong>{{ authEnterpriseRegisterFollowup.contact_email }}</strong>
              </div>
            <div v-if="authEnterpriseRegisterFollowup.submitted_at" class="enterprise-settings-status-item">
              <span>{{ t('enterprise_settings_application_submitted_at') }}</span>
              <strong>{{ authEnterpriseRegisterFollowup.submitted_at }}</strong>
            </div>
          </div>
          <small v-if="authEnterpriseRegisterFollowupUpdatedText" class="operations-last-fetched">
            {{ authEnterpriseRegisterFollowupUpdatedText }}
          </small>
          <div class="auth-status-actions">
              <button
                class="auth-dialog-inline-action"
                type="button"
                :disabled="authLoading"
                @click="continueEnterpriseRegisterFollowupEditing"
              >
                {{ t('auth_enterprise_register_followup_edit') }}
              </button>
              <button
                class="btn-ghost"
                type="button"
                :disabled="authLoading"
                @click="copyEnterpriseApplicationSummary(authEnterpriseRegisterFollowup)"
              >
                {{ t('enterprise_application_copy_summary') }}
              </button>
              <button
                class="btn-ghost"
                type="button"
                :disabled="authLoading"
                @click="copyEnterpriseApplicationCompanyName(authEnterpriseRegisterFollowup)"
              >
                {{ t('enterprise_application_copy_company_name') }}
              </button>
              <button
                v-if="authEnterpriseRegisterFollowup.contact_name"
                class="btn-ghost"
                type="button"
                :disabled="authLoading"
                @click="copyEnterpriseApplicationContactName(authEnterpriseRegisterFollowup)"
              >
                {{ t('enterprise_application_copy_contact_name') }}
              </button>
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
              <button
                class="btn-ghost"
                type="button"
                :disabled="authLoading"
                @click="dismissEnterpriseRegisterFollowup"
              >
                {{ t('auth_enterprise_register_followup_dismiss') }}
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

            <div class="auth-dialog-actions auth-dialog-actions-end">
              <button class="auth-dialog-submit auth-dialog-submit-compact" type="button" :disabled="authLoading" @click="handleAuthLogin">
                {{ authLoading ? t('auth_signing_in') : t('auth_sign_in') }}
              </button>
            </div>
          </div>
          </div>
        </template>

        <template v-else-if="authDialogView === 'personal-register'">
          <div class="auth-dialog-workspace">
            <div class="auth-dialog-divider">{{ t('auth_personal_register') }}</div>
            <p class="auth-dialog-hint">{{ t('auth_personal_register_hint') }}</p>

            <div class="auth-dialog-form">
              <label class="auth-dialog-field">
                <span>{{ t('auth_personal_register_display_name') }}</span>
                <input
                  v-model.trim="authPersonalRegisterForm.display_name"
                  :placeholder="t('auth_personal_register_display_name_placeholder')"
                />
              </label>
              <label class="auth-dialog-field">
                <span>{{ t('auth_username') }}</span>
                <input
                  v-model.trim="authPersonalRegisterForm.username"
                  :placeholder="t('auth_username_placeholder')"
                  @keydown.enter.prevent="handlePersonalRegister"
                />
              </label>
              <label class="auth-dialog-field">
                <span>{{ t('auth_password') }}</span>
                <input
                  v-model="authPersonalRegisterForm.password"
                  type="password"
                  :placeholder="t('auth_password_placeholder')"
                  @keydown.enter.prevent="handlePersonalRegister"
                />
              </label>

              <div class="auth-dialog-actions auth-dialog-actions-end">
                <button
                  class="auth-dialog-submit auth-dialog-submit-compact"
                  type="button"
                  :disabled="authLoading || !authPersonalRegisterValidation.valid"
                  @click="handlePersonalRegister"
                >
                  {{ authLoading ? t('auth_personal_register_submitting') : t('auth_personal_register_submit') }}
                </button>
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="auth-dialog-workspace">
          <div class="auth-dialog-divider">{{ t('auth_enterprise_register') }}</div>
          <p class="auth-dialog-hint">{{ t('auth_enterprise_register_hint') }}</p>
          <div
            v-if="authIsEnterpriseRole && authCurrentEnterpriseApplication"
            class="auth-status-note"
            :class="{
              'tone-pending': authCurrentAccountStatus === 'pending',
              'tone-rejected': authCurrentAccountStatus === 'rejected'
            }"
          >
            <div class="auth-status-note-head">
              <div>
                <strong>{{ t('auth_enterprise_register_existing_title') }}</strong>
                <span>{{ authEnterpriseRegisterExistingHint }}</span>
              </div>
              <button
                class="auth-dialog-inline-action"
                type="button"
                :disabled="authEnterpriseRegisterLoading"
                @click="runAuthEnterpriseRegisterExistingPrimaryAction"
              >
                {{ authEnterpriseRegisterExistingPrimaryActionLabel }}
              </button>
            </div>
            <div class="enterprise-settings-status-grid auth-enterprise-status-grid">
              <div class="enterprise-settings-status-item">
                <span>{{ t('enterprise_register_company_name') }}</span>
                <strong>{{ authCurrentEnterpriseApplication.company_name || '—' }}</strong>
              </div>
              <div class="enterprise-settings-status-item">
                <span>{{ t('enterprise_register_username') }}</span>
                <strong>{{ authCurrentEnterpriseApplication.username || '—' }}</strong>
              </div>
              <div class="enterprise-settings-status-item">
                <span>{{ t('enterprise_register_contact_name') }}</span>
                <strong>{{ authCurrentEnterpriseApplication.contact_name || '—' }}</strong>
              </div>
              <div class="enterprise-settings-status-item">
                <span>{{ t('enterprise_register_contact_email') }}</span>
                <strong>{{ authCurrentEnterpriseApplication.contact_email || '—' }}</strong>
              </div>
            </div>
            <div class="application-progress-grid">
              <article
                v-for="item in authEnterpriseApplicationProgressItems"
                :key="`auth-register-progress-${item.key}`"
                class="application-progress-item"
                :class="`is-${item.tone}`"
              >
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </article>
            </div>
            <small v-if="authAccountStatusLastCheckedText" class="operations-last-fetched">
              {{ authAccountStatusLastCheckedText }}
            </small>
            <div
              v-if="authCurrentEnterpriseApplication.review_note"
              class="auth-status-subnote"
            >
              <strong>{{ t('enterprise_settings_application_review_note') }}</strong>
              <span>{{ authCurrentEnterpriseApplication.review_note }}</span>
            </div>
            <div class="auth-status-subnote">
              <strong>{{ t('enterprise_settings_application_next_step_title') }}</strong>
              <span>{{ enterpriseApplicationNextStepText }}</span>
            </div>
            <div v-if="authEnterpriseRegisterSnapshotActionItems.length" class="auth-status-subnote">
              <strong>{{ t('auth_enterprise_actions_title') }}</strong>
              <span>{{ authEnterpriseQuickActionHint }}</span>
              <div class="auth-status-actions">
                <button
                  v-for="action in authEnterpriseRegisterSnapshotActionItems"
                  :key="`auth-enterprise-register-action-${action.key}`"
                  :class="action.tone === 'ghost' ? 'btn-ghost' : 'btn-secondary'"
                  type="button"
                  :disabled="authEnterpriseRegisterLoading"
                  @click="runAuthEnterpriseRegisterExistingAction(action.key)"
                >
                  {{ action.label }}
                </button>
              </div>
            </div>
            <div
              v-if="showEnterpriseWorkspaceBanner && enterpriseRoleWorkspaceActionItems.length"
              class="auth-status-subnote"
            >
              <strong>{{ enterpriseRoleFocus.title }}</strong>
              <span>{{ enterpriseRoleScopeText }}</span>
              <div class="auth-status-chip-list">
                <span
                  v-for="label in enterpriseWorkspaceSectionLabels"
                  :key="`auth-enterprise-register-workspace-${label}`"
                  class="point-badge enterprise-settings-chip enterprise-settings-chip-muted"
                >
                  {{ label }}
                </span>
              </div>
              <div class="auth-status-actions">
                <button
                  class="btn-secondary"
                  type="button"
                  :disabled="authEnterpriseRegisterLoading"
                  @click="applyEnterpriseWorkspaceFromAuth"
                >
                  {{ t('enterprise_settings_apply_workspace_preset') }}
                </button>
                <button
                  v-for="action in enterpriseRoleWorkspaceActionItems"
                  :key="`auth-enterprise-register-workspace-action-${action.key}`"
                  :class="action.tone === 'ghost' ? 'btn-ghost' : 'btn-secondary'"
                  type="button"
                  :disabled="authEnterpriseRegisterLoading"
                  @click="runEnterpriseWorkspaceAction(action.key, { closeAuth: true })"
                >
                  {{ action.label }}
                </button>
              </div>
            </div>
          </div>
          <div v-if="authEnterpriseRegisterDraftHasContent" class="auth-status-note">
            <strong>{{ t('auth_enterprise_register_draft_title') }}</strong>
            <span>{{ t('auth_enterprise_register_draft_hint') }}</span>
            <small v-if="authEnterpriseRegisterDraftUpdatedText" class="operations-last-fetched">
              {{ authEnterpriseRegisterDraftUpdatedText }}
            </small>
          <div
            v-if="authEnterpriseRegisterDraftDiffText"
            class="auth-status-subnote"
          >
            <strong>{{ t('auth_enterprise_register_draft_compare_title') }}</strong>
            <span>{{ authEnterpriseRegisterDraftDiffText }}</span>
          </div>
          <div v-if="authCurrentEnterpriseApplication" class="auth-status-actions">
            <button
              class="btn-ghost"
              type="button"
              :disabled="authEnterpriseRegisterLoading"
              @click="useCurrentEnterpriseApplicationForRegisterDraft"
            >
              {{ t('auth_enterprise_register_existing_action_use') }}
            </button>
            <button
              class="btn-ghost"
              type="button"
              :disabled="authEnterpriseRegisterLoading"
              @click="copyEnterpriseApplicationSummary(authCurrentEnterpriseApplication)"
            >
              {{ t('enterprise_application_copy_summary') }}
            </button>
          </div>
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

            <div
              v-if="authCurrentEnterpriseApplication || authEnterpriseRegisterDraftHasContent"
              class="auth-dialog-subtle-actions"
            >
              <button
                v-if="authCurrentEnterpriseApplication"
                class="auth-dialog-subtle-action"
                type="button"
                :disabled="authEnterpriseRegisterLoading"
                @click="runAuthEnterpriseRegisterExistingPrimaryAction"
              >
                {{ authEnterpriseRegisterExistingPrimaryActionLabel }}
              </button>
              <button
                class="auth-dialog-subtle-action"
                type="button"
                :disabled="authEnterpriseRegisterLoading || !authEnterpriseRegisterDraftHasContent"
                @click="clearEnterpriseRegisterDraft"
              >
                {{ t('auth_enterprise_register_clear_draft') }}
              </button>
              <button
                v-if="authCurrentEnterpriseApplication"
                class="auth-dialog-subtle-action"
                type="button"
                :disabled="authEnterpriseRegisterLoading"
                @click="useCurrentEnterpriseApplicationForRegisterDraft"
              >
                {{ t('auth_enterprise_register_existing_action_use') }}
              </button>
            </div>
            <div class="auth-dialog-actions auth-dialog-actions-end">
              <button
                class="auth-dialog-submit auth-dialog-submit-compact"
                type="button"
                :disabled="authEnterpriseRegisterLoading || !authEnterpriseRegisterValidation.valid"
                @click="handleEnterpriseRegister"
              >
                {{ authEnterpriseRegisterLoading ? t('auth_enterprise_register_submitting') : t('auth_enterprise_register_submit') }}
              </button>
            </div>
          </div>
          </div>
        </template>
      </div>
      <aside class="auth-dialog-side-panel auth-dialog-side-panel-demo">
        <div class="auth-dialog-entry-shell auth-dialog-demo-shell">
          <div class="auth-dialog-demo-label">{{ t('auth_demo_accounts') }}</div>
          <p class="auth-dialog-hint">{{ t('auth_demo_accounts_hint') }}</p>
          <div class="auth-side-guide-list">
            <article
              v-for="item in authSideGuideItems"
              :key="item.key"
              class="auth-side-guide-item"
            >
              <strong>{{ item.title }}</strong>
              <span>{{ item.hint }}</span>
            </article>
          </div>
        </div>
        <div
          v-if="authDialogView === 'personal-register'"
          class="auth-register-sidecard auth-register-sidecard-side"
        >
          <div class="auth-register-sidecard-head">
            <strong>{{ t('auth_personal_register_panel_title') }}</strong>
            <span class="auth-register-sidecard-state" :class="{ ready: authPersonalRegisterValidation.valid }">
              {{ authPersonalRegisterStatusText }}
            </span>
          </div>
          <div class="auth-register-checklist">
            <article
              v-for="item in authPersonalRegisterValidation.items"
              :key="item.key"
              class="auth-register-check-item"
              :class="{ ready: item.valid }"
            >
              <strong>{{ item.label }}</strong>
              <span>{{ item.valid ? t('auth_personal_register_requirement_complete') : item.message }}</span>
            </article>
          </div>

          <div class="auth-register-process">
            <strong>{{ t('auth_personal_register_process_title') }}</strong>
            <ol>
              <li>{{ t('auth_personal_register_process_step_submit') }}</li>
              <li>{{ t('auth_personal_register_process_step_unlock') }}</li>
              <li>{{ t('auth_personal_register_process_step_manage') }}</li>
            </ol>
          </div>
        </div>
        <div
          v-if="authDialogView === 'enterprise-register'"
          class="auth-register-sidecard auth-register-sidecard-side"
        >
          <div class="auth-register-sidecard-head">
            <strong>{{ t('auth_enterprise_register_panel_title') }}</strong>
            <span class="auth-register-sidecard-state" :class="{ ready: authEnterpriseRegisterValidation.valid }">
              {{ authEnterpriseRegisterStatusText }}
            </span>
          </div>
          <p class="auth-dialog-hint auth-register-draft-hint">
            {{ t('auth_enterprise_register_draft_hint') }}
          </p>
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
      </aside>
      </div>
    </div>
</template>

<script>
import { computed, defineComponent, reactive, ref, watchEffect } from 'vue'

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
    const selectedPreviewRole = ref('')

    const previewCapabilityGroupsByRole = {
      guest: {
        dispatch: false,
        fault: false,
        map: false,
        data: false,
        audit: false,
        ai: false,
        platform: false
      },
      personal: {
        dispatch: true,
        fault: true,
        map: true,
        data: true,
        audit: true,
        ai: false,
        platform: false
      },
      enterprise_operator: {
        dispatch: true,
        fault: true,
        map: false,
        data: false,
        audit: false,
        ai: true,
        platform: false
      },
      enterprise_logistics: {
        dispatch: false,
        fault: false,
        map: true,
        data: true,
        audit: false,
        ai: true,
        platform: false
      },
      enterprise_admin: {
        dispatch: true,
        fault: true,
        map: true,
        data: true,
        audit: true,
        ai: true,
        platform: false
      },
      platform_admin: {
        dispatch: true,
        fault: true,
        map: true,
        data: true,
        audit: true,
        ai: true,
        platform: true
      }
    }

    const previewIdentityOptions = computed(() => {
      const ui = props.ui || {}
      const t = typeof ui.t === 'function' ? ui.t : key => key
      const demoAccounts = Array.isArray(ui.authDemoAccounts) ? ui.authDemoAccounts : []
      const desiredRoles = [
        'guest',
        'personal',
        'enterprise_admin',
        'enterprise_operator',
        'enterprise_logistics',
        'platform_admin'
      ]
      return desiredRoles
        .map(role => {
          if (role === 'guest') {
            return {
              key: 'guest',
              role: 'guest',
              username: 'guest',
              label: t('auth_role_guest'),
              meta: t('auth_enter_guest')
            }
          }
          const matched = demoAccounts.find(account => account.role === role)
          if (!matched) return null
          return {
            ...matched,
            key: role,
            role,
            label: t(`auth_role_${role}`),
            meta: matched.username
          }
        })
        .filter(Boolean)
    })

    const selectedPreviewOption = computed(() => {
      const options = previewIdentityOptions.value
      return options.find(option => option.role === selectedPreviewRole.value) || options[0] || {
        key: 'guest',
        role: 'guest',
        username: 'guest',
        label: 'guest',
        meta: ''
      }
    })

    const previewCapabilityCards = computed(() => {
      const ui = props.ui || {}
      const t = typeof ui.t === 'function' ? ui.t : key => key
      const buildStateText = typeof ui.buildAuthCapabilityStateText === 'function'
        ? ui.buildAuthCapabilityStateText
        : enabled => (enabled ? 'enabled' : 'disabled')
      const groups = previewCapabilityGroupsByRole[selectedPreviewOption.value.role] || previewCapabilityGroupsByRole.guest
      const cardDefs = [
        { key: 'dispatch', label: t('auth_capability_dispatch_label'), hint: t('auth_capability_dispatch_hint') },
        { key: 'fault', label: t('auth_capability_fault_label'), hint: t('auth_capability_fault_hint') },
        { key: 'map', label: t('auth_capability_map_label'), hint: t('auth_capability_map_hint') },
        { key: 'data', label: t('auth_capability_data_label'), hint: t('auth_capability_data_hint') },
        { key: 'audit', label: t('auth_capability_audit_label'), hint: t('auth_capability_audit_hint') },
        { key: 'ai', label: t('auth_capability_ai_label'), hint: t('auth_capability_ai_hint') },
        { key: 'platform', label: t('auth_capability_platform_label'), hint: t('auth_capability_platform_hint') }
      ]
      return cardDefs.map(item => ({
        ...item,
        enabled: Boolean(groups[item.key]),
        stateText: buildStateText(Boolean(groups[item.key]))
      }))
    })

    const previewCapabilityHint = computed(() => {
      const ui = props.ui || {}
      const t = typeof ui.t === 'function' ? ui.t : key => key
      return selectedPreviewOption.value.role === 'guest'
        ? t('auth_capabilities_guest_hint')
        : t('auth_capabilities_hint')
    })

    const sideGuideItems = computed(() => {
      const ui = props.ui || {}
      const t = typeof ui.t === 'function' ? ui.t : key => key
      const items = [
        {
          key: 'preview',
          title: t('auth_side_guide_preview_title'),
          hint: t('auth_side_guide_preview_hint')
        },
        {
          key: 'enter',
          title: t('auth_side_guide_enter_title'),
          hint: t('auth_side_guide_enter_hint')
        }
      ]
      if (ui.authDialogView === 'personal-register') {
        items.push({
          key: 'personal-register',
          title: t('auth_side_guide_personal_register_title'),
          hint: t('auth_side_guide_personal_register_hint')
        })
      }
      if (ui.authDialogView === 'enterprise-register') {
        items.push({
          key: 'register',
          title: t('auth_side_guide_register_title'),
          hint: t('auth_side_guide_register_hint')
        })
      }
      return items
    })

    function selectAuthIdentityPreview(account) {
      selectedPreviewRole.value = String(account?.role || 'guest')
    }

    function activateAuthIdentityPreview(account) {
      const ui = props.ui || {}
      if (account?.role === 'guest') {
        if (typeof ui.enterGuestMode === 'function') ui.enterGuestMode()
        return
      }
      if (typeof ui.handleAuthQuickLogin === 'function') {
        ui.handleAuthQuickLogin(account)
      }
    }

    watchEffect(() => {
      const ui = props.ui || {}
      const options = previewIdentityOptions.value
      const desiredDefaultRole = ui.authAuthenticated ? String(ui.authCurrentRole || 'guest') : 'guest'
      if (!options.some(option => option.role === selectedPreviewRole.value)) {
        selectedPreviewRole.value = options.some(option => option.role === desiredDefaultRole)
          ? desiredDefaultRole
          : (options[0]?.role || 'guest')
      }
      Object.assign(exposed, ui, {
        authPreviewIdentityOptions: options,
        authSelectedPreviewRole: selectedPreviewRole.value,
        authPreviewIdentityLabel: selectedPreviewOption.value.label,
        authPreviewCapabilityCards: previewCapabilityCards.value,
        authPreviewCapabilityHint: previewCapabilityHint.value,
        authSideGuideItems: sideGuideItems.value,
        selectAuthIdentityPreview,
        activateAuthIdentityPreview
      })
    })

    return exposed
  }
})
</script>
