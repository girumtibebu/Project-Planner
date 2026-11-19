<template>
  <ProjectShell v-if="projectName">
    <RouterView />
  </ProjectShell>
  <RouterView v-else />
  <ToastProvider />
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ToastProvider } from 'frappe-ui'
import ProjectShell from './components/ProjectShell.vue'
import { ctx, loadProject } from './store'

const route = useRoute()
const projectName = computed(() => route.params.project)

watch(
  projectName,
  (name) => {
    if (name && ctx.project?.name !== name) loadProject(name)
  },
  { immediate: true },
)
</script>
