<template>
  <div class="point-library">
    <h2>{{ t('point_library') }}</h2>
    <p class="panel-hint">{{ t('point_fill_hint') }}</p>
    <div v-if="!authCanPointWrite" class="permission-gate-card compact">
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

    <div class="point-manage">
      <h3>{{ t('point_manage') }}</h3>
      <p class="panel-hint">{{ t('point_manage_hint') }}</p>
      <div class="form-grid">
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
        <input v-model.number="customPointForm.x" type="number" min="0" :max="currentGridCols - 1" />
        <label>{{ t('form_start_y') }}</label>
        <input v-model.number="customPointForm.y" type="number" min="0" :max="currentGridRows - 1" />
      </div>
      <button
        class="btn-primary full-width"
        type="button"
        :disabled="!authCanPointWrite"
        :title="buildCapabilityLockedTitle('data', authCanPointWrite)"
        @click="addCustomPointWithAuth"
      >
        {{ t('point_add') }}
      </button>
      <div v-if="pointFormStatus" class="point-status" :class="pointFormStatusType">
        {{ pointFormStatus }}
      </div>
    </div>

    <input
      v-model.trim="pointSearch"
      class="point-search"
      type="text"
      :placeholder="t('point_search_placeholder')"
    />

    <div v-if="filteredPoints.length === 0" class="point-empty">
      {{ t('point_search_empty') }}
    </div>

    <div v-else class="point-list">
      <article
        v-for="point in filteredPoints"
        :key="point.id"
        class="point-card"
        :class="{
          'search-hit': matchedPointIds.includes(point.id),
          'is-invalid': isPointInvalid(point)
        }"
        :title="isPointInvalid(point) ? formatPointInvalidReason(point) : ''"
      >
        <div class="point-head">
          <div class="point-head-main">
            <div class="point-kind-mark" :class="`is-${pointKindKey(point)}`">
              {{ pointKindCode(point) }}
            </div>
            <div class="point-head-copy">
              <strong>{{ pointName(point) }}</strong>
              <span class="point-kind-label">{{ pointKindText(point) }}</span>
            </div>
          </div>
          <div class="point-tags">
            <span class="point-zone">{{ pointZone(point) }}</span>
            <span class="point-badge" :class="{ custom: point.custom, danger: isPointInvalid(point) }">
              {{ pointTypeText(point) }}
            </span>
          </div>
        </div>
        <div class="point-meta">
          {{ t('point_coords') }}: ({{ point.x }}, {{ point.y }})
        </div>
        <div v-if="isPointInvalid(point)" class="point-meta template-meta-alert">
          {{ formatPointInvalidReason(point) }}
        </div>
        <div class="point-actions">
          <button class="btn-ghost point-locate-action" type="button" @click="focusPointOnMap(point)">
            {{ t('point_locate_map') }}
          </button>
          <button
            class="btn-secondary"
            type="button"
            :disabled="isPointInvalid(point)"
            @click="applyPointToTaskForm('start', point)"
          >
            {{ t('point_apply_start') }}
          </button>
          <button
            class="btn-ghost"
            type="button"
            :disabled="isPointInvalid(point)"
            @click="applyPointToTaskForm('end', point)"
          >
            {{ t('point_apply_end') }}
          </button>
          <button
            v-if="point.custom"
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
</template>

<script>
import { defineComponent, reactive, watchEffect } from 'vue'

export default defineComponent({
  name: 'PointLibraryPanel',
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
