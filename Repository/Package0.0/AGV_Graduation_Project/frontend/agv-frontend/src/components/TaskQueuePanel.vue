<template>
  <div class="queue-panel">
    <h2>{{ t('tasks') }}</h2>
    <div v-if="!authCanDispatchWrite" class="permission-gate-card compact">
      <div class="empty-note">
        {{ buildCapabilityReadonlyHint('dispatch') }}
      </div>
      <div v-if="buildEnterprisePanelReadonlyHint('dispatch')" class="task-line permission-gate-extra">
        {{ buildEnterprisePanelReadonlyHint('dispatch') }}
      </div>
      <button class="btn-primary" type="button" @click="openAuthDialog">
        {{ buildOperationsEntryActionText() }}
      </button>
    </div>
    <div class="queue-toolbar">
      <button
        class="queue-bulk-button"
        :class="{ active: taskQueueViewFilter === 'all' }"
        type="button"
        @click="taskQueueViewFilter = 'all'"
      >
        {{ t('queue_filter_all') }}
      </button>
      <button
        class="queue-bulk-button"
        :class="{ active: taskQueueViewFilter === 'orphaned' }"
        type="button"
        @click="taskQueueViewFilter = 'orphaned'"
      >
        {{ t('queue_filter_orphaned') }} ({{ orphanedTaskCount }})
      </button>
      <button
        class="queue-bulk-button danger"
        type="button"
        :disabled="!authCanDispatchWrite || orphanedTaskCount === 0"
        :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
        @click="deleteOrphanedTasks"
      >
        {{ t('queue_clear_orphaned') }}
      </button>
    </div>
    <div v-if="tasks.length === 0" class="empty">{{ t('tasks_empty') }}</div>

    <section v-for="group in taskGroups" :key="group.key" class="queue-group">
      <div class="queue-header" :class="{ prominent: group.key === 'finished' }">
        <button class="queue-header-main" type="button" @click="toggleQueueGroup(group.key)">
          <span>{{ group.title }}</span>
          <span class="queue-header-meta">
            <span class="queue-count">{{ group.tasks.length }}</span>
            <span class="queue-toggle-text">
              {{ isQueueGroupCollapsed(group.key) ? panelLocale.expand : panelLocale.collapse }}
            </span>
          </span>
        </button>
      </div>

      <template v-if="!isQueueGroupCollapsed(group.key)">
        <div v-if="group.tasks.length > 0" class="queue-bulk-actions" :class="{ prominent: group.key === 'finished' }">
          <button
            v-if="group.key === 'blocked'"
            class="queue-bulk-button"
            type="button"
            :disabled="!authCanDispatchWrite || countRetryableBlockedTasks(group) === 0"
            :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
            @click="retryAllBlockedTasksWithAStar(group)"
          >
            {{ t('queue_retry_all_astar') }}
          </button>
          <button
            class="queue-bulk-button"
            type="button"
            :disabled="areGroupTaskCardsCollapsed(group)"
            @click="setQueueGroupTaskCardsCollapsed(group, true)"
          >
            {{ queueViewLocale.collapseCards }}
          </button>
          <button
            class="queue-bulk-button"
            type="button"
            :disabled="areGroupTaskCardsExpanded(group)"
            @click="setQueueGroupTaskCardsCollapsed(group, false)"
          >
            {{ queueViewLocale.expandCards }}
          </button>
          <button
            v-if="group.key === 'finished'"
            class="queue-bulk-button"
            type="button"
            @click="exportFinishedTasksToJson"
          >
            {{ t('queue_export_finished') }}
          </button>
          <button
            v-if="group.key === 'finished'"
            class="queue-bulk-button danger"
            type="button"
            :disabled="!authCanDispatchWrite"
            :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
            @click="deleteFinishedTasks"
          >
            {{ t('queue_delete_finished') }}
          </button>
        </div>

        <div v-else class="queue-empty">
          {{ t('queue_empty') }}
        </div>

        <article
          v-for="task in group.tasks"
          :key="task.id"
          class="task-card"
          :class="{
            previewing: previewTaskId === task.id,
            collapsed: isTaskCardFolded(task.id),
            'search-hit': matchedTaskIds.includes(task.id)
          }"
          @mouseenter="onTaskHover(task)"
          @mouseleave="onTaskLeave"
        >
          <button class="task-head task-card-toggle" type="button" @click="toggleTaskCard(task.id)">
            <strong>#{{ task.id }}</strong>
            <span class="task-head-side">
              <span class="status-badge" :class="task.status">{{ taskStatusText(task.status) }}</span>
              <span class="task-card-toggle-text">
                {{ isTaskCardFolded(task.id) ? panelLocale.expand : panelLocale.collapse }}
              </span>
            </span>
          </button>

          <div v-if="isTaskCardFolded(task.id)" class="task-line task-line-compact">
            {{ formatTaskCompactSummary(task) }}
          </div>

          <template v-else>
            <div class="task-line">{{ formatTaskMeta(task) }}</div>
            <div v-if="formatTaskStageProgress(task)" class="task-line">{{ formatTaskStageProgress(task) }}</div>
            <div v-if="formatTaskCurrentStage(task)" class="task-line">{{ formatTaskCurrentStage(task) }}</div>
            <div class="task-line">{{ t('task_priority') }}: {{ task.priority }}</div>
            <div v-if="formatTaskAlgorithm(task)" class="task-line">{{ formatTaskAlgorithm(task) }}</div>
            <div v-if="formatTaskInitialPoint(task)" class="task-line">{{ formatTaskInitialPoint(task) }}</div>
            <div class="task-line">{{ formatTaskAgv(task) }}</div>
            <div v-if="formatTaskCreatedBy(task)" class="task-line">{{ formatTaskCreatedBy(task) }}</div>
            <div v-if="isTaskOrphaned(task)" class="task-line task-reason alert">
              {{ t('task_orphaned_hint') }}
            </div>
            <div v-if="formatTaskPathStats(task)" class="task-line">{{ formatTaskPathStats(task) }}</div>
            <div class="task-line task-reason" :class="{ alert: isTaskReasonAlert(task) }">
              {{ t('dispatch_reason') }}: {{ formatDispatchReason(task) }}
            </div>
            <div v-if="formatTaskLastAction(task)" class="task-line task-last-action">
              {{ taskLastActionLabel() }}: {{ formatTaskLastAction(task) }}
            </div>
            <div v-if="formatTaskLastOperator(task)" class="task-line task-last-action">
              {{ formatTaskLastOperator(task) }}
            </div>
            <div v-if="formatTaskTime(task)" class="task-line task-time">
              {{ formatTaskTime(task) }}
            </div>
            <div class="task-actions">
              <button
                v-if="isTaskDeletable(task)"
                class="btn-delete task-action-button"
                type="button"
                :disabled="!authCanDispatchWrite"
                :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                @click="deleteTask(task)"
              >
                {{ t('delete_task') }}
              </button>
              <button
                v-if="task.status === 'blocked' && !isRecoveryRequiredTask(task) && isCellOccupiedTimeoutTask(task)"
                class="btn-secondary task-action-button"
                type="button"
                :disabled="!authCanDispatchWrite || isTaskRecoveryBusy(task.id) || !task.preferred_agv_id"
                :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                @click="retryBlockedTaskFromCurrent(task)"
              >
                {{ retryFromCurrentButtonText() }}
              </button>
              <button
                v-if="task.status === 'blocked' && !isRecoveryRequiredTask(task)"
                class="btn-secondary task-action-button"
                type="button"
                :disabled="!authCanDispatchWrite || isTaskRecoveryBusy(task.id)"
                :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                @click="retryBlockedTaskWithAStar(task)"
              >
                {{ t('task_retry_astar') }}
              </button>
              <button
                v-if="task.status === 'blocked' && isRecoveryRequiredTask(task)"
                class="btn-secondary task-action-button"
                type="button"
                :disabled="!authCanDispatchWrite || isTaskRecoveryBusy(task.id) || !task.preferred_agv_id"
                :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                @click="recoverBlockedTask(task, 'bound')"
              >
                {{ recoveryActionText('bound', task) }}
              </button>
              <button
                v-if="task.status === 'blocked' && isRecoveryRequiredTask(task)"
                class="btn-secondary task-action-button"
                type="button"
                :disabled="!authCanDispatchWrite || isTaskRecoveryBusy(task.id)"
                :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                @click="recoverBlockedTask(task, 'reassign')"
              >
                {{ recoveryActionText('reassign', task) }}
              </button>
            </div>
          </template>
        </article>
      </template>
    </section>
  </div>
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'TaskQueuePanel',
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
