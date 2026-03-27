<template>
  <div v-if="showGuideCenter" class="guide-modal-mask" @click.self="closeGuideCenter">
    <section class="guide-modal">
      <header class="guide-modal-header">
        <strong>{{ guideCenterLocale.title }}</strong>
        <button class="btn-ghost" type="button" @click="closeGuideCenter">
          {{ guideCenterLocale.close }}
        </button>
      </header>
      <div class="guide-modal-body">
        <div class="guide-section">
          <div class="guide-section-title">{{ guideCenterLocale.modeTitle }}</div>
          <div class="guide-line">
            {{ guideCenterLocale.modeAutoTitle }}: {{ panelLocale.modeAutoHint }}
          </div>
          <div class="guide-line">
            {{ guideCenterLocale.modeManualTitle }}: {{ panelLocale.modeManualHint }}
          </div>
        </div>
        <div class="guide-section">
          <div class="guide-section-title">{{ guideCenterLocale.shortcutsTitle }}</div>
          <template v-if="Array.isArray(shortcutGuideEntries) && shortcutGuideEntries.length">
            <div
              v-for="entry in shortcutGuideEntries"
              :key="`guide-shortcut-${entry}`"
              class="guide-line"
            >
              {{ entry }}
            </div>
          </template>
          <template v-else>
            <div class="guide-line">{{ guideCenterLocale.shortcutCancel }}</div>
            <div class="guide-line">{{ guideCenterLocale.shortcutAlgorithm }}</div>
            <div class="guide-line">{{ guideCenterLocale.shortcutContext }}</div>
          </template>
        </div>
        <div class="guide-section">
          <div class="guide-section-title">{{ guideCenterLocale.workflowTitle }}</div>
          <div class="guide-line">{{ guideCenterLocale.workflowAuto }}</div>
          <div class="guide-line">{{ guideCenterLocale.workflowManual }}</div>
          <div class="guide-line">{{ guideCenterLocale.workflowForm }}</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'GuideCenterDialog',
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

