<template>
  <div class="dispatch-control-summary">
    <button class="dispatch-summary dispatch-summary-button" type="button" @click="toggleDispatchModeFromSummary">
      <span class="dispatch-summary-label">{{ panelLocale.currentMode }}</span>
      <strong>{{ currentDispatchModeLabel }}</strong>
    </button>
    <button
      class="dispatch-summary dispatch-summary-button dispatch-algorithm-note"
      type="button"
      @click="toggleAlgorithmMode"
    >
      <span class="dispatch-summary-label">{{ t('algorithm') }}</span>
      <strong>{{ algorithmText(algorithm) }}</strong>
      <p>{{ algorithmHintText }}</p>
    </button>

    <div
      v-if="compareDisplayMode === 'panel'"
      :ref="setComparePanelRoot"
      class="dispatch-summary algorithm-compare-panel"
    >
      <div class="algorithm-compare-header">
        <div>
          <span class="dispatch-summary-label">{{ algorithmCompareLocale.title }}</span>
          <strong>{{ taskBuilderMode === 'chain' ? taskChainLocale.title : currentTaskBuilderModeCompactLabel }}</strong>
        </div>
        <div class="algorithm-compare-actions">
          <button class="btn-ghost" type="button" @click="toggleComparePanelExpanded">
            {{ comparePanelExpanded ? panelLocale.collapse : panelLocale.expand }}
          </button>
          <button class="btn-secondary" type="button" :disabled="pathCompareLoading" @click="compareCurrentRoute">
            {{ pathCompareLoading ? '...' : algorithmCompareLocale.run }}
          </button>
          <button
            v-if="pathCompareResult || pathCompareError"
            class="btn-ghost"
            type="button"
            @click="clearPathCompare"
          >
            {{ algorithmCompareLocale.clear }}
          </button>
        </div>
      </div>
      <template v-if="comparePanelExpanded">
        <AlgorithmCompareWorkspace :ui="algorithmCompareWorkspaceBindings" />
      </template>
    </div>

    <section v-if="uiTreatAsEnterpriseRole" class="dispatch-summary runtime-inspector-card">
      <span class="dispatch-summary-label">{{ t('runtime_inspector_title') }}</span>
      <template v-if="selectedAgv && selectedAgv.source === 'backend'">
        <strong>
          {{ `AGV #${selectedAgv.id}` }}
          <span v-if="formatAgvBatteryText(selectedAgv)" class="runtime-inspector-battery">
            · {{ formatAgvBatteryText(selectedAgv) }}
          </span>
        </strong>
        <p>
          {{ statusText(selectedAgv.status) }} · {{ formatEnterpriseMotionStateLabel(selectedAgv.motionState) }}
        </p>
        <div v-if="selectedEnterpriseRuntimeDebugItems.length" class="runtime-inspector-chips">
          <span
            v-for="item in selectedEnterpriseRuntimeDebugItems"
            :key="`runtime-inspector-${item.key}`"
            class="runtime-inspector-chip"
            :class="`tone-${item.tone}`"
          >
            {{ item.text }}
          </span>
        </div>
      </template>
      <p v-else>{{ t('runtime_inspector_empty') }}</p>
    </section>
  </div>
</template>

<script>
import { defineAsyncComponent, defineComponent, reactive, watchEffect } from 'vue'

const AlgorithmCompareWorkspace = defineAsyncComponent(() => import('./AlgorithmCompareWorkspace.vue'))

export default defineComponent({
  name: 'DispatchControlSummaryPanel',
  components: {
    AlgorithmCompareWorkspace
  },
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

    function setComparePanelRoot(element) {
      const target = props.ui?.comparePanelRootRef
      if (target && typeof target === 'object' && 'value' in target) {
        target.value = element
      }
    }

    exposed.setComparePanelRoot = setComparePanelRoot

    return exposed
  }
})
</script>
