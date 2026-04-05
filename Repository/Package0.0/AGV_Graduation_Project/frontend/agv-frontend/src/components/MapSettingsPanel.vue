<template>
  <div v-if="showMapSettings" :ref="setMapSettingsPanelRoot" class="map-settings-panel">
    <div class="map-settings-title">{{ settingsLocale.title }}</div>
    <button class="map-settings-guide-button" type="button" @click="openGuideCenter">
      {{ guideCenterLocale.open }}
    </button>
    <label class="map-setting-row">
      <input v-model="showGuideCenterOnLoad" type="checkbox" />
      <span>{{ settingsLocale.showGuideCenterOnLoad }}</span>
    </label>
    <p class="panel-hint map-settings-hint">{{ settingsLocale.showGuideCenterOnLoadHint }}</p>
    <div class="map-settings-group">
      <div class="map-settings-subtitle">{{ settingsLocale.mapGroup }}</div>
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
      <div v-if="enterpriseTopologyViewAvailable" class="map-settings-select-group">
        <label class="map-settings-select-label" for="topology-view-mode">
          {{ settingsLocale.topologyViewMode }}
        </label>
        <select
          id="topology-view-mode"
          v-model="topologyViewMode"
          class="map-settings-select"
        >
          <option value="standard">{{ settingsLocale.topologyViewModeStandard }}</option>
          <option value="pure">{{ settingsLocale.topologyViewModePure }}</option>
        </select>
      </div>
      <p v-if="enterpriseTopologyViewAvailable" class="panel-hint map-settings-hint">
        {{ settingsLocale.topologyViewModeHint }}
      </p>
    </div>
    <div v-if="!authCanMapWrite" class="permission-gate-card compact">
      <div class="empty-note">
        {{ buildCapabilityReadonlyHint('map') }}
      </div>
      <div v-if="buildEnterprisePanelReadonlyHint('map')" class="task-line permission-gate-extra">
        {{ buildEnterprisePanelReadonlyHint('map') }}
      </div>
      <button class="btn-primary" type="button" @click="openAuthDialog">
        {{ buildOperationsEntryActionText() }}
      </button>
    </div>
    <div class="map-settings-group">
      <div class="map-settings-subtitle">{{ settingsLocale.obstacleGroup }}</div>
      <label class="map-setting-row">
        <input
          :checked="obstacleEditMode"
          type="checkbox"
          :disabled="!authCanMapWrite || obstacleMutationLocked"
          :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
          @change="toggleObstacleEditModeWithAuth"
        />
        <span>{{ settingsLocale.obstacleEdit }}</span>
      </label>
      <p class="panel-hint map-settings-hint">{{ settingsLocale.obstacleHint }}</p>
      <p v-if="obstacleMutationLocked" class="panel-hint map-settings-hint">
        {{ obstacleMutationLockedText() }}
      </p>
      <div class="map-settings-select-group">
        <label class="map-settings-select-label" for="obstacle-preset-select">
          {{ settingsLocale.obstaclePreset }}
        </label>
        <select
          id="obstacle-preset-select"
          v-model="selectedObstaclePreset"
          class="map-settings-select"
        >
          <option
            v-for="preset in obstaclePresets"
            :key="preset.key"
            :value="preset.key"
          >
            {{ obstaclePresetName(preset) }}
          </option>
        </select>
      </div>
      <p v-if="selectedObstaclePresetInfo" class="panel-hint map-settings-hint">
        {{ obstaclePresetDescription(selectedObstaclePresetInfo) }}
      </p>
      <div class="map-settings-status">
        {{ obstacleLayoutDirty ? settingsLocale.obstacleDirty : settingsLocale.obstacleSaved }}
      </div>
      <div
        v-if="obstacleLayoutStatus"
        class="map-settings-status"
        :class="`status-${obstacleLayoutStatusType}`"
      >
        {{ obstacleLayoutStatus }}
      </div>
      <div class="map-settings-actions">
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanMapWrite || obstacleMapSaving || obstacleMutationLocked || obstaclePresets.length === 0"
          :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
          @click="applyObstaclePreset"
        >
          {{ settingsLocale.obstaclePresetApply }}
        </button>
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanMapWrite || obstacleMapSaving"
          :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
          @click="saveCurrentObstaclePreset"
        >
          {{ settingsLocale.obstaclePresetSaveCustom }}
        </button>
        <button
          class="btn-ghost"
          type="button"
          :disabled="!authCanMapWrite || obstacleMapSaving || !selectedObstaclePresetDeletable"
          :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
          @click="deleteSelectedObstaclePreset"
        >
          {{ settingsLocale.obstaclePresetDelete }}
        </button>
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanMapWrite || obstacleMapSaving || obstacleMutationLocked || !obstacleLayoutDirty"
          :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
          @click="saveBlockedCells"
        >
          {{ settingsLocale.obstacleSave }}
        </button>
        <button class="btn-ghost" type="button" @click="downloadObstacleLayout">
          {{ settingsLocale.obstacleExport }}
        </button>
        <button
          class="btn-ghost"
          type="button"
          :disabled="!authCanMapWrite || obstacleMutationLocked"
          :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
          @click="triggerObstacleLayoutImportWithAuth"
        >
          {{ settingsLocale.obstacleImport }}
        </button>
        <button
          class="btn-ghost"
          type="button"
          :disabled="!authCanMapWrite || obstacleMapSaving || obstacleMutationLocked"
          :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
          @click="resetBlockedCellsToDefault"
        >
          {{ settingsLocale.obstacleReset }}
        </button>
        <button
          v-if="importedObstacleLayoutPendingPreset"
          class="btn-secondary"
          type="button"
          :disabled="!authCanMapWrite || obstacleMapSaving"
          :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
          @click="saveImportedObstacleAsPreset"
        >
          {{ obstacleImportSaveAsPresetText() }}
        </button>
      </div>
      <input
        :ref="setObstacleLayoutFileInput"
        type="file"
        accept="application/json,.json"
        class="hidden-file-input"
        @change="onObstacleLayoutFileChange"
      />
    </div>
    <div class="map-settings-group">
      <div class="map-settings-subtitle">{{ settingsLocale.infoGroup }}</div>
      <div class="map-settings-info-grid">
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.mapInfoSize }}</div>
          <div class="map-settings-info-value">{{ mapSizeLabel }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.mapInfoPreset }}</div>
          <div class="map-settings-info-value">{{ currentObstaclePresetLabel }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.mapInfoBlocked }}</div>
          <div class="map-settings-info-value">{{ blockedCellCount }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.mapInfoBackend }}</div>
          <div class="map-settings-info-value">{{ uiSettingsBackendMode }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.mapInfoProfile }}</div>
          <div class="map-settings-info-value">{{ currentMapProfileLabel }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.mapInfoResizeCheck }}</div>
          <div class="map-settings-info-value">{{ mapSizeResizeStatusLabel }}</div>
        </div>
      </div>
      <p v-if="currentMapProfileDescription" class="panel-hint map-settings-hint">
        {{ currentMapProfileDescription }}
      </p>
    </div>
    <div class="map-settings-group">
      <div class="map-settings-subtitle">{{ settingsLocale.profileGroup }}</div>
      <p class="panel-hint map-settings-hint">{{ settingsLocale.profileGroupHint }}</p>
      <p v-if="previewedMapProfile" class="panel-hint map-settings-hint">
        {{
          settingsLocale.mapProfilePreviewTarget
            .replace('{name}', localizedMapProfileField(previewedMapProfile.name) || previewedMapProfile.key)
            .replace('{size}', `${previewedMapProfile.grid_cols} x ${previewedMapProfile.grid_rows}`)
        }}
      </p>
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
            :key="`summary-${reasonKey}`"
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
            {{
              settingsLocale.mapProfileSummaryPreviousProfile
                .replace('{name}', mapProfileActionSummary.previousProfileName || '—')
            }}
          </div>
          <div class="map-profile-summary-metric">
            {{
              settingsLocale.mapProfileSummaryNextProfile
                .replace('{name}', mapProfileActionSummary.profileName || '—')
            }}
          </div>
          <div class="map-profile-summary-metric">
            {{
              settingsLocale.mapProfileSummarySizeBefore
                .replace('{size}', mapProfileActionSummary.previousSizeLabel || '—')
            }}
          </div>
          <div class="map-profile-summary-metric">
            {{
              settingsLocale.mapProfileSummarySizeAfter
                .replace('{size}', mapProfileActionSummary.nextSizeLabel || '—')
            }}
          </div>
          <div class="map-profile-summary-metric">
            {{
              settingsLocale.mapProfileSummaryBlockedBefore
                .replace('{count}', String(mapProfileActionSummary.previousBlockedCount ?? 0))
            }}
          </div>
          <div class="map-profile-summary-metric">
            {{
              settingsLocale.mapProfileSummaryBlockedAfter
                .replace('{count}', String(mapProfileActionSummary.nextBlockedCount ?? 0))
            }}
          </div>
          <div class="map-profile-summary-metric">
            {{
              settingsLocale.mapProfileSummaryRelocated
                .replace('{count}', String(mapProfileActionSummary.relocatedAgvs?.length ?? 0))
            }}
          </div>
          <div class="map-profile-summary-metric">
            {{
              settingsLocale.mapProfileSummaryTrimmed
                .replace('{count}', String(mapProfileActionSummary.trimmedBlockedCount ?? 0))
            }}
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
        <div
          v-if="mapProfileActionSummary.type === 'forced' && mapProfileActionSummary.trimmedBlockedCells?.length"
          class="map-profile-summary-text"
        >
          {{ settingsLocale.mapProfileSummaryTrimmedList }}
        </div>
        <ul
          v-if="mapProfileActionSummary.type === 'forced' && mapProfileActionSummary.trimmedBlockedCells?.length"
          class="map-size-preview-list compact"
        >
          <li
            v-for="cell in mapProfileActionSummary.trimmedBlockedCells"
            :key="`trimmed-${cell.x}-${cell.y}`"
          >
            <span>
              ({{ cell.x }}, {{ cell.y }})
            </span>
          </li>
        </ul>
        <ul
          v-if="mapProfileActionSummary.type === 'forced' && mapProfileActionSummary.relocatedAgvs?.length"
          class="map-size-preview-list compact"
        >
          <li
            v-for="item in mapProfileActionSummary.relocatedAgvs"
            :key="`relocated-${item.id}`"
          >
            <button
              type="button"
              class="map-size-preview-detail-action"
              @click.stop="focusMapPreviewCell(item.to)"
            >
              AGV #{{ item.id }}: ({{ item.from.x }}, {{ item.from.y }}) -> ({{ item.to.x }}, {{ item.to.y }})
            </button>
          </li>
        </ul>
      </div>
      <div class="map-settings-actions">
        <button
          class="btn-secondary"
          type="button"
          :disabled="!authCanMapWrite || mapProfileSaving || mapProfileImporting"
          :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
          @click="saveCurrentMapProfile"
        >
          {{ mapProfileSaving ? settingsLocale.mapProfileApplying : settingsLocale.mapProfileSave }}
        </button>
        <button
          class="btn-ghost"
          type="button"
          :disabled="!authCanMapWrite || mapProfileSaving || mapProfileImporting"
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
      <div class="map-profile-grid">
        <div
          v-for="profile in mapProfiles"
          :key="profile.key"
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
    <div class="map-settings-group">
      <div class="map-settings-subtitle">{{ settingsLocale.resizeGroup }}</div>
      <p class="panel-hint map-settings-hint">{{ settingsLocale.resizeGroupHint }}</p>
      <div class="map-settings-inline-grid">
        <label class="map-settings-select-group">
          <span class="map-settings-select-label">{{ settingsLocale.resizePreviewCols }}</span>
          <input
            v-model="mapResizePreviewColsInput"
            class="map-settings-number-input"
            type="number"
            min="1"
            step="1"
            @input="markMapResizePreviewDirty"
            @blur="normalizeMapResizePreviewInputs"
          />
        </label>
        <label class="map-settings-select-group">
          <span class="map-settings-select-label">{{ settingsLocale.resizePreviewRows }}</span>
          <input
            v-model="mapResizePreviewRowsInput"
            class="map-settings-number-input"
            type="number"
            min="1"
            step="1"
            @input="markMapResizePreviewDirty"
            @blur="normalizeMapResizePreviewInputs"
          />
        </label>
      </div>
      <div class="map-settings-actions">
        <button
          class="btn-secondary"
          type="button"
          :disabled="mapResizePreviewLoading"
          @click="runMapResizePrecheck()"
        >
          {{ settingsLocale.resizePreviewRun }}
        </button>
        <button
          class="btn-primary"
          type="button"
          :disabled="!authCanMapWrite || mapResizePreviewLoading || !canApplyMapResize"
          :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
          @click="applyMapResize"
        >
          {{ settingsLocale.resizeApply }}
        </button>
      </div>
      <div class="map-settings-info-grid">
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.resizePreviewCurrent }}</div>
          <div class="map-settings-info-value">{{ currentGridCols }} x {{ currentGridRows }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.resizePreviewRequested }}</div>
          <div class="map-settings-info-value">{{ mapResizeRequestedSizeLabel }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.resizePreviewResult }}</div>
          <div class="map-settings-info-value">{{ mapResizePreviewStatusLabel }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.resizePreviewActiveTasks }}</div>
          <div class="map-settings-info-value">{{ mapResizePreview?.active_task_count ?? '—' }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.resizePreviewBusyAgvs }}</div>
          <div class="map-settings-info-value">{{ mapResizePreview?.busy_agv_count ?? '—' }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.resizePreviewOverflowAgvs }}</div>
          <div class="map-settings-info-value">{{ mapResizePreview?.agv_overflow_count ?? '—' }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.resizePreviewOverflowPoints }}</div>
          <div class="map-settings-info-value">{{ mapResizePreview?.point_overflow_count ?? '—' }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.resizePreviewOverflowTemplates }}</div>
          <div class="map-settings-info-value">{{ mapResizePreview?.template_overflow_count ?? '—' }}</div>
        </div>
        <div class="map-settings-info-card">
          <div class="map-settings-info-label">{{ settingsLocale.resizePreviewOverflowObstacles }}</div>
          <div class="map-settings-info-value">{{ mapResizePreview?.blocked_overflow_count ?? '—' }}</div>
        </div>
      </div>
      <div
        v-if="mapResizePreviewReasonItems.length > 0"
        :id="mapResizeSectionDomId('reasons')"
        class="map-size-preview-reasons"
        :class="{ 'is-highlighted': mapResizeHighlightedSection === 'reasons' }"
      >
        <div class="map-settings-select-label">{{ settingsLocale.resizePreviewReasonTitle }}</div>
        <ul class="map-size-preview-list">
          <li v-for="reason in mapResizePreviewReasonItems" :key="reason.key">
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
      <div v-if="mapResizePreviewDetailSections.length > 0" class="map-size-preview-details">
        <div class="map-settings-select-label">{{ settingsLocale.resizePreviewDetailTitle }}</div>
        <div class="map-size-preview-detail-grid">
          <article
            v-for="section in mapResizePreviewDetailSections"
            :key="section.key"
            :id="mapResizeSectionDomId(section.key)"
            class="map-size-preview-detail-card"
            :class="{ 'is-highlighted': mapResizeHighlightedSection === section.key }"
          >
            <div class="map-size-preview-detail-title">{{ section.title }}</div>
            <ul class="map-size-preview-list compact">
              <li v-for="item in section.items" :key="item.key">
                <button
                  v-if="item.focus"
                  type="button"
                  class="map-size-preview-detail-action"
                  :class="{ 'is-highlighted': mapResizeHighlightedItemKeys.includes(item.key) }"
                  :title="item.text"
                  @click="
                    highlightMapResizeItems([item.key]);
                    focusMapPreviewCell(item.focus)
                  "
                >
                  {{ item.text }}
                </button>
                <span
                  v-else
                  :class="{ 'map-size-preview-detail-item-highlighted': mapResizeHighlightedItemKeys.includes(item.key) }"
                >
                  {{ item.text }}
                </span>
              </li>
            </ul>
          </article>
        </div>
      </div>
    </div>
    <div class="map-settings-group">
      <div class="map-settings-subtitle">{{ settingsLocale.compareGroup }}</div>
      <div class="map-settings-select-group">
        <label class="map-settings-select-label" for="compare-display-mode">
          {{ settingsLocale.compareDisplay }}
        </label>
        <select
          id="compare-display-mode"
          v-model="compareDisplayMode"
          class="map-settings-select"
        >
          <option value="panel">{{ settingsLocale.compareDisplayPanel }}</option>
          <option value="floating">{{ settingsLocale.compareDisplayFloating }}</option>
        </select>
      </div>
      <div v-if="compareDisplayMode === 'floating'" class="map-settings-select-group">
        <label class="map-settings-select-label" for="compare-opacity-range">
          {{ settingsLocale.compareOpacity }}
        </label>
        <input
          id="compare-opacity-range"
          v-model.number="compareFloatingOpacity"
          type="range"
          min="0.45"
          max="1"
          step="0.05"
        />
      </div>
    </div>
    <div class="map-settings-group">
      <div class="map-settings-subtitle">{{ settingsLocale.promptGroup }}</div>
      <label class="map-setting-row">
        <input v-model="showStatusLegend" type="checkbox" />
        <span>{{ settingsLocale.showAgvStatus }}</span>
      </label>
      <div v-if="showStatusLegend" class="map-settings-select-group">
        <label class="map-settings-select-label" for="status-legend-layout">
          {{ settingsLocale.agvLegendLayout }}
        </label>
        <select
          id="status-legend-layout"
          v-model="statusLegendLayout"
          class="map-settings-select"
        >
          <option value="horizontal">{{ settingsLocale.agvLegendLayoutHorizontal }}</option>
          <option value="vertical">{{ settingsLocale.agvLegendLayoutVertical }}</option>
        </select>
      </div>
      <div v-if="showStatusLegend" class="map-settings-select-group">
        <label class="map-settings-select-label" for="status-legend-opacity">
          {{ settingsLocale.agvLegendOpacity }}
        </label>
        <input
          id="status-legend-opacity"
          v-model.number="statusLegendOpacity"
          type="range"
          min="0.2"
          max="0.9"
          step="0.05"
        />
      </div>
    </div>
    <div class="map-settings-group">
      <div class="map-settings-subtitle">{{ settingsLocale.autonomyGroup }}</div>
      <p class="panel-hint map-settings-hint">{{ settingsLocale.autonomyGroupHint }}</p>
      <div class="map-settings-select-group">
        <label class="map-settings-select-label" for="idle-return-timeout">
          {{ settingsLocale.idleReturnTimeoutSec }}
        </label>
        <input
          id="idle-return-timeout"
          v-model.number="idleReturnTimeoutSec"
          class="map-settings-select"
          type="number"
          min="5"
          max="600"
          step="1"
        />
      </div>
      <p class="panel-hint map-settings-hint">{{ settingsLocale.idleReturnTimeoutSecHint }}</p>
      <div class="map-settings-select-group">
        <label class="map-settings-select-label" for="idle-charge-timeout">
          {{ settingsLocale.idleChargeTimeoutSec }}
        </label>
        <input
          id="idle-charge-timeout"
          v-model.number="idleChargeTimeoutSec"
          class="map-settings-select"
          type="number"
          min="5"
          max="600"
          step="1"
        />
      </div>
      <p class="panel-hint map-settings-hint">{{ settingsLocale.idleChargeTimeoutSecHint }}</p>
    </div>
    <button class="map-settings-action" type="button" @click="resetMapView">
      {{ settingsLocale.resetView }}
    </button>
  </div>
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'MapSettingsPanel',
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

    function setMapSettingsPanelRoot(element) {
      bindRef(props.ui?.mapSettingsPanelRootRef, element)
    }

    function setObstacleLayoutFileInput(element) {
      bindRef(props.ui?.obstacleLayoutFileInputRef, element)
    }

    function setMapProfileFileInput(element) {
      bindRef(props.ui?.mapProfileFileInputRef, element)
    }

    exposed.setMapSettingsPanelRoot = setMapSettingsPanelRoot
    exposed.setObstacleLayoutFileInput = setObstacleLayoutFileInput
    exposed.setMapProfileFileInput = setMapProfileFileInput

    return exposed
  }
})
</script>

