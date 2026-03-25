<template>
  <div :ref="setTaskBuilderRoot" class="task-form task-builder">
    <div class="task-builder-header">
      <h2>{{ taskBuilderTitleText }}</h2>
      <button class="task-builder-mode-toggle" type="button" @click="toggleTaskBuilderMode">
        <span class="task-builder-mode-toggle-label">{{ taskBuilderLocale.switchLabel }}</span>
        <strong>{{ currentTaskBuilderModeCompactLabel }}</strong>
      </button>
    </div>
    <p class="panel-hint">{{ currentTaskBuilderHint }}</p>
    <div v-if="!authCanDispatchWrite" class="permission-gate-card compact">
      <div class="empty-note">
        {{ buildCapabilityReadonlyHint('dispatch') }}
      </div>
      <div v-if="buildEnterprisePanelReadonlyHint('dispatch')" class="task-line permission-gate-extra">
        {{ buildEnterprisePanelReadonlyHint('dispatch') }}
      </div>
      <button class="btn-primary" type="button" @click="openAuthDialog">
        {{ buildOperationsEntryActionText() }}
      </button>
    </div>
    <p v-if="manualDispatchOriginText" class="panel-hint">{{ manualDispatchOriginText }}</p>
    <p v-if="taskBuilderMode === 'chain'" class="panel-hint">{{ taskChainLocale.priorityHint }}</p>
    <div class="task-builder-meta">
      <div class="task-builder-meta-group">
        <label>{{ t('task_priority') }}</label>
        <select v-model.number="taskForm.priority">
          <option :value="5">5</option>
          <option :value="4">4</option>
          <option :value="3">3</option>
          <option :value="2">2</option>
          <option :value="1">1</option>
        </select>
      </div>
      <div class="task-builder-meta-group">
        <label>{{ t('algorithm') }}</label>
        <div class="task-builder-algorithm-switch">
          <button
            class="task-builder-algorithm-button"
            :class="{ active: algorithm === 'simple' }"
            type="button"
            @click="algorithm = 'simple'"
          >
            {{ t('algo_simple') }}
          </button>
          <button
            class="task-builder-algorithm-button"
            :class="{ active: algorithm === 'astar' }"
            type="button"
            @click="algorithm = 'astar'"
          >
            {{ t('algo_astar') }}
          </button>
        </div>
      </div>
    </div>

    <template v-if="taskBuilderMode === 'single'">
      <div class="form-grid">
        <label>{{ singleTaskStartLabelX }}</label>
        <input v-model.number="taskForm.start_x" type="number" min="0" :max="currentGridCols - 1" />
        <label>{{ singleTaskStartLabelY }}</label>
        <input v-model.number="taskForm.start_y" type="number" min="0" :max="currentGridRows - 1" />
        <label>{{ singleTaskEndLabelX }}</label>
        <input v-model.number="taskForm.end_x" type="number" min="0" :max="currentGridCols - 1" />
        <label>{{ singleTaskEndLabelY }}</label>
        <input v-model.number="taskForm.end_y" type="number" min="0" :max="currentGridRows - 1" />
      </div>
      <button
        class="btn-primary full-width"
        type="button"
        :disabled="!authCanDispatchWrite || !manualDispatchReady"
        :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
        @click="addTaskFromForm"
      >
        {{ singleTaskSubmitText }}
      </button>
    </template>

    <template v-else>
      <div class="task-chain-map-actions">
        <div class="task-chain-map-toolbar">
          <button
            class="btn-secondary"
            type="button"
            :class="{ active: taskChainMapPickActive }"
            :disabled="dispatchMode === 'manual' && !manualDispatchReady"
            @click="toggleTaskChainMapPick"
          >
            {{ taskChainMapPickButtonText }}
          </button>
          <label class="task-chain-count-control">
            <span class="task-chain-count-label">{{ taskChainMapPickUiLocale.stageCount }}</span>
            <button
              class="btn-ghost task-chain-count-button"
              type="button"
              :disabled="taskChainMapPickStageCount <= 2"
              @click="setTaskChainMapPickStageCount(taskChainMapPickStageCount - 1)"
            >
              -
            </button>
            <input
              v-model.number="taskChainMapPickStageCountInput"
              class="task-chain-count-input"
              type="number"
              min="2"
            />
            <button
              class="btn-ghost task-chain-count-button"
              type="button"
              @click="setTaskChainMapPickStageCount(taskChainMapPickStageCount + 1)"
            >
              +
            </button>
          </label>
        </div>
        <span class="task-chain-map-status">{{ taskChainMapPickStatusText }}</span>
      </div>
      <div
        v-for="(stage, index) in taskChainStages"
        :key="`chain-stage-${index}`"
        class="task-chain-stage"
      >
        <div class="task-chain-stage-head">
          <strong>{{ taskChainLocale.stage }} {{ index + 1 }}</strong>
          <button
            class="btn-ghost"
            type="button"
            :disabled="taskChainStages.length <= 2"
            @click="removeTaskChainStage(index)"
          >
            {{ taskChainLocale.removeStage }}
          </button>
        </div>
        <div class="form-grid chain-form-grid">
          <label>{{ taskChainLocale.stageLabel }}</label>
          <input v-model.trim="stage.label" type="text" :placeholder="taskChainLocale.stageLabelPlaceholder" />
          <label>{{ t('form_start_x') }}</label>
          <input v-model.number="stage.start_x" type="number" min="0" :max="currentGridCols - 1" />
          <label>{{ t('form_start_y') }}</label>
          <input v-model.number="stage.start_y" type="number" min="0" :max="currentGridRows - 1" />
          <label>{{ t('form_end_x') }}</label>
          <input v-model.number="stage.end_x" type="number" min="0" :max="currentGridCols - 1" />
          <label>{{ t('form_end_y') }}</label>
          <input v-model.number="stage.end_y" type="number" min="0" :max="currentGridRows - 1" />
        </div>
      </div>
      <div class="task-chain-actions">
        <button class="btn-secondary" type="button" @click="addTaskChainStage">
          {{ taskChainLocale.addStage }}
        </button>
        <button class="btn-ghost" type="button" @click="resetTaskChainStages">
          {{ taskChainLocale.resetStages }}
        </button>
      </div>
      <button
        class="btn-primary full-width"
        type="button"
        :disabled="!authCanDispatchWrite || taskChainStages.length < 2 || !manualDispatchReady"
        :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
        @click="addTaskChainFromForm"
      >
        {{ chainTaskSubmitText }}
      </button>
    </template>
  </div>
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'TaskBuilderPanel',
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

    function setTaskBuilderRoot(element) {
      const target = props.ui?.taskBuilderRootRef
      if (target && typeof target === 'object' && 'value' in target) {
        target.value = element
      }
    }

    exposed.setTaskBuilderRoot = setTaskBuilderRoot

    return exposed
  }
})
</script>
