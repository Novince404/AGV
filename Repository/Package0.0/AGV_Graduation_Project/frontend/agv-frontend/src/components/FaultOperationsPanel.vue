<template>
  <div class="dispatch-summary fault-panel">
    <div class="fault-panel-header">
      <div>
        <span class="dispatch-summary-label">{{ faultLocale.title }}</span>
        <strong>{{ faultLocale.selectedAgv }}</strong>
      </div>
      <div class="fault-filter-group">
        <button
          class="btn-ghost fault-filter-button"
          :class="{ active: faultEventFilter === 'open' }"
          type="button"
          @click="faultEventFilter = 'open'"
        >
          {{ faultLocale.filterOpen }}
        </button>
        <button
          class="btn-ghost fault-filter-button"
          :class="{ active: faultEventFilter === 'resolved' }"
          type="button"
          @click="faultEventFilter = 'resolved'"
        >
          {{ faultLocale.filterResolved }}
        </button>
        <button
          class="btn-ghost fault-filter-button"
          :class="{ active: faultEventFilter === 'all' }"
          type="button"
          @click="faultEventFilter = 'all'"
        >
          {{ faultLocale.filterAll }}
        </button>
      </div>
    </div>
    <div v-if="!authCanFaultWrite" class="permission-gate-card">
      <div class="empty-note">
        {{ buildCapabilityReadonlyHint('fault') }}
      </div>
      <div v-if="buildEnterprisePanelReadonlyHint('fault')" class="task-line permission-gate-extra">
        {{ buildEnterprisePanelReadonlyHint('fault') }}
      </div>
      <button class="btn-primary" type="button" @click="openAuthDialog">
        {{ buildOperationsEntryActionText() }}
      </button>
    </div>

    <template v-if="selectedBackendAgv">
      <div
        :ref="faultSelectedAgvCardRef"
        class="fault-selected-agv"
        :class="{ 'recovery-focus': faultSelectedAgvPulse }"
      >
        <div class="fault-selected-line">
          <strong>AGV #{{ selectedBackendAgv.id }}</strong>
          <div class="fault-selected-head-actions">
            <span class="status-badge" :class="selectedBackendAgv.status">{{ statusText(selectedBackendAgv.status) }}</span>
            <button
              class="btn-ghost fault-selected-clear-button"
              type="button"
              :disabled="agvActionLoadingId === selectedBackendAgv.id"
              @click="cancelSelection"
            >
              {{ faultLocale.clearSelection }}
            </button>
          </div>
        </div>
        <div class="task-line">
          {{ faultLocale.currentTask }}:
          {{ selectedAgvTask ? `#${selectedAgvTask.id}` : faultLocale.currentTaskNone }}
        </div>
        <div v-if="canManageEnterpriseAgvDuty" class="task-line">
          {{ selectedEnterpriseAgvOffboardHintText() }}
        </div>
        <div class="fault-action-row">
          <button
            v-if="selectedBackendAgv.status !== 'emergency_stop'"
            class="btn-danger fault-action-button"
            type="button"
            :disabled="!authCanFaultWrite || agvActionLoadingId === selectedBackendAgv.id || selectedBackendAgv.status === 'fault'"
            :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
            @click="emergencyStopSelectedAgv"
          >
            {{ faultLocale.emergencyStop }}
          </button>
          <button
            v-else
            class="btn-secondary fault-action-button"
            type="button"
            :disabled="!authCanFaultWrite || agvActionLoadingId === selectedBackendAgv.id"
            :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
            @click="resumeSelectedAgv"
          >
            {{ faultLocale.resume }}
          </button>
          <button
            class="btn-secondary fault-action-button"
            type="button"
            :disabled="!authCanFaultWrite || agvActionLoadingId === selectedBackendAgv.id"
            :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
            @click="showFaultReportForm = !showFaultReportForm"
          >
            {{ faultLocale.reportFault }}
          </button>
          <button
            v-if="canManageEnterpriseAgvDuty && uiTreatAsEnterpriseRole"
            class="btn-secondary fault-action-button"
            type="button"
            :disabled="
              !authCanDispatchWrite ||
              agvActionLoadingId === selectedBackendAgv.id ||
              !selectedEnterpriseAgvCanOffboard
            "
            :title="
              !authCanDispatchWrite
                ? buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)
                : selectedEnterpriseAgvOffboardHintText()
            "
            @click="offboardSelectedEnterpriseAgv"
          >
            {{ t('agv_offboard') }}
          </button>
          <button
            class="btn-secondary fault-action-button"
            type="button"
            :disabled="!authCanFaultWrite || agvActionLoadingId === selectedBackendAgv.id || ['running', 'relocating'].includes(selectedBackendAgv.status)"
            :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
            @click="moveSelectedAgvToMaintenance"
          >
            {{ moveToMaintenanceText() }}
          </button>
        </div>
        <div v-if="showFaultReportForm" class="fault-report-form">
          <label>
            {{ faultLocale.faultType }}
            <select v-model="faultReportForm.fault_type">
              <option value="path_blocked">{{ faultTypeText('path_blocked') }}</option>
              <option value="battery">{{ faultTypeText('battery') }}</option>
              <option value="motor">{{ faultTypeText('motor') }}</option>
              <option value="communication">{{ faultTypeText('communication') }}</option>
              <option value="manual">{{ faultTypeText('manual') }}</option>
              <option value="other">{{ faultTypeText('other') }}</option>
            </select>
          </label>
          <label>
            {{ faultLocale.severity }}
            <select v-model="faultReportForm.severity">
              <option value="low">{{ faultSeverityText('low') }}</option>
              <option value="medium">{{ faultSeverityText('medium') }}</option>
              <option value="high">{{ faultSeverityText('high') }}</option>
              <option value="critical">{{ faultSeverityText('critical') }}</option>
            </select>
          </label>
          <label>
            {{ faultLocale.message }}
            <textarea v-model.trim="faultReportForm.message" rows="2"></textarea>
          </label>
          <div class="fault-action-row">
            <button
              class="btn-primary fault-action-button"
              type="button"
              :disabled="!authCanFaultWrite || agvActionLoadingId === selectedBackendAgv.id"
              :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
              @click="submitFaultReport"
            >
              {{ faultLocale.reportFaultSubmit }}
            </button>
            <button
              class="btn-ghost fault-action-button"
              type="button"
              @click="showFaultReportForm = false"
            >
              {{ faultLocale.reportFaultCancel }}
            </button>
          </div>
        </div>
      </div>
    </template>
    <p v-else class="panel-hint">{{ faultLocale.noSelectedAgv }}</p>

    <div v-if="maintenanceBackendAgvs.length > 0" class="fault-maintenance-panel">
      <div class="dispatch-summary-label">{{ maintenanceListTitleText() }}</div>
      <div class="fault-maintenance-list">
        <article v-for="maintenanceAgv in maintenanceBackendAgvs" :key="`maintenance-${maintenanceAgv.id}`" class="fault-maintenance-item">
          <strong>AGV #{{ maintenanceAgv.id }}</strong>
          <div class="fault-action-row">
            <button
              class="btn-secondary fault-action-button"
              type="button"
              :disabled="!authCanFaultWrite || agvActionLoadingId === maintenanceAgv.id"
              :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
              @click="returnAgvToService(maintenanceAgv.id)"
            >
              {{ returnToServiceText() }}
            </button>
            <button
              v-if="canManagePersonalAgvs"
              class="btn-danger fault-action-button"
              type="button"
              :disabled="!authCanDispatchWrite || agvActionLoadingId === maintenanceAgv.id"
              :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
              @click="deletePersonalMaintenanceAgv(maintenanceAgv.id)"
            >
              {{ t('agv_delete') }}
            </button>
          </div>
        </article>
      </div>
    </div>

    <div v-if="faultPanelStatus" class="template-status" :class="faultPanelStatusType">
      {{ faultPanelStatus }}
    </div>

    <div class="fault-event-list">
      <article v-for="eventItem in filteredFaultEvents" :key="eventItem.id" class="fault-event-card">
        <div class="fault-event-head">
          <strong>#{{ eventItem.id }} · AGV #{{ eventItem.agv_id }}</strong>
          <span class="status-badge" :class="eventItem.status === 'resolved' ? 'finished' : 'blocked'">
            {{ faultEventStatusText(eventItem.status) }}
          </span>
        </div>
        <div class="task-line">
          {{ faultLocale.eventType }}: {{ faultEventTypeText(eventItem.event_type) }}
        </div>
        <div class="task-line">
          {{ faultLocale.faultType }}: {{ faultTypeText(eventItem.fault_type) }}
        </div>
        <div class="task-line">
          {{ faultLocale.severity }}: {{ faultSeverityText(eventItem.severity) }}
        </div>
        <div v-if="eventItem.message" class="task-line task-reason">
          {{ faultLocale.message }}: {{ eventItem.message }}
        </div>
        <div class="task-line task-time">
          {{ faultLocale.reportedAt }}: {{ eventItem.reported_at }}
        </div>
        <div v-if="formatFaultReportedBy(eventItem)" class="task-line">
          {{ formatFaultReportedBy(eventItem) }}
        </div>
        <div v-if="eventItem.resolved_at" class="task-line task-time">
          {{ faultLocale.resolvedAt }}: {{ eventItem.resolved_at }}
        </div>
        <div v-if="formatFaultResolvedBy(eventItem)" class="task-line">
          {{ formatFaultResolvedBy(eventItem) }}
        </div>
        <div class="task-actions">
          <button
            v-if="eventItem.status !== 'resolved'"
            class="btn-secondary task-action-button"
            type="button"
            :disabled="!authCanFaultWrite || resolvingFaultId === eventItem.id"
            :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
            @click="resolveFaultEventItem(eventItem)"
          >
            {{ faultLocale.resolve }}
          </button>
        </div>
      </article>
      <div v-if="filteredFaultEvents.length === 0" class="empty-note">
        {{ faultLocale.empty }}
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'FaultOperationsPanel',
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
