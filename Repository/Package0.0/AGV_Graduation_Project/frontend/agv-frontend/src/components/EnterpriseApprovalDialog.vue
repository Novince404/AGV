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
          <article class="approval-summary-card">
            <strong>{{ enterpriseApprovalSummary.pending || 0 }}</strong>
            <span>{{ t('enterprise_approval_status_pending') }}</span>
          </article>
          <article class="approval-summary-card">
            <strong>{{ enterpriseApprovalSummary.approved || 0 }}</strong>
            <span>{{ t('enterprise_approval_status_approved') }}</span>
          </article>
          <article class="approval-summary-card">
            <strong>{{ enterpriseApprovalSummary.rejected || 0 }}</strong>
            <span>{{ t('enterprise_approval_status_rejected') }}</span>
          </article>
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
          <button class="auth-dialog-inline-action" type="button" :disabled="enterpriseApprovalLoading" @click="fetchEnterpriseApplications({ forceSelectFirst: false })">
            {{ t('enterprise_approval_refresh') }}
          </button>
        </div>

        <div class="approval-layout">
          <div class="approval-list">
            <div v-if="enterpriseApprovalLoading" class="approval-empty">{{ t('enterprise_approval_loading') }}</div>
            <button
              v-for="item in enterpriseApplications"
              :key="item.id"
              class="approval-list-item"
              :class="{ active: Number(selectedEnterpriseApplicationId) === Number(item.id) }"
              type="button"
              @click="selectedEnterpriseApplicationId = item.id"
            >
              <strong>{{ item.company_name }}</strong>
              <span>{{ item.contact_name }} · {{ item.username }}</span>
              <small>{{ t(`enterprise_approval_status_${item.status}`) }}</small>
            </button>
            <div v-if="!enterpriseApprovalLoading && enterpriseApplications.length === 0" class="approval-empty">
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

            <label class="auth-dialog-field">
              <span>{{ t('enterprise_approval_review_note') }}</span>
              <textarea v-model.trim="enterpriseApprovalReviewNote" rows="4"></textarea>
            </label>

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
