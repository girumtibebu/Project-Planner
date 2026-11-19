<script setup lang="ts">
/**
 * UiPill — colored status/tag pill with dot
 * Design spec: 999px radius, 6px colored dot, 14% tint background, 1px 18% border
 */
interface Props {
  color?: string;     // hex color or CSS color
  dot?: boolean;      // show colored dot (default true)
  size?: 'sm' | 'md';
}

const props = withDefaults(defineProps<Props>(), {
  color: 'var(--text-3)',
  dot: true,
  size: 'md',
});
</script>

<template>
  <span
    class="ui-pill"
    :class="`ui-pill--${size}`"
    :style="{
      backgroundColor: `${props.color}14`,
      borderColor: `${props.color}2E`,
      color: props.color,
    }"
  >
    <span
      v-if="dot"
      class="ui-pill__dot"
      :style="{ backgroundColor: props.color }"
    />
    <span class="ui-pill__text">
      <slot />
    </span>
  </span>
</template>

<style scoped>
.ui-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  border: 1px solid;
  font-weight: 500;
  white-space: nowrap;
}

.ui-pill--sm {
  padding: 2px 8px;
  font-size: 10.5px;
}

.ui-pill--md {
  padding: 3px 10px;
  font-size: 11.5px;
}

.ui-pill__dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  flex-shrink: 0;
}

.ui-pill__text {
  line-height: 1;
}
</style>
