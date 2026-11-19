<template>
  <!-- Full page work item: /planner/<project>/item/EVT-12 (or the Task name) -->
  <div v-if="name" class="h-full">
    <ItemDetail :name="name" :items="items" mode="page" @navigate="go" @deleted="back" />
  </div>
  <div v-else-if="missing" class="p-10 text-center text-sm text-ink-gray-5">Work item {{ route.params.id }} not found in this project.</div>
  <div v-else class="flex h-full items-center justify-center"><LoadingIndicator class="size-5" /></div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LoadingIndicator } from 'frappe-ui'
import ItemDetail from '../components/ItemDetail.vue'
import { api } from '../api'
import { ctx, fail } from '../store'
import { itemId } from '../utils'

const route = useRoute()
const router = useRouter()
const items = ref([])
const missing = ref(false)

watch(
  () => ctx.project?.name,
  async (project) => {
    if (!project) return
    try {
      items.value = await api.items(project, [], 'sequence asc')
      missing.value = !name.value
    } catch (err) {
      fail(err)
    }
  },
  { immediate: true },
)

const name = computed(() => {
  const id = route.params.id
  return items.value.find((i) => i.name === id || itemId(ctx.project, i) === id)?.name || null
})

function go(taskName) {
  const item = items.value.find((i) => i.name === taskName)
  router.push({ name: 'item', params: { project: ctx.project.name, id: item ? itemId(ctx.project, item) : taskName } })
}

function back() {
  router.push({ name: 'items', params: { project: ctx.project.name } })
}
</script>
