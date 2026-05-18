<template>
  <p class="panel-hint">{{ currentCompareHint }}</p>
  <div v-if="pathCompareError" class="template-status error">{{ pathCompareError }}</div>
  <div v-else-if="pathCompareResult" class="algorithm-compare-grid">
    <article
      v-for="entry in compareResultEntries"
      :key="entry[0]"
      class="algorithm-compare-card"
      :class="{
        active: algorithm === entry[0],
        recommended: recommendedCompareAlgorithm === entry[0]
      }"
    >
      <div class="algorithm-compare-card-head">
        <strong>{{ algorithmText(entry[0]) }}</strong>
        <button class="btn-ghost" type="button" @click="applyComparedAlgorithm(entry[0])">
          {{ compareResultBadgeText(entry[0]) }}
        </button>
      </div>
      <div class="task-line">
        {{ formatCompareResultStatus(entry[1]) }}
      </div>
      <div class="task-line">
        {{ algorithmCompareLocale.total }}:
        {{ entry[1].total_length ?? '--' }}
      </div>
      <div class="task-line">
        {{ algorithmCompareLocale.stages }}:
        {{ formatCompareStageLengths(entry[1]) || '--' }}
      </div>
      <div
        v-if="formatCompareDispatchStart(entry[1])"
        class="task-line"
        :class="{ 'task-reason': entry[1].reachable && !entry[1].dispatch_reachable }"
      >
        {{ algorithmCompareLocale.dispatchStart }}:
        {{ formatCompareDispatchStart(entry[1]) }}
      </div>
      <div v-if="entry[1].failed_stage_index !== null" class="task-line task-reason">
        {{ algorithmCompareLocale.failedStage }}: {{ Number(entry[1].failed_stage_index) + 1 }}
      </div>
    </article>
  </div>
  <div v-if="pathCompareResult" class="json-actions">
    <button
      class="btn-primary"
      type="button"
      :disabled="!authCanExperimentWrite"
      :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
      @click="saveCurrentExperimentRecordWithAuth"
    >
      {{ experimentLocale.saveCurrent }}
    </button>
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
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'AlgorithmCompareWorkspace',
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
