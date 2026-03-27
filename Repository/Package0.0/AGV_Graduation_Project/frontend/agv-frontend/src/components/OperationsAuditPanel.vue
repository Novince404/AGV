<template>
  <div class="operations-panel">
    <h2>{{ t('operations_title') }}</h2>
    <p class="panel-hint">
      {{ buildOperationsHintText() }}
    </p>

    <template v-if="authCanViewAudit">
      <div class="operations-toolbar">
        <div class="operations-filter-grid">
          <label>
            {{ t('operations_filter_resource') }}
            <select v-model="operationAuditResourceFilter">
              <option
                v-for="option in operationAuditResourceOptions"
                :key="`resource-${option.value}`"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>
          </label>
          <label>
            {{ t('operations_filter_action') }}
            <select v-model="operationAuditActionFilter">
              <option
                v-for="option in operationAuditActionOptions"
                :key="`action-${option.value}`"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>
          </label>
        </div>
        <div class="operations-toolbar-actions">
          <div v-if="operationAuditLastFetchedAt" class="task-line operations-last-fetched">
            {{ formatInlineMessage(t('operations_last_updated'), { at: operationAuditLastFetchedAt }) }}
          </div>
          <button class="btn-ghost" type="button" @click="resetOperationAuditFilters">
            {{ t('operations_reset_filters') }}
          </button>
          <button class="btn-secondary" type="button" @click="exportFilteredOperationAuditsJsonWithAuth">
            {{ t('operations_export_json') }}
          </button>
          <button class="btn-secondary" type="button" @click="exportFilteredOperationAuditsCsvWithAuth">
            {{ t('operations_export_csv') }}
          </button>
          <button class="btn-secondary" type="button" :disabled="operationAuditLoading" @click="fetchOperationAudits({ force: true })">
            {{ operationAuditLoading ? `${t('operations_refresh')}...` : t('operations_refresh') }}
          </button>
        </div>
      </div>

      <div v-if="operationAuditLoading && operationAudits.length === 0" class="template-status info">
        {{ t('operations_loading') }}
      </div>

      <div v-if="filteredOperationAudits.length === 0" class="empty-note">
        {{ t('operations_empty') }}
      </div>

      <div v-else class="operations-list">
        <article
          v-for="entry in filteredOperationAudits"
          :key="entry.id"
          class="operations-card"
          :class="{ 'search-hit': matchedOperationAuditIds.includes(entry.id) }"
        >
          <div class="operations-card-head">
            <div>
              <strong>{{ formatOperationAuditTitle(entry) }}</strong>
              <div class="task-line">{{ formatOperationAuditResourceRef(entry) }}</div>
            </div>
            <span class="point-badge">{{ operationActionLabel(entry.action) }}</span>
          </div>
          <div class="task-line">{{ formatOperationAuditOperator(entry) }}</div>
          <div class="task-line task-time">{{ entry.performed_at }}</div>
          <div v-if="formatOperationAuditMetadata(entry)" class="task-line operations-summary">
            {{ formatOperationAuditMetadata(entry) }}
          </div>
          <div class="operations-card-actions">
            <button
              class="btn-delete"
              type="button"
              :disabled="Number(deletingOperationAuditId) === Number(entry.id)"
              @click="deleteOperationAuditWithAuth(entry)"
            >
              {{
                Number(deletingOperationAuditId) === Number(entry.id)
                  ? `${t('operations_delete_record')}...`
                  : t('operations_delete_record')
              }}
            </button>
          </div>
        </article>
      </div>
    </template>

    <div v-else class="operations-login-card">
      <div class="empty-note">
        {{ buildOperationsHintText() }}
      </div>
      <button class="btn-primary" type="button" @click="openAuthDialog">
        {{ buildOperationsEntryActionText() }}
      </button>
    </div>
  </div>
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'OperationsAuditPanel',
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
