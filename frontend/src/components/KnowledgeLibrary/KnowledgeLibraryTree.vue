<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  PhArticle,
  PhBooks,
  PhCloudArrowUp,
  PhMagnifyingGlass,
  PhPencilSimple,
  PhPlus,
  PhSpinner,
} from '@phosphor-icons/vue'
import type { Folder, FolderTreeNode, LibraryDocumentPayload, Task } from '../../types'
import { useLibraryDocuments } from '../../composables/useLibraryDocuments'
import KnowledgeTreeNode from './KnowledgeTreeNode.vue'
import LibraryDocumentEditor from './LibraryDocumentEditor.vue'

const props = defineProps<{
  tasks: Task[]
  folders: Folder[]
  folderTree: FolderTreeNode[]
  selectedTask: Task | null
  gitConfigured: boolean
  gitStatus: string
  isSyncingGit: boolean
}>()

const emit = defineEmits<{
  selectTask: [task: Task]
  changed: []
  removed: [documentId: string]
  syncGit: []
}>()

const {
  isSavingDocument,
  isRemovingDocument,
  libraryDocumentError,
  createDocument,
  updateDocument,
  removeDocument,
} = useLibraryDocuments()

const keyword = ref('')
const editorOpen = ref(false)
const editingDocument = ref<Task | null>(null)

const documents = computed(() =>
  props.tasks.filter(task =>
    task.library_visible !== false
    && (
      task.source_type === 'manual'
      || Boolean((task.summary || '').trim() || (task.transcript || '').trim())
    ),
  ),
)

const filteredDocuments = computed(() => {
  const query = keyword.value.trim().toLocaleLowerCase('zh-CN')
  if (!query) return documents.value
  return documents.value.filter(task =>
    [task.title, task.topic, task.summary, task.author_name]
      .some(value => String(value || '').toLocaleLowerCase('zh-CN').includes(query)),
  )
})

const rootDocuments = computed(() =>
  filteredDocuments.value
    .filter(document => !document.folder_id)
    .sort((a, b) => (a.title || '').localeCompare(b.title || '', 'zh-CN')),
)

const rootFolderCount = computed(() => props.folderTree.length)
const pendingSync = computed(() => props.gitStatus === 'pending_sync')
const syncingGit = computed(() => props.isSyncingGit || props.gitStatus === 'syncing')

const openCreate = () => {
  editingDocument.value = null
  editorOpen.value = true
}

const openEdit = (document: Task) => {
  editingDocument.value = document
  editorOpen.value = true
}

const closeEditor = () => {
  if (isSavingDocument.value || isRemovingDocument.value) return
  editorOpen.value = false
}

const saveDocument = async (payload: LibraryDocumentPayload) => {
  const saved = editingDocument.value
    ? await updateDocument(editingDocument.value.id, payload)
    : await createDocument(payload)
  if (!saved) return
  editorOpen.value = false
  emit('changed')
  emit('selectTask', saved)
}

const removeCurrentDocument = async () => {
  if (!editingDocument.value) return
  const documentId = editingDocument.value.id
  if (!await removeDocument(documentId)) return
  editorOpen.value = false
  emit('removed', documentId)
  emit('changed')
}
</script>

<template>
  <div class="knowledge-library">
    <header class="library-header">
      <div class="title-row">
        <div>
          <h2><PhBooks :size="17" weight="duotone" />藏经阁</h2>
          <p>按目录整理和阅读你的知识文档</p>
        </div>
        <button class="new-button" type="button" @click="openCreate">
          <PhPlus :size="14" weight="bold" />
          新建
        </button>
      </div>

      <div class="library-counts">
        <span><b>{{ documents.length }}</b> 篇文档</span>
        <span><b>{{ rootFolderCount }}</b> 个根目录</span>
        <button
          type="button"
          :class="['sync-button', pendingSync ? 'pending' : '']"
          :disabled="!gitConfigured || syncingGit"
          :title="gitConfigured ? '把当前文库快照同步到 Git' : '请先在设置中配置 Git 文库'"
          @click="emit('syncGit')"
        >
          <PhSpinner v-if="syncingGit" :size="13" class="spin" />
          <PhCloudArrowUp v-else :size="13" />
          {{ syncingGit ? '同步中' : pendingSync ? '待同步' : '同步 Git' }}
        </button>
      </div>

      <div class="search-box">
        <PhMagnifyingGlass :size="15" />
        <input v-model="keyword" placeholder="搜索题名、主题或正文">
      </div>
    </header>

    <div v-if="documents.length" class="library-scroll">
      <div class="tree-caption">
        <span>文库目录</span>
        <small>悬停文档可编辑</small>
      </div>

      <KnowledgeTreeNode
        v-for="node in folderTree"
        :key="node.id"
        :node="node"
        :documents="filteredDocuments"
        :selectedTask="selectedTask"
        :depth="0"
        @select="emit('selectTask', $event)"
        @edit="openEdit"
      />

      <section v-if="rootDocuments.length" class="unfiled">
        <div class="unfiled-title">
          <PhArticle :size="14" />
          <span>未归档</span>
          <b>{{ rootDocuments.length }}</b>
        </div>
        <div
          v-for="document in rootDocuments"
          :key="document.id"
          :class="['root-document', selectedTask?.id === document.id ? 'selected' : '']"
        >
          <button type="button" class="document-main" @click="emit('selectTask', document)">
            <PhArticle :size="14" weight="duotone" />
            <span>{{ document.title || document.topic || '未命名文档' }}</span>
          </button>
          <button type="button" class="edit-button" title="编辑文档" @click="openEdit(document)">
            <PhPencilSimple :size="13" />
          </button>
        </div>
      </section>

      <p v-if="keyword && filteredDocuments.length === 0" class="empty-search">没有找到匹配的文档</p>
      <footer>目录和正文修改后，点击“同步 Git”发布最新快照</footer>
    </div>

    <div v-else class="empty-library">
      <div class="empty-mark"><PhBooks :size="27" weight="duotone" /></div>
      <h3>藏经阁还是空的</h3>
      <p>新建一篇手写文档，或从采集台带回第一份材料。</p>
      <button type="button" @click="openCreate"><PhPlus :size="14" />新建文档</button>
    </div>

    <LibraryDocumentEditor
      :show="editorOpen"
      :document="editingDocument"
      :folders="folders"
      :isSaving="isSavingDocument"
      :isRemoving="isRemovingDocument"
      :error="libraryDocumentError"
      @close="closeEditor"
      @save="saveDocument"
      @remove="removeCurrentDocument"
    />
  </div>
</template>

<style scoped>
.knowledge-library { height: 100%; display: flex; flex-direction: column; color: var(--xw-ink); background: var(--xw-surface); font-family: var(--xw-font-ui); }
.library-header { padding: 17px 15px 14px; border-bottom: 1px solid var(--xw-border); background: linear-gradient(180deg, #fff, #fcfdff); }
.title-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.title-row h2 { display: flex; align-items: center; gap: 7px; margin: 0; color: var(--xw-ink); font-size: 14px; font-weight: 700; }
.title-row h2 svg { color: var(--xw-accent); }
.title-row p { margin: 4px 0 0; color: var(--xw-ink-faint); font-size: 10px; }
.new-button { min-height: 32px; display: flex; align-items: center; gap: 5px; padding: 0 10px; border-radius: 9px; color: #fff; background: var(--xw-accent); font-size: 11px; font-weight: 650; box-shadow: 0 5px 12px rgba(37, 99, 235, .16); transition: background .16s ease, box-shadow .16s ease, transform .16s ease; }
.new-button:hover { background: var(--xw-accent-strong); box-shadow: 0 7px 15px rgba(37, 99, 235, .2); }
.new-button:active { transform: translateY(1px); }
.library-counts { min-height: 27px; display: flex; align-items: center; gap: 10px; margin-top: 10px; color: var(--xw-ink-soft); font-size: 10px; }
.library-counts b { color: var(--xw-ink); font-variant-numeric: tabular-nums; }
.sync-button { margin-left: auto; min-height: 28px; display: flex; align-items: center; gap: 5px; padding: 0 8px; border: 1px solid var(--xw-border-strong); border-radius: 8px; color: var(--xw-ink-soft); background: #fff; font-size: 10px; transition: border-color .16s ease, color .16s ease, background .16s ease; }
.sync-button:hover:not(:disabled) { color: var(--xw-accent-strong); border-color: #a9c5f6; background: var(--xw-accent-soft); }
.sync-button.pending { color: var(--xw-accent-strong); border-color: #a9c5f6; background: var(--xw-accent-soft); }
.sync-button:disabled { opacity: .45; cursor: not-allowed; }
.search-box { display: flex; align-items: center; gap: 7px; margin-top: 10px; padding: 8px 10px; border: 1px solid var(--xw-border); border-radius: 10px; background: var(--xw-surface-muted); color: var(--xw-ink-faint); transition: border-color .16s ease, box-shadow .16s ease, background .16s ease; }
.search-box:focus-within { border-color: #9abcf2; box-shadow: 0 0 0 3px rgba(37, 99, 235, .1); background: #fff; }
.search-box input { min-width: 0; flex: 1; border: 0; background: transparent; color: var(--xw-ink); font-size: 11px; outline: none; }
.library-scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 10px 7px 18px; }
.tree-caption { display: flex; align-items: center; padding: 6px 8px 9px; color: var(--xw-ink-soft); font-size: 10px; font-weight: 700; }
.tree-caption small { margin-left: auto; color: var(--xw-ink-faint); font-size: 9px; font-weight: 400; }
.unfiled { margin-top: 8px; padding-top: 7px; border-top: 1px solid var(--xw-border); }
.unfiled-title { display: flex; align-items: center; gap: 6px; padding: 6px 8px; color: var(--xw-ink-soft); font-size: 11px; }
.unfiled-title b { margin-left: auto; color: var(--xw-ink-faint); font: 500 10px/1 ui-monospace, monospace; }
.root-document { min-height: 38px; display: flex; align-items: center; padding: 0 6px 0 18px; color: #64748b; transition: color .16s ease, background .16s ease; }
.root-document:hover { color: var(--xw-ink); background: #f8fafc; }
.root-document.selected { color: var(--xw-accent-strong); background: var(--xw-accent-soft); box-shadow: inset 3px 0 0 #4f8de8; }
.document-main { min-width: 0; flex: 1; min-height: 38px; display: flex; align-items: center; gap: 8px; text-align: left; font-size: 11px; }
.document-main span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.edit-button { width: 27px; height: 27px; display: grid; place-items: center; border-radius: 7px; color: #94a3b8; opacity: 0; transition: opacity .16s ease, color .16s ease, background .16s ease; }
.root-document:hover .edit-button, .root-document.selected .edit-button { opacity: 1; }
.edit-button:hover { color: var(--xw-accent-strong); background: #dbeafe; }
.empty-search, footer { margin: 13px 8px; color: var(--xw-ink-faint); text-align: center; font-size: 9px; line-height: 1.6; }
footer { padding-top: 10px; border-top: 1px solid #eef2f7; }
.empty-library { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 24px; text-align: center; }
.empty-mark { width: 54px; height: 54px; display: grid; place-items: center; border-radius: 16px; color: var(--xw-accent); background: var(--xw-accent-soft); }
.empty-library h3 { margin: 15px 0 6px; color: var(--xw-ink); font-size: 14px; font-weight: 700; }
.empty-library p { margin: 0; color: var(--xw-ink-faint); font-size: 11px; line-height: 1.6; }
.empty-library button { display: flex; align-items: center; gap: 5px; margin-top: 14px; padding: 8px 11px; border-radius: 8px; color: var(--xw-accent-strong); background: var(--xw-accent-soft); font-size: 11px; font-weight: 650; }
.spin { animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
