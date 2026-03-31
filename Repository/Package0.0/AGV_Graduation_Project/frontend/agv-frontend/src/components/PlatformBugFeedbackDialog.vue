<template>
  <div class="auth-dialog-backdrop">
    <div class="approval-dialog-card feedback-dialog-card">
      <div class="auth-dialog-header">
        <div>
          <div class="auth-dialog-kicker">{{ t('platform_bug_feedback_entry') }}</div>
          <h2 class="auth-dialog-title">{{ t('platform_bug_feedback_title') }}</h2>
          <p class="auth-dialog-hint">{{ platformBugFeedbackManagementMode ? t('platform_bug_feedback_manage_hint') : t('platform_bug_feedback_hint') }}</p>
        </div>
        <button class="auth-dialog-close" type="button" @click="closePlatformBugFeedbackDialog">
          {{ t('auth_close') }}
        </button>
      </div>

      <div class="approval-summary-grid feedback-summary-grid">
        <button
          v-for="item in platformBugFeedbackStatusCards"
          :key="item.key"
          class="approval-summary-card"
          :class="{ active: platformBugFeedbackStatusFilter === item.key }"
          type="button"
          @click="platformBugFeedbackStatusFilter = item.key"
        >
          <strong>{{ item.count }}</strong>
          <span>{{ item.label }}</span>
        </button>
      </div>

      <div class="approval-toolbar">
        <div class="task-line operations-last-fetched approval-filter-summary">
          {{ platformBugFeedbackFilterSummaryText }}
        </div>
        <label class="auth-dialog-field">
          <span>{{ t('platform_bug_feedback_filter_status') }}</span>
          <select v-model="platformBugFeedbackStatusFilter">
            <option v-for="item in platformBugFeedbackStatusCards" :key="`platform-bug-status-${item.key}`" :value="item.key">
              {{ item.label }}
            </option>
          </select>
        </label>
        <label class="auth-dialog-field">
          <span>{{ t('platform_bug_feedback_filter_category') }}</span>
          <select v-model="platformBugFeedbackCategoryFilter">
            <option v-for="item in platformBugFeedbackCategoryOptions" :key="`platform-bug-category-${item.key}`" :value="item.key">
              {{ item.label }}
            </option>
          </select>
        </label>
        <label class="auth-dialog-field account-governance-search-field">
          <span>{{ t('platform_bug_feedback_filter_search') }}</span>
          <input
            v-model.trim="platformBugFeedbackSearch"
            type="text"
            :placeholder="t('platform_bug_feedback_filter_search_placeholder')"
            @keyup.enter="fetchPlatformBugFeedback({ forceSelectFirst: true })"
          />
        </label>
        <div v-if="platformBugFeedbackLastFetchedText" class="task-line operations-last-fetched">
          {{ platformBugFeedbackLastFetchedText }}
        </div>
        <button class="auth-dialog-inline-action" type="button" :disabled="platformBugFeedbackLoading" @click="fetchPlatformBugFeedback({ forceSelectFirst: false })">
          {{ platformBugFeedbackLoading ? `${t('platform_bug_feedback_refresh')}...` : t('platform_bug_feedback_refresh') }}
        </button>
        <button class="btn-ghost" type="button" @click="resetPlatformBugFeedbackFilters">
          {{ t('platform_bug_feedback_reset_filters') }}
        </button>
      </div>

      <div class="approval-layout">
        <div class="approval-list">
          <div v-if="platformBugFeedbackLoading && platformBugFeedbackItems.length === 0" class="approval-empty">
            {{ t('platform_bug_feedback_loading') }}
          </div>
          <div
            v-for="item in platformBugFeedbackItems"
            :key="item.id"
            class="approval-list-item"
            :class="{ active: String(selectedPlatformBugFeedbackId || '') === String(item.id || '') }"
            @click="selectedPlatformBugFeedbackId = String(item.id || '')"
          >
            <strong>{{ item.title }}</strong>
            <span class="managed-user-item-meta">{{ buildPlatformBugMeta(item) }}</span>
            <div class="approval-list-meta">
              <small>{{ platformBugCategoryLabel(item.category) }}</small>
              <span class="point-badge approval-draft-badge">{{ feedbackStatusLabel(item.status) }}</span>
            </div>
          </div>
          <div v-if="!platformBugFeedbackLoading && platformBugFeedbackItems.length === 0" class="approval-empty">
            <strong>{{ t('platform_bug_feedback_empty_title') }}</strong>
            <span>{{ platformBugFeedbackEmptyHint }}</span>
            <div class="approval-actions approval-empty-actions">
              <button class="btn-secondary" type="button" @click="resetPlatformBugFeedbackFilters">
                {{ t('platform_bug_feedback_reset_filters') }}
              </button>
            </div>
          </div>
        </div>

        <div class="approval-detail feedback-dialog-detail">
          <div class="approval-existing-note feedback-create-box">
            <strong>{{ t('platform_bug_feedback_create_title') }}</strong>
            <p>{{ t('platform_bug_feedback_create_hint') }}</p>
            <div class="approval-detail-grid">
              <label class="auth-dialog-field">
                <span>{{ t('platform_bug_feedback_field_category') }}</span>
                <select v-model="platformBugFeedbackDraft.category">
                  <option value="ui">{{ t('platform_bug_feedback_category_ui') }}</option>
                  <option value="logic">{{ t('platform_bug_feedback_category_logic') }}</option>
                  <option value="data">{{ t('platform_bug_feedback_category_data') }}</option>
                  <option value="permission">{{ t('platform_bug_feedback_category_permission') }}</option>
                  <option value="other">{{ t('platform_bug_feedback_category_other') }}</option>
                </select>
              </label>
            </div>
            <label class="auth-dialog-field">
              <span>{{ t('platform_bug_feedback_field_title') }}</span>
              <input v-model.trim="platformBugFeedbackDraft.title" type="text" :placeholder="t('platform_bug_feedback_title_placeholder')" />
            </label>
            <label class="auth-dialog-field">
              <span>{{ t('platform_bug_feedback_field_content') }}</span>
              <textarea
                v-model.trim="platformBugFeedbackDraft.content"
                rows="4"
                :placeholder="t('platform_bug_feedback_content_placeholder')"
              ></textarea>
            </label>
            <div class="approval-actions">
              <button class="btn-secondary" type="button" :disabled="platformBugFeedbackActionLoading" @click="submitPlatformBugFeedback">
                {{ platformBugFeedbackActionLoading ? `${t('platform_bug_feedback_submit')}...` : t('platform_bug_feedback_submit') }}
              </button>
            </div>
          </div>

          <template v-if="selectedPlatformBugFeedback">
            <div class="approval-detail-toolbar">
              <strong>{{ selectedPlatformBugFeedback.title }}</strong>
              <div class="approval-actions approval-detail-actions">
                <span class="point-badge">{{ platformBugCategoryLabel(selectedPlatformBugFeedback.category) }}</span>
                <span class="point-badge">{{ feedbackStatusLabel(selectedPlatformBugFeedback.status) }}</span>
              </div>
            </div>
            <div class="approval-detail-grid">
              <div>
                <strong>{{ t('platform_bug_feedback_field_submitter') }}</strong>
                <span>{{ selectedPlatformBugFeedback.submitter_display_name || selectedPlatformBugFeedback.submitter_username || '-' }}</span>
              </div>
              <div>
                <strong>{{ t('account_governance_field_role') }}</strong>
                <span>{{ t(`auth_role_${selectedPlatformBugFeedback.submitter_role || 'guest'}`) }}</span>
              </div>
              <div>
                <strong>{{ t('enterprise_request_field_created_at') }}</strong>
                <span>{{ selectedPlatformBugFeedback.created_at || '-' }}</span>
              </div>
              <div>
                <strong>{{ t('enterprise_request_field_updated_at') }}</strong>
                <span>{{ selectedPlatformBugFeedback.updated_at || '-' }}</span>
              </div>
            </div>
            <div class="approval-existing-note">
              <strong>{{ t('platform_bug_feedback_field_content') }}</strong>
              <p>{{ selectedPlatformBugFeedback.content }}</p>
            </div>
            <div v-if="selectedPlatformBugFeedback.response_note" class="approval-existing-note">
              <strong>{{ t('enterprise_request_field_response_note') }}</strong>
              <p>{{ selectedPlatformBugFeedback.response_note }}</p>
            </div>
            <div v-if="platformBugFeedbackCanManageSelected" class="approval-existing-note feedback-action-box">
              <strong>{{ t('platform_bug_feedback_action_title') }}</strong>
              <p>{{ t('platform_bug_feedback_action_hint') }}</p>
              <label class="auth-dialog-field">
                <span>{{ t('enterprise_request_field_response_note') }}</span>
                <textarea
                  v-model.trim="platformBugFeedbackResponseNote"
                  rows="3"
                  :placeholder="t('platform_bug_feedback_response_placeholder')"
                ></textarea>
              </label>
              <div class="approval-actions">
                <button class="btn-ghost" type="button" :disabled="platformBugFeedbackActionLoading" @click="updateSelectedPlatformBugFeedbackStatus('in_progress')">
                  {{ t('feedback_status_in_progress') }}
                </button>
                <button class="btn-secondary" type="button" :disabled="platformBugFeedbackActionLoading" @click="updateSelectedPlatformBugFeedbackStatus('resolved')">
                  {{ t('feedback_status_resolved') }}
                </button>
                <button class="btn-delete" type="button" :disabled="platformBugFeedbackActionLoading" @click="updateSelectedPlatformBugFeedbackStatus('closed')">
                  {{ t('feedback_status_closed') }}
                </button>
              </div>
            </div>
          </template>
          <div v-else class="approval-detail-empty">
            {{ t('platform_bug_feedback_select_hint') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'PlatformBugFeedbackDialog',
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
      platformBugCategoryLabel(category) {
        return exposed.t?.(`platform_bug_feedback_category_${category || 'ui'}`) || String(category || 'ui')
      },
      buildPlatformBugMeta(item) {
        if (!item) return ''
        const submitter = item.submitter_display_name || item.submitter_username || '-'
        const role = exposed.t?.(`auth_role_${item.submitter_role || 'guest'}`) || item.submitter_role || '-'
        return `${submitter} · ${role}`
      }
    })

    const platformBugFeedbackStatusCards = computed(() => [
      { key: 'all', label: exposed.t?.('feedback_status_all') || 'All', count: exposed.platformBugFeedbackSummary?.all || 0 },
      { key: 'open', label: exposed.feedbackStatusLabel?.('open') || 'Open', count: exposed.platformBugFeedbackSummary?.open || 0 },
      { key: 'in_progress', label: exposed.feedbackStatusLabel?.('in_progress') || 'In Progress', count: exposed.platformBugFeedbackSummary?.in_progress || 0 },
      { key: 'resolved', label: exposed.feedbackStatusLabel?.('resolved') || 'Resolved', count: exposed.platformBugFeedbackSummary?.resolved || 0 },
      { key: 'closed', label: exposed.feedbackStatusLabel?.('closed') || 'Closed', count: exposed.platformBugFeedbackSummary?.closed || 0 }
    ])

    const platformBugFeedbackCategoryOptions = computed(() => [
      { key: 'all', label: exposed.t?.('platform_bug_feedback_category_all') || 'All' },
      { key: 'ui', label: exposed.platformBugCategoryLabel?.('ui') || 'UI' },
      { key: 'logic', label: exposed.platformBugCategoryLabel?.('logic') || 'Logic' },
      { key: 'data', label: exposed.platformBugCategoryLabel?.('data') || 'Data' },
      { key: 'permission', label: exposed.platformBugCategoryLabel?.('permission') || 'Permission' },
      { key: 'other', label: exposed.platformBugCategoryLabel?.('other') || 'Other' }
    ])

    exposed.platformBugFeedbackStatusCards = platformBugFeedbackStatusCards
    exposed.platformBugFeedbackCategoryOptions = platformBugFeedbackCategoryOptions

    watchEffect(() => {
      Object.assign(exposed, props.ui || {})
    })

    return exposed
  }
})
</script>
