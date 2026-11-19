<script setup lang="ts">
const props = withDefaults(defineProps<{
  name?: string
  email?: string
  color?: string
  size?: number
}>(), {
  size: 20,
  color: '#CC785C',
})

function initials(name?: string, email?: string): string {
  const src = name || email || '?'
  const parts = src.split(/[\s@.]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return src.slice(0, 2).toUpperCase()
}

const bg = props.color + '22'
const border = props.color + '44'
const fontSz = Math.round(props.size * 0.48)
</script>

<template>
  <span
    :style="{
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: size + 'px',
      height: size + 'px',
      borderRadius: '999px',
      background: bg,
      color: color,
      fontSize: fontSz + 'px',
      fontWeight: 600,
      letterSpacing: '.02em',
      border: `1px solid ${border}`,
      flexShrink: 0,
    }"
  >{{ initials(name, email) }}</span>
</template>
