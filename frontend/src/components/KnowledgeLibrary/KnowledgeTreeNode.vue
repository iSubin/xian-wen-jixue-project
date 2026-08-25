<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  PhArticle,
  PhCaretDown,
  PhCaretRight,
  PhFolderNotch,
  PhFolderNotchOpen,
  PhPencilSimple,
} from '@phosphor-icons/vue'
import type { FolderTreeNode, Task } from '../../types'

const props = defineProps<{
  node: FolderTreeNode
  documents: Task[]
  selectedTask: Task | null
  depth: number
  searchActive: boolean
}>()

const emit = defineEmits<{
  select: [task: Task]
  edit: [task: Task]
}>()

const expanded = ref(false)
const isOpen = computed(() => expanded.value || props.searchActive)
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

const displayDocumentTitle = (document: Task) => {
  const title = document.title || document.topic || '未命名文档'
  return document.source_type === 'homeway_post'
    ? title.replace(/^\d{4}-\d{2}-\d{2}\s+/, '')
    : title
}
</script>

<template>
  <div class="library-node">
    <button
      type="button"
      class="folder-row"
      :style="{ paddingLeft: `${8 + depth * 15}px` }"
      @click="expanded = !expanded"
    >
      <component :is="isOpen ? PhCaretDown : PhCaretRight" :size="12" class="caret" />
      <component :is="isOpen ? PhFolderNotchOpen : PhFolderNotch" :size="17" weight="duotone" class="folder-icon" />
      <span class="folder-name">{{ node.name }}</span>
      <span class="folder-count">{{ documentCount }}</span>
    </button>

    <div v-if="isOpen" class="folder-children">
      <div
        v-for="document in directDocuments"
        :key="document.id"
        :class="['document-row', selectedTask?.id === document.id ? 'selected' : '']"
        :style="{ paddingLeft: `${36 + depth * 15}px` }"
      >
        <button type="button" class="document-main" @click="emit('select', document)">
          <PhArticle :size="14" weight="duotone" />
          <span>
            <strong>{{ displayDocumentTitle(document) }}</strong>
            <small>{{ document.source_type === 'manual' ? '手写文档' : document.source_type === 'wechat_article' ? '公众号文章' : document.source_type === 'homeway_post' ? '订阅帖子' : '整理文稿' }}</small>
          </span>
        </button>
        <button type="button" class="edit-button" title="编辑文档" @click="emit('edit', document)">
          <PhPencilSimple :size="13" />
        </button>
      </div>

      <KnowledgeTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :documents="documents"
        :selectedTask="selectedTask"
        :depth="depth + 1"
        :searchActive="searchActive"
        @select="emit('select', $event)"
        @edit="emit('edit', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.folder-row { width: 100%; min-height: 36px; display: flex; align-items: center; gap: 6px; border: 0; color: var(--xw-ink-soft); text-align: left; transition: background .16s ease, color .16s ease; }
.folder-row:hover { color: #1e3a8a; background: #f8fafc; }
.caret { color: var(--xw-ink-faint); }
.folder-icon { color: var(--xw-accent); }
.folder-name { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 650 12px/1.4 var(--xw-font-ui); }
.folder-count { margin-right: 8px; color: var(--xw-ink-faint); font: 10px/1 ui-monospace, monospace; }
.document-row { width: 100%; min-height: 42px; display: flex; align-items: center; padding-right: 6px; color: #64748b; transition: background .16s ease, color .16s ease; }
.document-row:hover { color: var(--xw-ink); background: #f8fafc; }
.document-row.selected { color: var(--xw-accent-strong); background: var(--xw-accent-soft); box-shadow: inset 3px 0 0 #4f8de8; }
.document-main { min-width: 0; flex: 1; min-height: 42px; display: flex; align-items: center; gap: 8px; text-align: left; }
.document-main > span { display: flex; min-width: 0; flex-direction: column; gap: 2px; }
.document-main strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 550 12px/1.35 var(--xw-font-ui); }
.document-main small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--xw-ink-faint); font: 9px/1.25 var(--xw-font-ui); }
.edit-button { width: 27px; height: 27px; flex: 0 0 auto; display: grid; place-items: center; border-radius: 7px; color: #94a3b8; opacity: 0; transition: opacity .16s ease, color .16s ease, background .16s ease; }
.document-row:hover .edit-button, .document-row.selected .edit-button { opacity: 1; }
.edit-button:hover { color: var(--xw-accent-strong); background: #dbeafe; }
</style>
