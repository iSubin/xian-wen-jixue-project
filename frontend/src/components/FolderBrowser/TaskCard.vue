<script setup lang="ts">
import { computed } from 'vue'
import {
  PhSpinner,
  PhCheckCircle,
  PhXCircle,
  PhClock,
  PhTrash,
  PhInfo,
  PhCheckSquare,
  PhSquare,
} from '@phosphor-icons/vue'
import type { Task } from '../../types'
import { TaskStatus } from '../../types'

const props = defineProps<{
  task: Task
  isSelected: boolean
  multiSelectMode?: boolean
  isChecked?: boolean
}>()

const emit = defineEmits<{
  select: [task: Task]
  delete: [taskId: string]
  showInfo: [task: Task]
  dragstart: [taskId: string]
  toggleSelect: [taskId: string]
}>()

const isInProgress = computed(() =>
  ([TaskStatus.DOWNLOADING, TaskStatus.UPLOADING, TaskStatus.TRANSCRIBING, TaskStatus.SUMMARIZING] as TaskStatus[]).includes(props.task.status)
)

const getStatusClass = (status: TaskStatus) => {
  switch (status) {
    case TaskStatus.COMPLETED: return 'bg-emerald-100 text-emerald-700'
    case TaskStatus.FAILED: return 'bg-red-100 text-red-700'
    case TaskStatus.PENDING: return 'bg-slate-100 text-slate-600'
    default: return 'bg-blue-100 text-blue-700'
  }
}

const getStatusIcon = (status: TaskStatus) => {
  switch (status) {
    case TaskStatus.COMPLETED: return PhCheckCircle
    case TaskStatus.FAILED: return PhXCircle
    case TaskStatus.PENDING: return PhClock
    default: return PhSpinner
  }
}

const statusLabel = computed(() => {
  switch (props.task.status) {
    case TaskStatus.PENDING: return '等待'
    case TaskStatus.DOWNLOADING: return '下载'
    case TaskStatus.UPLOADING: return '上传'
    case TaskStatus.TRANSCRIBING: return '转录'
    case TaskStatus.SUMMARIZING: {
      const total = props.task.summary_chunk_total
      const done = props.task.summary_chunk_done
      if (total && total > 0) {
        return `总结 (${Math.min(done ?? 0, total)}/${total})`
      }
      return '总结'
    }
    case TaskStatus.COMPLETED: return '完成'
    case TaskStatus.FAILED: return '失败'
    default: return ''
  }
})

const progress = computed(() => Math.min(100, Math.round(props.task.progress || 0)))

const sourceLabel = computed(() => {
  if (props.task.source_type === 'wechat_article') return '公众号'
  return ''
})

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
</script>

<template>
  <div
    :class="[
      'p-3 rounded-2xl border cursor-pointer transition-all hover:shadow-sm active:scale-[0.98] group relative',
      isChecked ? 'border-blue-400 bg-blue-50 ring-1 ring-blue-400/30 shadow-sm' : isSelected ? 'border-blue-200 bg-blue-50/60 ring-1 ring-primary/20 shadow-sm' : 'border-transparent hover:bg-white hover:border-gray-100'
    ]"
    draggable="true"
    @dragstart="emit('dragstart', task.id)"
    @click="multiSelectMode ? emit('toggleSelect', task.id) : emit('select', task)"
  >
    <!-- checkbox in multi-select mode -->
    <div v-if="multiSelectMode" class="absolute top-2 left-2 z-10">
      <component
        :is="isChecked ? PhCheckSquare : PhSquare"
        :size="18"
        :class="isChecked ? 'text-blue-500' : 'text-slate-300'"
      />
    </div>
    <div :class="multiSelectMode ? 'pl-5' : ''">
    <div class="flex justify-between items-start mb-1">
      <div class="flex flex-wrap items-center gap-1.5">
        <span :class="['text-xs font-medium px-2 py-0.5 rounded-full flex items-center gap-1', getStatusClass(task.status)]">
          <component
            :is="getStatusIcon(task.status)"
            :size="12"
            :class="isInProgress ? 'animate-spin' : ''"
          />
          {{ statusLabel }}
        </span>
        <span
          v-if="sourceLabel"
          class="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700"
        >
          {{ sourceLabel }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-[10px] text-slate-400">{{ formatDate(task.created_at) }}</span>
        <div class="flex items-center gap-1 md:opacity-0 md:group-hover:opacity-100 md:transition-opacity">
          <button @click.stop="emit('showInfo', task)" class="text-slate-400 hover:text-blue-500 p-1" title="查看信息">
            <PhInfo :size="14" />
          </button>
          <button @click.stop="emit('delete', task.id)" class="text-slate-400 hover:text-red-500 p-1" title="删除任务">
            <PhTrash :size="14" />
          </button>
        </div>
      </div>
    </div>
    <!-- title as primary, topic as secondary -->
    <div class="text-sm font-medium text-slate-700 truncate" :title="task.title || task.video_url">
      {{ task.title || task.video_url }}
    </div>
    <div v-if="task.topic" class="text-xs text-slate-400 truncate mt-0.5" :title="task.topic">
      {{ task.topic }}
    </div>
    <!-- progress bar -->
    <div v-if="isInProgress" class="w-full bg-blue-100 h-1 rounded-full mt-2 overflow-hidden">
      <div class="bg-blue-500 h-full rounded-full transition-all duration-500" :style="{ width: progress + '%' }"></div>
    </div>
    </div><!-- end padding wrapper -->
  </div>
</template>
