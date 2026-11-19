<script setup lang="ts">
/**
 * UiCard — Generic card container for sidebar sections
 * Clean, minimal card with optional header
 */
interface Props {
  title?: string;
  icon?: string;
}

const props = defineProps<Props>();
</script>

<template>
  <div class="ui-card">
    <div v-if="props.title" class="ui-card__header">
      <span v-if="props.icon" class="ui-card__icon">{{ props.icon }}</span>
      <span class="ui-card__title">{{ props.title }}</span>
    </div>
    <div class="ui-card__content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.ui-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.ui-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--panel-2);
}

.ui-card__icon {
  font-size: 14px;
  color: var(--text-3);
}

.ui-card__title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
}

.ui-card__content {
  padding: 14px;
}
</style>
