<template>
<div class="auth-dialog-backdrop">
      <div class="approval-dialog-card">
        <div class="auth-dialog-header">
          <div>
            <div class="auth-dialog-kicker">{{ t('auth_role_platform_admin') }}</div>
            <h2 class="auth-dialog-title">{{ t('enterprise_approval_title') }}</h2>
            <p class="auth-dialog-hint">{{ t('enterprise_approval_hint') }}</p>
          </div>
          <button class="auth-dialog-close" type="button" @click="closeEnterpriseApprovalDialog">
            {{ t('auth_close') }}
          </button>
        </div>

        <div class="approval-summary-grid">
          <button
            class="approval-summary-card"
            :class="{ active: enterpriseApprovalStatusFilter === 'pending' }"
            type="button"
            @click="setEnterpriseApprovalStatusFilter('pending')"
          >
            <strong>{{ enterpriseApprovalSummary.pending || 0 }}</strong>
            <span>{{ t('enterprise_approval_status_pending') }}</span>
          </button>
          <button
            class="approval-summary-card"
            :class="{ active: enterpriseApprovalStatusFilter === 'approved' }"
            type="button"
            @click="setEnterpriseApprovalStatusFilter('approved')"
          >
            <strong>{{ enterpriseApprovalSummary.approved || 0 }}</strong>
            <span>{{ t('enterprise_approval_status_approved') }}</span>
          </button>
          <button
            class="approval-summary-card"
            :class="{ active: enterpriseApprovalStatusFilter === 'rejected' }"
            type="button"
            @click="setEnterpriseApprovalStatusFilter('rejected')"
          >
            <strong>{{ enterpriseApprovalSummary.rejected || 0 }}</strong>
            <span>{{ t('enterprise_approval_status_rejected') }}</span>
          </button>
        </div>

        <div v-if="recentReviewedEnterpriseApplications.length" class="approval-history-shell">
          <div class="approval-history-head">
            <strong>{{ t('enterprise_approval_history_title') }}</strong>
            <span>{{ t('enterprise_approval_history_hint') }}</span>
          </div>
          <div class="approval-history-list">
            <button
              v-for="item in recentReviewedEnterpriseApplications"
              :key="`history-${item.id}`"
              class="approval-history-card"
              type="button"
              @click="openEnterpriseApprovalDialogForItem(item.id, item.status)"
            >
              <div class="approval-history-title-row">
                <strong>{{ item.company_name }}</strong>
                <small>{{ t(`enterprise_approval_status_${item.status}`) }}</small>
              </div>
              <span>{{ formatInlineMessage(t('enterprise_approval_item_meta'), { contact: item.contact_name, username: item.username }) }}</span>
              <span>{{ formatInlineMessage(t('enterprise_approval_history_reviewed_meta'), { reviewer: item.reviewed_by || '-', reviewedAt: item.reviewed_at || item.submitted_at || '-' }) }}</span>
              <p v-if="item.review_note">{{ item.review_note }}</p>
            </button>
          </div>
        </div>

        <div class="approval-toolbar">
          <label class="auth-dialog-field">
            <span>{{ t('enterprise_approval_filter_status') }}</span>
            <select v-model="enterpriseApprovalStatusFilter">
              <option value="all">{{ t('enterprise_approval_status_all') }}</option>
              <option value="pending">{{ t('enterprise_approval_status_pending') }}</option>
              <option value="approved">{{ t('enterprise_approval_status_approved') }}</option>
              <option value="rejected">{{ t('enterprise_approval_status_rejected') }}</option>
            </select>
          </label>
          <label class="auth-dialog-field">
            <span>{{ t('enterprise_approval_filter_search') }}</span>
            <input
              v-model.trim="enterpriseApprovalSearch"
              type="text"
              :placeholder="t('enterprise_approval_filter_search_placeholder')"
            />
          </label>
          <button class="auth-dialog-inline-action" type="button" :disabled="enterpriseApprovalLoading" @click="fetchEnterpriseApplications({ forceSelectFirst: false })">
            {{ t('enterprise_approval_refresh') }}
          </button>
          <button class="btn-ghost" type="button" @click="resetEnterpriseApprovalFilters">
            {{ t('enterprise_approval_reset_filters') }}
          </button>
          <button class="btn-ghost" type="button" @click="exportEnterpriseApplicationsJson">
            {{ t('enterprise_approval_export_json') }}
          </button>
          <button class="btn-ghost" type="button" @click="exportEnterpriseApplicationsCsv">
            {{ t('enterprise_approval_export_csv') }}
          </button>
        </div>

        <div class="approval-layout">
          <div class="approval-list">
            <div v-if="enterpriseApprovalLoading" class="approval-empty">{{ t('enterprise_approval_loading') }}</div>
            <button
              v-for="item in filteredEnterpriseApplications"
              :key="item.id"
              class="approval-list-item"
              :class="{ active: Number(selectedEnterpriseApplicationId) === Number(item.id) }"
              type="button"
              @click="selectedEnterpriseApplicationId = item.id"
            >
              <strong>{{ item.company_name }}</strong>
              <span>{{ formatInlineMessage(t('enterprise_approval_item_meta'), { contact: item.contact_name, username: item.username }) }}</span>
              <small>{{ t(`enterprise_approval_status_${item.status}`) }}</small>
            </button>
            <div v-if="!enterpriseApprovalLoading && filteredEnterpriseApplications.length === 0" class="approval-empty">
              {{ t('enterprise_approval_empty') }}
            </div>
          </div>

          <div class="approval-detail" v-if="selectedEnterpriseApplication">
            <div class="approval-detail-grid">
              <div><strong>{{ t('enterprise_register_company_name') }}</strong><span>{{ selectedEnterpriseApplication.company_name }}</span></div>
              <div><strong>{{ t('enterprise_register_contact_name') }}</strong><span>{{ selectedEnterpriseApplication.contact_name }}</span></div>
              <div><strong>{{ t('enterprise_register_contact_email') }}</strong><span>{{ selectedEnterpriseApplication.contact_email }}</span></div>
              <div><strong>{{ t('enterprise_register_username') }}</strong><span>{{ selectedEnterpriseApplication.username }}</span></div>
              <div><strong>{{ t('enterprise_approval_status_label') }}</strong><span>{{ t(`enterprise_approval_status_${selectedEnterpriseApplication.status}`) }}</span></div>
              <div><strong>{{ t('enterprise_approval_submitted_at') }}</strong><span>{{ selectedEnterpriseApplication.submitted_at }}</span></div>
              <div v-if="selectedEnterpriseApplication.reviewed_at"><strong>{{ t('enterprise_approval_reviewed_at') }}</strong><span>{{ selectedEnterpriseApplication.reviewed_at }}</span></div>
              <div v-if="selectedEnterpriseApplication.reviewed_by"><strong>{{ t('enterprise_approval_reviewed_by') }}</strong><span>{{ selectedEnterpriseApplication.reviewed_by }}</span></div>
            </div>

            <div class="approval-detail-toolbar">
              <strong>{{ t('enterprise_application_progress_title') }}</strong>
              <button
                v-if="selectedEnterpriseApplication.username"
                class="btn-ghost"
                type="button"
                @click="copyEnterpriseApplicationUsername(selectedEnterpriseApplication)"
              >
                {{ t('enterprise_application_copy_username') }}
              </button>
            </div>
            <div class="application-progress-grid">
              <article
                v-for="item in selectedEnterpriseApplicationProgressItems"
                :key="`approval-progress-${item.key}`"
                class="application-progress-item"
                :class="`is-${item.tone}`"
              >
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </article>
            </div>
            <div class="approval-existing-note">
              <strong>{{ t('enterprise_approval_next_step_title') }}</strong>
              <p>{{ selectedEnterpriseApplicationNextStepText }}</p>
            </div>

            <label class="auth-dialog-field">
              <span>{{ t('enterprise_approval_review_note') }}</span>
              <textarea v-model.trim="enterpriseApprovalReviewNote" rows="4"></textarea>
            </label>

            <div v-if="selectedEnterpriseApplication.review_note" class="approval-existing-note">
              <strong>{{ t('enterprise_approval_existing_review_note') }}</strong>
              <p>{{ selectedEnterpriseApplication.review_note }}</p>
            </div>

            <div class="approval-actions">
              <button
                class="button-save"
                type="button"
                :disabled="enterpriseApprovalReviewLoading || selectedEnterpriseApplication.status !== 'pending'"
                @click="reviewEnterpriseApplication('approve')"
              >
                {{ t('enterprise_approval_approve') }}
              </button>
              <button
                class="button-danger"
                type="button"
                :disabled="enterpriseApprovalReviewLoading || selectedEnterpriseApplication.status !== 'pending'"
                @click="reviewEnterpriseApplication('reject')"
              >
                {{ t('enterprise_approval_reject') }}
              </button>
            </div>
          </div>

          <div v-else class="approval-empty approval-detail-empty">
            {{ t('enterprise_approval_select_hint') }}
          </div>
        </div>
      </div>
    </div>
</template>


<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'EnterpriseApprovalDialog',
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

