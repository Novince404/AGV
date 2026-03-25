<template>
  <div class="task-templates">
    <h2>{{ t('template_library') }}</h2>
    <p class="panel-hint">{{ t('template_hint') }}</p>
    <div v-if="!authCanTemplateWrite" class="permission-gate-card compact">
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

    <div class="template-manage">
      <h3>{{ t('template_manage') }}</h3>
      <div class="form-grid template-manage-grid">
        <label>{{ t('template_name') }}</label>
        <input
          v-model.trim="taskTemplateForm.name"
          type="text"
          :placeholder="t('template_name_placeholder')"
        />
      </div>
      <div class="template-save-actions">
        <button
          class="btn-primary full-width"
          type="button"
          :disabled="!authCanTemplateWrite"
          :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
          @click="saveCurrentTaskTemplateWithAuth"
        >
          {{ t('template_save_current') }}
        </button>
        <button
          class="btn-secondary full-width"
          type="button"
          :disabled="!authCanTemplateWrite"
          :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
          @click="saveCurrentTaskChainTemplateWithAuth"
        >
          {{ taskChainLocale.saveTemplate }}
        </button>
      </div>
      <div v-if="taskTemplateStatus" class="template-status" :class="taskTemplateStatusType">
        {{ taskTemplateStatus }}
      </div>
    </div>

    <div class="template-manage template-json-tools">
      <h3>{{ templateJsonLocale.title }}</h3>
      <p class="panel-hint">{{ templateJsonLocale.hint }}</p>
      <input
        ref="templateFileInputRef"
        class="visually-hidden"
        type="file"
        accept=".json,application/json"
        @change="handleTemplateFileChange"
      />
      <textarea
        v-model="templateJsonText"
        class="json-area"
        rows="6"
        :placeholder="templateJsonLocale.placeholder"
      ></textarea>
      <div class="template-json-action-grid">
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanTemplateWrite"
          :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
          @click="importTaskTemplatesFromJsonWithAuth"
        >
          {{ templateJsonLocale.import }}
        </button>
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanTemplateWrite"
          :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
          @click="triggerTemplateFileImport"
        >
          {{ templateJsonLocale.importFile }}
        </button>
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanTemplateWrite"
          :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
          @click="exportTaskTemplatesToJsonWithAuth"
        >
          {{ templateJsonLocale.export }}
        </button>
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanTemplateWrite"
          :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
          @click="downloadTemplateJsonFileWithAuth"
        >
          {{ templateJsonLocale.downloadFile }}
        </button>
      </div>
      <div class="template-json-action-stack">
        <button
          class="btn-ghost"
          type="button"
          :disabled="!authCanTemplateWrite"
          :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
          @click="clearTemplateJsonTextWithAuth"
        >
          {{ templateJsonLocale.clear }}
        </button>
      </div>
      <div v-if="templateJsonStatus" class="template-status" :class="templateJsonStatusType">
        {{ templateJsonStatus }}
      </div>
    </div>

    <div class="template-list">
      <article
        v-for="template in taskTemplates"
        :key="template.id"
        class="template-card"
        :class="{ 'search-hit': matchedTemplateIds.includes(template.id) }"
      >
        <div class="template-head">
          <strong>{{ taskTemplateName(template) }}</strong>
          <span class="point-badge" :class="{ custom: template.custom }">
            {{ taskTemplateTypeText(template) }}
          </span>
        </div>
        <div class="template-meta">
          {{ formatTemplateMeta(template) }}
        </div>
        <div v-if="formatTemplateStageCount(template)" class="template-meta">
          {{ formatTemplateStageCount(template) }}
        </div>
        <div class="template-meta">{{ t('task_priority') }}: {{ template.priority }}</div>
        <div class="template-actions">
          <button
            class="btn-secondary"
            type="button"
            @click="onTemplateApplyClick(template)"
            @dblclick.stop="onTemplateApplyDoubleClick(template)"
          >
            {{ t('template_apply') }}
          </button>
          <button
            class="btn-ghost"
            type="button"
            :disabled="!authCanDispatchWrite"
            :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
            @click="createTaskFromTemplateWithAuth(template)"
          >
            {{ t('template_run') }}
          </button>
          <button
            v-if="template.custom"
            class="btn-delete"
            type="button"
            :disabled="!authCanTemplateWrite"
            :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
            @click="deleteTaskTemplateWithAuth(template)"
          >
            {{ t('template_delete') }}
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

<script>
import { defineComponent, reactive, ref, watchEffect } from 'vue'

export default defineComponent({
  name: 'TaskTemplatesPanel',
  props: {
    ui: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const exposed = reactive({})
    const templateFileInputRef = ref(null)

    watchEffect(() => {
      Object.assign(exposed, props.ui || {})
    })

    function triggerTemplateFileImport() {
      templateFileInputRef.value?.click()
    }

    exposed.templateFileInputRef = templateFileInputRef
    exposed.triggerTemplateFileImport = triggerTemplateFileImport

    return exposed
  }
})
</script>
