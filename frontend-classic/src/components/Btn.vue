<script setup lang="ts">
import Icons from './Icons.vue'
const props = withDefaults(defineProps<{
  kind?: 'default' | 'primary' | 'danger'
  icon?: string
  size?: 'sm' | 'md'
  disabled?: boolean
}>(), {
  kind: 'default',
  size: 'md',
})
</script>

<template>
  <button
    :disabled="disabled"
    :class="['ep-btn', `ep-btn--${kind}`, size === 'sm' ? 'ep-btn--sm' : '']"
  >
    <Icons v-if="icon" :name="icon" :size="13" />
    <slot />
  </button>
</template>

<style scoped>
.ep-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-2);
  background: var(--panel-2);
  color: var(--text);
  transition: background 0.1s;
  font-family: inherit;
  white-space: nowrap;
}
.ep-btn:hover:not(:disabled) { background: var(--row-hover); }
.ep-btn--primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.ep-btn--primary:hover:not(:disabled) { background: var(--accent-2); border-color: var(--accent-2); }
.ep-btn--danger { background: transparent; color: var(--danger); border-color: var(--danger); }
.ep-btn--danger:hover:not(:disabled) { background: rgba(194,65,12,.08); }
.ep-btn--sm { padding: 3px 7px; font-size: 11px; }
.ep-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
