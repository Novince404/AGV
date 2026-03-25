<template>
  <div
    v-if="compareDisplayMode === 'floating' && showFloatingCompare"
    class="floating-compare-panel"
    :style="compareFloatingStyle"
  >
    <div class="floating-compare-head" @mousedown="startFloatingCompareDrag">
      <div>
        <span class="dispatch-summary-label">{{ algorithmCompareLocale.title }}</span>
        <strong>{{ taskBuilderMode === 'chain' ? taskChainLocale.title : currentTaskBuilderModeCompactLabel }}</strong>
      </div>
      <button class="btn-ghost" type="button" @mousedown.stop @click="closeFloatingCompare">×</button>
    </div>
    <div class="algorithm-compare-actions">
      <button class="btn-secondary" type="button" :disabled="pathCompareLoading" @click="compareCurrentRoute">
        {{ pathCompareLoading ? '...' : algorithmCompareLocale.run }}
      </button>
    </div>
    <AlgorithmCompareWorkspace :ui="algorithmCompareWorkspaceBindings" />
  </div>
</template>

<script>
import { defineAsyncComponent, defineComponent, reactive, watchEffect } from 'vue'

const AlgorithmCompareWorkspace = defineAsyncComponent(() => import('./AlgorithmCompareWorkspace.vue'))

export default defineComponent({
  name: 'FloatingComparePanel',
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

    return exposed
  }
})
</script>
