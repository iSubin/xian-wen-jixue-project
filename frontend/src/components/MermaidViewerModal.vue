<script setup lang="ts">
import {
  PhArrowsClockwise,
  PhArrowsCounterClockwise,
  PhMinus,
  PhPlus,
  PhX,
} from '@phosphor-icons/vue'
import { ref } from 'vue'
import FloatingToolbarDivider from './FloatingToolbarDivider.vue'
import FloatingToolbarShell from './FloatingToolbarShell.vue'

interface Props {
  show: boolean
  currentZoom: number
  svgContent: string
  hintText?: string
}

const props = withDefaults(defineProps<Props>(), {
  hintText: '滚轮缩放 · 拖拽平移 · 双击适应',
})

const emit = defineEmits<{
  close: []
  resetView: []
  fitView: []
  zoomIn: []
  zoomOut: []
}>()

const stage = ref<HTMLElement | null>(null)
const viewport = ref<HTMLElement | null>(null)

defineExpose({
  stage,
  viewport,
})
</script>

<template>
  <transition name="fade">
    <div
      v-if="props.show"
      class="fixed inset-0 z-[70] bg-slate-100/95 backdrop-blur-sm"
      @click.self="emit('close')"
    >
      <div class="absolute top-4 left-1/2 z-20 -translate-x-1/2">
        <FloatingToolbarShell>
          <div class="rounded-full bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">
            {{ Math.round(props.currentZoom * 100) }}%
          </div>

          <button
            class="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors"
            title="缩小"
            @click="emit('zoomOut')"
          >
            <PhMinus :size="16" />
          </button>
          <button
            class="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors"
            title="放大"
            @click="emit('zoomIn')"
          >
            <PhPlus :size="16" />
          </button>
          <button
            class="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors"
            title="适应屏幕"
            @click="emit('fitView')"
          >
            <PhArrowsClockwise :size="16" />
          </button>
          <button
            class="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors"
            title="100% 视图"
            @click="emit('resetView')"
          >
            <PhArrowsCounterClockwise :size="16" />
          </button>
          <FloatingToolbarDivider />
          <button
            class="p-2 text-slate-600 hover:text-rose-600 hover:bg-rose-50 rounded-full transition-colors"
            title="关闭"
            @click="emit('close')"
          >
            <PhX :size="16" />
          </button>
        </FloatingToolbarShell>
      </div>

      <div
        ref="stage"
        class="mermaid-stage absolute inset-0 select-none overflow-hidden touch-none"
      >
        <div
          ref="viewport"
          class="mermaid-viewport"
          @dblclick="emit('fitView')"
          v-html="props.svgContent"
        ></div>
      </div>

      <div class="pointer-events-none absolute bottom-8 left-1/2 z-20 -translate-x-1/2 rounded-lg border border-slate-200 bg-white/95 px-3 py-1.5 text-xs text-slate-500 shadow-sm">
        {{ props.hintText }}
      </div>
    </div>
  </transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.mermaid-viewport {
  position: absolute;
  left: 0;
  top: 0;
  transform-origin: 0 0;
  will-change: transform;
}

.mermaid-stage :deep(svg) {
  display: block;
  max-width: none !important;
  max-height: none !important;
}

.mermaid-stage :deep(.label),
.mermaid-stage :deep(text) {
  fill: #0f172a;
}
</style>
