<script setup lang="ts">
import { ref, computed } from 'vue'
import { PhFolderPlus, PhCheckSquare, PhX, PhSparkle, PhWaveform, PhFileText, PhTrash } from '@phosphor-icons/vue'
import type { Task, Folder, FolderNode } from '../../types'
import FolderTreeNode from './FolderTreeNode.vue'
import TaskCard from './TaskCard.vue'
import FolderCreateDialog from './FolderCreateDialog.vue'

const props = defineProps<{
  tasks: Task[]
  folders: Folder[]
  folderTree: FolderNode[]
  selectedTask: Task | null
  multiSelectMode: boolean
  selectedTaskIds: Set<string>
}>()

const emit = defineEmits<{
  selectTask: [task: Task]
  deleteTask: [taskId: string]
  showInfo: [task: Task]
  createFolder: [name: string, parentId: string | null]
  renameFolder: [folderId: string, newName: string]
  deleteFolder: [folderId: string]
  toggleFolder: [folderId: string]
  assignTaskToFolder: [taskId: string, folderId: string | null]
  moveFolder: [folderId: string, newParentId: string | null]
  toggleMultiSelectMode: []
  toggleTaskSelection: [taskId: string]
  selectAllTasks: []
  clearSelection: []
  batchReSummarize: [taskIds: string[]]
  batchReTranscribe: [taskIds: string[]]
  batchDownloadMarkdown: [taskIds: string[]]
  batchDownloadTxt: [taskIds: string[]]
  batchDelete: [taskIds: string[]]
  toggleFolderSelection: [taskIds: string[], selected: boolean]
}>()

const expandedMap = ref<Record<string, boolean>>({})
const showCreateDialog = ref(false)

const tasksByFolder = computed(() => {
  const result = new Map<string, Task[]>()
  for (const folder of props.folders) {
    result.set(folder.id, [])
  }
  for (const task of props.tasks) {
    const fid = task.folder_id
    if (fid && result.has(fid)) {
      result.get(fid)!.push(task)
    }
  }
  return result
})

const rootTasks = computed(() => props.tasks.filter(t => !t.folder_id))

const isExpanded = (folderId: string) => !!expandedMap.value[folderId]

const toggleExpand = (folderId: string) => {
  expandedMap.value[folderId] = !expandedMap.value[folderId]
}

// Auto-expand auto-created folders on mount
for (const folder of props.folders) {
  if (folder.folder_type === 'auto') {
    expandedMap.value[folder.id] = true
  }
}

const handleTaskDragstart = (e: DragEvent, taskId: string) => {
  e.dataTransfer?.setData('text/plain', JSON.stringify({ type: 'task', id: taskId }))
}
</script>

<template>
  <div class="space-y-2">
    <!-- Top toolbar: new folder + multi-select toggle -->
    <div v-if="!showCreateDialog" class="flex items-center justify-between px-2">
      <button
        @click="showCreateDialog = true"
        class="flex items-center gap-1.5 py-1.5 text-xs text-slate-400 hover:text-blue-500 hover:bg-blue-50/50 rounded-lg transition-colors"
      >
        <PhFolderPlus :size="14" />
        新建文件夹
      </button>
      <button
        @click="emit('toggleMultiSelectMode')"
        :class="[
          'flex items-center gap-1.5 py-1.5 px-2 text-xs rounded-lg transition-colors',
          multiSelectMode ? 'text-blue-500 bg-blue-50' : 'text-slate-400 hover:text-blue-500 hover:bg-blue-50/50'
        ]"
      >
        <PhCheckSquare :size="14" />
        {{ multiSelectMode ? '取消多选' : '多选' }}
      </button>
    </div>
    <FolderCreateDialog
      v-if="showCreateDialog"
      :parentId="null"
      @create="(name: string, parentId: string | null) => { emit('createFolder', name, parentId); showCreateDialog = false }"
      @cancel="showCreateDialog = false"
    />

    <!-- Folder tree -->
    <div v-if="folderTree.length > 0" class="space-y-0.5">
      <FolderTreeNode
        v-for="node in folderTree"
        :key="node.id"
        :folder="node"
        :depth="0"
        :tasks="tasksByFolder.get(node.id) || []"
        :selectedTask="selectedTask"
        :isExpanded="isExpanded(node.id)"
        :expandedMap="expandedMap"
        :multiSelectMode="multiSelectMode"
        :selectedTaskIds="selectedTaskIds"
        @toggle="toggleExpand"
        @selectTask="emit('selectTask', $event)"
        @deleteTask="emit('deleteTask', $event)"
        @showInfo="emit('showInfo', $event)"
        @rename="(a: any, b: any) => emit('renameFolder', a, b)"
        @delete="emit('deleteFolder', $event)"
        @dropTask="(a: any, b: any) => emit('assignTaskToFolder', a, b)"
        @dropFolder="(a: any, b: any) => emit('moveFolder', a, b)"
        @toggleTaskSelection="emit('toggleTaskSelection', $event)"
        @toggleFolderSelection="(ids: any, selected: any) => emit('toggleFolderSelection', ids, selected)"
      />
    </div>

    <!-- Root-level (unassigned) tasks -->
    <div v-if="rootTasks.length > 0 || folderTree.length === 0" class="space-y-1.5">
      <div v-if="folderTree.length > 0" class="text-xs font-semibold text-slate-400 uppercase tracking-wider px-2 py-1">
        未分配
      </div>
      <div
        v-for="task in rootTasks"
        :key="task.id"
        draggable="true"
        @dragstart="handleTaskDragstart($event, task.id)"
      >
        <TaskCard
          :task="task"
          :isSelected="selectedTask?.id === task.id"
          :multiSelectMode="multiSelectMode"
          :isChecked="selectedTaskIds.has(task.id)"
          @select="emit('selectTask', task)"
          @delete="emit('deleteTask', task.id)"
          @showInfo="emit('showInfo', task)"
          @toggleSelect="emit('toggleTaskSelection', task.id)"
        />
      </div>
    </div>

    <!-- Empty state -->
    <p v-if="tasks.length === 0" class="text-center text-gray-400 py-8 text-sm">暂无任务记录</p>

    <!-- Batch action bar -->
    <div v-if="multiSelectMode && selectedTaskIds.size > 0" class="sticky bottom-0 bg-white/95 backdrop-blur border-t border-slate-200 p-2 rounded-b-xl space-y-2">
      <div class="text-xs text-slate-500 text-center">已选 {{ selectedTaskIds.size }} 个任务</div>
      <div class="flex items-center justify-center gap-1.5 flex-wrap">
        <button @click="emit('selectAllTasks')" class="text-xs text-slate-400 hover:text-blue-500 px-2 py-1 rounded-lg hover:bg-blue-50/50 transition-colors">全选</button>
        <button @click="emit('batchReSummarize', Array.from(selectedTaskIds))" class="flex items-center gap-1 text-xs text-slate-500 hover:text-blue-500 px-2 py-1 rounded-lg hover:bg-blue-50/50 transition-colors">
          <PhSparkle :size="12" /> 重新总结
        </button>
        <button @click="emit('batchReTranscribe', Array.from(selectedTaskIds))" class="flex items-center gap-1 text-xs text-slate-500 hover:text-blue-500 px-2 py-1 rounded-lg hover:bg-blue-50/50 transition-colors">
          <PhWaveform :size="12" /> 重新转录
        </button>
        <button @click="emit('batchDownloadMarkdown', Array.from(selectedTaskIds))" class="flex items-center gap-1 text-xs text-slate-500 hover:text-blue-500 px-2 py-1 rounded-lg hover:bg-blue-50/50 transition-colors">
          <PhFileText :size="12" /> 下载MD
        </button>
        <button @click="emit('batchDelete', Array.from(selectedTaskIds))" class="flex items-center gap-1 text-xs text-slate-500 hover:text-red-500 px-2 py-1 rounded-lg hover:bg-red-50/50 transition-colors">
          <PhTrash :size="12" /> 删除
        </button>
        <button @click="emit('clearSelection')" class="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-500 px-2 py-1 rounded-lg transition-colors">
          <PhX :size="12" /> 取消
        </button>
      </div>
    </div>
  </div>
</template>