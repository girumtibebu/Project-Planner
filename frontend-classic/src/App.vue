<script setup lang="ts">
import { computed, provide, ref, watch } from "vue";
import { useRoute } from "vue-router";
import AppShell from "./components/AppShell.vue";
import { useFrappeDoc } from "./composables/useFrappe";

const route = useRoute();
const projectName = computed(() => route.params.project as string);

// Load the Project doc and provide it to all descendant pages
const { doc: project, loading, error } = useFrappeDoc("Project", projectName);

provide("project", project);
provide("projectName", projectName);
provide("projectLoading", loading);
</script>

<template>
  <div v-if="loading" style="display:flex;align-items:center;justify-content:center;height:100vh;color:var(--text-3);font-size:13px;">
    Loading project…
  </div>
  <div v-else-if="error" style="display:flex;align-items:center;justify-content:center;height:100vh;color:var(--danger);font-size:13px;">
    Error loading project: {{ error }}
  </div>
  <AppShell v-else />
</template>
