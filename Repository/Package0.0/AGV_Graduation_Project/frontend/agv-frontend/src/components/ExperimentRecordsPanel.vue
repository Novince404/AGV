<template>
  <div class="experiment-panel">
    <h2>{{ experimentLocale.title }}</h2>
    <p class="panel-hint">{{ experimentLocale.hint }}</p>
    <div v-if="!authCanExperimentWrite" class="permission-gate-card compact">
      <div class="empty-note">
        {{ buildCapabilityReadonlyHint('data') }}
      </div>
      <div v-if="buildEnterprisePanelReadonlyHint('data')" class="task-line permission-gate-extra">
        {{ buildEnterprisePanelReadonlyHint('data') }}
      </div>
      <button class="btn-primary" type="button" @click="openAuthDialog">
        {{ buildOperationsEntryActionText() }}
      </button>
    </div>

    <div class="experiment-action-stack">
      <button
        class="btn-primary"
        type="button"
        :disabled="!authCanExperimentWrite"
        :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
        @click="saveCurrentExperimentRecordWithAuth"
      >
        {{ experimentLocale.saveCurrent }}
      </button>
      <div class="experiment-action-grid">
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanExperimentWrite"
          :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
          @click="exportCurrentCompareResultJsonWithAuth"
        >
          {{ experimentLocale.exportCurrentJson }}
        </button>
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanExperimentWrite"
          :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
          @click="exportCurrentCompareResultCsvWithAuth"
        >
          {{ experimentLocale.exportCurrentCsv }}
        </button>
      </div>
      <div class="experiment-action-grid">
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanExperimentWrite"
          :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
          @click="exportAllExperimentRecordsJsonWithAuth"
        >
          {{ experimentLocale.exportAllJson }}
        </button>
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanExperimentWrite"
          :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
          @click="exportAllExperimentRecordsCsvWithAuth"
        >
          {{ experimentLocale.exportAllCsv }}
        </button>
      </div>
      <button
        class="btn-ghost"
        type="button"
        :disabled="!authCanExperimentWrite || experimentRecordCount === 0"
        :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
        @click="clearExperimentRecordsWithAuth"
      >
        {{ experimentLocale.clearAll }}
      </button>
    </div>

    <div v-if="experimentStatus" class="template-status" :class="experimentStatusType">
      {{ experimentStatus }}
    </div>

    <div v-if="experimentRecordCount === 0" class="empty-note">
      {{ experimentLocale.empty }}
    </div>

    <div v-else class="experiment-record-list">
      <article
        v-for="(record, recordIndex) in experimentRecords"
        :key="record.id"
        class="experiment-record-card"
        :class="{ 'search-hit': matchedExperimentRecordIds.includes(record.id) }"
      >
        <div class="experiment-record-head">
          <strong :title="`ID: ${record.id}`">{{ formatExperimentCardTitle(record, recordIndex) }}</strong>
          <span class="point-badge">{{ record.task_mode === 'chain' ? taskChainLocale.title : taskBuilderLocale.single }}</span>
        </div>
        <div class="task-line">
          {{ t('task_stages') }}: {{ record.stage_count }} | {{ experimentLocale.obstacles }}: {{ record.obstacle_count }} | {{ record.grid_cols }}x{{ record.grid_rows }}
        </div>
        <div class="task-line">
          {{ experimentLocale.route }}: {{ record.route_summary }}
        </div>
        <div class="task-line">
          {{ experimentLocale.currentAlgorithm }}: {{ algorithmText(record.current_algorithm) }}
        </div>
        <div v-if="record.recommended_algorithm" class="task-line">
          {{ experimentLocale.recommendedAlgorithm }}: {{ algorithmText(record.recommended_algorithm) }}
        </div>
        <div class="task-line">
          {{ formatExperimentAlgorithms(record) }}
        </div>
        <div class="task-line task-time">
          {{ experimentLocale.savedAt }}: {{ formatExperimentSavedAt(record.saved_at) }}
        </div>
        <div class="task-actions">
          <button class="btn-secondary task-action-button" type="button" @click="exportExperimentRecord(record, 'json')">
            JSON
          </button>
          <button class="btn-secondary task-action-button" type="button" @click="exportExperimentRecord(record, 'csv')">
            CSV
          </button>
          <button
            class="btn-delete task-action-button"
            type="button"
            :disabled="!authCanExperimentWrite"
            :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
            @click="deleteExperimentRecordWithAuth(record.id)"
          >
            {{ experimentLocale.delete }}
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'ExperimentRecordsPanel',
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
