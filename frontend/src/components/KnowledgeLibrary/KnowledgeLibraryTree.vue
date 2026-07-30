<script setup lang="ts">
import { computed, ref } from 'vue'
import { PhArticle, PhBooks, PhMagnifyingGlass, PhSealCheck } from '@phosphor-icons/vue'
import type { FolderTreeNode, Task } from '../../types'
import KnowledgeTreeNode from './KnowledgeTreeNode.vue'

const props = defineProps<{
  tasks: Task[]
  folderTree: FolderTreeNode[]
  selectedTask: Task | null
}>()

const emit = defineEmits<{
  selectTask: [task: Task]
}>()

const keyword = ref('')
const documents = computed(() =>
  props.tasks.filter(task => Boolean((task.summary || '').trim() || (task.transcript || '').trim())),
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
const completedCount = computed(() =>
  documents.value.filter(document => document.status === 'COMPLETED').length,
)
</script>

<template>
  <div class="knowledge-library">
    <header class="library-header">
      <p>藏 书 阁</p>
      <div class="library-counts">
        <span><b>{{ documents.length }}</b> 卷</span>
        <i />
        <span><b>{{ folderTree.length }}</b> 部</span>
        <i />
        <span><b>{{ completedCount }}</b> 已成篇</span>
      </div>
      <div class="search-box">
        <PhMagnifyingGlass :size="15" />
        <input v-model="keyword" placeholder="检索题名、主题或正文">
      </div>
    </header>

    <div v-if="documents.length" class="library-scroll">
      <div class="tree-caption">
        <PhBooks :size="15" weight="duotone" />
        <span>文库目录</span>
        <small>点击篇目进入阅读</small>
      </div>

      <KnowledgeTreeNode
        v-for="node in folderTree"
        :key="node.id"
        :node="node"
        :documents="filteredDocuments"
        :selectedTask="selectedTask"
        :depth="0"
        @select="emit('selectTask', $event)"
      />

      <section v-if="rootDocuments.length" class="unfiled">
        <div class="unfiled-title">
          <PhArticle :size="14" />
          未归档
          <span>{{ rootDocuments.length }}</span>
        </div>
        <button
          v-for="document in rootDocuments"
          :key="document.id"
          type="button"
          :class="['root-document', selectedTask?.id === document.id ? 'selected' : '']"
          @click="emit('selectTask', document)"
        >
          <PhArticle :size="14" weight="duotone" />
          <span>{{ document.title || document.topic || '未命名文档' }}</span>
        </button>
      </section>

      <p v-if="keyword && filteredDocuments.length === 0" class="empty-search">没有找到相合的篇目</p>
      <footer>
        <PhSealCheck :size="14" weight="duotone" />
        在采集台拖拽篇目，即可调整目录归属
      </footer>
    </div>

    <div v-else class="empty-library">
      <div class="empty-mark">學</div>
      <h3>文库尚空</h3>
      <p>从采集台带回第一份材料，转写与提炼完成后便会在此成篇。</p>
    </div>
  </div>
</template>

<style scoped>
.knowledge-library {
  height: 100%;
  color: #342f28;
  background:
    linear-gradient(rgba(122, 101, 72, .025) 1px, transparent 1px),
    #fbf8f0;
  background-size: 100% 28px;
  font-family: "Noto Serif SC", "Songti SC", STSong, serif;
}
.library-header { padding: 18px 16px 14px; border-bottom: 1px solid #e5dac8; background: rgba(251, 248, 240, .94); }
.library-header > p { margin: 0 0 8px; color: #a84735; font-size: 11px; font-weight: 700; letter-spacing: .36em; }
.library-counts { display: flex; align-items: baseline; gap: 8px; color: #7c7366; font-size: 10px; }
.library-counts b { color: #39332b; font: 600 18px/1 ui-monospace, monospace; }
.library-counts i { width: 1px; height: 10px; background: #d7cab8; }
.search-box { display: flex; align-items: center; gap: 7px; margin-top: 13px; padding: 8px 10px; border: 1px solid #ded3c2; background: rgba(255,255,255,.68); color: #9c9182; }
.search-box input { min-width: 0; flex: 1; border: 0; background: transparent; color: #3d372f; font: 12px/1.2 ui-sans-serif, system-ui, sans-serif; outline: none; }
.library-scroll { height: calc(100% - 126px); overflow-y: auto; padding: 11px 8px 20px; }
.tree-caption { display: flex; align-items: center; gap: 6px; padding: 7px 8px 10px; color: #6d6255; font-size: 11px; letter-spacing: .08em; }
.tree-caption small { margin-left: auto; color: #a0988c; font: 9px/1 ui-sans-serif, system-ui, sans-serif; letter-spacing: 0; }
.unfiled { margin-top: 9px; padding-top: 8px; border-top: 1px solid #e7ddcd; }
.unfiled-title { display: flex; align-items: center; gap: 6px; padding: 6px 8px; color: #73695c; font-size: 11px; }
.unfiled-title span { margin-left: auto; font: 10px/1 ui-monospace, monospace; }
.root-document { width: 100%; display: flex; align-items: center; gap: 8px; padding: 9px 10px 9px 21px; color: #746b5f; text-align: left; font-size: 12px; }
.root-document:hover { background: #f5eee3; color: #39332b; }
.root-document.selected { color: #8f3f30; background: #f3e5dc; box-shadow: inset 3px 0 0 #a84735; }
.root-document span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-search, footer { margin: 14px 8px; color: #9a9185; text-align: center; font: 10px/1.6 ui-sans-serif, system-ui, sans-serif; }
footer { display: flex; align-items: center; justify-content: center; gap: 5px; padding-top: 10px; border-top: 1px solid #e7ddcd; }
.empty-library { display: grid; place-items: center; padding: 64px 24px; text-align: center; }
.empty-mark { display: grid; place-items: center; width: 58px; height: 58px; border: 1px solid #b45b49; color: #a84735; font-size: 28px; transform: rotate(-2deg); }
.empty-library h3 { margin: 18px 0 7px; font-size: 17px; letter-spacing: .18em; }
.empty-library p { margin: 0; color: #8b8174; font: 11px/1.8 ui-sans-serif, system-ui, sans-serif; }
</style>
