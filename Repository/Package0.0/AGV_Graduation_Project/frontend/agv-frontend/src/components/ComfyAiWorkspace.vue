<script setup>
const props = defineProps({
  t: { type: Function, required: true },
  formatInlineMessage: { type: Function, required: true },
  canRender: { type: Boolean, default: false },
  heading: { type: String, default: '' },
  hintText: { type: String, default: '' },
  statusText: { type: String, default: '' },
  statusType: { type: String, default: 'info' },
  preflightItems: { type: Array, default: () => [] },
  healthSummaryText: { type: String, default: '' },
  healthLoading: { type: Boolean, default: false },
  comfyBaseUrl: { type: String, default: '' },
  builtinTemplates: { type: Array, default: () => [] },
  selectedBuiltinTemplate: { type: Object, default: null },
  selectedBuiltinTemplateMatchesRecommendation: { type: Boolean, default: false },
  recommendedBuiltinTemplate: { type: Object, default: null },
  recommendedBuiltinReasonText: { type: String, default: '' },
  sourceOptions: { type: Array, default: () => [] },
  workflowPresetOptions: { type: Array, default: () => [] },
  promptStyleOptions: { type: Array, default: () => [] },
  savedTemplates: { type: Array, default: () => [] },
  hasCustomTemplates: { type: Boolean, default: false },
  sharedTemplates: { type: Array, default: () => [] },
  selectedSharedTemplate: { type: Object, default: null },
  hasSharedTemplates: { type: Boolean, default: false },
  sharedTemplatesHintText: { type: String, default: '' },
  sharedTemplateMetaText: { type: String, default: '' },
  checkpointListId: { type: String, default: 'comfy-checkpoint-options' },
  availableCheckpoints: { type: Array, default: () => [] },
  workflowPresetSummary: { type: String, default: '' },
  promptStyleSummary: { type: String, default: '' },
  recommendedCheckpointSummary: { type: String, default: '' },
  submitting: { type: Boolean, default: false },
  loadingJobs: { type: Boolean, default: false },
  sharedTemplateSaving: { type: Boolean, default: false },
  sharedTemplatesLoading: { type: Boolean, default: false },
  jobs: { type: Array, default: () => [] },
  jobsTitle: { type: String, default: '' },
  jobsEmptyText: { type: String, default: '' },
  matchedJobIds: { type: Array, default: () => [] },
  deletingJobId: { type: [String, Number, null], default: null },
  lastFetchedText: { type: String, default: '' },
  noAccessActionText: { type: String, default: '' },
  onRefreshHealth: { type: Function, default: () => {} },
  onOpenBuiltinOverview: { type: Function, required: true },
  onApplyBuiltin: { type: Function, required: true },
  onLoadSource: { type: Function, required: true },
  onFillDefaultWorkflow: { type: Function, required: true },
  onSubmit: { type: Function, required: true },
  onRefreshJobs: { type: Function, required: true },
  onSaveTemplate: { type: Function, required: true },
  onApplyTemplate: { type: Function, required: true },
  onExportTemplate: { type: Function, required: true },
  onImportTemplate: { type: Function, required: true },
  onDeleteTemplate: { type: Function, required: true },
  onSaveSharedTemplate: { type: Function, required: true },
  onApplySharedTemplate: { type: Function, required: true },
  onRefreshSharedTemplates: { type: Function, required: true },
  onDeleteSharedTemplate: { type: Function, required: true },
  onPreviewAsset: { type: Function, required: true },
  onDeleteJob: { type: Function, required: true },
  onCopyPromptId: { type: Function, default: () => {} },
  onRefreshJob: { type: Function, default: () => {} },
  onReuseJob: { type: Function, default: () => {} },
  onEntryAction: { type: Function, required: true },
  formatSource: { type: Function, required: true },
  formatStatus: { type: Function, required: true },
  formatAssetActionLabel: { type: Function, required: true },
  jobMetaText: { type: Function, required: true }
})

const builtinTemplateKey = defineModel('builtinTemplateKey', { default: '' })
const sourceType = defineModel('sourceType', { default: '' })
const sourceRef = defineModel('sourceRef', { default: '' })
const checkpointName = defineModel('checkpointName', { default: '' })
const workflowPreset = defineModel('workflowPreset', { default: '' })
const promptStyle = defineModel('promptStyle', { default: '' })
const templateName = defineModel('templateName', { default: '' })
const selectedTemplateId = defineModel('selectedTemplateId', { default: '' })
const promptText = defineModel('promptText', { default: '' })
const inputJsonText = defineModel('inputJsonText', { default: '' })
const workflowJsonText = defineModel('workflowJsonText', { default: '' })
const selectedSharedTemplateId = defineModel('selectedSharedTemplateId', { default: '' })
const advancedEditorOpen = defineModel('advancedEditorOpen', { default: false })

function handleTemplateFileChange(event) {
  props.onImportTemplate(event)
}
</script>

<template>
  <div class="ai-panel">
    <h2 v-if="heading">{{ heading }}</h2>
    <p v-if="hintText" class="panel-hint">{{ hintText }}</p>

    <template v-if="canRender">
      <div v-if="statusText" :class="['template-status', statusType]">
        {{ statusText }}
      </div>

      <div class="ai-preflight-shell">
        <div class="ai-preflight-head">
          <div>
            <div class="enterprise-settings-subtitle ai-template-subtitle">{{ t('ai_render_preflight_title') }}</div>
            <div v-if="healthSummaryText" class="task-line ai-template-inline-hint">{{ healthSummaryText }}</div>
          </div>
          <button class="btn-ghost" type="button" :disabled="healthLoading" @click="onRefreshHealth">
            {{ healthLoading ? `${t('ai_render_health_refresh')}...` : t('ai_render_health_refresh') }}
          </button>
        </div>
        <div class="ai-preflight-grid">
          <article
            v-for="item in preflightItems"
            :key="item.key"
            class="ai-preflight-card"
            :class="`is-${item.status || 'info'}`"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p v-if="item.detail">{{ item.detail }}</p>
          </article>
        </div>
      </div>

      <div class="ai-template-shell ai-template-shell-highlight">
        <div class="enterprise-settings-subtitle ai-template-subtitle">{{ t('ai_render_builtin_templates') }}</div>
        <div class="task-line ai-template-inline-hint">{{ t('ai_render_builtin_templates_hint') }}</div>
        <div v-if="recommendedBuiltinTemplate && recommendedBuiltinReasonText" class="task-line ai-template-inline-hint">
          {{ formatInlineMessage(t('ai_render_recommended_template_reason_line'), {
            template: recommendedBuiltinTemplate.label,
            reason: recommendedBuiltinReasonText
          }) }}
        </div>
        <div class="ai-template-selector-row">
          <label class="ai-template-selector-field">
            <span class="ai-template-selector-label">{{ t('ai_render_builtin_template_select') }}</span>
            <select v-model="builtinTemplateKey">
              <option v-for="item in builtinTemplates" :key="item.key" :value="item.key">
                {{ item.label }}
              </option>
            </select>
          </label>
          <button class="btn-ghost ai-template-overview-trigger" type="button" @click="onOpenBuiltinOverview">
            {{ t('ai_render_show_builtin_overview') }}
          </button>
        </div>
        <article v-if="selectedBuiltinTemplate" class="ai-template-card builtin">
          <div class="ai-template-card-head">
            <div class="ai-template-card-copy">
              <strong>{{ selectedBuiltinTemplate.label }}</strong>
              <div class="task-line">{{ selectedBuiltinTemplate.hint }}</div>
            </div>
            <span class="point-badge enterprise-settings-chip">{{ selectedBuiltinTemplate.workflowPreset }}</span>
          </div>
          <div class="ai-template-chip-row">
            <span
              v-if="selectedBuiltinTemplateMatchesRecommendation"
              class="point-badge enterprise-settings-chip"
            >
              {{ t('ai_render_recommended_template_title') }}
            </span>
            <span class="point-badge enterprise-settings-chip enterprise-settings-chip-muted">
              {{ selectedBuiltinTemplate.promptStyleLabel }}
            </span>
            <span
              v-for="sourceLabel in selectedBuiltinTemplate.recommendedSources"
              :key="sourceLabel"
              class="point-badge enterprise-settings-chip enterprise-settings-chip-muted"
            >
              {{ sourceLabel }}
            </span>
          </div>
          <button class="btn-secondary full-width" type="button" :disabled="submitting" @click="onApplyBuiltin">
            {{ t('ai_render_apply_builtin') }}
          </button>
        </article>
      </div>

      <div class="ai-form-shell">
        <div class="form-grid ai-form-grid">
          <label>
            <span>{{ t('ai_render_source_type') }}</span>
            <select v-model="sourceType">
              <option v-for="option in sourceOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
          <label>
            <span>{{ t('ai_render_source_ref') }}</span>
            <input
              v-model.trim="sourceRef"
              :placeholder="t('ai_render_source_ref_placeholder')"
            />
          </label>
          <label>
            <span>{{ t('ai_render_checkpoint_name') }}</span>
            <input
              v-model.trim="checkpointName"
              :list="checkpointListId"
              :placeholder="t('ai_render_checkpoint_name_placeholder')"
            />
          </label>
          <label>
            <span>{{ t('ai_render_workflow_preset') }}</span>
            <select v-model="workflowPreset">
              <option v-for="option in workflowPresetOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
          <label>
            <span>{{ t('ai_render_prompt_style') }}</span>
            <select v-model="promptStyle">
              <option v-for="option in promptStyleOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
          <label class="span-2">
            <span>{{ t('ai_render_template_name') }}</span>
            <input
              v-model.trim="templateName"
              :placeholder="t('ai_render_template_name_placeholder')"
            />
          </label>
          <label class="span-2">
            <span>{{ t('ai_render_saved_templates') }}</span>
            <select v-model="selectedTemplateId">
              <option value="">{{ t('ai_render_template_none') }}</option>
              <option v-for="item in savedTemplates" :key="item.id" :value="item.id">
                {{ item.name }}
              </option>
            </select>
          </label>
        </div>

        <div class="ai-action-grid primary">
          <button class="btn-secondary" type="button" :disabled="submitting" @click="onLoadSource">
            {{ t('ai_render_load_source') }}
          </button>
          <button class="btn-secondary" type="button" :disabled="submitting" @click="onFillDefaultWorkflow">
            {{ t('ai_render_fill_default_workflow') }}
          </button>
          <button class="btn-primary" type="button" :disabled="submitting" @click="onSubmit">
            {{ submitting ? t('ai_render_submitting') : t('ai_render_submit') }}
          </button>
        </div>

        <div class="ai-advanced-editor">
          <button
            class="ai-advanced-toggle"
            type="button"
            :aria-expanded="advancedEditorOpen"
            @click="advancedEditorOpen = !advancedEditorOpen"
          >
            <span>{{ t('ai_render_advanced_editor') }}</span>
            <span>{{ advancedEditorOpen ? t('ai_render_advanced_collapse') : t('ai_render_advanced_expand') }}</span>
          </button>
          <div v-if="advancedEditorOpen" class="form-grid ai-form-grid ai-advanced-grid">
            <label class="span-2">
              <span>{{ t('ai_render_prompt_text') }}</span>
              <textarea v-model="promptText" rows="3" />
            </label>
            <label class="span-2">
              <span>{{ t('ai_render_input_json') }}</span>
              <textarea v-model="inputJsonText" rows="7" spellcheck="false" />
            </label>
            <label class="span-2">
              <span>{{ t('ai_render_workflow_json') }}</span>
              <textarea v-model="workflowJsonText" rows="8" spellcheck="false" />
            </label>
          </div>
        </div>

        <div class="ai-template-shell">
          <div class="enterprise-settings-subtitle ai-template-subtitle">{{ t('ai_render_saved_templates_title') }}</div>
          <div class="task-line ai-template-inline-hint">{{ t('ai_render_saved_templates_hint') }}</div>
          <div class="ai-action-grid compact">
            <button class="btn-secondary" type="button" :disabled="submitting" @click="onSaveTemplate">
              {{ t('ai_render_save_template') }}
            </button>
            <button class="btn-secondary" type="button" :disabled="submitting || !hasCustomTemplates" @click="onApplyTemplate">
              {{ t('ai_render_apply_template') }}
            </button>
            <button class="btn-secondary" type="button" :disabled="submitting || !hasCustomTemplates" @click="onExportTemplate">
              {{ t('ai_render_export_template') }}
            </button>
            <label class="btn-secondary ai-file-trigger file-trigger-button">
              <input type="file" accept="application/json" hidden @change="handleTemplateFileChange" />
              <span>{{ t('ai_render_import_template') }}</span>
            </label>
            <button class="btn-ghost" type="button" :disabled="submitting || !hasCustomTemplates" @click="onDeleteTemplate">
              {{ t('ai_render_delete_template') }}
            </button>
          </div>
        </div>

        <div class="ai-template-shell">
          <div class="enterprise-settings-subtitle ai-template-subtitle">{{ t('ai_render_shared_templates_title') }}</div>
          <div class="task-line ai-template-inline-hint">{{ sharedTemplatesHintText }}</div>
          <div class="form-grid ai-form-grid">
            <label class="span-2">
              <span>{{ t('ai_render_shared_templates_select') }}</span>
              <select v-model="selectedSharedTemplateId">
                <option value="">{{ t('ai_render_shared_template_none') }}</option>
                <option v-for="item in sharedTemplates" :key="item.id" :value="item.id">
                  {{ item.name }} · {{ item.createdBy || 'system' }}
                </option>
              </select>
            </label>
          </div>
          <div v-if="selectedSharedTemplate" class="task-line panel-hint">
            {{ sharedTemplateMetaText }}
          </div>
          <div v-else-if="!sharedTemplatesLoading && !hasSharedTemplates" class="empty-note">
            {{ t('ai_render_shared_templates_empty') }}
          </div>
          <div class="ai-action-grid compact">
            <button class="btn-secondary" type="button" :disabled="submitting || sharedTemplateSaving" @click="onSaveSharedTemplate">
              {{ t('ai_render_save_shared_template') }}
            </button>
            <button class="btn-secondary" type="button" :disabled="submitting || !hasSharedTemplates" @click="onApplySharedTemplate">
              {{ t('ai_render_apply_shared_template') }}
            </button>
            <button class="btn-secondary" type="button" :disabled="sharedTemplatesLoading" @click="onRefreshSharedTemplates">
              {{ sharedTemplatesLoading ? `${t('ai_render_refresh')}...` : t('ai_render_shared_templates_refresh') }}
            </button>
            <button class="btn-ghost" type="button" :disabled="submitting || !selectedSharedTemplate?.editable" @click="onDeleteSharedTemplate">
              {{ t('ai_render_delete_shared_template') }}
            </button>
          </div>
        </div>

        <datalist :id="checkpointListId">
          <option v-for="checkpointItem in availableCheckpoints" :key="checkpointItem" :value="checkpointItem" />
        </datalist>

        <div class="ai-status-stack">
          <div class="task-line panel-hint">
            {{ t('ai_render_default_workflow_hint') }}
          </div>
          <div class="task-line panel-hint">
            {{ workflowPresetSummary }}
          </div>
          <div class="task-line panel-hint">
            {{ promptStyleSummary }}
          </div>
          <div class="task-line panel-hint">
            {{ recommendedCheckpointSummary }}
          </div>
        </div>
      </div>

      <div class="operations-toolbar ai-toolbar">
        <div v-if="lastFetchedText" class="task-line operations-last-fetched">
          {{ lastFetchedText }}
        </div>
        <button class="btn-secondary" type="button" :disabled="loadingJobs" @click="onRefreshJobs">
          {{ loadingJobs ? `${t('ai_render_refresh')}...` : t('ai_render_refresh') }}
        </button>
      </div>

      <div class="enterprise-settings-subsection" v-if="jobsTitle">
        <div class="enterprise-settings-subtitle">{{ jobsTitle }}</div>
      </div>

      <div v-if="loadingJobs && jobs.length === 0" class="template-status info">
        {{ t('ai_render_loading') }}
      </div>

      <div v-else-if="jobs.length === 0" class="empty-note">
        {{ jobsEmptyText || t('ai_render_empty') }}
      </div>

      <div v-else class="ai-jobs-list">
        <article
          v-for="job in jobs"
          :key="job.id"
          class="ai-job-card"
          :class="{ 'search-hit': matchedJobIds.includes(job.id) }"
        >
          <div class="ai-job-head">
            <div>
              <strong>#{{ job.id }} · {{ formatSource(job) }}</strong>
              <div class="task-line">{{ jobMetaText(job) }}</div>
            </div>
            <span class="point-badge">{{ formatStatus(job.status) }}</span>
          </div>
          <div v-if="job.error_message" class="task-line template-status error">
            {{ job.error_message }}
          </div>
          <div class="ai-job-debug-grid">
            <div>
              <span>{{ t('ai_render_prompt_id') }}</span>
              <code>{{ job.prompt_id || '—' }}</code>
            </div>
            <div>
              <span>{{ t('ai_render_comfy_base_url') }}</span>
              <code>{{ comfyBaseUrl || '—' }}</code>
            </div>
          </div>
          <div v-if="job.asset_urls?.length" class="ai-job-assets">
            <button
              v-for="(assetUrl, assetIndex) in job.asset_urls"
              :key="`${job.id}-asset-${assetIndex}`"
              class="ai-job-asset-link"
              type="button"
              @click="onPreviewAsset(job, assetUrl, assetIndex)"
            >
              {{ formatAssetActionLabel(job, assetIndex) }}
            </button>
          </div>
          <div class="ai-job-actions">
            <button
              class="btn-secondary"
              type="button"
              :disabled="!job.prompt_id"
              @click="onCopyPromptId(job)"
            >
              {{ t('ai_render_copy_prompt_id') }}
            </button>
            <button class="btn-secondary" type="button" @click="onRefreshJob(job.id)">
              {{ t('ai_render_refresh_job') }}
            </button>
            <button class="btn-secondary" type="button" @click="onReuseJob(job)">
              {{ t('ai_render_reuse_job') }}
            </button>
            <button
              class="btn-danger"
              type="button"
              :disabled="deletingJobId === job.id"
              @click="onDeleteJob(job.id)"
            >
              {{ deletingJobId === job.id ? `${t('ai_render_delete')}...` : t('ai_render_delete') }}
            </button>
          </div>
        </article>
      </div>
    </template>

    <div v-else class="operations-login-card">
      <div class="empty-note">
        {{ hintText }}
      </div>
      <button class="btn-primary" type="button" @click="onEntryAction">
        {{ noAccessActionText }}
      </button>
    </div>
  </div>
</template>
