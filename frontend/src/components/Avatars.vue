<template>
  <div class="flex items-center -space-x-1.5">
    <Tooltip v-for="user in shown" :key="user" :text="memberName(user)">
      <Avatar :label="memberName(user)" :image="memberIndex[user]?.user_image" size="xs" class="ring-2 ring-surface-base" />
    </Tooltip>
    <span v-if="users.length > max" class="pl-2 text-xs text-ink-gray-5">+{{ users.length - max }}</span>
    <span v-if="!users.length && placeholder" class="lucide-user-round-plus size-4 text-ink-gray-4" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Avatar, Tooltip } from 'frappe-ui'
import { memberIndex, memberName } from '../store'

const props = defineProps({
  users: { type: Array, default: () => [] },
  max: { type: Number, default: 3 },
  placeholder: { type: Boolean, default: false },
})
const shown = computed(() => props.users.slice(0, props.max))
</script>
