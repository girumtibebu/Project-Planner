<template>
  <!-- New project: link the sales order, fill the details, start from a saved board or blank -->
  <Dialog :model-value="modelValue" title="New project" :options="{ size: '3xl' }" @update:model-value="(v) => emit('update:modelValue', v)">
    <div v-if="options" class="flex flex-col gap-4">
      <div class="grid grid-cols-2 gap-3">
        <div class="relative">
          <div class="mb-1.5 text-xs text-ink-gray-5">Sales order (won proposal)</div>
          <div v-if="form.sales_order" class="field flex items-center gap-2">
            <span class="lucide-receipt size-3.5 text-ink-gray-5" />
            <span class="min-w-0 flex-1 truncate">{{ form.sales_order }} · {{ picked?.customer_name }}</span>
            <button class="text-ink-gray-4 hover:text-ink-gray-8" title="Remove" @click="clearSalesOrder"><span class="lucide-x block size-3.5" /></button>
          </div>
          <template v-else>
            <input v-model="soQuery" class="field" placeholder="Search by number or client…" @focus="soOpen = true" @blur="closeSoLater" @input="searchSo" />
            <div v-if="soOpen" class="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border border-outline-gray-2 bg-surface-base p-1 shadow-lg">
              <button
                v-for="so in soResults"
                :key="so.name"
                class="flex w-full flex-col items-start rounded px-2 py-1.5 text-left hover:bg-surface-gray-2"
                @mousedown.prevent="pickSalesOrder(so)"
              >
                <span class="text-sm text-ink-gray-8">{{ so.customer_name || so.customer }}</span>
                <span class="text-xs text-ink-gray-5">{{ so.name }} · {{ so.transaction_date }} · {{ so.status }}</span>
              </button>
              <div v-if="!soResults.length" class="px-2 py-1.5 text-sm text-ink-gray-5">{{ soLoading ? 'Searching…' : 'No open sales order without a project matches' }}</div>
            </div>
          </template>
        </div>
        <div>
          <div class="mb-1.5 text-xs text-ink-gray-5">Client</div>
          <select v-model="form.customer" class="field">
            <option value="">None</option>
            <option v-for="c in options.customers" :key="c.name" :value="c.name">{{ c.customer_name || c.name }}</option>
          </select>
        </div>
      </div>
      <FormControl v-model="form.project_name" label="Project name" placeholder="e.g. Coca-Cola Summer Launch" />
      <div class="grid grid-cols-4 gap-3">
        <FormControl v-model="form.project_type" type="select" label="Type" :options="typeOptions" />
        <FormControl v-model="form.expected_start_date" type="date" label="Start" />
        <FormControl v-model="form.expected_end_date" type="date" label="End" />
        <FormControl v-model="form.location" label="Venue" placeholder="e.g. Meskel Square" />
      </div>
      <div>
        <div class="mb-1.5 text-xs text-ink-gray-5">Start from</div>
        <TemplateCards v-model="template" :templates="options.templates" />
      </div>
    </div>
    <div v-else class="flex h-40 items-center justify-center"><LoadingIndicator class="size-5" /></div>

    <template #actions>
      <div class="flex items-center justify-end gap-2">
        <span class="mr-auto text-sm text-ink-gray-5">Save any project as a template from its sidebar menu.</span>
        <Button label="Cancel" @click="emit('update:modelValue', false)" />
        <Button variant="solid" label="Create project" :loading="creating" :disabled="!form.project_name.trim()" @click="create" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Dialog, FormControl, LoadingIndicator } from 'frappe-ui'
import TemplateCards from './TemplateCards.vue'
import { api } from '../api'
import { fail } from '../store'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])
const router = useRouter()

const options = ref(null)
const EMPTY = { sales_order: '', customer: '', project_name: '', project_type: '', expected_start_date: '', expected_end_date: '', location: '' }
const form = reactive({ ...EMPTY })
const template = ref('')
const creating = ref(false)

const typeOptions = computed(() => [{ value: '', label: 'No type' }, ...(options.value?.project_types || []).map((t) => ({ value: t, label: t }))])

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    Object.assign(form, EMPTY)
    soQuery.value = ''
    picked.value = null
    searchSo()
    try {
      options.value = await api.newProjectOptions()
      pickTemplate(options.value.templates[0]?.name || '')
    } catch (err) {
      fail(err)
    }
  },
)

function pickTemplate(name) {
  template.value = name
}
watch(template, (name) => {
  const t = options.value?.templates.find((x) => x.name === name)
  if (t?.project_type) form.project_type = t.project_type
})

// sales order: searched on the server as you type
const soQuery = ref('')
const soResults = ref([])
const soOpen = ref(false)
const soLoading = ref(false)
const picked = ref(null)
let soTimer = null
function searchSo() {
  clearTimeout(soTimer)
  soLoading.value = true
  soTimer = setTimeout(async () => {
    try {
      soResults.value = await api.searchSalesOrders(soQuery.value)
    } catch (err) {
      fail(err)
    } finally {
      soLoading.value = false
    }
  }, 250)
}
const closeSoLater = () => setTimeout(() => (soOpen.value = false), 150)
function clearSalesOrder() {
  form.sales_order = ''
  picked.value = null
}

function pickSalesOrder(so) {
  picked.value = so
  form.sales_order = so.name
  soOpen.value = false
  // the client may be outside the loaded list (or the user may not list clients)
  if (!options.value.customers.some((c) => c.name === so.customer)) options.value.customers.unshift({ name: so.customer, customer_name: so.customer_name })
  form.customer = so.customer
  if (!form.project_name.trim()) form.project_name = so.customer_name || so.customer
  if (!form.expected_start_date && so.delivery_date) form.expected_start_date = so.delivery_date
}

async function create() {
  if (!form.project_name.trim() || creating.value) return
  creating.value = true
  try {
    const { name } = await api.createProject(form, template.value || null)
    emit('update:modelValue', false)
    router.push({ name: 'overview', params: { project: name } })
  } catch (err) {
    fail(err)
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.field {
  @apply h-7 w-full rounded border-0 bg-surface-gray-2 px-2 text-base text-ink-gray-8 focus:ring-2 focus:ring-outline-gray-3;
}
</style>
