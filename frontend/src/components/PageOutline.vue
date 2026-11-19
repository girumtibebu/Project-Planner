<template>
  <!-- "On this page", Plane style: a card when open, short heading marks at the edge when closed (hover them to peek) -->
  <aside v-if="toc.length" class="sticky top-0 hidden w-60 shrink-0 self-start pt-10 lg:block">
    <div v-if="open" class="outline-card">
      <OutlineList :toc="toc" :active="active" :min-level="minLevel" @jump="(i) => emit('jump', i)" />
    </div>
    <div v-else class="group/marks relative ml-auto w-8">
      <div class="flex flex-col items-end gap-2 py-2 pr-1">
        <span
          v-for="(h, i) in toc"
          :key="i"
          class="h-0.5 rounded-full"
          :class="active === i ? 'bg-surface-gray-7' : 'bg-surface-gray-4'"
          :style="{ width: `${20 - (h.level - minLevel) * 5}px` }"
        />
      </div>
      <div class="outline-card invisible absolute right-0 top-0 w-60 opacity-0 transition group-hover/marks:visible group-hover/marks:opacity-100">
        <OutlineList :toc="toc" :active="active" :min-level="minLevel" @jump="(i) => emit('jump', i)" />
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, defineComponent, h } from 'vue'

const props = defineProps({ toc: { type: Array, default: () => [] }, active: Number, open: Boolean })
const emit = defineEmits(['jump'])
const minLevel = computed(() => Math.min(...props.toc.map((t) => t.level), 3))

const OutlineList = defineComponent({
  props: { toc: Array, active: Number, minLevel: Number },
  emits: ['jump'],
  setup(p, { emit: send }) {
    return () =>
      h(
        'nav',
        { class: 'flex flex-col gap-0.5' },
        p.toc.map((t, i) =>
          h(
            'button',
            {
              key: i,
              class: [
                'truncate rounded-md px-2 py-1.5 text-left text-sm transition',
                p.active === i ? 'bg-surface-gray-3 font-medium text-ink-gray-9' : 'text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-9',
              ],
              style: { paddingLeft: `${(t.level - p.minLevel) * 12 + 8}px` },
              title: t.text,
              onClick: () => send('jump', i),
            },
            t.text,
          ),
        ),
      )
  },
})
</script>

<style scoped>
.outline-card {
  @apply max-h-[70vh] overflow-y-auto rounded-xl bg-surface-gray-1 p-2 shadow-sm ring-1 ring-outline-gray-1;
}
</style>
