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
          <small v-if="enterpriseApprovalReviewFollowupUpdatedText" class="operations-last-fetched">
            {{ enterpriseApprovalReviewFollowupUpdatedText }}
          </small>
          <div class="auth-status-subnote">
            <strong>{{ t('enterprise_approval_next_step_title') }}</strong>
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
            <div v-if="authEnterpriseRegisterExistingActionItems.length" class="auth-status-subnote">
              <strong>{{ t('auth_enterprise_actions_title') }}</strong>
              <span>{{ authEnterpriseQuickActionHint }}</span>
              <div class="auth-status-actions">
                <button
                  v-for="action in authEnterpriseRegisterExistingActionItems"
                  :key="`auth-enterprise-register-action-${action.key}`"
                  :class="action.tone === 'ghost' ? 'btn-ghost' : 'btn-secondary'"
                  type="button"
                  :disabled="authEnterpriseRegisterLoading"
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
            <div class="auth-status-actions">
              <button
                class="auth-dialog-inline-action"
                type="button"
                :disabled="authEnterpriseRegisterLoading"
                @click="runAuthEnterpriseRegisterExistingPrimaryAction"
              >
                {{ authEnterpriseRegisterExistingPrimaryActionLabel }}
              </button>
              <button
                class="btn-ghost"
                type="button"
                :disabled="authEnterpriseRegisterLoading"
                @click="copyEnterpriseApplicationSummary(authCurrentEnterpriseApplication)"
              >
                {{ t('enterprise_application_copy_summary') }}
              </button>
              <button
                class="btn-ghost"
                type="button"
                :disabled="authEnterpriseRegisterLoading"
                @click="refreshEnterpriseAccountStatus"
              >
                {{ t('auth_status_notice_refresh_action') }}
              </button>
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
                v-if="authCurrentEnterpriseApplication"
                class="btn-ghost"
                type="button"
                :disabled="authEnterpriseRegisterLoading"
                @click="runAuthEnterpriseRegisterExistingPrimaryAction"
              >
                {{ authEnterpriseRegisterExistingPrimaryActionLabel }}
              </button>
              <button
                class="btn-ghost"
                type="button"
                :disabled="authEnterpriseRegisterLoading || !authEnterpriseRegisterDraftHasContent"
                @click="clearEnterpriseRegisterDraft"
              >
                {{ t('auth_enterprise_register_clear_draft') }}
              </button>
              <button
                v-if="authCurrentEnterpriseApplication"
                class="btn-ghost"
                type="button"
                :disabled="authEnterpriseRegisterLoading"
                @click="useCurrentEnterpriseApplicationForRegisterDraft"
              >
                {{ t('auth_enterprise_register_existing_action_use') }}
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
