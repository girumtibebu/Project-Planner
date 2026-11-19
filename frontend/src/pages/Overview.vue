<template>
  <div class="h-full overflow-y-auto">
    <header class="flex h-12 items-center gap-2 border-b border-outline-gray-1 px-4">
      <span class="lucide-layout-dashboard size-4 text-ink-gray-5" />
      <h1 class="text-base font-semibold text-ink-gray-9">Overview</h1>
    </header>
    <div class="mx-auto flex max-w-5xl flex-col gap-6 p-6">
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Fact label="Dates" :value="dates" icon="lucide-calendar-range" />
        <Fact label="Customer" :value="p.customer || '—'" icon="lucide-building-2" />
        <Fact label="Sales order" :value="p.sales_order || '—'" icon="lucide-receipt" />
        <Fact label="Division" :value="p.cost_center || '—'" icon="lucide-network" />
        <Fact label="Project type" :value="p.project_type || '—'" icon="lucide-shapes" />
        <Fact label="Status" :value="p.status" icon="lucide-activity" />
        <Fact label="Progress" :value="`${Math.round(p.percent_complete || 0)}%`" icon="lucide-gauge" />
        <Fact label="Location" :value="p.location || '—'" icon="lucide-map-pin" />
      </div>

      <section class="rounded-2xl border border-outline-gray-1 p-5">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-ink-gray-8">Work by state</h2>
          <span class="text-sm text-ink-gray-5">{{ items.length }} work items</span>
        </div>
        <div class="mb-3 flex h-2 overflow-hidden rounded-full bg-surface-gray-2">
          <div v-for="row in byState" :key="row.state.name" :style="{ width: `${(row.count / (items.length || 1)) * 100}%`, background: row.state.color }" />
        </div>
        <div class="grid grid-cols-2 gap-2 md:grid-cols-3">
          <router-link
            v-for="row in byState"
            :key="row.state.name"
            :to="{ name: 'items', params: { project: p.name } }"
            class="flex items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-surface-gray-1"
          >
            <StateIcon :state="row.state" /> {{ row.state.title }}
            <span class="ml-auto text-ink-gray-5">{{ row.count }}</span>
          </router-link>
        </div>
      </section>

      <div class="grid gap-6 md:grid-cols-2">
        <section class="rounded-2xl border border-outline-gray-1 p-5">
          <h2 class="mb-3 text-sm font-semibold text-ink-gray-8">Due in the next 14 days</h2>
          <ItemLine v-for="item in upcoming" :key="item.name" :item="item" />
          <div v-if="!upcoming.length" class="text-sm text-ink-gray-5">Nothing due soon.</div>
        </section>
        <section class="rounded-2xl border border-outline-gray-1 p-5">
          <h2 class="mb-3 text-sm font-semibold text-ink-gray-8">Overdue</h2>
          <ItemLine v-for="item in overdue" :key="item.name" :item="item" />
          <div v-if="!overdue.length" class="text-sm text-ink-gray-5">Nothing overdue.</div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import StateIcon from '../components/StateIcon.vue'
import { api } from '../api'
import { ctx, fail, stateOf } from '../store'
import { addDays, dayKey, formatDate, isOverdue, itemId } from '../utils'

const p = computed(() => ctx.project)
const items = ref([])
onMounted(async () => {
  try {
    items.value = await api.items(p.value.name, [], 'due_date asc')
  } catch (err) {
    fail(err)
  }
})

const dates = computed(() => {
  const s = formatDate(p.value.expected_start_date)
  const e = formatDate(p.value.expected_end_date)
  return s || e ? `${s || '?'} – ${e || '?'}` : '—'
})
const byState = computed(() =>
  ctx.states.map((state) => ({ state, count: items.value.filter((i) => stateOf(i).name === state.name).length })).filter((r) => r.count),
)
const open = (i) => !['Completed', 'Cancelled'].includes(stateOf(i).state_group)
const upcoming = computed(() => {
  const limit = dayKey(addDays(new Date(), 14))
  return items.value.filter((i) => open(i) && i.exp_end_date && !isOverdue(i) && dayKey(i.exp_end_date) <= limit).slice(0, 10)
})
const overdue = computed(() => items.value.filter((i) => open(i) && isOverdue(i)).slice(0, 10))

const Fact = defineComponent({
  props: { label: String, value: String, icon: String },
  setup(props) {
    return () =>
      h('div', { class: 'rounded-2xl border border-outline-gray-1 p-4' }, [
        h('div', { class: 'mb-1 flex items-center gap-1.5 text-xs text-ink-gray-5' }, [h('span', { class: [props.icon, 'size-3.5'] }), props.label]),
        h('div', { class: 'truncate text-sm font-medium text-ink-gray-8', title: props.value }, props.value),
      ])
  },
})

const ItemLine = defineComponent({
  props: { item: Object },
  setup(props) {
    return () =>
      h(
        RouterLink,
        {
          to: { name: 'items', params: { project: p.value.name }, query: { item: props.item.name } },
          class: 'flex items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-surface-gray-1',
        },
        () => [
          h(StateIcon, { state: stateOf(props.item) }),
          h('span', { class: 'w-14 text-xs text-ink-gray-5' }, itemId(p.value, props.item)),
          h('span', { class: 'min-w-0 flex-1 truncate' }, props.item.subject),
          h('span', { class: isOverdue(props.item) ? 'text-xs text-ink-red-4' : 'text-xs text-ink-gray-5' }, formatDate(props.item.exp_end_date)),
        ],
      )
  },
})
</script>
