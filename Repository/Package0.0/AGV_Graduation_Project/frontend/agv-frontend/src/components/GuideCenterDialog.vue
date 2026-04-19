<template>
  <Teleport to="body">
    <div
      v-if="showGuideCenter"
      class="guide-modal-mask"
      @click.self="closeGuideCenter"
    >
      <section
        class="guide-modal"
        role="dialog"
        aria-modal="true"
        :aria-label="guideCenterTitle || guideCenterLocale.title"
      >
        <header class="guide-modal-header">
          <div>
            <strong>{{ guideCenterTitle || guideCenterLocale.title }}</strong>
            <p v-if="guideCenterSubtitle" class="guide-modal-subtitle">
              {{ guideCenterSubtitle }}
            </p>
          </div>
          <button class="btn-ghost" type="button" @click="closeGuideCenter">
            {{ guideCenterLocale.close }}
          </button>
        </header>
        <div class="guide-modal-body">
          <template v-if="Array.isArray(guideCenterSections) && guideCenterSections.length">
            <details
              v-for="section in guideCenterSections"
              :key="`guide-section-${section.key}`"
              class="guide-section guide-section-collapsible"
              :open="section.open !== false"
            >
              <summary class="guide-section-summary">
                <span>{{ section.title }}</span>
                <small v-if="section.hint">{{ section.hint }}</small>
              </summary>
              <div class="guide-section-content">
                <div
                  v-for="(line, index) in section.lines"
                  :key="`guide-section-line-${section.key}-${index}`"
                  class="guide-line"
                >
                  {{ line }}
                </div>
              </div>
            </details>
          </template>
          <template v-else>
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
          <div
            v-if="Array.isArray(statusGuideEntries) && statusGuideEntries.length"
            class="guide-section"
          >
            <div class="guide-section-title">{{ guideCenterLocale.statusTitle }}</div>
            <div
              v-for="entry in statusGuideEntries"
              :key="`guide-status-${entry}`"
              class="guide-line"
            >
              {{ entry }}
            </div>
          </div>
          <div
            v-if="Array.isArray(topologyGuideEntries) && topologyGuideEntries.length"
            class="guide-section"
          >
            <div class="guide-section-title">{{ guideCenterLocale.topologyTitle }}</div>
            <div
              v-for="entry in topologyGuideEntries"
              :key="`guide-topology-${entry}`"
              class="guide-line"
            >
              {{ entry }}
            </div>
          </div>
          </template>
        </div>
      </section>
    </div>
  </Teleport>
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
