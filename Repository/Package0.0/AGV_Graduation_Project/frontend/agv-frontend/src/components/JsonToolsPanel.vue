<template>
  <div class="json-tools">
    <h2>{{ t('json_tools') }}</h2>
    <div v-if="!authCanJsonWrite" class="permission-gate-card compact">
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
    <div class="json-example-grid">
      <button class="btn-secondary" type="button" @click="fillTaskJsonExample('single')">
        {{ taskJsonLocale.singleExample }}
      </button>
      <button class="btn-secondary" type="button" @click="fillTaskJsonExample('chain')">
        {{ taskJsonLocale.chainExample }}
      </button>
      <button class="btn-ghost" type="button" @click="downloadTaskJsonExample('single')">
        {{ taskJsonExampleFileLocale.singleDownload }}
      </button>
      <button class="btn-ghost" type="button" @click="downloadTaskJsonExample('chain')">
        {{ taskJsonExampleFileLocale.chainDownload }}
      </button>
    </div>
    <textarea
      v-model="jsonText"
      class="json-area"
      rows="8"
      :placeholder="t('json_placeholder')"
    ></textarea>
    <div class="json-actions-shell">
      <div class="json-actions-heading">
        <strong>{{ taskJsonLocale.actionTitle || t('json_tools') }}</strong>
        <span>{{ taskJsonLocale.actionHint || t('json_placeholder') }}</span>
      </div>
      <div class="json-actions-grid">
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanJsonWrite"
          :title="buildCapabilityLockedTitle('data', authCanJsonWrite)"
          @click="importTasksFromJson"
        >
          {{ taskJsonLocale.importText || t('import_json') }}
        </button>
        <label
          class="btn-secondary file-trigger-button json-file-trigger"
          :class="{ disabled: !authCanJsonWrite }"
          :title="buildCapabilityLockedTitle('data', authCanJsonWrite)"
        >
          <input
            type="file"
            accept="application/json"
            hidden
            :disabled="!authCanJsonWrite"
            @change="importTasksFromJsonFile"
          />
          <span>{{ taskJsonLocale.importFile || t('import_json') }}</span>
        </label>
        <button
          class="btn-ghost"
          type="button"
          :disabled="!authCanJsonWrite"
          :title="buildCapabilityLockedTitle('data', authCanJsonWrite)"
          @click="exportTasksToJsonWithAuth"
        >
          {{ taskJsonLocale.exportCurrent || t('export_json') }}
        </button>
        <button
          class="btn-ghost"
          type="button"
          :disabled="!authCanJsonWrite"
          :title="buildCapabilityLockedTitle('data', authCanJsonWrite)"
          @click="clearJsonTextWithAuth"
        >
          {{ taskJsonLocale.clearEditor || t('clear_json') }}
        </button>
      </div>
    </div>
    <div v-if="jsonStatus" class="json-status">{{ jsonStatus }}</div>
  </div>
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'JsonToolsPanel',
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
