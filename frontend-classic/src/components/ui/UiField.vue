<script setup lang="ts">
/**
 * UiField — Field section card for Event Brief
 * Uppercase label + content area + optional meta row
 * Design spec: card with uppercase 10px label, editable content area
 */
interface Props {
  label: string;
  meta?: string;        // optional meta text (e.g., "Last edited 2 min ago")
}

const props = defineProps<Props>();
</script>

<template>
  <div class="ui-field">
    <div class="ui-field__header">
      <span class="ui-field__label">{{ props.label }}</span>
      <span v-if="props.meta" class="ui-field__meta">{{ props.meta }}</span>
    </div>
    <div class="ui-field__content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.ui-field {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  transition: box-shadow var(--transition-fast);
}

.ui-field:hover {
  box-shadow: var(--shadow-sm);
}

.ui-field__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}

.ui-field__label {
  font-size: 10.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-3);
}

.ui-field__meta {
  font-size: 10.5px;
  color: var(--text-3);
  font-family: var(--font-mono);
}

.ui-field__content {
  min-height: 60px;
}
</style>
