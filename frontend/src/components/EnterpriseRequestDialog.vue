<template>
  <div class="auth-dialog-backdrop">
    <div class="approval-dialog-card feedback-dialog-card">
      <div class="auth-dialog-header">
        <div>
          <div class="auth-dialog-kicker">{{ t('enterprise_request_entry') }}</div>
          <h2 class="auth-dialog-title">{{ t('enterprise_request_title') }}</h2>
          <p class="auth-dialog-hint">{{ t('enterprise_request_hint') }}</p>
        </div>
        <button class="auth-dialog-close" type="button" @click="closeEnterpriseRequestDialog">
          {{ t('auth_close') }}
        </button>
      </div>

      <div class="approval-summary-grid feedback-summary-grid">
        <button
          v-for="item in enterpriseRequestStatusCards"
          :key="item.key"
          class="approval-summary-card"
          :class="{ active: enterpriseRequestStatusFilter === item.key }"
          type="button"
          @click="enterpriseRequestStatusFilter = item.key"
        >
          <strong>{{ item.count }}</strong>
          <span>{{ item.label }}</span>
        </button>
      </div>

      <div class="approval-toolbar">
        <div class="task-line operations-last-fetched approval-filter-summary">
          {{ enterpriseRequestFilterSummaryText }}
        </div>
        <label class="auth-dialog-field">
          <span>{{ t('enterprise_request_filter_status') }}</span>
          <select v-model="enterpriseRequestStatusFilter">
            <option v-for="item in enterpriseRequestStatusCards" :key="`enterprise-request-status-${item.key}`" :value="item.key">
              {{ item.label }}
            </option>
          </select>
        </label>
        <label class="auth-dialog-field">
          <span>{{ t('enterprise_request_filter_category') }}</span>
          <select v-model="enterpriseRequestCategoryFilter">
            <option v-for="item in enterpriseRequestCategoryOptions" :key="`enterprise-request-category-${item.key}`" :value="item.key">
              {{ item.label }}
            </option>
          </select>
        </label>
        <label class="auth-dialog-field account-governance-search-field">
          <span>{{ t('enterprise_request_filter_search') }}</span>
          <input
            v-model.trim="enterpriseRequestSearch"
            type="text"
            :placeholder="t('enterprise_request_filter_search_placeholder')"
            @keyup.enter="fetchEnterpriseRequests({ forceSelectFirst: true })"
          />
        </label>
        <div v-if="enterpriseRequestLastFetchedText" class="task-line operations-last-fetched">
          {{ enterpriseRequestLastFetchedText }}
        </div>
        <button class="auth-dialog-inline-action" type="button" :disabled="enterpriseRequestLoading" @click="fetchEnterpriseRequests({ forceSelectFirst: false })">
          {{ enterpriseRequestLoading ? `${t('enterprise_request_refresh')}...` : t('enterprise_request_refresh') }}
        </button>
        <button class="btn-ghost" type="button" @click="resetEnterpriseRequestFilters">
          {{ t('enterprise_request_reset_filters') }}
        </button>
      </div>

      <div class="approval-layout">
        <div class="approval-list">
          <div v-if="enterpriseRequestLoading && enterpriseRequestItems.length === 0" class="approval-empty">
            {{ t('enterprise_request_loading') }}
          </div>
          <div
            v-for="item in enterpriseRequestItems"
            :key="item.id"
            class="approval-list-item"
            :class="{ active: String(selectedEnterpriseRequestId || '') === String(item.id || '') }"
            @click="selectedEnterpriseRequestId = String(item.id || '')"
          >
            <strong>{{ item.title }}</strong>
            <span class="managed-user-item-meta">{{ buildEnterpriseRequestMeta(item) }}</span>
            <div class="approval-list-meta">
              <small>{{ enterpriseRequestCategoryLabel(item.category) }}</small>
              <span class="point-badge approval-draft-badge">{{ feedbackStatusLabel(item.status) }}</span>
            </div>
          </div>
          <div v-if="!enterpriseRequestLoading && enterpriseRequestItems.length === 0" class="approval-empty">
            <strong>{{ t('enterprise_request_empty_title') }}</strong>
            <span>{{ enterpriseRequestEmptyHint }}</span>
            <div class="approval-actions approval-empty-actions">
              <button class="btn-secondary" type="button" @click="resetEnterpriseRequestFilters">
                {{ t('enterprise_request_reset_filters') }}
              </button>
            </div>
          </div>
        </div>

        <div class="approval-detail feedback-dialog-detail">
          <div class="approval-existing-note feedback-create-box">
            <strong>{{ t('enterprise_request_create_title') }}</strong>
            <p>{{ t('enterprise_request_create_hint') }}</p>
            <div class="approval-detail-grid">
              <label class="auth-dialog-field">
                <span>{{ t('enterprise_request_field_target') }}</span>
                <select v-model="enterpriseRequestDraft.target_user_id">
                  <option value="">{{ t('enterprise_request_target_placeholder') }}</option>
                  <option v-for="recipient in enterpriseRequestRecipients" :key="`enterprise-request-recipient-${recipient.id}`" :value="String(recipient.id)">
                    {{ buildEnterpriseRecipientLabel(recipient) }}
                  </option>
                </select>
              </label>
              <label class="auth-dialog-field">
                <span>{{ t('enterprise_request_field_category') }}</span>
                <select v-model="enterpriseRequestDraft.category">
                  <option value="request">{{ t('enterprise_request_category_request') }}</option>
                  <option value="error">{{ t('enterprise_request_category_error') }}</option>
                </select>
              </label>
            </div>
            <label class="auth-dialog-field">
              <span>{{ t('enterprise_request_field_title') }}</span>
              <input v-model.trim="enterpriseRequestDraft.title" type="text" :placeholder="t('enterprise_request_title_placeholder')" />
            </label>
            <label class="auth-dialog-field">
              <span>{{ t('enterprise_request_field_content') }}</span>
              <textarea
                v-model.trim="enterpriseRequestDraft.content"
                rows="4"
                :placeholder="t('enterprise_request_content_placeholder')"
              ></textarea>
            </label>
            <div class="approval-actions">
              <button class="btn-secondary" type="button" :disabled="enterpriseRequestActionLoading" @click="submitEnterpriseRequest">
                {{ enterpriseRequestActionLoading ? `${t('enterprise_request_submit')}...` : t('enterprise_request_submit') }}
              </button>
            </div>
          </div>

          <template v-if="selectedEnterpriseRequest">
            <div class="approval-detail-toolbar">
              <strong>{{ selectedEnterpriseRequest.title }}</strong>
              <div class="approval-actions approval-detail-actions">
                <span class="point-badge">{{ enterpriseRequestCategoryLabel(selectedEnterpriseRequest.category) }}</span>
                <span class="point-badge">{{ feedbackStatusLabel(selectedEnterpriseRequest.status) }}</span>
              </div>
            </div>
            <div class="approval-detail-grid">
              <div>
                <strong>{{ t('enterprise_request_field_submitter') }}</strong>
                <span>{{ buildEnterpriseRequestActor(selectedEnterpriseRequest, 'submitter') }}</span>
              </div>
              <div>
                <strong>{{ t('enterprise_request_field_target') }}</strong>
                <span>{{ buildEnterpriseRequestActor(selectedEnterpriseRequest, 'target') }}</span>
              </div>
              <div>
                <strong>{{ t('enterprise_request_field_created_at') }}</strong>
                <span>{{ selectedEnterpriseRequest.created_at || '-' }}</span>
              </div>
              <div>
                <strong>{{ t('enterprise_request_field_updated_at') }}</strong>
                <span>{{ selectedEnterpriseRequest.updated_at || '-' }}</span>
              </div>
            </div>
            <div class="approval-existing-note">
              <strong>{{ t('enterprise_request_field_content') }}</strong>
              <p>{{ selectedEnterpriseRequest.content }}</p>
            </div>
            <div v-if="selectedEnterpriseRequest.response_note" class="approval-existing-note">
              <strong>{{ t('enterprise_request_field_response_note') }}</strong>
              <p>{{ selectedEnterpriseRequest.response_note }}</p>
            </div>
            <div v-if="enterpriseRequestCanManageSelected" class="approval-existing-note feedback-action-box">
              <strong>{{ t('enterprise_request_action_title') }}</strong>
              <p>{{ t('enterprise_request_action_hint') }}</p>
              <label class="auth-dialog-field">
                <span>{{ t('enterprise_request_field_response_note') }}</span>
                <textarea
                  v-model.trim="enterpriseRequestResponseNote"
                  rows="3"
                  :placeholder="t('enterprise_request_response_placeholder')"
                ></textarea>
              </label>
              <div class="approval-actions">
                <button class="btn-ghost" type="button" :disabled="enterpriseRequestActionLoading" @click="updateSelectedEnterpriseRequestStatus('in_progress')">
                  {{ t('feedback_status_in_progress') }}
                </button>
                <button class="btn-secondary" type="button" :disabled="enterpriseRequestActionLoading" @click="updateSelectedEnterpriseRequestStatus('resolved')">
                  {{ t('feedback_status_resolved') }}
                </button>
                <button class="btn-delete" type="button" :disabled="enterpriseRequestActionLoading" @click="updateSelectedEnterpriseRequestStatus('closed')">
                  {{ t('feedback_status_closed') }}
                </button>
              </div>
            </div>
          </template>
          <div v-else class="approval-detail-empty">
            {{ t('enterprise_request_select_hint') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'EnterpriseRequestDialog',
  props: {
    ui: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const exposed = reactive({
      feedbackStatusLabel(status) {
        return exposed.t?.(`feedback_status_${status || 'open'}`) || String(status || 'open')
      },
      enterpriseRequestCategoryLabel(category) {
        return exposed.t?.(`enterprise_request_category_${category || 'request'}`) || String(category || 'request')
      },
      buildEnterpriseRequestActor(item, type) {
        if (!item) return '-'
        const prefix = type === 'target' ? 'target' : 'submitter'
        return item[`${prefix}_display_name`] || item[`${prefix}_username`] || '-'
      },
      buildEnterpriseRecipientLabel(recipient) {
        if (!recipient) return '-'
        const roleText = exposed.t?.(`auth_role_${recipient.role || 'enterprise_admin'}`) || recipient.role || '-'
        const nameText = recipient.display_name || recipient.username || '-'
        return `${nameText} · ${roleText}`
      },
      buildEnterpriseRequestMeta(item) {
        if (!item) return ''
        const submitter = item.submitter_display_name || item.submitter_username || '-'
        const target = item.target_display_name || item.target_username || '-'
        return `${submitter} → ${target}`
      }
    })

    const enterpriseRequestStatusCards = computed(() => [
      { key: 'all', label: exposed.t?.('feedback_status_all') || 'All', count: exposed.enterpriseRequestSummary?.all || 0 },
      { key: 'open', label: exposed.feedbackStatusLabel?.('open') || 'Open', count: exposed.enterpriseRequestSummary?.open || 0 },
      { key: 'in_progress', label: exposed.feedbackStatusLabel?.('in_progress') || 'In Progress', count: exposed.enterpriseRequestSummary?.in_progress || 0 },
      { key: 'resolved', label: exposed.feedbackStatusLabel?.('resolved') || 'Resolved', count: exposed.enterpriseRequestSummary?.resolved || 0 },
      { key: 'closed', label: exposed.feedbackStatusLabel?.('closed') || 'Closed', count: exposed.enterpriseRequestSummary?.closed || 0 }
    ])

    const enterpriseRequestCategoryOptions = computed(() => [
      { key: 'all', label: exposed.t?.('enterprise_request_category_all') || 'All' },
      { key: 'request', label: exposed.enterpriseRequestCategoryLabel?.('request') || 'Request' },
      { key: 'error', label: exposed.enterpriseRequestCategoryLabel?.('error') || 'Error' }
    ])

    exposed.enterpriseRequestStatusCards = enterpriseRequestStatusCards
    exposed.enterpriseRequestCategoryOptions = enterpriseRequestCategoryOptions

    watchEffect(() => {
      Object.assign(exposed, props.ui || {})
    })

    return exposed
  }
})
</script>
