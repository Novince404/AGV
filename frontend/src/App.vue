<script setup>
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppShell from '@/layouts/AppShell.vue'

const route = useRoute()
const isStandaloneRoute = computed(() => Boolean(route.meta.public || route.meta.legacy || route.meta.standalone))
</script>

<template>
  <RouterView v-if="isStandaloneRoute" />
  <AppShell v-else />
</template>
