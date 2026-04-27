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

        <div
          class="enterprise-settings-shell"
          :class="{ 'is-sidebar-collapsed': enterpriseSettingsSidebarCollapsed }"
        >
          <aside
            class="enterprise-settings-sidebar"
            :class="{ 'is-collapsed': enterpriseSettingsSidebarCollapsed }"
          >
            <div class="enterprise-settings-sidebar-head">
              <div
                v-if="!enterpriseSettingsSidebarCollapsed"
                class="enterprise-settings-sidebar-title"
              >
                {{ t('enterprise_settings_navigation') }}
              </div>
              <button
                class="enterprise-settings-sidebar-toggle"
                type="button"
                :title="enterpriseSettingsSidebarCollapsed ? t('enterprise_settings_sidebar_expand') : t('enterprise_settings_sidebar_collapse')"
                @click="toggleEnterpriseSettingsSidebar"
              >
                <span class="enterprise-settings-sidebar-toggle-icon">
                  {{ enterpriseSettingsSidebarCollapsed ? '>>' : '<<' }}
                </span>
                <span v-if="!enterpriseSettingsSidebarCollapsed">
                  {{ enterpriseSettingsSidebarCollapsed ? t('enterprise_settings_sidebar_expand') : t('enterprise_settings_sidebar_collapse') }}
                </span>
              </button>
            </div>
              <button
                v-for="tab in enterpriseSettingsTabDefinitions"
                :key="tab.key"
                class="enterprise-settings-tab"
                :class="{ active: enterpriseSettingsActiveTab === tab.key, 'is-primary': tab.primary }"
                type="button"
                :title="`${tab.label} · ${tab.hint}`"
                @click="switchEnterpriseSettingsTab(tab.key)"
              >
                <span
                  class="enterprise-settings-tab-short"
                  :class="{ 'is-visible': enterpriseSettingsSidebarCollapsed }"
                >
                  {{ tab.shortLabel }}
                </span>
                <span
                  v-if="!enterpriseSettingsSidebarCollapsed"
                  class="enterprise-settings-tab-copy"
                >
                  {{ tab.label }}
                </span>
                <span
                  v-if="!enterpriseSettingsSidebarCollapsed"
                  class="enterprise-settings-tab-hint"
                >
                  {{ tab.hint }}
                </span>
                <span
                  v-if="!enterpriseSettingsSidebarCollapsed"
                  class="enterprise-settings-tab-badges"
                >
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
              <div class="enterprise-settings-sidebar-footer">
                <button
                  class="enterprise-settings-sidebar-action"
                  type="button"
                  :title="`${t('enterprise_settings_page_settings_entry')} · ${t('enterprise_settings_page_settings_hint')}`"
                  @click="openPageSettingsFromEnterpriseSettings"
                >
                  <span class="enterprise-settings-sidebar-action-icon" aria-hidden="true">⚙</span>
                  <template v-if="!enterpriseSettingsSidebarCollapsed">
                    <span class="enterprise-settings-sidebar-action-copy">
                      {{ t('enterprise_settings_page_settings_entry') }}
                    </span>
                    <span class="enterprise-settings-sidebar-action-hint">
                      {{ t('enterprise_settings_page_settings_hint') }}
                    </span>
                  </template>
                </button>
              </div>
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
              <div
                v-if="enterpriseRoleWorkspaceActionItems.length"
                class="enterprise-settings-role-note"
              >
                <strong>{{ enterpriseRoleFocus.title }}</strong>
                <p>{{ enterpriseRoleScopeText }}</p>
                <div class="enterprise-settings-actions">
                  <button class="btn-secondary" type="button" @click="applyCurrentEnterpriseWorkspacePreset">
                    {{ t('enterprise_settings_apply_workspace_preset') }}
                  </button>
                  <button
                    v-for="action in enterpriseRoleWorkspaceActionItems"
                    :key="`enterprise-overview-workspace-action-${action.key}`"
                    :class="action.tone === 'ghost' ? 'btn-ghost' : 'btn-secondary'"
                    type="button"
                    @click="runEnterpriseWorkspaceAction(action.key)"
                  >
                    {{ action.label }}
                  </button>
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
                <strong>{{ t('enterprise_settings_overview_quick_tabs_title') }}</strong>
                <p>{{ t('enterprise_settings_overview_quick_tabs_hint') }}</p>
                <div class="enterprise-settings-chip-list">
                  <button
                    v-for="tab in enterpriseOverviewQuickTabs"
                    :key="`enterprise-overview-tab-${tab.key}`"
                    class="btn-ghost enterprise-settings-action-chip"
                    type="button"
                    @click="switchEnterpriseSettingsTab(tab.key)"
                  >
                    {{ tab.label }} · {{ tab.accessLabel }}
                  </button>
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
                      v-if="authCurrentEnterpriseApplication?.company_name || authCurrentOrganizationName"
                      class="btn-ghost enterprise-settings-inline-button"
                      type="button"
                      @click="copyEnterpriseApplicationCompanyName(authCurrentEnterpriseApplication)"
                    >
                      {{ t('enterprise_application_copy_company_name') }}
                    </button>
                    <button
                      v-if="authCurrentEnterpriseApplication?.contact_name"
                      class="btn-ghost enterprise-settings-inline-button"
                      type="button"
                      @click="copyEnterpriseApplicationContactName(authCurrentEnterpriseApplication)"
                    >
                      {{ t('enterprise_application_copy_contact_name') }}
                    </button>
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
                <div
                  v-if="authEnterpriseRegisterDraftHasContent"
                  class="enterprise-settings-status-note"
                >
                  <strong>{{ t('auth_enterprise_register_draft_title') }}</strong>
                  <p>{{ t('auth_enterprise_register_draft_hint') }}</p>
                  <div
                    v-if="authEnterpriseRegisterDraftDiffText"
                    class="task-line"
                  >
                    {{ authEnterpriseRegisterDraftDiffText }}
                  </div>
                  <div
                    v-if="authEnterpriseRegisterDraftUpdatedText"
                    class="task-line operations-last-fetched"
                  >
                    {{ authEnterpriseRegisterDraftUpdatedText }}
                  </div>
                  <div class="enterprise-settings-actions enterprise-settings-status-actions">
                    <button
                      class="btn-ghost"
                      type="button"
                      @click="useCurrentEnterpriseApplicationForRegisterDraft"
                    >
                      {{ t('auth_enterprise_register_existing_action_use') }}
                    </button>
                    <button
                      class="btn-secondary"
                      type="button"
                      @click="resumeEnterpriseRegistrationFromApplication(authCurrentEnterpriseApplication, { closeSettings: true })"
                    >
                      {{ t('auth_enterprise_register_followup_edit') }}
                    </button>
                  </div>
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
                <div
                  v-if="authEnterpriseStatusFollowupVisible"
                  class="enterprise-settings-status-note"
                >
                  <strong>{{ authEnterpriseStatusFollowupTitle }}</strong>
                  <p>{{ authEnterpriseStatusFollowupHint }}</p>
                  <div class="application-progress-grid">
                    <article
                      v-for="item in authEnterpriseStatusFollowupProgressItems"
                      :key="`enterprise-settings-followup-progress-${item.key}`"
                      class="application-progress-item"
                      :class="`is-${item.tone}`"
                    >
                      <span>{{ item.label }}</span>
                      <strong>{{ item.value }}</strong>
                    </article>
                  </div>
                  <div v-if="authEnterpriseStatusFollowup.review_note" class="task-line">
                    {{ authEnterpriseStatusFollowup.review_note }}
                  </div>
                  <div v-if="authEnterpriseStatusFollowupUpdatedText" class="task-line operations-last-fetched">
                    {{ authEnterpriseStatusFollowupUpdatedText }}
                  </div>
                  <div class="task-line">
                    {{ authEnterpriseStatusFollowupNextStepText }}
                  </div>
                  <div class="enterprise-settings-actions enterprise-settings-status-actions">
                    <button
                      v-if="authEnterpriseStatusFollowup.status === 'approved'"
                      class="btn-secondary"
                      type="button"
                      @click="runEnterpriseStatusFollowupAction('apply-workspace')"
                    >
                      {{ t('enterprise_settings_apply_workspace_preset') }}
                    </button>
                    <button
                      v-if="authEnterpriseStatusFollowup.status === 'rejected'"
                      class="btn-secondary"
                      type="button"
                      @click="runEnterpriseStatusFollowupAction('resume-registration')"
                    >
                      {{ t('enterprise_application_resume_registration') }}
                    </button>
                    <button
                      v-if="authEnterpriseStatusFollowup.status === 'rejected' && authEnterpriseStatusFollowup.review_note"
                      class="btn-ghost"
                      type="button"
                      @click="runEnterpriseStatusFollowupAction('copy-review-note')"
                    >
                      {{ t('enterprise_application_copy_review_note') }}
                    </button>
                    <button
                      class="btn-ghost"
                      type="button"
                      @click="runEnterpriseStatusFollowupAction('copy-summary')"
                    >
                      {{ t('enterprise_application_copy_summary') }}
                    </button>
                    <button
                      class="btn-ghost"
                      type="button"
                      @click="runEnterpriseStatusFollowupAction('dismiss')"
                    >
                      {{ t('auth_enterprise_status_followup_dismiss') }}
                    </button>
                  </div>
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
              <div v-if="enterpriseMemberManagementEnabled" class="enterprise-settings-role-note">
                <div class="enterprise-settings-status-head">
                  <div>
                    <strong>{{ t('enterprise_member_title') }}</strong>
                    <p>{{ t('enterprise_member_hint') }}</p>
                  </div>
                  <div class="enterprise-settings-inline-actions">
                    <button
                      class="btn-ghost enterprise-settings-inline-button"
                      type="button"
                      :disabled="enterpriseMemberLoading"
                      @click="fetchEnterpriseMembers()"
                    >
                      {{ t('enterprise_member_refresh') }}
                    </button>
                  </div>
                </div>
                <div class="enterprise-settings-status-grid">
                  <div class="enterprise-settings-status-item">
                    <span>{{ t('enterprise_member_current_org') }}</span>
                    <strong>{{ authCurrentOrganizationName || '—' }}</strong>
                  </div>
                  <div class="enterprise-settings-status-item">
                    <span>{{ t('enterprise_member_count') }}</span>
                    <strong>{{ enterpriseMemberItems.length }}</strong>
                  </div>
                </div>
                <div v-if="enterpriseMemberLastFetchedText" class="task-line operations-last-fetched">
                  {{ enterpriseMemberLastFetchedText }}
                </div>
                <div
                  v-if="enterpriseMemberStatus"
                  class="enterprise-settings-status-note"
                  :class="`is-${enterpriseMemberStatusType}`"
                >
                  <p>{{ enterpriseMemberStatus }}</p>
                </div>
                <div class="enterprise-settings-subgrid">
                  <div class="enterprise-settings-subsection">
                    <div class="enterprise-settings-subtitle">{{ t('enterprise_member_list_title') }}</div>
                    <div v-if="enterpriseMemberItems.length === 0" class="empty-note">
                      {{ t('enterprise_member_list_empty') }}
                    </div>
                    <div v-else class="enterprise-settings-list">
                      <article
                        v-for="member in enterpriseMemberItems"
                        :key="`enterprise-member-${member.id}`"
                        class="enterprise-settings-list-item"
                      >
                        <div class="enterprise-settings-list-main">
                          <strong>{{ member.display_name || member.username }}</strong>
                          <span>{{ t(`auth_role_${member.role}`) }}</span>
                        </div>
                        <div class="task-line">{{ member.username }}</div>
                      </article>
                    </div>
                  </div>
                  <div class="enterprise-settings-subsection">
                    <div class="enterprise-settings-subtitle">{{ t('enterprise_member_create_title') }}</div>
                    <div class="enterprise-topology-node-editor">
                      <label class="auth-field enterprise-topology-node-editor__full">
                        <span>{{ t('enterprise_member_role') }}</span>
                        <select
                          class="auth-input"
                          :value="enterpriseMemberForm.role"
                          :disabled="enterpriseMemberCreating"
                          @change="enterpriseMemberForm.role = $event.target.value"
                        >
                          <option
                            v-for="option in enterpriseMemberCreateRoleOptions"
                            :key="`enterprise-member-role-${option.value}`"
                            :value="option.value"
                          >
                            {{ option.label }}
                          </option>
                        </select>
                      </label>
                      <label class="auth-field enterprise-topology-node-editor__full">
                        <span>{{ t('enterprise_member_display_name') }}</span>
                        <input
                          class="auth-input"
                          :value="enterpriseMemberForm.display_name"
                          :disabled="enterpriseMemberCreating"
                          @input="enterpriseMemberForm.display_name = $event.target.value"
                        />
                      </label>
                      <label class="auth-field enterprise-topology-node-editor__full">
                        <span>{{ t('enterprise_member_username') }}</span>
                        <input
                          class="auth-input"
                          :value="enterpriseMemberForm.username"
                          :disabled="enterpriseMemberCreating"
                          @input="enterpriseMemberForm.username = $event.target.value"
                        />
                      </label>
                      <label class="auth-field enterprise-topology-node-editor__full">
                        <span>{{ t('enterprise_member_password') }}</span>
                        <input
                          class="auth-input"
                          type="password"
                          :value="enterpriseMemberForm.password"
                          :disabled="enterpriseMemberCreating"
                          @input="enterpriseMemberForm.password = $event.target.value"
                        />
                      </label>
                    </div>
                    <div class="enterprise-settings-actions">
                      <button
                        class="btn-primary"
                        type="button"
                        :disabled="enterpriseMemberCreating"
                        @click="submitEnterpriseMemberCreate"
                      >
                        {{ enterpriseMemberCreating ? `${t('enterprise_member_create_action')}...` : t('enterprise_member_create_action') }}
                      </button>
                    </div>
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
                <button class="btn-secondary" type="button" @click="applyCurrentEnterpriseWorkspacePreset()">
                  {{ t('enterprise_settings_apply_workspace_preset') }}
                </button>
                <button
                  v-for="action in enterpriseRoleWorkspaceActionItems"
                  :key="`enterprise-overview-footer-action-${action.key}`"
                  :class="action.tone === 'ghost' ? 'btn-ghost' : 'btn-secondary'"
                  type="button"
                  @click="runEnterpriseWorkspaceAction(action.key)"
                >
                  {{ action.label }}
                </button>
              </div>
            </template>

            <template v-else-if="enterpriseSettingsActiveTab === 'map_profiles'">
              <p class="panel-hint">{{ t('enterprise_settings_map_profiles_hint') }}</p>
              <div class="enterprise-settings-role-note">
                <strong>{{ enterpriseActiveTabModeLabel }}</strong>
                <p>{{ enterpriseActiveTabModeHint }}</p>
              </div>
              <div class="enterprise-settings-role-note">
                <strong>{{ t('enterprise_settings_map_profiles_workspace_title') }}</strong>
                <p>{{ t('enterprise_settings_map_profiles_workspace_hint') }}</p>
                <div class="map-settings-info-grid enterprise-settings-grid">
                  <div
                    v-for="card in enterpriseMapWorkspaceCards"
                    :key="`enterprise-map-workspace-${card.key}`"
                    class="map-settings-info-card"
                  >
                    <div class="map-settings-info-label">{{ card.label }}</div>
                    <div class="map-settings-info-value">{{ card.value }}</div>
                  </div>
                </div>
                <div
                  v-if="enterpriseMapWorkspaceMetaText"
                  class="task-line operations-last-fetched"
                >
                  {{ enterpriseMapWorkspaceMetaText }}
                </div>
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
              <div class="enterprise-settings-role-note">
                <strong>{{ t('enterprise_settings_route_topology_title') }}</strong>
                <p>{{ t('enterprise_settings_route_topology_hint') }}</p>
                <div class="map-settings-info-grid enterprise-settings-grid">
                  <div
                    v-for="card in enterpriseRouteTopologyCards"
                    :key="`enterprise-route-topology-${card.key}`"
                    class="map-settings-info-card"
                  >
                    <div class="map-settings-info-label">{{ card.label }}</div>
                    <div class="map-settings-info-value">{{ card.value }}</div>
                  </div>
                </div>
                <div class="task-line operations-last-fetched">
                  {{ enterpriseRouteTopologyMetaText }}
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
                <div class="enterprise-settings-actions">
                  <button
                    class="btn-secondary"
                    type="button"
                    :disabled="!authCanMapWrite || mapProfileImporting"
                    :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                    @click="triggerMapProfileImport"
                  >
                    {{ mapProfileImporting ? settingsLocale.mapProfileImporting : settingsLocale.mapProfileImport }}
                  </button>
                </div>
                <input
                  :ref="setMapProfileFileInput"
                  type="file"
                  accept="application/json,.json"
                  class="hidden-file-input"
                  @change="onMapProfileFileChange"
                />
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
                    <div v-if="formatMapProfileTopologySummary(profile)" class="map-profile-operator">
                      {{ formatMapProfileTopologySummary(profile) }}
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
                <button
                  class="btn-primary"
                  type="button"
                  :disabled="!authCanMapWrite || enterpriseMapEditorSaving"
                  :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                  @click="openEnterpriseMapEditorDialog"
                >
                  {{ t('enterprise_settings_map_editor_open') }}
                </button>
                <button class="btn-secondary" type="button" @click="openPageSettingsFromEnterpriseSettings">
                  {{ t('enterprise_settings_open_page_settings') }}
                </button>
                <button
                  class="btn-secondary"
                  type="button"
                  @click="openEnterpriseTopologyEditorDialog"
                >
                  {{ t('enterprise_settings_route_topology_open') }}
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
                <strong>{{ t('enterprise_settings_point_templates_workspace_title') }}</strong>
                <p>{{ t('enterprise_settings_point_templates_workspace_hint') }}</p>
                <div class="map-settings-info-grid enterprise-settings-grid">
                  <div
                    v-for="card in enterprisePointTemplateWorkspaceCards"
                    :key="`enterprise-point-template-workspace-${card.key}`"
                    class="map-settings-info-card"
                  >
                    <div class="map-settings-info-label">{{ card.label }}</div>
                    <div class="map-settings-info-value">{{ card.value }}</div>
                  </div>
                </div>
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
                <strong>{{ t('enterprise_settings_runtime_workspace_title') }}</strong>
                <p>{{ t('enterprise_settings_runtime_workspace_hint') }}</p>
                <div class="map-settings-info-grid enterprise-settings-grid">
                  <div
                    v-for="card in enterpriseRuntimeWorkspaceCards"
                    :key="`enterprise-runtime-workspace-${card.key}`"
                    class="map-settings-info-card"
                  >
                    <div class="map-settings-info-label">{{ card.label }}</div>
                    <div class="map-settings-info-value">{{ card.value }}</div>
                  </div>
                </div>
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
                <strong>{{ t('enterprise_settings_ai_workspace_title') }}</strong>
                <p>{{ t('enterprise_settings_ai_workspace_hint') }}</p>
                <div class="map-settings-info-grid enterprise-settings-grid">
                  <div
                    v-for="card in enterpriseAiWorkspaceCards"
                    :key="`enterprise-ai-workspace-${card.key}`"
                    class="map-settings-info-card"
                  >
                    <div class="map-settings-info-label">{{ card.label }}</div>
                    <div class="map-settings-info-value">{{ card.value }}</div>
                  </div>
                </div>
                <div
                  v-if="comfyRenderLastFetchedText"
                  class="task-line operations-last-fetched"
                >
                  {{ comfyRenderLastFetchedText }}
                </div>
                <div class="enterprise-settings-inline-actions">
                  <button class="btn-ghost enterprise-settings-inline-button" type="button" @click="fetchComfyCheckpoints({ force: true })">
                    {{ t('enterprise_settings_ai_refresh_checkpoints') }}
                  </button>
                  <button class="btn-ghost enterprise-settings-inline-button" type="button" @click="fetchComfyRenderJobs({ force: true })">
                    {{ t('enterprise_settings_ai_refresh_jobs') }}
                  </button>
                  <button class="btn-ghost enterprise-settings-inline-button" type="button" @click="fetchComfySharedTemplates({ force: true })">
                    {{ t('enterprise_settings_ai_refresh_shared') }}
                  </button>
                </div>
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
              <div class="enterprise-settings-role-note">
                <strong>{{ t('enterprise_settings_audit_workspace_title') }}</strong>
                <p>{{ t('enterprise_settings_audit_workspace_hint') }}</p>
                <div class="map-settings-info-grid enterprise-settings-grid">
                  <div
                    v-for="card in enterpriseAuditWorkspaceCards"
                    :key="`enterprise-audit-workspace-${card.key}`"
                    class="map-settings-info-card"
                  >
                    <div class="map-settings-info-label">{{ card.label }}</div>
                    <div class="map-settings-info-value">{{ card.value }}</div>
                  </div>
                </div>
                <div
                  v-if="operationAuditLastFetchedAt"
                  class="task-line operations-last-fetched"
                >
                  {{ formatInlineMessage(t('operations_last_updated'), { at: operationAuditLastFetchedAt }) }}
                </div>
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
                    <span
                      v-if="selectedVisibleOperationAuditCount(enterpriseFilteredAuditEntries)"
                      class="point-badge operations-selection-badge"
                    >
                      {{
                        formatInlineMessage(t('operations_selection_count'), {
                          count: selectedVisibleOperationAuditCount(enterpriseFilteredAuditEntries)
                        })
                      }}
                    </span>
                    <button class="btn-ghost" type="button" @click="toggleSelectVisibleOperationAudits(enterpriseFilteredAuditEntries)">
                      {{
                        areAllVisibleOperationAuditsSelected(enterpriseFilteredAuditEntries)
                          ? t('operations_clear_selection')
                          : t('operations_select_visible')
                      }}
                    </button>
                    <button
                      class="btn-delete"
                      type="button"
                      :disabled="operationAuditBulkDeleting"
                      @click="deleteSelectedOperationAuditsWithAuth(enterpriseFilteredAuditEntries)"
                    >
                      {{
                        operationAuditBulkDeleting
                          ? `${t('operations_bulk_delete')}...`
                          : t('operations_bulk_delete')
                      }}
                    </button>
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
                      <div class="operations-card-head-main">
                        <label class="operations-card-select">
                          <input
                            type="checkbox"
                            :checked="isOperationAuditSelected(entry)"
                            @change="toggleOperationAuditSelection(entry)"
                          />
                        </label>
                        <div>
                        <strong>{{ formatOperationAuditTitle(entry) }}</strong>
                        <div class="task-line">{{ formatOperationAuditResourceRef(entry) }}</div>
                        </div>
                      </div>
                      <span class="point-badge">{{ operationActionLabel(entry.action) }}</span>
                    </div>
                    <div class="task-line">{{ formatOperationAuditOperator(entry) }}</div>
                    <div class="task-line task-time">{{ entry.performed_at }}</div>
                    <div v-if="formatOperationAuditMetadata(entry)" class="task-line operations-summary">
                      {{ formatOperationAuditMetadata(entry) }}
                    </div>
                    <div class="operations-card-actions">
                      <button
                        class="btn-delete"
                        type="button"
                        :disabled="operationAuditBulkDeleting || Number(deletingOperationAuditId) === Number(entry.id)"
                        @click="deleteOperationAuditWithAuth(entry)"
                      >
                        {{
                          Number(deletingOperationAuditId) === Number(entry.id)
                            ? `${t('operations_delete_record')}...`
                            : t('operations_delete_record')
                        }}
                      </button>
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

        <Teleport to="body">
        <div
          v-if="enterprisePageSettingsDialogOpen"
          class="enterprise-settings-overlay"
          @click.self="closeEnterprisePageSettingsDialog"
        >
          <section class="enterprise-settings-overlay-card" role="dialog" aria-modal="true">
            <header class="enterprise-settings-overlay-header">
              <div>
                <div class="auth-dialog-kicker">{{ t('enterprise_settings_page_settings_entry') }}</div>
                <h3 class="auth-dialog-title">{{ t('enterprise_settings_page_settings_title') }}</h3>
                <p class="auth-dialog-hint">{{ t('enterprise_settings_page_settings_dialog_hint') }}</p>
              </div>
              <button class="auth-dialog-close" type="button" @click="closeEnterprisePageSettingsDialog">
                ×
              </button>
            </header>

            <div class="enterprise-settings-overlay-body">
              <section class="enterprise-settings-subsection enterprise-page-settings-group">
                <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_page_settings_display_title') }}</div>
                <p class="panel-hint">{{ t('enterprise_settings_page_settings_display_hint') }}</p>
                <label class="map-setting-row">
                  <input v-model="showAutoPath" type="checkbox" />
                  <span>{{ settingsLocale.showAutoPath }}</span>
                </label>
                <label class="map-setting-row">
                  <input v-model="showMarkerIcons" type="checkbox" />
                  <span>{{ settingsLocale.showMarkerIcons }}</span>
                </label>
                <label class="map-setting-row">
                  <input v-model="showPathArrows" type="checkbox" />
                  <span>{{ settingsLocale.showPathArrows }}</span>
                </label>
                <label class="map-setting-row">
                  <input v-model="showMinimap" type="checkbox" />
                  <span>{{ settingsLocale.showMinimap }}</span>
                </label>
                <label class="map-setting-row">
                  <input v-model="showBusinessPoints" type="checkbox" />
                  <span>{{ settingsLocale.showBusinessPoints }}</span>
                </label>
                <p class="panel-hint">{{ settingsLocale.showBusinessPointsHint }}</p>
                <label v-if="enterpriseTopologyViewAvailable" class="auth-field">
                  <span>{{ settingsLocale.topologyViewMode }}</span>
                  <select v-model="topologyViewMode" class="auth-input">
                    <option value="standard">{{ settingsLocale.topologyViewModeStandard }}</option>
                    <option value="pure">{{ settingsLocale.topologyViewModePure }}</option>
                  </select>
                </label>
                <p v-if="enterpriseTopologyViewAvailable" class="panel-hint">
                  {{ settingsLocale.topologyViewModeHint }}
                </p>
                <label class="map-setting-row">
                  <input v-model="showStatusLegend" type="checkbox" />
                  <span>{{ settingsLocale.showAgvStatus }}</span>
                </label>
                <label v-if="showStatusLegend" class="auth-field">
                  <span>{{ settingsLocale.agvLegendLayout }}</span>
                  <select v-model="statusLegendLayout" class="auth-input">
                    <option value="horizontal">{{ settingsLocale.agvLegendLayoutHorizontal }}</option>
                    <option value="vertical">{{ settingsLocale.agvLegendLayoutVertical }}</option>
                  </select>
                </label>
              </section>

              <section class="enterprise-settings-subsection enterprise-page-settings-group">
                <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_page_settings_overlap_title') }}</div>
                <p class="panel-hint">{{ t('enterprise_settings_page_settings_overlap_hint') }}</p>
                <div class="enterprise-page-settings-shortcuts">
                  <article class="enterprise-page-settings-shortcut-card">
                    <strong>{{ t('enterprise_settings_page_settings_overlap_map_title') }}</strong>
                    <p>{{ t('enterprise_settings_page_settings_overlap_map_hint') }}</p>
                    <button
                      class="btn-secondary"
                      type="button"
                      @click="closeEnterprisePageSettingsDialog(); switchEnterpriseSettingsTab('map_profiles')"
                    >
                      {{ t('enterprise_settings_page_settings_jump_map_profiles') }}
                    </button>
                  </article>
                  <article class="enterprise-page-settings-shortcut-card">
                    <strong>{{ t('enterprise_settings_page_settings_overlap_runtime_title') }}</strong>
                    <p>{{ t('enterprise_settings_page_settings_overlap_runtime_hint') }}</p>
                    <button
                      class="btn-secondary"
                      type="button"
                      @click="closeEnterprisePageSettingsDialog(); switchEnterpriseSettingsTab('runtime')"
                    >
                      {{ t('enterprise_settings_page_settings_jump_runtime') }}
                    </button>
                  </article>
                </div>
              </section>

              <section class="enterprise-settings-subsection enterprise-page-settings-group">
                <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_page_settings_tools_title') }}</div>
                <p class="panel-hint">{{ t('enterprise_settings_page_settings_tools_hint') }}</p>
                <label class="map-setting-row">
                  <input v-model="showGuideCenterOnLoad" type="checkbox" />
                  <span>{{ t('enterprise_settings_page_settings_guide_auto_open') }}</span>
                </label>
                <p class="panel-hint">{{ t('enterprise_settings_page_settings_guide_auto_open_hint') }}</p>
                <label class="auth-field">
                  <span>{{ settingsLocale.baseSpeed }}</span>
                  <input
                    v-model.number="baseSpeed"
                    class="auth-input"
                    type="number"
                    min="0.2"
                    max="6"
                    step="0.01"
                  />
                </label>
                <p class="panel-hint">{{ settingsLocale.baseSpeedHint }}</p>
                <label class="auth-field">
                  <span>{{ settingsLocale.followDistance }}</span>
                  <input
                    v-model.number="followDistance"
                    class="auth-input"
                    type="number"
                    min="0.25"
                    max="3"
                    step="0.05"
                  />
                </label>
                <p class="panel-hint">{{ settingsLocale.followDistanceHint }}</p>
                <label class="auth-field">
                  <span>{{ settingsLocale.deadlockTimeoutSec }}</span>
                  <input
                    v-model.number="deadlockTimeoutSec"
                    class="auth-input"
                    type="number"
                    min="1"
                    max="20"
                    step="0.5"
                  />
                </label>
                <p class="panel-hint">{{ settingsLocale.deadlockTimeoutSecHint }}</p>
                <label class="auth-field">
                  <span>{{ settingsLocale.idleReturnTimeoutSec }}</span>
                  <input
                    v-model.number="idleReturnTimeoutSec"
                    class="auth-input"
                    type="number"
                    min="5"
                    max="600"
                    step="1"
                  />
                </label>
                <p class="panel-hint">{{ settingsLocale.idleReturnTimeoutSecHint }}</p>
                <label class="auth-field">
                  <span>{{ settingsLocale.idleChargeTimeoutSec }}</span>
                  <input
                    v-model.number="idleChargeTimeoutSec"
                    class="auth-input"
                    type="number"
                    min="5"
                    max="600"
                    step="1"
                  />
                </label>
                <p class="panel-hint">{{ settingsLocale.idleChargeTimeoutSecHint }}</p>
                <label class="auth-field">
                  <span>{{ settingsLocale.idleChargeBatteryThreshold }}</span>
                  <input
                    v-model.number="idleChargeBatteryThreshold"
                    class="auth-input"
                    type="number"
                    min="24"
                    max="95"
                    step="1"
                  />
                </label>
                <p class="panel-hint">{{ settingsLocale.idleChargeBatteryThresholdHint }}</p>
                <label class="auth-field">
                  <span>{{ settingsLocale.lowBatteryThreshold }}</span>
                  <input
                    v-model.number="lowBatteryThreshold"
                    class="auth-input"
                    type="number"
                    min="5"
                    max="80"
                    step="1"
                  />
                </label>
                <p class="panel-hint">{{ settingsLocale.lowBatteryThresholdHint }}</p>
                <label class="auth-field">
                  <span>{{ settingsLocale.batteryActiveDrainPerSec }}</span>
                  <input
                    v-model.number="batteryActiveDrainPerSec"
                    class="auth-input"
                    type="number"
                    min="0.01"
                    max="10"
                    step="0.01"
                  />
                </label>
                <p class="panel-hint">{{ settingsLocale.batteryActiveDrainPerSecHint }}</p>
                <label class="auth-field">
                  <span>{{ settingsLocale.batteryWaitingDrainPerSec }}</span>
                  <input
                    v-model.number="batteryWaitingDrainPerSec"
                    class="auth-input"
                    type="number"
                    min="0"
                    max="5"
                    step="0.01"
                  />
                </label>
                <p class="panel-hint">{{ settingsLocale.batteryWaitingDrainPerSecHint }}</p>
                <label class="auth-field">
                  <span>{{ settingsLocale.batteryIdleDrainPerSec }}</span>
                  <input
                    v-model.number="batteryIdleDrainPerSec"
                    class="auth-input"
                    type="number"
                    min="0"
                    max="2"
                    step="0.001"
                  />
                </label>
                <p class="panel-hint">{{ settingsLocale.batteryIdleDrainPerSecHint }}</p>
                <label class="auth-field">
                  <span>{{ settingsLocale.batteryParkingIdleDrainPerSec }}</span>
                  <input
                    v-model.number="batteryParkingIdleDrainPerSec"
                    class="auth-input"
                    type="number"
                    min="0"
                    max="2"
                    step="0.001"
                  />
                </label>
                <p class="panel-hint">{{ settingsLocale.batteryParkingIdleDrainPerSecHint }}</p>
                <label class="auth-field">
                  <span>{{ settingsLocale.batteryChargePerSec }}</span>
                  <input
                    v-model.number="batteryChargePerSec"
                    class="auth-input"
                    type="number"
                    min="0.1"
                    max="20"
                    step="0.1"
                  />
                </label>
                <p class="panel-hint">{{ settingsLocale.batteryChargePerSecHint }}</p>
                <div class="enterprise-settings-subtitle">{{ settingsLocale.runtimeDebugGroup }}</div>
                <p class="panel-hint">{{ settingsLocale.runtimeDebugGroupHint }}</p>
                <label class="map-setting-row">
                  <input v-model="showRuntimeSegmentType" type="checkbox" />
                  <span>{{ settingsLocale.showRuntimeSegmentType }}</span>
                </label>
                <label class="map-setting-row">
                  <input v-model="showTopologyEdgeSpeed" type="checkbox" />
                  <span>{{ settingsLocale.showTopologyEdgeSpeed }}</span>
                </label>
                <label class="map-setting-row">
                  <input v-model="showRuntimeConflictReason" type="checkbox" />
                  <span>{{ settingsLocale.showRuntimeConflictReason }}</span>
                </label>
                <label class="map-setting-row">
                  <input v-model="showSelectedAgvRuntimeOverlay" type="checkbox" />
                  <span>{{ settingsLocale.showSelectedAgvRuntimeOverlay }}</span>
                </label>
                <div class="enterprise-page-settings-shortcut-list">
                  <div
                    v-for="entry in shortcutGuideEntries"
                    :key="`enterprise-shortcut-guide-${entry}`"
                    class="task-line"
                  >
                    {{ entry }}
                  </div>
                </div>
                <div class="enterprise-settings-actions">
                  <button class="btn-secondary" type="button" @click="openGuideCenter">
                    {{ guideCenterLocale.open }}
                  </button>
                  <button class="btn-ghost" type="button" @click="resetMapView">
                    {{ settingsLocale.resetView }}
                  </button>
                  <button class="btn-ghost" type="button" @click="openEnterpriseShortcutPlannerDialog">
                    {{ t('enterprise_settings_shortcuts_entry') }}
                  </button>
                </div>
              </section>
            </div>
          </section>
        </div>
        </Teleport>

        <Teleport to="body">
        <div
          v-if="enterpriseShortcutPlannerDialogOpen"
          class="enterprise-settings-overlay"
          @click.self="closeEnterpriseShortcutPlannerDialog"
        >
          <section class="enterprise-settings-overlay-card enterprise-settings-overlay-card-compact" role="dialog" aria-modal="true">
            <header class="enterprise-settings-overlay-header">
              <div>
                <div class="auth-dialog-kicker">{{ t('enterprise_settings_shortcuts_entry') }}</div>
                <h3 class="auth-dialog-title">{{ t('enterprise_settings_shortcuts_dialog_title') }}</h3>
                <p class="auth-dialog-hint">{{ t('enterprise_settings_shortcuts_dialog_hint') }}</p>
              </div>
              <button class="auth-dialog-close" type="button" @click="closeEnterpriseShortcutPlannerDialog">
                ×
              </button>
            </header>

            <div class="enterprise-settings-overlay-body">
              <section class="enterprise-settings-subsection enterprise-page-settings-group">
                <div class="enterprise-settings-subtitle">{{ guideCenterLocale.shortcutsTitle }}</div>
                <div class="enterprise-page-settings-shortcut-list">
                  <div
                    v-for="entry in shortcutGuideEntries"
                    :key="`shortcut-guide-entry-${entry}`"
                    class="task-line"
                  >
                    {{ entry }}
                  </div>
                </div>
                <p class="panel-hint">{{ t('shortcut_editor_fixed_mouse_hint') }}</p>
              </section>

              <section class="enterprise-settings-subsection enterprise-page-settings-group">
                <div class="enterprise-settings-subtitle">{{ t('shortcut_editor_live_title') }}</div>
                <p class="panel-hint">{{ t('shortcut_editor_live_hint') }}</p>
                <p class="panel-hint">{{ t('shortcut_editor_scope_hint') }}</p>
                <p
                  v-if="shortcutEditorStatus"
                  class="panel-hint"
                  :class="{
                    'status-error': shortcutEditorStatusType === 'error',
                    'status-success': shortcutEditorStatusType === 'success'
                  }"
                >
                  {{ shortcutEditorStatus }}
                </p>
                <div v-if="!shortcutEditorCanEdit" class="permission-gate-card compact">
                  <div class="empty-note">{{ t('shortcut_editor_readonly_hint') }}</div>
                </div>
                <div v-else class="enterprise-shortcut-editor-grid-shell">
                  <div
                    v-if="shortcutEditorHasUnsavedChanges"
                    class="enterprise-shortcut-editor-banner is-warning"
                  >
                    {{ t('shortcut_editor_unsaved_changes') }}
                  </div>
                  <div v-if="shortcutEditorHasConflicts" class="enterprise-shortcut-editor-banner">
                    {{ t('shortcut_editor_conflict') }}
                  </div>
                  <div class="enterprise-shortcut-editor-grid">
                  <article
                    v-for="item in shortcutEditorRows"
                    :key="item.key"
                    class="enterprise-shortcut-editor-card"
                    :class="{ 'is-conflict': item.conflictKey }"
                  >
                    <div class="enterprise-shortcut-editor-head">
                      <div>
                        <strong>{{ item.label }}</strong>
                        <p>{{ item.hint }}</p>
                      </div>
                      <span
                        class="point-badge enterprise-shortcut-key-badge"
                        :class="{ 'is-conflict': item.conflictKey }"
                      >
                        {{ item.currentLabel }}
                      </span>
                    </div>
                    <div class="enterprise-shortcut-editor-meta">
                      <span>{{ t('shortcut_editor_current_key') }}{{ item.currentLabel }}</span>
                      <span>{{ t('shortcut_editor_default_key') }}{{ item.defaultLabel }}</span>
                    </div>
                    <div v-if="item.fixedHint" class="panel-hint">{{ item.fixedHint }}</div>
                    <div v-if="item.conflictKey" class="panel-hint status-error">
                      {{ t('shortcut_editor_conflict') }}
                    </div>
                    <div class="enterprise-settings-actions">
                      <button
                        class="btn-secondary"
                        type="button"
                        @click="startShortcutCapture(item.key)"
                      >
                        {{
                          shortcutEditorCaptureActionKey === item.key
                            ? t('shortcut_editor_capturing')
                            : t('shortcut_editor_record')
                        }}
                      </button>
                      <button
                        class="btn-ghost"
                        type="button"
                        :disabled="item.isEmpty"
                        @click="clearShortcutEditorActionBinding(item.key)"
                      >
                        {{ t('shortcut_editor_clear_binding') }}
                      </button>
                      <button
                        class="btn-ghost"
                        type="button"
                        :disabled="item.isDefault"
                        @click="restoreShortcutEditorActionDefault(item.key)"
                      >
                        {{ t('shortcut_editor_restore_item') }}
                      </button>
                      <button
                        v-if="shortcutEditorCaptureActionKey === item.key"
                        class="btn-ghost"
                        type="button"
                        @click="stopShortcutCapture"
                      >
                        {{ t('shortcut_editor_stop_capture') }}
                      </button>
                    </div>
                  </article>
                </div>
                </div>
              </section>

              <section class="enterprise-settings-subsection enterprise-page-settings-group">
                <div class="enterprise-settings-actions">
                  <button class="btn-ghost" type="button" @click="restoreShortcutEditorDefaults">
                    {{ t('shortcut_editor_restore_defaults') }}
                  </button>
                  <button class="btn-secondary" type="button" @click="closeEnterpriseShortcutPlannerDialog">
                    {{ t('enterprise_settings_map_editor_cancel') }}
                  </button>
                  <button
                    class="btn-primary"
                    type="button"
                    :disabled="!shortcutEditorCanEdit || shortcutEditorHasConflicts || !shortcutEditorHasUnsavedChanges"
                    @click="saveShortcutEditorDraft"
                  >
                    {{ t('shortcut_editor_save') }}
                  </button>
                </div>
              </section>
            </div>
          </section>
        </div>
        </Teleport>

        <Teleport to="body">
        <div
          v-if="enterpriseMapEditorDialogOpen"
          class="enterprise-settings-overlay"
          @click.self="closeEnterpriseMapEditorDialog"
        >
          <section class="enterprise-settings-overlay-card enterprise-settings-overlay-card-wide" role="dialog" aria-modal="true">
            <header class="enterprise-settings-overlay-header">
              <div>
                <div class="auth-dialog-kicker">{{ t('enterprise_settings_tab_map_profiles') }}</div>
                <h3 class="auth-dialog-title">{{ t('enterprise_settings_map_editor_title') }}</h3>
                <p class="auth-dialog-hint">{{ t('enterprise_settings_map_editor_hint') }}</p>
              </div>
              <button class="auth-dialog-close" type="button" @click="closeEnterpriseMapEditorDialog">
                ×
              </button>
            </header>

            <div class="enterprise-settings-overlay-body">
              <section class="enterprise-settings-subsection enterprise-page-settings-group">
                <div class="map-settings-info-grid enterprise-settings-grid">
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.mapInfoSize }}</div>
                    <div class="map-settings-info-value">{{ enterpriseMapEditorSizeLabel }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_map_editor_valid_count') }}</div>
                    <div class="map-settings-info-value">{{ enterpriseMapEditorValidCount }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_map_editor_blocked_count') }}</div>
                    <div class="map-settings-info-value">{{ enterpriseMapEditorBlockedCount }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_map_editor_help_locked_title') }}</div>
                    <div class="map-settings-info-value">{{ enterpriseMapEditorLockedCount }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_map_editor_help_warning_title') }}</div>
                    <div class="map-settings-info-value">{{ enterpriseMapEditorWarningCount }}</div>
                  </div>
                </div>
                <div class="enterprise-settings-chip-list">
                  <span class="point-badge enterprise-settings-chip">{{ t('enterprise_settings_map_editor_help_add') }}</span>
                  <span class="point-badge enterprise-settings-chip enterprise-settings-chip-muted">{{ t('enterprise_settings_map_editor_help_remove') }}</span>
                  <span
                    class="point-badge enterprise-settings-chip"
                    :class="{ 'enterprise-settings-chip-muted': !enterpriseMapEditorIsIrregular }"
                  >
                    {{ enterpriseMapEditorIsIrregular ? t('map_shape_irregular') : enterpriseMapEditorFootprintLabel }}
                  </span>
                  <span class="point-badge enterprise-settings-chip">{{ t('enterprise_settings_map_editor_help_runtime_locked') }}</span>
                  <span class="point-badge enterprise-settings-chip enterprise-settings-chip-muted">{{ t('enterprise_settings_map_editor_help_referenced') }}</span>
                </div>
              </section>

              <section class="enterprise-settings-subsection enterprise-page-settings-group">
                <div class="enterprise-settings-subtitle">{{ t('enterprise_settings_map_editor_grid_title') }}</div>
                <div class="enterprise-map-editor-draft-controls">
                  <div class="enterprise-map-editor-draft-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_map_editor_bounds_title') }}</div>
                    <div class="enterprise-map-editor-draft-summary">{{ enterpriseMapEditorFootprintLabel }}</div>
                    <p class="panel-hint enterprise-map-editor-draft-hint">
                      {{ t('enterprise_settings_map_editor_bounds_hint') }}
                    </p>
                  </div>
                  <div class="enterprise-map-editor-stepper-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_map_editor_bounds_cols') }}</div>
                    <div class="enterprise-map-editor-stepper">
                      <button
                        class="btn-ghost enterprise-map-editor-stepper-button"
                        type="button"
                        :disabled="!canResizeEnterpriseMapEditorTo(enterpriseMapEditorDraftCols - 1, enterpriseMapEditorDraftRows)"
                        @click="resizeEnterpriseMapEditorDraft('cols', -1)"
                      >
                        -
                      </button>
                      <strong>{{ enterpriseMapEditorDraftCols }}</strong>
                      <button
                        class="btn-ghost enterprise-map-editor-stepper-button"
                        type="button"
                        :disabled="!canResizeEnterpriseMapEditorTo(enterpriseMapEditorDraftCols + 1, enterpriseMapEditorDraftRows)"
                        @click="resizeEnterpriseMapEditorDraft('cols', 1)"
                      >
                        +
                      </button>
                    </div>
                    <div class="enterprise-map-editor-anchor-toggle">
                      <button
                        class="btn-ghost enterprise-map-editor-anchor-button"
                        :class="{ active: enterpriseMapEditorColAnchor === 'left' }"
                        type="button"
                        @click="enterpriseMapEditorColAnchor = 'left'"
                      >
                        {{ t('enterprise_settings_map_editor_anchor_left') }}
                      </button>
                      <button
                        class="btn-ghost enterprise-map-editor-anchor-button"
                        :class="{ active: enterpriseMapEditorColAnchor === 'right' }"
                        type="button"
                        @click="enterpriseMapEditorColAnchor = 'right'"
                      >
                        {{ t('enterprise_settings_map_editor_anchor_right') }}
                      </button>
                    </div>
                  </div>
                  <div class="enterprise-map-editor-stepper-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_map_editor_bounds_rows') }}</div>
                    <div class="enterprise-map-editor-stepper">
                      <button
                        class="btn-ghost enterprise-map-editor-stepper-button"
                        type="button"
                        :disabled="!canResizeEnterpriseMapEditorTo(enterpriseMapEditorDraftCols, enterpriseMapEditorDraftRows - 1)"
                        @click="resizeEnterpriseMapEditorDraft('rows', -1)"
                      >
                        -
                      </button>
                      <strong>{{ enterpriseMapEditorDraftRows }}</strong>
                      <button
                        class="btn-ghost enterprise-map-editor-stepper-button"
                        type="button"
                        :disabled="!canResizeEnterpriseMapEditorTo(enterpriseMapEditorDraftCols, enterpriseMapEditorDraftRows + 1)"
                        @click="resizeEnterpriseMapEditorDraft('rows', 1)"
                      >
                        +
                      </button>
                    </div>
                    <div class="enterprise-map-editor-anchor-toggle">
                      <button
                        class="btn-ghost enterprise-map-editor-anchor-button"
                        :class="{ active: enterpriseMapEditorRowAnchor === 'top' }"
                        type="button"
                        @click="enterpriseMapEditorRowAnchor = 'top'"
                      >
                        {{ t('enterprise_settings_map_editor_anchor_top') }}
                      </button>
                      <button
                        class="btn-ghost enterprise-map-editor-anchor-button"
                        :class="{ active: enterpriseMapEditorRowAnchor === 'bottom' }"
                        type="button"
                        @click="enterpriseMapEditorRowAnchor = 'bottom'"
                      >
                        {{ t('enterprise_settings_map_editor_anchor_bottom') }}
                      </button>
                    </div>
                  </div>
                  <div class="enterprise-map-editor-stepper-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_map_editor_shift_title') }}</div>
                    <div class="enterprise-map-editor-shift-grid">
                      <button
                        class="btn-ghost enterprise-map-editor-shift-button enterprise-map-editor-shift-button-up"
                        type="button"
                        :disabled="!canShiftEnterpriseMapEditorDraft(0, -1)"
                        @click="shiftEnterpriseMapEditorDraft(0, -1)"
                      >
                        ↑
                      </button>
                      <button
                        class="btn-ghost enterprise-map-editor-shift-button"
                        type="button"
                        :disabled="!canShiftEnterpriseMapEditorDraft(-1, 0)"
                        @click="shiftEnterpriseMapEditorDraft(-1, 0)"
                      >
                        ←
                      </button>
                      <button
                        class="btn-ghost enterprise-map-editor-shift-button"
                        type="button"
                        :disabled="!canShiftEnterpriseMapEditorDraft(1, 0)"
                        @click="shiftEnterpriseMapEditorDraft(1, 0)"
                      >
                        →
                      </button>
                      <button
                        class="btn-ghost enterprise-map-editor-shift-button enterprise-map-editor-shift-button-down"
                        type="button"
                        :disabled="!canShiftEnterpriseMapEditorDraft(0, 1)"
                        @click="shiftEnterpriseMapEditorDraft(0, 1)"
                      >
                        ↓
                      </button>
                    </div>
                    <p class="panel-hint enterprise-map-editor-draft-hint">
                      {{ t('enterprise_settings_map_editor_shift_hint') }}
                    </p>
                  </div>
                  <div class="enterprise-map-editor-stepper-card enterprise-map-editor-zoom-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_map_editor_zoom_title') }}</div>
                    <div class="enterprise-map-editor-zoom-controls">
                      <button
                        class="btn-ghost enterprise-map-editor-stepper-button"
                        type="button"
                        :title="t('enterprise_settings_map_editor_zoom_out')"
                        @click="adjustEnterpriseMapEditorZoom(-0.05)"
                      >
                        -
                      </button>
                      <button
                        class="btn-ghost enterprise-map-editor-zoom-readout"
                        type="button"
                        :title="t('enterprise_settings_map_editor_zoom_reset')"
                        @click="resetEnterpriseMapEditorZoom"
                      >
                        {{ enterpriseMapEditorZoomPercent }}
                      </button>
                      <button
                        class="btn-ghost enterprise-map-editor-stepper-button"
                        type="button"
                        :title="t('enterprise_settings_map_editor_zoom_in')"
                        @click="adjustEnterpriseMapEditorZoom(0.05)"
                      >
                        +
                      </button>
                    </div>
                  </div>
                </div>
                <div class="enterprise-map-editor-grid-shell" @wheel.prevent="handleEnterpriseMapEditorWheel">
                  <div
                    class="enterprise-map-editor-grid"
                    :style="enterpriseMapEditorGridStyle"
                  >
                    <template v-for="row in enterpriseMapEditorRows" :key="`enterprise-map-editor-row-${row}`">
                      <button
                        v-for="col in enterpriseMapEditorCols"
                        :key="`enterprise-map-editor-cell-${col}-${row}`"
                        type="button"
                        class="enterprise-map-editor-cell"
                        :class="{
                          'is-valid': isEnterpriseMapEditorCellValid(col, row),
                          'is-void': !isEnterpriseMapEditorCellValid(col, row),
                          'is-blocked': isEnterpriseMapEditorCellBlocked(col, row),
                          'is-occupied': isCellOccupied(col, row),
                          'is-locked': isEnterpriseMapEditorCellLocked(col, row),
                          'is-expanded': isEnterpriseMapEditorCellExpanded(col, row),
                          'is-referenced': isEnterpriseMapEditorCellWarned(col, row)
                        }"
                        :disabled="isEnterpriseMapEditorCellLocked(col, row)"
                        :title="buildEnterpriseMapEditorCellTitle(col, row)"
                        @click="applyEnterpriseMapEditorCell({ x: col, y: row }, $event)"
                      >
                        <span v-if="isEnterpriseMapEditorCellLocked(col, row)">×</span>
                        <span v-else-if="isEnterpriseMapEditorCellBlocked(col, row)">■</span>
                        <span v-else-if="isEnterpriseMapEditorCellWarned(col, row)">!</span>
                        <span v-else-if="isEnterpriseMapEditorCellExpanded(col, row)">+</span>
                        <span v-else-if="isEnterpriseMapEditorCellValid(col, row)">□</span>
                      </button>
                    </template>
                  </div>
                </div>
              </section>

              <div class="enterprise-settings-actions">
                <button class="btn-ghost" type="button" @click="resetEnterpriseMapEditorDraft">
                  {{ t('enterprise_settings_map_editor_reset') }}
                </button>
                <button class="btn-secondary" type="button" @click="closeEnterpriseMapEditorDialog">
                  {{ t('enterprise_settings_map_editor_cancel') }}
                </button>
                <button
                  class="btn-primary"
                  type="button"
                  :disabled="enterpriseMapEditorSaving || !authCanMapWrite"
                  :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                  @click="saveEnterpriseMapEditorDraft"
                >
                  {{
                    enterpriseMapEditorSaving
                      ? `${t('enterprise_settings_map_editor_save')}...`
                      : t('enterprise_settings_map_editor_save')
                  }}
                </button>
              </div>
            </div>
          </section>
        </div>
        </Teleport>

        <Teleport to="body">
        <div
          v-if="enterpriseTopologyEditorDialogOpen"
          class="enterprise-settings-overlay"
          @click.self="closeEnterpriseTopologyEditorDialog"
        >
          <section class="enterprise-settings-overlay-card enterprise-settings-overlay-card-wide" role="dialog" aria-modal="true">
            <header class="enterprise-settings-overlay-header">
              <div>
                <div class="auth-dialog-kicker">{{ t('enterprise_settings_route_topology_title') }}</div>
                <h3 class="auth-dialog-title">{{ t('enterprise_settings_route_topology_editor_title') }}</h3>
                <p class="auth-dialog-hint">{{ t('enterprise_settings_route_topology_editor_hint') }}</p>
              </div>
              <button class="auth-dialog-close" type="button" @click="closeEnterpriseTopologyEditorDialog">
                ×
              </button>
            </header>

            <div class="enterprise-settings-overlay-body">
              <section class="enterprise-settings-subsection enterprise-page-settings-group">
                <div class="map-settings-info-grid enterprise-settings-grid">
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_route_topology_nodes') }}</div>
                    <div class="map-settings-info-value">{{ enterpriseTopologyDraftSummary.node_count }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_route_topology_edges') }}</div>
                    <div class="map-settings-info-value">{{ enterpriseTopologyDraftSummary.edge_count }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_route_topology_stations') }}</div>
                    <div class="map-settings-info-value">{{ enterpriseTopologyDraftSummary.station_count }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_route_topology_parking') }}</div>
                    <div class="map-settings-info-value">{{ enterpriseTopologyDraftSummary.parking_count }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_route_topology_charge') }}</div>
                    <div class="map-settings-info-value">{{ enterpriseTopologyDraftSummary.charge_count }}</div>
                  </div>
                </div>
                <div class="enterprise-settings-chip-list">
                  <span class="point-badge enterprise-settings-chip">{{ t('enterprise_settings_route_topology_help_add') }}</span>
                  <span class="point-badge enterprise-settings-chip enterprise-settings-chip-muted">{{ t('enterprise_settings_route_topology_help_connect') }}</span>
                  <span class="point-badge enterprise-settings-chip enterprise-settings-chip-muted">{{ t('enterprise_settings_route_topology_help_select_edge') }}</span>
                  <span class="point-badge enterprise-settings-chip enterprise-settings-chip-muted">{{ t('enterprise_settings_route_topology_help_blocked') }}</span>
                </div>
                <div v-if="!authCanMapWrite" class="empty-note">
                  {{ t('enterprise_settings_route_topology_readonly_hint') }}
                </div>
              </section>

              <section class="enterprise-settings-subsection enterprise-page-settings-group enterprise-route-topology-layout">
                <div class="enterprise-route-topology-canvas">
                  <div class="enterprise-map-editor-grid-shell">
                    <div class="enterprise-route-topology-stage">
                      <svg
                        v-if="enterpriseTopologyEditorSpecialGroupSegments.length"
                        class="enterprise-route-topology-svg enterprise-route-topology-group-svg"
                        :style="enterpriseTopologyEdgeSvgStyle"
                        aria-hidden="true"
                      >
                        <line
                          v-for="segment in enterpriseTopologyEditorSpecialGroupSegments"
                          :key="`enterprise-topology-group-${segment.key}`"
                          :x1="segment.x1"
                          :y1="segment.y1"
                          :x2="segment.x2"
                          :y2="segment.y2"
                          class="enterprise-route-topology-group-line"
                          :class="`is-${segment.nodeType}`"
                        />
                      </svg>
                      <div
                        v-for="group in enterpriseTopologyEditorSpecialGroups.filter(item => item.hasIntegratedShell)"
                        :key="`enterprise-topology-group-shell-${group.key}`"
                        class="enterprise-route-topology-group-shell"
                        :class="`is-${group.nodeType}`"
                        :style="{
                          left: `${group.shellLeft}px`,
                          top: `${group.shellTop}px`,
                          width: `${group.shellWidth}px`,
                          height: `${group.shellHeight}px`
                        }"
                      >
                        <div class="enterprise-route-topology-group-shell-head">
                          <span class="enterprise-route-topology-group-shell-title">{{ topologySpecialGroupBaseLabel(group.nodeType) }}</span>
                          <span class="enterprise-route-topology-group-shell-metric">{{ group.count }}</span>
                        </div>
                      </div>
                      <svg class="enterprise-route-topology-svg" :style="enterpriseTopologyEdgeSvgStyle" aria-hidden="true">
                        <line
                          v-for="edge in enterpriseTopologySvgEdges"
                          :key="`enterprise-topology-svg-${edge.key}`"
                          :x1="edge.x1"
                          :y1="edge.y1"
                          :x2="edge.x2"
                          :y2="edge.y2"
                          class="enterprise-route-topology-line"
                          :class="{ 'is-selected': enterpriseTopologySelectedEdge && enterpriseTopologySelectedEdge.key === edge.key }"
                        />
                      </svg>
                      <div class="enterprise-map-editor-grid" :style="enterpriseTopologyGridStyle">
                        <template v-for="row in currentGridRows" :key="`enterprise-topology-row-${row}`">
                          <button
                            v-for="col in currentGridCols"
                            :key="`enterprise-topology-cell-${col - 1}-${row - 1}`"
                            type="button"
                            class="enterprise-map-editor-cell enterprise-route-topology-cell"
                            :class="{
                              'is-valid': isEnterpriseTopologyCellValid(col - 1, row - 1),
                              'is-void': !isEnterpriseTopologyCellValid(col - 1, row - 1),
                              'is-blocked': isEnterpriseTopologyCellBlocked(col - 1, row - 1),
                              'has-node': !!enterpriseTopologyNodesByCell[`${col - 1},${row - 1}`],
                              'has-station-node': enterpriseTopologyNodesByCell[`${col - 1},${row - 1}`]?.node_type === 'station',
                              'has-parking-node': enterpriseTopologyNodesByCell[`${col - 1},${row - 1}`]?.node_type === 'parking',
                              'has-charge-node': enterpriseTopologyNodesByCell[`${col - 1},${row - 1}`]?.node_type === 'charge',
                              'is-link-source': enterpriseTopologyLinkSourceNode && enterpriseTopologyLinkSourceNode.key === enterpriseTopologyNodesByCell[`${col - 1},${row - 1}`]?.key,
                              'is-selected': enterpriseTopologySelectedNode && enterpriseTopologySelectedNode.key === enterpriseTopologyNodesByCell[`${col - 1},${row - 1}`]?.key
                            }"
                            :disabled="!isEnterpriseTopologyCellValid(col - 1, row - 1) || (isEnterpriseTopologyCellBlocked(col - 1, row - 1) && !enterpriseTopologyNodesByCell[`${col - 1},${row - 1}`])"
                            @click="applyEnterpriseTopologyCell({ x: col - 1, y: row - 1 })"
                          >
                            <span
                              v-if="enterpriseTopologyNodesByCell[`${col - 1},${row - 1}`]"
                              class="enterprise-route-topology-node-badge"
                              :class="{
                                'is-station': enterpriseTopologyNodesByCell[`${col - 1},${row - 1}`]?.node_type === 'station',
                                'is-parking': enterpriseTopologyNodesByCell[`${col - 1},${row - 1}`]?.node_type === 'parking',
                                'is-charge': enterpriseTopologyNodesByCell[`${col - 1},${row - 1}`]?.node_type === 'charge'
                              }"
                            >
                              {{ formatEnterpriseTopologyNodeBadge(enterpriseTopologyNodesByCell[`${col - 1},${row - 1}`]) }}
                            </span>
                          </button>
                        </template>
                      </div>
                      <div
                        v-for="group in enterpriseTopologyEditorSpecialGroups.filter(item => !item.hasIntegratedShell)"
                        :key="`enterprise-topology-group-label-${group.key}`"
                        class="enterprise-route-topology-group-label"
                        :class="`is-${group.nodeType}`"
                        :style="{
                          left: `${group.labelLeft}px`,
                          top: `${group.labelTop}px`
                        }"
                      >
                        {{ formatTopologySpecialGroupEditorLabel(group) }}
                      </div>
                    </div>
                  </div>
                </div>

                <div class="enterprise-route-topology-inspector">
                  <div class="enterprise-map-editor-draft-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_route_topology_nodes') }}</div>
                    <div v-if="enterpriseTopologyDraftSummary.node_count === 0" class="empty-note">
                      {{ t('enterprise_settings_route_topology_empty_hint') }}
                    </div>
                    <div v-else class="enterprise-settings-chip-list">
                      <button
                        v-for="node in enterpriseTopologyEditorDraft.nodes"
                        :key="`enterprise-topology-node-${node.key}`"
                        type="button"
                        class="btn-ghost enterprise-settings-action-chip"
                        :class="{ 'is-active': enterpriseTopologySelectedNode && enterpriseTopologySelectedNode.key === node.key }"
                        @click="selectEnterpriseTopologyNode(node.key)"
                      >
                        {{ formatEnterpriseTopologyNodeListLabel(node) }}
                      </button>
                    </div>
                  </div>

                  <div class="enterprise-map-editor-draft-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_route_topology_edges') }}</div>
                    <div v-if="enterpriseTopologyDraftSummary.edge_count === 0" class="empty-note">
                      {{ t('enterprise_settings_route_topology_edges_empty') }}
                    </div>
                    <div v-else class="enterprise-settings-chip-list">
                      <button
                        v-for="edge in enterpriseTopologyEditorDraft.edges"
                        :key="`enterprise-topology-edge-${edge.key}`"
                        type="button"
                        class="btn-ghost enterprise-settings-action-chip"
                        :class="{ 'is-active': enterpriseTopologySelectedEdge && enterpriseTopologySelectedEdge.key === edge.key }"
                        @click="selectEnterpriseTopologyEdge(edge.key)"
                      >
                        {{ edge.source }} → {{ edge.target }}
                      </button>
                    </div>
                  </div>

                  <div v-if="enterpriseTopologySelectedNode" class="enterprise-map-editor-draft-card">
                    <div class="map-settings-info-label">
                      {{ t('enterprise_settings_route_topology_node_editor') }}
                      <span
                        v-if="enterpriseTopologyNodeEditorDirty"
                        class="point-badge enterprise-settings-chip enterprise-settings-chip-muted"
                      >
                        {{ t('enterprise_settings_route_topology_node_unsaved') }}
                      </span>
                    </div>
                    <div class="enterprise-topology-node-editor-summary">
                      <span
                        class="enterprise-route-topology-node-badge enterprise-topology-node-editor-summary__badge"
                        :class="{
                          'is-station': enterpriseTopologyNodeEditorDraft.node_type === 'station',
                          'is-parking': enterpriseTopologyNodeEditorDraft.node_type === 'parking',
                          'is-charge': enterpriseTopologyNodeEditorDraft.node_type === 'charge'
                        }"
                      >
                        {{ formatEnterpriseTopologyNodeBadge({ ...enterpriseTopologySelectedNode, node_type: enterpriseTopologyNodeEditorDraft.node_type }) }}
                      </span>
                      <div class="enterprise-topology-node-editor-summary__copy">
                        <strong>
                          {{
                            formatEnterpriseTopologyNodeListLabel({
                              ...enterpriseTopologySelectedNode,
                              node_type: enterpriseTopologyNodeEditorDraft.node_type,
                              label: enterpriseTopologyNodeEditorDraft.label || null
                            })
                          }}
                        </strong>
                        <span>
                          {{ topologyNodeTypeLabel(enterpriseTopologyNodeEditorDraft.node_type) }}
                          · ({{ enterpriseTopologySelectedNode.x }}, {{ enterpriseTopologySelectedNode.y }})
                        </span>
                      </div>
                    </div>
                    <div class="enterprise-topology-node-editor">
                      <label class="auth-field enterprise-topology-node-editor__full">
                        <span>{{ t('enterprise_settings_route_topology_node_type') }}</span>
                        <select
                          class="auth-input"
                          :value="enterpriseTopologyNodeEditorDraft.node_type"
                          :disabled="!authCanMapWrite"
                          @change="updateEnterpriseTopologyNodeEditorDraft({ node_type: $event.target.value })"
                        >
                          <option
                            v-for="option in enterpriseTopologyNodeTypeOptions"
                            :key="`enterprise-topology-type-${option.value}`"
                            :value="option.value"
                          >
                            {{ option.label }}
                          </option>
                        </select>
                      </label>
                      <label class="auth-field enterprise-topology-node-editor__full">
                        <span>{{ t('enterprise_settings_route_topology_node_label') }}</span>
                        <input
                          class="auth-input"
                          :value="enterpriseTopologyNodeEditorDraft.label || ''"
                          type="text"
                          :disabled="!authCanMapWrite"
                          @input="updateEnterpriseTopologyNodeEditorDraft({ label: $event.target.value })"
                        />
                      </label>
                      <label
                        v-if="enterpriseTopologyNodeEditorDraft.node_type !== 'waypoint'"
                        class="auth-field enterprise-topology-node-editor__full"
                      >
                        <span>{{ t('enterprise_settings_route_topology_node_capacity') }}</span>
                        <input
                          class="auth-input"
                          :value="enterpriseTopologyNodeEditorDraft.capacity"
                          :min="getTopologyNodeDefaultCapacity(enterpriseTopologyNodeEditorDraft.node_type)"
                          step="1"
                          type="number"
                          :disabled="!authCanMapWrite"
                          @input="updateEnterpriseTopologyNodeEditorDraft({ capacity: Number($event.target.value || getTopologyNodeDefaultCapacity(enterpriseTopologyNodeEditorDraft.node_type)) })"
                        />
                      </label>
                      <div
                        v-if="enterpriseTopologyNodeEditorDraft.node_type !== 'waypoint'"
                        class="enterprise-topology-node-editor__hint"
                      >
                        {{ t('enterprise_settings_route_topology_node_capacity_hint') }}
                      </div>
                    </div>
                    <div class="enterprise-settings-actions">
                      <button class="btn-ghost" type="button" :disabled="!authCanMapWrite" @click="toggleEnterpriseTopologyLinkSource">
                        {{
                          enterpriseTopologyLinkSourceNode && enterpriseTopologyLinkSourceNode.key === enterpriseTopologySelectedNode.key
                            ? t('enterprise_settings_route_topology_cancel_connect')
                            : t('enterprise_settings_route_topology_start_connect')
                        }}
                      </button>
                      <button
                        class="btn-ghost"
                        type="button"
                        :disabled="!authCanMapWrite || !enterpriseTopologyNodeEditorDirty"
                        @click="restoreSelectedEnterpriseTopologyNodeDraft"
                      >
                        {{ t('enterprise_settings_route_topology_restore_node') }}
                      </button>
                      <button
                        class="btn-secondary"
                        type="button"
                        :disabled="!authCanMapWrite || !enterpriseTopologyNodeEditorDirty"
                        @click="saveSelectedEnterpriseTopologyNodeDraft"
                      >
                        {{ t('enterprise_settings_route_topology_save_node') }}
                      </button>
                      <button class="btn-delete" type="button" :disabled="!authCanMapWrite" @click="removeSelectedEnterpriseTopologyNode">
                        {{ t('enterprise_settings_route_topology_delete_node') }}
                      </button>
                    </div>
                  </div>

                  <div v-if="enterpriseTopologySelectedEdge" class="enterprise-map-editor-draft-card">
                    <div class="map-settings-info-label">{{ t('enterprise_settings_route_topology_edge_editor') }}</div>
                    <div class="enterprise-topology-edge-editor">
                      <label class="auth-field enterprise-topology-edge-editor__field">
                        <span>{{ t('enterprise_settings_route_topology_edge_direction') }}</span>
                        <select
                          class="auth-input"
                          :value="enterpriseTopologySelectedEdge.direction"
                          :disabled="!authCanMapWrite"
                          @change="updateEnterpriseTopologyEdge({ direction: $event.target.value })"
                        >
                          <option
                            v-for="option in enterpriseTopologyEdgeDirectionOptions"
                            :key="`enterprise-topology-direction-${option.value}`"
                            :value="option.value"
                          >
                            {{ option.label }}
                          </option>
                        </select>
                      </label>
                      <label class="auth-field enterprise-topology-edge-editor__field">
                        <span>{{ t('enterprise_settings_route_topology_lane_type') }}</span>
                        <select
                          class="auth-input"
                          :value="enterpriseTopologySelectedEdge.lane_type"
                          :disabled="!authCanMapWrite"
                          @change="updateEnterpriseTopologyEdge({ lane_type: $event.target.value })"
                        >
                          <option
                            v-for="option in enterpriseTopologyLaneTypeOptions"
                            :key="`enterprise-topology-lane-${option.value}`"
                            :value="option.value"
                          >
                            {{ option.label }}
                          </option>
                        </select>
                      </label>
                      <label class="auth-field enterprise-topology-edge-editor__field">
                        <span>{{ t('enterprise_settings_route_topology_edge_weight') }}</span>
                        <input
                          class="auth-input"
                          :value="enterpriseTopologySelectedEdge.weight"
                          min="0.1"
                          step="0.1"
                          type="number"
                          :disabled="!authCanMapWrite"
                          @input="updateEnterpriseTopologyEdge({ weight: Number($event.target.value || 1) })"
                        />
                      </label>
                      <label class="auth-field enterprise-topology-edge-editor__field">
                        <span>{{ t('enterprise_settings_route_topology_edge_speed_multiplier') }}</span>
                        <input
                          class="auth-input"
                          :value="enterpriseTopologySelectedEdge.speed_multiplier"
                          min="0.1"
                          step="0.1"
                          type="number"
                          :disabled="!authCanMapWrite"
                          @input="updateEnterpriseTopologyEdge({ speed_multiplier: Number($event.target.value || 1) })"
                        />
                      </label>
                    </div>
                    <div class="enterprise-settings-actions">
                      <button class="btn-delete" type="button" :disabled="!authCanMapWrite" @click="removeSelectedEnterpriseTopologyEdge">
                        {{ t('enterprise_settings_route_topology_delete_edge') }}
                      </button>
                    </div>
                  </div>
                </div>
              </section>

              <div class="enterprise-settings-actions">
                <button class="btn-ghost" type="button" @click="resetEnterpriseTopologyEditorDraft">
                  {{ t('enterprise_settings_route_topology_reset') }}
                </button>
                <button class="btn-secondary" type="button" @click="closeEnterpriseTopologyEditorDialog">
                  {{ t('enterprise_settings_route_topology_cancel') }}
                </button>
                <button
                  class="btn-primary"
                  type="button"
                  :disabled="!authCanMapWrite"
                  :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                  @click="saveEnterpriseTopologyEditorDraft"
                >
                  {{ t('enterprise_settings_route_topology_save') }}
                </button>
              </div>
            </div>
          </section>
        </div>
        </Teleport>
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

    function bindRef(targetRef, element) {
      if (targetRef && typeof targetRef === 'object' && 'value' in targetRef) {
        targetRef.value = element
      }
    }

    function setMapProfileFileInput(element) {
      bindRef(props.ui?.mapProfileFileInputRef, element)
    }

    exposed.setMapProfileFileInput = setMapProfileFileInput

    return exposed
  }
})
</script>


