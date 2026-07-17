<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => String(route.meta.title ?? '工作台'))
const description = computed(() => String(route.meta.description ?? '此模块正在迁移到 v3 工作台。'))
const migrationStage = computed(() => route.name === 'overview' ? '应用外壳已就绪' : '领域页面迁移中')
</script>

<template>
  <div class="workspace-placeholder">
    <section class="workspace-hero">
      <p class="workspace-kicker">{{ migrationStage }}</p>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
      <RouterLink class="workspace-primary-action" to="/dispatch">打开现有调度工作区</RouterLink>
    </section>

    <section class="workspace-grid" aria-label="模块状态">
      <article>
        <span class="workspace-status is-ready">已完成</span>
        <h3>统一应用壳</h3>
        <p>路由、按权限显示的导航、会话 Cookie 和 CSRF 请求保护已经接入。</p>
      </article>
      <article>
        <span class="workspace-status is-progress">迁移中</span>
        <h3>领域页面</h3>
        <p>任务、车辆、地图、故障和管理页面将从原有工作区逐项抽离。</p>
      </article>
      <article>
        <span class="workspace-status is-planned">下一步</span>
        <h3>实时事件时间线</h3>
        <p>后端事件流准备完成后，此处将解释等待、让行、重规划与故障恢复。</p>
      </article>
    </section>
  </div>
</template>

<style scoped>
.workspace-placeholder { display: grid; gap: var(--agv-space-5); }.workspace-hero { padding: clamp(24px, 5vw, 52px); border: 1px solid var(--agv-border); border-radius: var(--agv-radius-lg); background: linear-gradient(125deg, rgba(67, 182, 255, .17), rgba(19, 38, 61, .8)); box-shadow: var(--agv-shadow-sm); }.workspace-kicker { margin: 0 0 10px; color: var(--agv-brand); font-size: 13px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }.workspace-hero h2 { margin: 0; font-size: clamp(26px, 4vw, 40px); }.workspace-hero > p:not(.workspace-kicker) { max-width: 660px; color: var(--agv-text-secondary); line-height: 1.7; }.workspace-primary-action { display: inline-block; margin-top: var(--agv-space-3); padding: 11px 15px; border-radius: var(--agv-radius-sm); color: #06111d; background: var(--agv-brand); font-weight: 700; text-decoration: none; }.workspace-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--agv-space-4); }.workspace-grid article { padding: var(--agv-space-5); border: 1px solid var(--agv-border); border-radius: var(--agv-radius-md); background: var(--agv-bg-surface); }.workspace-grid h3 { margin: var(--agv-space-3) 0 var(--agv-space-2); }.workspace-grid p { margin: 0; color: var(--agv-text-secondary); line-height: 1.65; }.workspace-status { display: inline-block; padding: 4px 8px; border-radius: 999px; font-size: 12px; }.is-ready { color: var(--agv-success); background: rgba(54, 197, 138, .12); }.is-progress { color: var(--agv-warning); background: rgba(246, 184, 74, .12); }.is-planned { color: var(--agv-brand); background: rgba(67, 182, 255, .12); }@media (max-width: 900px) { .workspace-grid { grid-template-columns: 1fr; } }
</style>
