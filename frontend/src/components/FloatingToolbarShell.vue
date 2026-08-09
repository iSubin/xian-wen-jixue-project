<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  variant?: 'glass' | 'solid'
  noWrap?: boolean
}>(), {
  variant: 'glass',
  noWrap: true,
})

const variantClass = computed(() => {
  if (props.variant === 'solid') {
    return 'bg-white border border-gray-100 shadow-sm hover:shadow-md'
  }
  return 'bg-white/95 backdrop-blur-sm shadow-lg hover:shadow-xl'
})
</script>

<template>
  <div
    :class="[
      'xw-floating-shell group flex items-center rounded-full p-1.5 gap-1 transition-all duration-200',
      variantClass,
      noWrap ? 'whitespace-nowrap' : '',
    ]"
  >
    <slot />
  </div>
</template>
