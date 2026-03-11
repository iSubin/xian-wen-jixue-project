<script setup lang="ts">
import { computed } from 'vue'
import Toast from './Toast.vue'
import type { ToastItem } from '../composables/useToast'

const props = defineProps<{
  toasts: ToastItem[]
  position?: 'top-right' | 'top-center' | 'bottom-right' | 'bottom-center'
}>()

const emit = defineEmits<{
  close: [id: string]
}>()

// 位置样式映射
const positionClasses = computed(() => {
  switch (props.position) {
    case 'top-right':
      return 'top-4 right-4 items-end'
    case 'top-center':
      return 'top-4 left-1/2 -translate-x-1/2 items-center'
    case 'bottom-right':
      return 'bottom-4 right-4 items-end'
    case 'bottom-center':
      return 'bottom-4 left-1/2 -translate-x-1/2 items-center'
    default:
      return 'bottom-4 right-4 items-end'
  }
})
</script>

<template>
  <transition-group
    name="toast"
    tag="div"
    class="fixed z-[60] flex flex-col gap-2 pointer-events-none"
    :class="positionClasses"
  >
    <Toast
      v-for="toast in toasts"
      :key="toast.id"
      v-bind="toast"
      class="pointer-events-auto"
      @close="emit('close', $event)"
    />
  </transition-group>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 220ms ease, transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.94);
}

.toast-enter-to,
.toast-leave-from {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.toast-move {
  transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active,
  .toast-move {
    transition: none;
  }
}
</style>
