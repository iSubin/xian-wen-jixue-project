<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  PhArticle,
  PhCaretDown,
  PhCaretRight,
  PhFolderNotch,
  PhFolderNotchOpen,
} from '@phosphor-icons/vue'
import type { FolderTreeNode, Task } from '../../types'

const props = defineProps<{
  node: FolderTreeNode
  documents: Task[]
  selectedTask: Task | null
  depth: number
}>()

const emit = defineEmits<{
  select: [task: Task]
}>()

const expanded = ref(true)
const directDocuments = computed(() =>
  props.documents
    .filter(document => document.folder_id === props.node.id)
    .sort((a, b) => (a.title || '').localeCompare(b.title || '', 'zh-CN')),
)

const descendantFolderIds = (node: FolderTreeNode): string[] => [
  node.id,
  ...node.children.flatMap(descendantFolderIds),
]

const documentCount = computed(() => {
  const ids = new Set(descendantFolderIds(props.node))
  return props.documents.filter(document => document.folder_id && ids.has(document.folder_id)).length
})
</script>

<template>
  <div class="library-node">
    <button
      type="button"
      class="folder-row"
      :style="{ paddingLeft: `${8 + depth * 15}px` }"
      @click="expanded = !expanded"
    >
      <component :is="expanded ? PhCaretDown : PhCaretRight" :size="12" class="caret" />
      <component :is="expanded ? PhFolderNotchOpen : PhFolderNotch" :size="17" weight="duotone" class="folder-icon" />
      <span class="folder-name">{{ node.name }}</span>
      <span class="folder-count">{{ documentCount }}</span>
    </button>

    <div v-if="expanded" class="folder-children">
      <button
        v-for="document in directDocuments"
        :key="document.id"
        type="button"
        :class="['document-row', selectedTask?.id === document.id ? 'selected' : '']"
        :style="{ paddingLeft: `${36 + depth * 15}px` }"
        @click="emit('select', document)"
      >
        <PhArticle :size="14" weight="duotone" />
        <span>
          <strong>{{ document.title || document.topic || '未命名文档' }}</strong>
          <small>{{ document.topic || (document.source_type === 'wechat_article' ? '公众号文章' : '知识文稿') }}</small>
        </span>
      </button>

      <KnowledgeTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :documents="documents"
        :selectedTask="selectedTask"
        :depth="depth + 1"
        @select="emit('select', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.folder-row, .document-row { width: 100%; display: flex; align-items: center; border: 0; text-align: left; }
.folder-row { min-height: 34px; gap: 6px; color: #514a40; transition: background .16s ease; }
.folder-row:hover { background: rgba(155, 75, 57, .06); }
.caret { color: #94897a; }
.folder-icon { color: #9c6b35; }
.folder-name { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 600 12px/1.4 "Noto Serif SC", "Songti SC", serif; letter-spacing: .04em; }
.folder-count { margin-right: 8px; color: #9a9185; font: 10px/1 ui-monospace, monospace; }
.document-row { min-height: 42px; gap: 8px; padding-right: 8px; color: #746b5f; transition: background .16s ease, color .16s ease; }
.document-row:hover { color: #363029; background: #f5eee3; }
.document-row.selected { color: #8f3f30; background: #f3e5dc; box-shadow: inset 3px 0 0 #a84735; }
.document-row > span { display: flex; min-width: 0; flex-direction: column; gap: 2px; }
.document-row strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 500 12px/1.35 "Noto Serif SC", "Songti SC", serif; }
.document-row small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #9a9185; font: 9px/1.25 ui-sans-serif, system-ui, sans-serif; }
</style>
