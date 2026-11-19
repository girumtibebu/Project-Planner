<script setup lang="ts">
// Lightweight stroke icon set. 16px grid, currentColor.
const props = withDefaults(defineProps<{
  name: string
  size?: number
  strokeWidth?: number
}>(), {
  size: 16,
  strokeWidth: 1.6,
})

const PATHS: Record<string, string | null> = {
  home:     "M2.5 7.5 8 2.5l5.5 5M3.5 7v6h9V7",
  brief:    "M4 2.5h6l2.5 2.5v8a.5.5 0 0 1-.5.5H4a.5.5 0 0 1-.5-.5v-10A.5.5 0 0 1 4 2.5ZM10 2.5V5h2.5M5.5 8h5M5.5 10.5h5M5.5 5.5h2",
  debrief:  "M4 2.5h6l2.5 2.5v8a.5.5 0 0 1-.5.5H4a.5.5 0 0 1-.5-.5v-10A.5.5 0 0 1 4 2.5ZM10 2.5V5h2.5M5.5 8.5l1.5 1.5 3-3M5.5 11.5h5",
  action:   "M2.5 4h11M2.5 8h11M2.5 12h11M5 4v8",
  timeline: "M2.5 4.5h6M5 8.5h7M3.5 12.5h5",
  calendar: "M3 3.5h10a.5.5 0 0 1 .5.5v9a.5.5 0 0 1-.5.5H3a.5.5 0 0 1-.5-.5V4a.5.5 0 0 1 .5-.5ZM2.5 6.5h11M5.5 2.5v2M10.5 2.5v2",
  schedule: "M2.5 4h11M2.5 8h11M2.5 12h11",
  close:    "M4 4l8 8M12 4l-8 8",
  chevdown: "M4 6l4 4 4-4",
  chevright:"M6 4l4 4-4 4",
  chevleft: "M10 4 6 8l4 4",
  plus:     "M8 3v10M3 8h10",
  search:   "M7 2.5a4.5 4.5 0 1 1 0 9 4.5 4.5 0 0 1 0-9ZM10.5 10.5l3 3",
  filter:   "M2.5 3.5h11l-4 5v4l-3-1.5v-2.5z",
  download: "M8 2.5v8M4.5 7 8 10.5 11.5 7M3 13h10",
  drag:     null,  // special: sw=2
  bold:     "M4.5 3h3.5a2 2 0 0 1 0 4H4.5zM4.5 7h4.5a2 2 0 0 1 0 4H4.5z",
  italic:   "M7 3h5M4 13h5M9.5 3 6.5 13",
  underline:"M4.5 3v5a3.5 3.5 0 0 0 7 0V3M3.5 13.5h9",
  h1:       "M3 3v10M9 3v10M3 8h6M11.5 5l1.5-1v9",
  h2:       "M3 3v10M8 3v10M3 8h5M10 5.5a1.5 1.5 0 0 1 3 0c0 2.5-3 3.5-3 5.5h3",
  list:     "M3 4h.01M3 8h.01M3 12h.01M6 4h7M6 8h7M6 12h7",
  table:    "M2.5 3.5h11v9h-11zM2.5 6.5h11M2.5 9.5h11M6 3.5v9M10 3.5v9",
  image:    "M2.5 3.5h11v9h-11zM2.5 10 6 7l3 2.5L11 8l2.5 2",
  link:     "M7 9.5a2.5 2.5 0 0 0 3.5 0l2-2a2.5 2.5 0 0 0-3.5-3.5l-1 1M9 6.5a2.5 2.5 0 0 0-3.5 0l-2 2a2.5 2.5 0 0 0 3.5 3.5l1-1",
  quote:    "M3 5.5c0-1 .5-2 2-2M3 5.5h2.5V9H3zM8 5.5c0-1 .5-2 2-2M8 5.5h2.5V9H8z",
  code:     "M5.5 4 2 8l3.5 4M10.5 4 14 8l-3.5 4",
  user:     "M8 8.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM3 13c.5-2 2.5-3 5-3s4.5 1 5 3",
  dot:      null, // special: sw=4
  check:    "M3 8.5 6.5 12 13 4",
  dots:     null, // special: sw=2.5
  kanban:   "M3 3.5h3v9H3zM6.5 3.5h3v5h-3zM10 3.5h3v7h-3z",
  arrow:    "M3 8h10M9 4l4 4-4 4",
  back:     "M13 8H3M7 4 3 8l4 4",
  clock:    "M8 13.5a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11ZM8 5v3.5L10 10",
  truck:    "M2 4.5h7v6H2zM9 6.5h3l2 2v2h-5zM4.5 12.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2ZM11.5 12.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z",
  box:      "M2.5 5 8 2.5 13.5 5v6L8 13.5 2.5 11zM2.5 5 8 7.5 13.5 5M8 7.5V13.5",
  grip:     null,
}

const SW_OVERRIDES: Record<string, number> = {
  drag: 2, dot: 4, dots: 2.5, grip: 2,
}

// Multi-path icons (children instead of single d)
const MULTI: Record<string, string[]> = {
  drag: ["M6 4.5h.01M6 8h.01M6 11.5h.01M10 4.5h.01M10 8h.01M10 11.5h.01"],
  dot:  ["M8 8h.01"],
  dots: ["M4 8h.01M8 8h.01M12 8h.01"],
  grip: ["M6 3h.01M10 3h.01M6 6.5h.01M10 6.5h.01M6 10h.01M10 10h.01M6 13.5h.01M10 13.5h.01"],
}

const d = PATHS[props.name] ?? null
const sw = SW_OVERRIDES[props.name] ?? props.strokeWidth
const multi = MULTI[props.name] ?? null
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    :stroke-width="sw"
    stroke-linecap="round"
    stroke-linejoin="round"
    style="flex-shrink:0;"
  >
    <path v-if="d" :d="d" />
    <template v-else-if="multi">
      <path v-for="(pd, i) in multi" :key="i" :d="pd" />
    </template>
  </svg>
</template>
