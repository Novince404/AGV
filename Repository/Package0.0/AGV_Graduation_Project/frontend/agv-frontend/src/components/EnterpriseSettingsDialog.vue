<template>
<div class="auth-dialog-backdrop" @click.self="closeEnterpriseSettingsDialog">
      <section class="enterprise-settings-dialog-card" role="dialog" aria-modal="true">
        <header class="auth-dialog-header">
          <div>
            <div class="auth-dialog-kicker">{{ authRoleLabel }}</div>
            <h2 class="auth-dialog-title">{{ t('enterprise_settings_title') }}</h2>
            <p class="auth-dialog-hint">{{ t('enterprise_settings_hint') }}</p>
          </div>
          <button class="auth-dialog-close" type="button" @click="closeEnterpriseSettingsDialog">
            ×
          </button>
        </header>

        <div class="enterprise-settings-shell">
          <aside class="enterprise-settings-sidebar">
            <div class="enterprise-settings-sidebar-title">{{ t('enterprise_settings_navigation') }}</div>
              <button
                v-for="tab in enterpriseSettingsTabDefinitions"
                :key="tab.key"
                class="enterprise-settings-tab"
                :class="{ active: enterpriseSettingsActiveTab === tab.key, 'is-primary': tab.primary }"
                type="button"
                @click="switchEnterpriseSettingsTab(tab.key)"
              >
                <span class="enterprise-settings-tab-copy">{{ tab.label }}</span>
                <span class="enterprise-settings-tab-hint">{{ tab.hint }}</span>
                <span class="enterprise-settings-tab-badges">
                  <span class="enterprise-settings-tab-badge">
                    {{ tab.primary ? t('enterprise_settings_tab_badge_primary') : t('enterprise_settings_tab_badge_secondary') }}
                  </span>
                  <span
                    class="enterprise-settings-tab-badge enterprise-settings-tab-access-badge"
                    :class="`is-${tab.accessMode}`"
                  >
                    {{ enterpriseTabAccessLabel(tab.accessMode) }}
                  </span>
                </span>
              </button>
          </aside>

          <div class="enterprise-settings-content">
            <div class="enterprise-settings-section-title">{{ enterpriseSettingsTabLabel }}</div>
            <div class="enterprise-settings-section-meta">
              <span class="point-badge enterprise-settings-chip">
                {{ enterpriseActiveTabModeLabel }}
              </span>
              <span class="point-badge enterprise-settings-chip enterprise-settings-chip-muted">
                {{ enterpriseActiveTabAccessLabel }}
              </span>
            </div>
            <p class="panel-hint enterprise-settings-section-hint">{{ enterpriseActiveTabAccessHint }}</p>

            <template v-if="enterpriseSettingsActiveTab === 'overview'">
              <p class="panel-hint">{{ t('enterprise_settings_overview_hint') }}</p>
              <div class="enterprise-settings-focus-card">
                <strong>{{ enterpriseRoleFocus.title }}</strong>
                <p>{{ enterpriseRoleFocus.hint }}</p>
              </div>
              <div class="enterprise-settings-role-note">
                <strong>{{ t('enterprise_settings_workspace_title') }}</strong>
                <p>{{ enterpriseRoleScopeText }}</p>
                <div class="enterprise-settings-chip-list">
                  <span
                    v-for="label in enterpriseWorkspaceSectionLabels"
                    :key="`enterprise-workspace-${label}`"
                    class="point-badge enterprise-settings-chip"
                  >
                    {{ label }}
                  </span>
                </div>
              </div>
              <div class="enterprise-settings-role-note">
                <strong>{{ t('enterprise_settings_capabilities_title') }}</strong>
                <p>{{ t('enterprise_settings_capabilities_hint') }}</p>
                <div class="enterprise-settings-chip-list">
                  <span
                    v-for="item in enterpriseEnabledCapabilityCards"
                    :key="`enterprise-capability-enabled-${item.key}`"
                    class="point-badge enterprise-settings-chip"
                  >
                    {{ item.label }}
                  </span>
                </div>
                <div v-if="enterpriseReadonlyCapabilityCards.length" class="task-line">
                  {{ t('enterprise_settings_capabilities_readonly_title') }}
                </div>
                <div v-if="enterpriseReadonlyCapabilityCards.length" class="enterprise-settings-chip-list">
                  <span
                    v-for="item in enterpriseReadonlyCapabilityCards"
                    :key="`enterprise-capability-readonly-${item.key}`"
                    class="point-badge enterprise-settings-chip enterprise-settings-chip-muted"
                  >
                    {{ item.label }}
                  </span>
                </div>
              </div>
              <div class="enterprise-settings-role-note">
                <div class="enterprise-settings-status-head">
                  <div>
                    <strong>{{ t('enterprise_settings_application_status_title') }}</strong>
                    <p>{{ t('enterprise_settings_application_status_hint') }}</p>
                  </div>
                  <div class="enterprise-settings-inline-actions">
                    <button
                      v-if="authCurrentEnterpriseApplication?.username"
                      class="btn-ghost enterprise-settings-inline-button"
                      type="button"
                      @click="copyEnterpriseApplicationUsername(authCurrentEnterpriseApplication)"
                    >
                      {{ t('enterprise_application_copy_username') }}
                    </button>
                    <button class="btn-ghost enterprise-settings-inline-button" type="button" @click="refreshEnterpriseAccountStatus()">
                      {{ t('enterprise_settings_application_refresh') }}
                    </button>
                    <button
                      v-if="authCurrentEnterpriseApplication?.contact_email"
                      class="btn-ghost enterprise-settings-inline-button"
                      type="button"
                      @click="copyEnterpriseApplicationContactEmail(authCurrentEnterpriseApplication)"
                    >
                      {{ t('enterprise_application_copy_contact_email') }}
                    </button>
                  </div>
                </div>
                <div class="enterprise-settings-status-grid">
                  <div class="enterprise-settings-status-item">
                    <span>{{ t('enterprise_register_company_name') }}</span>
                    <strong>{{ authCurrentEnterpriseApplication?.company_name || authCurrentOrganizationName || '—' }}</strong>
                  </div>
                  <div class="enterprise-settings-status-item">
                    <span>{{ t('enterprise_register_username') }}</span>
                    <strong>{{ authCurrentEnterpriseApplication?.username || '—' }}</strong>
                  </div>
                  <div class="enterprise-settings-status-item">
                    <span>{{ t('enterprise_register_contact_name') }}</span>
                    <strong>{{ authCurrentEnterpriseApplication?.contact_name || '—' }}</strong>
                  </div>
                  <div class="enterprise-settings-status-item">
                    <span>{{ t('enterprise_register_contact_email') }}</span>
                    <strong>{{ authCurrentEnterpriseApplication?.contact_email || '—' }}</strong>
                  </div>
                  <div class="enterprise-settings-status-item">
                    <span>{{ t('enterprise_settings_summary_status') }}</span>
                    <strong>{{ authAccountStatusLabel }}</strong>
                  </div>
                  <div class="enterprise-settings-status-item">
                    <span>{{ t('enterprise_settings_application_submitted_at') }}</span>
                    <strong>{{ authCurrentEnterpriseApplication?.submitted_at || '—' }}</strong>
                  </div>
                  <div class="enterprise-settings-status-item">
                    <span>{{ t('enterprise_settings_application_reviewed_at') }}</span>
                    <strong>{{ authCurrentEnterpriseApplication?.reviewed_at || '—' }}</strong>
                  </div>
                  <div class="enterprise-settings-status-item">
                    <span>{{ t('enterprise_settings_application_reviewed_by') }}</span>
                    <strong>{{ authCurrentEnterpriseApplication?.reviewed_by || '—' }}</strong>
                  </div>
                </div>
                <div v-if="authAccountStatusLastCheckedText" class="task-line operations-last-fetched">
                  {{ authAccountStatusLastCheckedText }}
                </div>
                <div class="application-progress-grid">
                  <article
                    v-for="item in authEnterpriseApplicationProgressItems"
                    :key="`enterprise-settings-progress-${item.key}`"
                    class="application-progress-item"
                    :class="`is-${item.tone}`"
                  >
                    <span>{{ item.label }}</span>
                    <strong>{{ item.value }}</strong>
                  </article>
                </div>
                <div
                  v-if="authCurrentEnterpriseApplication?.review_note"
                  class="enterprise-settings-status-note"
                >
                  <strong>{{ t('enterprise_settings_application_review_note') }}</strong>
                  <p>{{ authCurrentEnterpriseApplication.review_note }}</p>
                </div>
                <div class="enterprise-settings-status-note">
                  <strong>{{ t('enterprise_settings_application_next_step_title') }}</strong>
                  <p>{{ enterpriseApplicationNextStepText }}</p>
                </div>
                <div
                  v-if="enterpriseApplicationActionItems.length"
                  class="enterprise-settings-status-note"
                >
                  <strong>{{ t('enterprise_settings_application_actions_title') }}</strong>
                  <p>{{ t('enterprise_settings_application_actions_hint') }}</p>
                  <div class="enterprise-settings-actions enterprise-settings-status-actions">
                    <button
                      v-for="action in enterpriseApplicationActionItems"
                      :key="`enterprise-application-action-${action.key}`"
                      :class="action.tone === 'ghost' ? 'btn-ghost' : 'btn-secondary'"
                      type="button"
                      @click="runEnterpriseApplicationAction(action.key)"
                    >
                      {{ action.label }}
                    </button>
                  </div>
                </div>
              </div>
              <div class="map-settings-info-grid enterprise-settings-grid">
                <div v-for="card in enterpriseOverviewCards" :key="card.key" class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ card.label }}</div>
                  <div class="map-settings-info-value">{{ card.value }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_map_profile') }}</div>
                  <div class="map-settings-info-value">{{ currentMapProfileLabel }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_dispatch_mode') }}</div>
                  <div class="map-settings-info-value">{{ currentDispatchModeLabel }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_active_tasks') }}</div>
                  <div class="map-settings-info-value">{{ enterpriseActiveTasks }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_open_faults') }}</div>
                  <div class="map-settings-info-value">{{ enterpriseOpenFaults }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_busy_agvs') }}</div>
                  <div class="map-settings-info-value">{{ enterpriseBusyAgvs }}</div>
                </div>
              </div>
              <div class="enterprise-settings-subsection">
                <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_recent_tasks_title') }}</div>
                <div v-if="enterpriseRecentTasks.length === 0" class="empty-note">{{ t('enterprise_settings_recent_tasks_empty') }}</div>
                <div v-else class="enterprise-settings-list">
                  <article v-for="task in enterpriseRecentTasks" :key="`enterprise-task-${task.id}`" class="enterprise-settings-list-item">
                    <div class="enterprise-settings-list-main">
                      <strong>{{ formatInlineMessage(t('enterprise_settings_recent_task_label'), { id: task.id, status: taskStatusText(task.status) }) }}</strong>
                      <span>{{ formatTaskCompactSummary(task) }}</span>
                    </div>
                    <div class="task-line">{{ formatTaskTime(task) || formatDateTimeInline(task.created_at) }}</div>
                  </article>
                </div>
              </div>
              <div class="enterprise-settings-subgrid">
                <div class="enterprise-settings-subsection">
                  <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_recent_faults_title') }}</div>
                  <div v-if="enterpriseRecentFaults.length === 0" class="empty-note">{{ t('enterprise_settings_recent_faults_empty') }}</div>
                  <div v-else class="enterprise-settings-list">
                    <article v-for="eventItem in enterpriseRecentFaults" :key="`enterprise-fault-${eventItem.id}`" class="enterprise-settings-list-item">
                      <div class="enterprise-settings-list-main">
                        <strong>{{ faultTypeText(eventItem.fault_type) }}</strong>
                        <span>{{ faultSeverityText(eventItem.severity) }}</span>
                      </div>
                      <div class="task-line">{{ formatDateTimeInline(eventItem.created_at) }}</div>
                    </article>
                  </div>
                </div>
                <div v-if="authCanViewAudit" class="enterprise-settings-subsection">
                  <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_recent_audit_title') }}</div>
                  <div v-if="enterpriseRecentAuditEntries.length === 0" class="empty-note">{{ t('enterprise_settings_recent_audit_empty') }}</div>
                  <div v-else class="enterprise-settings-list">
                    <article v-for="entry in enterpriseRecentAuditEntries" :key="`enterprise-audit-${entry.id}`" class="enterprise-settings-list-item">
                      <div class="enterprise-settings-list-main">
                        <strong>{{ formatOperationAuditTitle(entry) }}</strong>
                        <span>{{ formatOperationAuditOperator(entry) }}</span>
                      </div>
                      <div class="task-line">{{ formatDateTimeInline(entry.created_at) }}</div>
                    </article>
                  </div>
                </div>
              </div>
              <div class="enterprise-settings-actions">
                <button class="btn-secondary" type="button" @click="applyEnterprisePanelPreset()">
                  {{ t('enterprise_settings_apply_workspace_preset') }}
                </button>
                <button class="btn-secondary" type="button" @click="jumpFromEnterpriseSettings('control')">
                  {{ t('enterprise_settings_open_dispatch') }}
                </button>
                <button class="btn-secondary" type="button" @click="jumpFromEnterpriseSettings('queue')">
                  {{ t('enterprise_settings_open_queue') }}
                </button>
              </div>
            </template>

            <template v-else-if="enterpriseSettingsActiveTab === 'map_profiles'">
              <p class="panel-hint">{{ t('enterprise_settings_map_profiles_hint') }}</p>
              <div class="enterprise-settings-role-note">
                <strong>{{ enterpriseActiveTabModeLabel }}</strong>
                <p>{{ enterpriseActiveTabModeHint }}</p>
              </div>
              <div class="map-settings-info-grid enterprise-settings-grid">
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ settingsLocale.mapInfoProfile }}</div>
                  <div class="map-settings-info-value">{{ currentMapProfileLabel }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ settingsLocale.mapInfoSize }}</div>
                  <div class="map-settings-info-value">{{ mapSizeLabel }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ settingsLocale.mapInfoBlocked }}</div>
                  <div class="map-settings-info-value">{{ blockedCellCount }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_profile_count') }}</div>
                  <div class="map-settings-info-value">{{ mapProfiles.length }}</div>
                </div>
              </div>
              <div
                v-if="mapProfileActionSummary"
                class="map-profile-summary-card"
                :class="{
                  'is-blocked': mapProfileActionSummary.type === 'blocked',
                  'is-forced': mapProfileActionSummary.type === 'forced'
                }"
              >
                <div class="map-profile-summary-title">{{ mapProfileActionSummaryTitle() }}</div>
                <div class="map-profile-summary-text">
                  {{ mapProfileActionSummary.profileName }}
                </div>
                <div
                  v-if="mapProfileActionSummary.type === 'blocked' && mapProfileActionSummary.forceApplyAllowed"
                  class="map-profile-summary-text"
                >
                  {{ settingsLocale.mapProfileSummaryForceHint }}
                </div>
                <ul
                  v-if="mapProfileActionSummary.type === 'blocked' && Array.isArray(mapProfileActionSummary.blockers)"
                  class="map-size-preview-list compact"
                >
                  <li
                    v-for="reasonKey in mapProfileActionSummary.blockers"
                    :key="`enterprise-summary-${reasonKey}`"
                  >
                    <button
                      type="button"
                      class="map-size-preview-reason-action"
                      @click.stop="focusMapResizeReasonKey(reasonKey)"
                    >
                      {{ buildMapResizeReasonItem(reasonKey).text }}
                    </button>
                  </li>
                </ul>
                <div
                  v-if="mapProfileActionSummary.type === 'forced'"
                  class="map-profile-summary-metrics"
                >
                  <div class="map-profile-summary-metric">
                    {{ settingsLocale.mapProfileSummaryPreviousProfile.replace('{name}', mapProfileActionSummary.previousProfileName || '—') }}
                  </div>
                  <div class="map-profile-summary-metric">
                    {{ settingsLocale.mapProfileSummaryNextProfile.replace('{name}', mapProfileActionSummary.profileName || '—') }}
                  </div>
                  <div class="map-profile-summary-metric">
                    {{ settingsLocale.mapProfileSummarySizeBefore.replace('{size}', mapProfileActionSummary.previousSizeLabel || '—') }}
                  </div>
                  <div class="map-profile-summary-metric">
                    {{ settingsLocale.mapProfileSummarySizeAfter.replace('{size}', mapProfileActionSummary.nextSizeLabel || '—') }}
                  </div>
                  <div class="map-profile-summary-metric">
                    {{ settingsLocale.mapProfileSummaryBlockedBefore.replace('{count}', String(mapProfileActionSummary.previousBlockedCount ?? 0)) }}
                  </div>
                  <div class="map-profile-summary-metric">
                    {{ settingsLocale.mapProfileSummaryBlockedAfter.replace('{count}', String(mapProfileActionSummary.nextBlockedCount ?? 0)) }}
                  </div>
                  <div class="map-profile-summary-metric">
                    {{ settingsLocale.mapProfileSummaryRelocated.replace('{count}', String(mapProfileActionSummary.relocatedAgvs?.length ?? 0)) }}
                  </div>
                  <div class="map-profile-summary-metric">
                    {{ settingsLocale.mapProfileSummaryTrimmed.replace('{count}', String(mapProfileActionSummary.trimmedBlockedCount ?? 0)) }}
                  </div>
                </div>
                <div
                  v-if="mapProfileActionSummary.type === 'forced'"
                  class="map-profile-summary-actions"
                >
                  <button
                    type="button"
                    class="btn-ghost"
                    @click="exportMapProfileActionSummary"
                  >
                    {{ settingsLocale.mapProfileSummaryExport }}
                  </button>
                </div>
              </div>
              <div class="enterprise-settings-subsection">
                <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_profile_list_title') }}</div>
                <div v-if="mapProfiles.length === 0" class="empty-note">{{ t('enterprise_settings_profile_list_empty') }}</div>
                <div v-else class="map-profile-grid enterprise-settings-map-profile-grid">
                  <div
                    v-for="profile in mapProfiles"
                    :key="`enterprise-profile-${profile.key}`"
                    class="map-profile-card"
                    :class="{ 'is-current': isCurrentMapProfile(profile) }"
                  >
                    <div class="map-profile-head">
                      <div class="map-profile-name">{{ localizedMapProfileField(profile.name) }}</div>
                      <span v-if="isCurrentMapProfile(profile)" class="map-profile-badge">
                        {{ settingsLocale.mapProfileCurrent }}
                      </span>
                    </div>
                    <div class="map-profile-meta">
                      {{ profile.grid_cols }} x {{ profile.grid_rows }}
                    </div>
                    <div class="map-profile-desc">
                      {{ localizedMapProfileField(profile.description) }}
                    </div>
                    <div v-if="formatMapProfileCreatedBy(profile)" class="map-profile-operator">
                      {{ formatMapProfileCreatedBy(profile) }}
                    </div>
                    <div v-if="formatMapProfileLastOperator(profile)" class="map-profile-operator">
                      {{ formatMapProfileLastOperator(profile) }}
                    </div>
                    <div
                      v-if="mapProfilePreviewStatusText(profile)"
                      class="map-profile-preview-status"
                      :class="{
                        'is-ready': mapProfilePreviewStatus(profile) === 'ready',
                        'is-blocked': mapProfilePreviewStatus(profile) === 'blocked',
                        'is-current': mapProfilePreviewStatus(profile) === 'current'
                      }"
                    >
                      {{ mapProfilePreviewStatusText(profile) }}
                    </div>
                    <div
                      v-if="mapProfilePreviewReasonItems(profile).length > 0"
                      class="map-profile-preview-reasons"
                    >
                      <div class="map-profile-preview-reason-title">
                        {{ settingsLocale.mapProfilePreviewReasonTitle }}
                      </div>
                      <ul class="map-size-preview-list compact">
                        <li
                          v-for="reason in mapProfilePreviewReasonItems(profile)"
                          :key="`${profile.key}-${reason.key}`"
                        >
                          <button
                            type="button"
                            class="map-size-preview-reason-action"
                            @click.stop="focusMapResizeReasonItem(reason)"
                          >
                            {{ reason.text }}
                          </button>
                        </li>
                      </ul>
                    </div>
                    <div class="map-profile-actions">
                      <button
                        :class="canForceApplyMapProfile(profile) ? 'btn-danger' : 'btn-secondary'"
                        type="button"
                        :disabled="isCurrentMapProfile(profile) || Boolean(mapProfileApplyingKey) || Boolean(mapProfileDeletingKey) || Boolean(mapProfileExportingKey) || mapProfileImporting || !canApplyMapProfileWithCapability(profile)"
                        :title="buildMapProfileApplyTitle(profile)"
                        @click="applyMapProfile(profile)"
                      >
                        {{
                          isCurrentMapProfile(profile)
                            ? settingsLocale.mapProfileCurrent
                            : isMapProfileApplying(profile)
                              ? settingsLocale.mapProfileApplying
                              : canForceApplyMapProfile(profile)
                                ? settingsLocale.mapProfileForceApply
                                : settingsLocale.mapProfileApply
                        }}
                      </button>
                      <button
                        class="btn-ghost"
                        type="button"
                        :disabled="Boolean(mapProfileApplyingKey) || Boolean(mapProfileDeletingKey) || Boolean(mapProfileExportingKey) || mapProfileImporting || isMapProfilePreviewing(profile)"
                        @click="previewMapProfile(profile)"
                      >
                        {{
                          isMapProfilePreviewing(profile)
                            ? settingsLocale.mapProfilePreviewing
                            : settingsLocale.mapProfilePreview
                        }}
                      </button>
                      <button
                        class="btn-ghost"
                        type="button"
                        :disabled="Boolean(mapProfileApplyingKey) || Boolean(mapProfileDeletingKey) || Boolean(mapProfileExportingKey) || mapProfileImporting"
                        @click="exportMapProfile(profile)"
                      >
                        {{
                          isMapProfileExporting(profile)
                            ? settingsLocale.mapProfileExporting
                            : settingsLocale.mapProfileExport
                        }}
                      </button>
                      <button
                        v-if="profile.deletable"
                        class="btn-delete"
                        type="button"
                        :disabled="!authCanMapWrite || Boolean(mapProfileApplyingKey) || Boolean(mapProfileDeletingKey) || Boolean(mapProfileExportingKey) || mapProfileImporting"
                        :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                        @click="deleteMapProfile(profile)"
                      >
                        {{
                          isMapProfileDeleting(profile)
                            ? settingsLocale.mapProfileDeleting
                            : settingsLocale.mapProfileDelete
                        }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="enterprise-settings-actions">
                <button class="btn-secondary" type="button" @click="jumpFromEnterpriseSettings('control')">
                  {{ t('enterprise_settings_open_map_settings') }}
                </button>
              </div>
            </template>

            <template v-else-if="enterpriseSettingsActiveTab === 'point_templates'">
              <p class="panel-hint">{{ t('enterprise_settings_point_templates_hint') }}</p>
              <div class="enterprise-settings-role-note">
                <strong>{{ enterpriseActiveTabModeLabel }}</strong>
                <p>{{ enterpriseActiveTabModeHint }}</p>
              </div>
              <div class="enterprise-settings-role-note">
                <strong>{{ t('enterprise_settings_actions_title') }}</strong>
                <p>{{ t('enterprise_settings_point_templates_action_hint') }}</p>
                <div class="enterprise-settings-chip-list">
                  <span
                    v-for="item in enterprisePointTemplateActionScope.enabled"
                    :key="`enterprise-point-template-enabled-${item.key}`"
                    class="point-badge enterprise-settings-chip"
                  >
                    {{ item.label }}
                  </span>
                </div>
                <div v-if="enterprisePointTemplateActionScope.readonly.length" class="task-line">
                  {{ t('enterprise_settings_capabilities_readonly_title') }}
                </div>
                <div v-if="enterprisePointTemplateActionScope.readonly.length" class="enterprise-settings-chip-list">
                  <span
                    v-for="item in enterprisePointTemplateActionScope.readonly"
                    :key="`enterprise-point-template-readonly-${item.key}`"
                    class="point-badge enterprise-settings-chip enterprise-settings-chip-muted"
                  >
                    {{ item.label }}
                  </span>
                </div>
              </div>
              <div class="enterprise-settings-role-note">
                <strong>{{ enterprisePointTemplateFocus.title }}</strong>
                <p>{{ enterprisePointTemplateFocus.hint }}</p>
                <div class="enterprise-settings-chip-list">
                  <button
                    v-for="action in enterprisePointTemplateFocus.actions"
                    :key="`enterprise-point-template-action-${action.key}`"
                    class="btn-ghost enterprise-settings-action-chip"
                    type="button"
                    @click="jumpFromEnterpriseSettings(action.key)"
                  >
                    {{ action.label }}
                  </button>
                </div>
              </div>
              <div class="map-settings-info-grid enterprise-settings-grid">
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_points_total') }}</div>
                  <div class="map-settings-info-value">{{ pointLibrary.length }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_points_custom') }}</div>
                  <div class="map-settings-info-value">{{ customPoints.length }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_templates_total') }}</div>
                  <div class="map-settings-info-value">{{ taskTemplates.length }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_templates_custom') }}</div>
                  <div class="map-settings-info-value">{{ customTaskTemplates.length }}</div>
                </div>
              </div>
              <div class="enterprise-settings-subgrid">
                <div class="enterprise-settings-subsection">
                  <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_points_quick_manage_title') }}</div>
                  <p class="panel-hint">{{ t('enterprise_settings_points_quick_manage_hint') }}</p>
                  <div class="form-grid enterprise-settings-inline-form">
                    <label>{{ t('point_form_name') }}</label>
                    <input
                      v-model.trim="customPointForm.name"
                      type="text"
                      :placeholder="t('point_form_name_placeholder')"
                    />
                    <label>{{ t('point_form_zone') }}</label>
                    <input
                      v-model.trim="customPointForm.zone"
                      type="text"
                      :placeholder="t('point_form_zone_placeholder')"
                    />
                    <label>{{ t('form_start_x') }}</label>
                    <input
                      v-model.number="customPointForm.x"
                      type="number"
                      min="0"
                      :max="currentGridCols - 1"
                    />
                    <label>{{ t('form_start_y') }}</label>
                    <input
                      v-model.number="customPointForm.y"
                      type="number"
                      min="0"
                      :max="currentGridRows - 1"
                    />
                  </div>
                  <div class="enterprise-settings-inline-actions">
                    <button
                      class="btn-primary"
                      type="button"
                      :disabled="!authCanPointWrite"
                      :title="buildCapabilityLockedTitle('data', authCanPointWrite)"
                      @click="addCustomPointWithAuth"
                    >
                      {{ t('point_add') }}
                    </button>
                  </div>
                  <div v-if="pointFormStatus" class="point-status" :class="pointFormStatusType">
                    {{ pointFormStatus }}
                  </div>
                </div>
                <div class="enterprise-settings-subsection">
                  <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_templates_quick_manage_title') }}</div>
                  <p class="panel-hint">{{ t('enterprise_settings_templates_quick_manage_hint') }}</p>
                  <div class="form-grid enterprise-settings-inline-form">
                    <label>{{ t('template_name') }}</label>
                    <input
                      v-model.trim="taskTemplateForm.name"
                      type="text"
                      :placeholder="t('template_name_placeholder')"
                    />
                  </div>
                  <div class="enterprise-settings-inline-actions">
                    <button
                      class="btn-primary"
                      type="button"
                      :disabled="!authCanTemplateWrite"
                      :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
                      @click="saveCurrentTaskTemplateWithAuth"
                    >
                      {{ t('template_save_current') }}
                    </button>
                    <button
                      class="btn-secondary"
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
              </div>
              <div class="enterprise-settings-subgrid">
                <div class="enterprise-settings-subsection">
                  <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_points_list_title') }}</div>
                  <div v-if="enterpriseRecentCustomPoints.length === 0" class="empty-note">{{ t('enterprise_settings_points_list_empty') }}</div>
                  <div v-else class="enterprise-settings-list">
                    <article v-for="point in enterpriseRecentCustomPoints" :key="`enterprise-point-${point.id}`" class="enterprise-settings-list-item">
                      <div class="enterprise-settings-list-main">
                        <strong>{{ point.name }}</strong>
                        <span>{{ point.x }}, {{ point.y }}</span>
                      </div>
                      <div class="task-line">{{ point.zone || '—' }}</div>
                      <div class="enterprise-settings-inline-actions enterprise-settings-inline-actions-compact">
                        <button class="btn-secondary" type="button" @click="applyPointToTaskForm('start', point)">
                          {{ t('point_apply_start') }}
                        </button>
                        <button class="btn-ghost" type="button" @click="applyPointToTaskForm('end', point)">
                          {{ t('point_apply_end') }}
                        </button>
                        <button
                          class="btn-delete"
                          type="button"
                          :disabled="!authCanPointWrite"
                          :title="buildCapabilityLockedTitle('data', authCanPointWrite)"
                          @click="deleteCustomPointWithAuth(point)"
                        >
                          {{ t('point_delete') }}
                        </button>
                      </div>
                    </article>
                  </div>
                </div>
                <div class="enterprise-settings-subsection">
                  <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_templates_list_title') }}</div>
                  <div v-if="enterpriseRecentCustomTemplates.length === 0" class="empty-note">{{ t('enterprise_settings_templates_list_empty') }}</div>
                  <div v-else class="enterprise-settings-list">
                    <article v-for="template in enterpriseRecentCustomTemplates" :key="`enterprise-template-${template.id}`" class="enterprise-settings-list-item">
                      <div class="enterprise-settings-list-main">
                        <strong>{{ template.name }}</strong>
                        <span>{{ formatInlineMessage(t('enterprise_settings_templates_stage_count'), { count: template.stages?.length || 0 }) }}</span>
                      </div>
                      <div class="task-line">{{ template.description || '—' }}</div>
                      <div class="enterprise-settings-inline-actions enterprise-settings-inline-actions-compact">
                        <button class="btn-secondary" type="button" @click="onTemplateApplyClick(template)">
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
              </div>
              <div class="enterprise-settings-actions">
                <button class="btn-secondary" type="button" @click="jumpFromEnterpriseSettings('points')">
                  {{ t('enterprise_settings_open_points') }}
                </button>
                <button class="btn-secondary" type="button" @click="jumpFromEnterpriseSettings('templates')">
                  {{ t('enterprise_settings_open_templates') }}
                </button>
              </div>
            </template>

            <template v-else-if="enterpriseSettingsActiveTab === 'runtime'">
              <p class="panel-hint">{{ t('enterprise_settings_runtime_hint') }}</p>
              <div class="enterprise-settings-role-note">
                <strong>{{ enterpriseActiveTabModeLabel }}</strong>
                <p>{{ enterpriseActiveTabModeHint }}</p>
              </div>
              <div class="enterprise-settings-role-note">
                <strong>{{ t('enterprise_settings_actions_title') }}</strong>
                <p>{{ t('enterprise_settings_runtime_action_hint') }}</p>
                <div class="enterprise-settings-chip-list">
                  <span
                    v-for="item in enterpriseRuntimeActionScope.enabled"
                    :key="`enterprise-runtime-enabled-${item.key}`"
                    class="point-badge enterprise-settings-chip"
                  >
                    {{ item.label }}
                  </span>
                </div>
                <div v-if="enterpriseRuntimeActionScope.readonly.length" class="task-line">
                  {{ t('enterprise_settings_capabilities_readonly_title') }}
                </div>
                <div v-if="enterpriseRuntimeActionScope.readonly.length" class="enterprise-settings-chip-list">
                  <span
                    v-for="item in enterpriseRuntimeActionScope.readonly"
                    :key="`enterprise-runtime-readonly-${item.key}`"
                    class="point-badge enterprise-settings-chip enterprise-settings-chip-muted"
                  >
                    {{ item.label }}
                  </span>
                </div>
              </div>
              <div class="enterprise-settings-role-note">
                <strong>{{ enterpriseRuntimeFocus.title }}</strong>
                <p>{{ enterpriseRuntimeFocus.hint }}</p>
                <div class="enterprise-settings-chip-list">
                  <button
                    v-for="action in enterpriseRuntimeFocus.actions"
                    :key="`enterprise-runtime-action-${action.key}`"
                    class="btn-ghost enterprise-settings-action-chip"
                    type="button"
                    @click="jumpFromEnterpriseSettings(action.key)"
                  >
                    {{ action.label }}
                  </button>
                </div>
              </div>
              <div class="map-settings-info-grid enterprise-settings-grid">
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('dispatch') }}</div>
                  <div class="map-settings-info-value">{{ currentDispatchModeLabel }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('algorithm') }}</div>
                  <div class="map-settings-info-value">{{ algorithmText(algorithm) }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('priority') }}</div>
                  <div class="map-settings-info-value">{{ taskPriority }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ compareDisplayTitleLabel }}</div>
                  <div class="map-settings-info-value">{{ compareDisplayMode === 'floating' ? compareDisplayFloatingLabel : compareDisplayPanelLabel }}</div>
                </div>
              </div>
              <div class="enterprise-settings-subgrid">
                <div class="enterprise-settings-subsection">
                  <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_runtime_controls_title') }}</div>
                  <p class="panel-hint">{{ t('enterprise_settings_runtime_controls_hint') }}</p>

                  <div class="enterprise-settings-segmented-group">
                    <strong>{{ t('enterprise_settings_runtime_mode_title') }}</strong>
                    <div class="enterprise-settings-segmented-options">
                      <button
                        class="btn-secondary enterprise-settings-segmented-button"
                        :class="{ active: dispatchMode === 'auto' }"
                        type="button"
                        :disabled="!authCanDispatchWrite"
                        :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                        @click="setDispatchModeFromEnterprise('auto')"
                      >
                        {{ dispatchModeAutoLabel }}
                      </button>
                      <button
                        class="btn-secondary enterprise-settings-segmented-button"
                        :class="{ active: dispatchMode === 'manual' }"
                        type="button"
                        :disabled="!authCanDispatchWrite"
                        :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                        @click="setDispatchModeFromEnterprise('manual')"
                      >
                        {{ dispatchModeManualLabel }}
                      </button>
                    </div>
                  </div>

                  <div class="enterprise-settings-segmented-group">
                    <strong>{{ t('enterprise_settings_runtime_algorithm_title') }}</strong>
                    <div class="enterprise-settings-segmented-options">
                      <button
                        class="btn-secondary enterprise-settings-segmented-button"
                        :class="{ active: algorithm === 'simple' }"
                        type="button"
                        :disabled="!authCanExperimentWrite"
                        :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
                        @click="setRuntimeAlgorithmFromEnterprise('simple')"
                      >
                        {{ algorithmText('simple') }}
                      </button>
                      <button
                        class="btn-secondary enterprise-settings-segmented-button"
                        :class="{ active: algorithm === 'astar' }"
                        type="button"
                        :disabled="!authCanExperimentWrite"
                        :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
                        @click="setRuntimeAlgorithmFromEnterprise('astar')"
                      >
                        {{ algorithmText('astar') }}
                      </button>
                    </div>
                  </div>

                  <div class="enterprise-settings-segmented-group">
                    <strong>{{ t('enterprise_settings_runtime_display_title') }}</strong>
                    <div class="enterprise-settings-segmented-options">
                      <button
                        class="btn-secondary enterprise-settings-segmented-button"
                        :class="{ active: compareDisplayMode === 'panel' }"
                        type="button"
                        @click="setCompareDisplayModeFromEnterprise('panel')"
                      >
                        {{ compareDisplayPanelLabel }}
                      </button>
                      <button
                        class="btn-secondary enterprise-settings-segmented-button"
                        :class="{ active: compareDisplayMode === 'floating' }"
                        type="button"
                        @click="setCompareDisplayModeFromEnterprise('floating')"
                      >
                        {{ compareDisplayFloatingLabel }}
                      </button>
                    </div>
                  </div>
                </div>
                <div class="enterprise-settings-subsection">
                  <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_runtime_compare_title') }}</div>
                  <p class="panel-hint">{{ t('enterprise_settings_runtime_compare_hint') }}</p>
                  <div class="enterprise-settings-inline-actions">
                    <button class="btn-primary" type="button" @click="compareCurrentRoute">
                      {{ algorithmCompareLocale.run }}
                    </button>
                    <button
                      class="btn-secondary"
                      type="button"
                      :disabled="!authCanExperimentWrite"
                      :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
                      @click="algorithmCompareWorkspaceBindings.saveCurrentExperimentRecordWithAuth"
                    >
                      {{ experimentLocale.saveCurrent }}
                    </button>
                    <button
                      class="btn-secondary"
                      type="button"
                      :disabled="!authCanExperimentWrite"
                      :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
                      @click="algorithmCompareWorkspaceBindings.exportCurrentCompareResultJsonWithAuth"
                    >
                      {{ experimentLocale.exportCurrentJson }}
                    </button>
                    <button
                      class="btn-secondary"
                      type="button"
                      :disabled="!authCanExperimentWrite"
                      :title="buildCapabilityLockedTitle('data', authCanExperimentWrite)"
                      @click="algorithmCompareWorkspaceBindings.exportCurrentCompareResultCsvWithAuth"
                    >
                      {{ experimentLocale.exportCurrentCsv }}
                    </button>
                  </div>
                  <div class="enterprise-settings-embedded-panel">
                    <AlgorithmCompareWorkspace :ui="algorithmCompareWorkspaceBindings" />
                  </div>
                </div>
              </div>
              <div class="enterprise-settings-subsection">
                <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_runtime_notes_title') }}</div>
                <div class="enterprise-settings-list">
                  <article class="enterprise-settings-list-item">
                    <div class="enterprise-settings-list-main">
                      <strong>{{ t('enterprise_settings_runtime_note_tasks') }}</strong>
                      <span>{{ enterpriseActiveTasks }}</span>
                    </div>
                    <div class="task-line">{{ t('enterprise_settings_runtime_note_tasks_hint') }}</div>
                  </article>
                  <article class="enterprise-settings-list-item">
                    <div class="enterprise-settings-list-main">
                      <strong>{{ t('enterprise_settings_runtime_note_faults') }}</strong>
                      <span>{{ enterpriseOpenFaults }}</span>
                    </div>
                    <div class="task-line">{{ t('enterprise_settings_runtime_note_faults_hint') }}</div>
                  </article>
                </div>
              </div>
              <div class="enterprise-settings-actions">
                <button class="btn-secondary" type="button" @click="jumpFromEnterpriseSettings('control')">
                  {{ t('enterprise_settings_open_dispatch') }}
                </button>
                <button class="btn-secondary" type="button" @click="jumpFromEnterpriseSettings('experiments')">
                  {{ t('enterprise_settings_open_experiments') }}
                </button>
              </div>
            </template>

            <template v-else-if="enterpriseSettingsActiveTab === 'ai'">
              <p class="panel-hint">{{ t('enterprise_settings_ai_hint') }}</p>
              <div class="enterprise-settings-role-note">
                <strong>{{ enterpriseActiveTabModeLabel }}</strong>
                <p>{{ enterpriseActiveTabModeHint }}</p>
              </div>
              <div class="enterprise-settings-role-note">
                <strong>{{ t('enterprise_settings_actions_title') }}</strong>
                <p>{{ t('enterprise_settings_ai_action_hint') }}</p>
                <div class="enterprise-settings-chip-list">
                  <span
                    v-for="item in enterpriseAiActionScope.enabled"
                    :key="`enterprise-ai-enabled-${item.key}`"
                    class="point-badge enterprise-settings-chip"
                  >
                    {{ item.label }}
                  </span>
                </div>
                <div v-if="enterpriseAiActionScope.readonly.length" class="task-line">
                  {{ t('enterprise_settings_capabilities_readonly_title') }}
                </div>
                <div v-if="enterpriseAiActionScope.readonly.length" class="enterprise-settings-chip-list">
                  <span
                    v-for="item in enterpriseAiActionScope.readonly"
                    :key="`enterprise-ai-readonly-${item.key}`"
                    class="point-badge enterprise-settings-chip enterprise-settings-chip-muted"
                  >
                    {{ item.label }}
                  </span>
                </div>
              </div>
              <div class="map-settings-info-grid enterprise-settings-grid">
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('ai_render_title') }}</div>
                  <div class="map-settings-info-value">{{ comfyRenderJobs.length }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_checkpoint_count') }}</div>
                  <div class="map-settings-info-value">{{ comfyRenderAvailableCheckpoints.length || '—' }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_last_ai_job') }}</div>
                  <div class="map-settings-info-value">{{ comfyRenderJobs[0]?.created_at || '—' }}</div>
                </div>
              </div>
              <ComfyAiWorkspace
                v-model:builtin-template-key="comfyRenderBuiltinTemplateKey"
                v-model:source-type="comfyRenderSourceType"
                v-model:source-ref="comfyRenderSourceRef"
                v-model:checkpoint-name="comfyRenderCheckpointName"
                v-model:workflow-preset="comfyRenderWorkflowPreset"
                v-model:prompt-style="comfyRenderPromptStyle"
                v-model:template-name="comfyRenderTemplateName"
                v-model:selected-template-id="comfyRenderSelectedTemplateId"
                v-model:prompt-text="comfyRenderPromptText"
                v-model:input-json-text="comfyRenderInputJsonText"
                v-model:workflow-json-text="comfyRenderWorkflowJsonText"
                v-model:selected-shared-template-id="comfyRenderSelectedSharedTemplateId"
                :t="t"
                :format-inline-message="formatInlineMessage"
                :can-render="authCanAiRender"
                :status-text="comfyRenderStatus"
                :status-type="comfyRenderStatusType"
                :builtin-templates="comfyRenderBuiltinTemplates"
                :selected-builtin-template="comfyRenderSelectedBuiltinTemplate"
                :selected-builtin-template-matches-recommendation="comfyRenderSelectedBuiltinTemplateMatchesRecommendation"
                :recommended-builtin-template="comfyRenderRecommendedBuiltinTemplate"
                :recommended-builtin-reason-text="comfyRenderRecommendedBuiltinReasonText"
                :source-options="comfyRenderSourceOptions"
                :workflow-preset-options="comfyRenderWorkflowPresetOptions"
                :prompt-style-options="comfyRenderPromptStyleOptions"
                :saved-templates="comfyRenderSavedTemplates"
                :has-custom-templates="comfyRenderHasCustomTemplates"
                :shared-templates="comfyRenderSharedTemplates"
                :selected-shared-template="comfyRenderSelectedSharedTemplate"
                :has-shared-templates="comfyRenderHasSharedTemplates"
                :shared-templates-hint-text="buildAiRenderSharedTemplatesHintText()"
                :shared-template-meta-text="comfyRenderSelectedSharedTemplateMetaText"
                checkpoint-list-id="enterprise-comfy-checkpoint-options"
                :available-checkpoints="comfyRenderAvailableCheckpoints"
                :workflow-preset-summary="comfyRenderWorkflowPresetSummary"
                :prompt-style-summary="comfyRenderPromptStyleSummary"
                :recommended-checkpoint-summary="comfyRenderRecommendedCheckpointSummary"
                :submitting="comfyRenderSubmitting"
                :loading-jobs="comfyRenderLoading"
                :shared-template-saving="comfyRenderSharedTemplateSaving"
                :shared-templates-loading="comfyRenderSharedTemplatesLoading"
                :jobs="enterpriseRecentAiJobs"
                :jobs-title="t('enterprise_settings_ai_jobs_title')"
                :jobs-empty-text="t('enterprise_settings_ai_jobs_empty')"
                :matched-job-ids="[]"
                :deleting-job-id="deletingComfyJobId"
                :last-fetched-text="''"
                :no-access-action-text="buildOperationsEntryActionText()"
                :on-open-builtin-overview="openComfyBuiltinTemplateOverview"
                :on-apply-builtin="applySelectedBuiltinComfyTemplate"
                :on-load-source="loadComfySourcePayload"
                :on-fill-default-workflow="loadDefaultComfyWorkflow"
                :on-submit="submitComfyRenderJob"
                :on-refresh-jobs="() => fetchComfyRenderJobs({ force: true })"
                :on-save-template="saveCurrentComfyTemplate"
                :on-apply-template="applySelectedComfyTemplate"
                :on-export-template="exportSelectedComfyTemplate"
                :on-import-template="onComfyTemplateFileChange"
                :on-delete-template="deleteSelectedComfyTemplate"
                :on-save-shared-template="saveCurrentComfySharedTemplate"
                :on-apply-shared-template="applySelectedSharedTemplate"
                :on-refresh-shared-templates="() => fetchComfySharedTemplates({ force: true })"
                :on-delete-shared-template="deleteSelectedSharedTemplate"
                :on-preview-asset="openComfyRenderAssetPreview"
                :on-delete-job="deleteComfyRenderJob"
                :on-entry-action="openAuthDialog"
                :format-source="formatComfyRenderSource"
                :format-status="formatComfyRenderStatus"
                :format-asset-action-label="formatComfyRenderAssetActionLabel"
                :job-meta-text="formatEnterpriseComfyRenderJobMeta"
              />
              <p class="panel-hint">{{ buildAiRenderHintText() }}</p>
              <div class="enterprise-settings-actions">
                <button class="btn-secondary" type="button" @click="jumpFromEnterpriseSettings('ai')">
                  {{ t('enterprise_settings_open_ai') }}
                </button>
              </div>
            </template>

            <template v-else-if="enterpriseSettingsActiveTab === 'audit'">
              <p class="panel-hint">{{ t('enterprise_settings_audit_hint') }}</p>
              <div class="enterprise-settings-role-note">
                <strong>{{ enterpriseActiveTabModeLabel }}</strong>
                <p>{{ enterpriseActiveTabModeHint }}</p>
              </div>
              <div class="map-settings-info-grid enterprise-settings-grid">
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('operations_title') }}</div>
                  <div class="map-settings-info-value">{{ operationAudits.length }}</div>
                </div>
                <div class="map-settings-info-card">
                  <div class="map-settings-info-label">{{ t('enterprise_settings_summary_last_audit') }}</div>
                  <div class="map-settings-info-value">{{ operationAuditLastFetchedAt || '—' }}</div>
                </div>
              </div>
              <div class="enterprise-settings-subsection">
                <div class="enterprise-settings-subtitle">{{ t('operations_title') }}</div>
                <div class="operations-toolbar enterprise-settings-operations-toolbar">
                  <div class="operations-filter-grid">
                    <label>
                      {{ t('operations_filter_resource') }}
                      <select v-model="operationAuditResourceFilter">
                        <option
                          v-for="option in operationAuditResourceOptions"
                          :key="`enterprise-audit-resource-${option.value}`"
                          :value="option.value"
                        >
                          {{ option.label }}
                        </option>
                      </select>
                    </label>
                    <label>
                      {{ t('operations_filter_action') }}
                      <select v-model="operationAuditActionFilter">
                        <option
                          v-for="option in operationAuditActionOptions"
                          :key="`enterprise-audit-action-${option.value}`"
                          :value="option.value"
                        >
                          {{ option.label }}
                        </option>
                      </select>
                    </label>
                  </div>
                  <div class="operations-toolbar-actions">
                    <div v-if="operationAuditLastFetchedAt" class="task-line operations-last-fetched">
                      {{ formatInlineMessage(t('operations_last_updated'), { at: operationAuditLastFetchedAt }) }}
                    </div>
                    <button class="btn-ghost" type="button" @click="resetOperationAuditFilters">
                      {{ t('operations_reset_filters') }}
                    </button>
                    <button class="btn-secondary" type="button" @click="exportFilteredOperationAuditsJsonWithAuth">
                      {{ t('operations_export_json') }}
                    </button>
                    <button class="btn-secondary" type="button" @click="exportFilteredOperationAuditsCsvWithAuth">
                      {{ t('operations_export_csv') }}
                    </button>
                    <button class="btn-secondary" type="button" :disabled="operationAuditLoading" @click="fetchOperationAudits({ force: true })">
                      {{ operationAuditLoading ? `${t('operations_refresh')}...` : t('operations_refresh') }}
                    </button>
                  </div>
                </div>
              </div>
              <div class="enterprise-settings-subsection">
                <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_recent_audit_title') }}</div>
                <div v-if="operationAuditLoading && enterpriseFilteredAuditEntries.length === 0" class="template-status info">
                  {{ t('operations_loading') }}
                </div>
                <div v-else-if="enterpriseFilteredAuditEntries.length === 0" class="empty-note">{{ t('operations_empty') }}</div>
                <div v-else class="operations-list enterprise-settings-operations-list">
                  <article
                    v-for="entry in enterpriseFilteredAuditEntries"
                    :key="`enterprise-audit-panel-${entry.id}`"
                    class="operations-card"
                    :class="{ 'search-hit': matchedOperationAuditIds.includes(entry.id) }"
                  >
                    <div class="operations-card-head">
                      <div>
                        <strong>{{ formatOperationAuditTitle(entry) }}</strong>
                        <div class="task-line">{{ formatOperationAuditResourceRef(entry) }}</div>
                      </div>
                      <span class="point-badge">{{ operationActionLabel(entry.action) }}</span>
                    </div>
                    <div class="task-line">{{ formatOperationAuditOperator(entry) }}</div>
                    <div class="task-line task-time">{{ entry.performed_at }}</div>
                    <div v-if="formatOperationAuditMetadata(entry)" class="task-line operations-summary">
                      {{ formatOperationAuditMetadata(entry) }}
                    </div>
                  </article>
                </div>
              </div>
              <p class="panel-hint">{{ buildOperationsHintText() }}</p>
              <div class="enterprise-settings-actions">
                <button class="btn-secondary" type="button" @click="jumpFromEnterpriseSettings('operations')">
                  {{ t('enterprise_settings_open_audit') }}
                </button>
              </div>
            </template>
          </div>
        </div>
      </section>
    </div>
</template>


<script>
import { defineAsyncComponent, defineComponent, reactive, watchEffect } from 'vue'

const ComfyAiWorkspace = defineAsyncComponent(() => import('./ComfyAiWorkspace.vue'))
const AlgorithmCompareWorkspace = defineAsyncComponent(() => import('./AlgorithmCompareWorkspace.vue'))

export default defineComponent({
  name: 'EnterpriseSettingsDialog',
  components: {
    ComfyAiWorkspace,
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


