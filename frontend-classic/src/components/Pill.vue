<script setup lang="ts">
const props = defineProps<{
  color?: string
}>()
const bg = props.color ? props.color + '22' : 'var(--bg-2)'
const textColor = props.color || 'var(--text-2)'
const border = props.color ? props.color + '44' : 'var(--border)'
</script>

<template>
  <span
    :style="{
      display: 'inline-flex',
      alignItems: 'center',
      padding: '2px 7px',
      borderRadius: '999px',
      fontSize: '11px',
      fontWeight: 500,
      letterSpacing: '.03em',
      background: bg,
      color: textColor,
      border: `1px solid ${border}`,
    }"
  ><slot /></span>
</template>
