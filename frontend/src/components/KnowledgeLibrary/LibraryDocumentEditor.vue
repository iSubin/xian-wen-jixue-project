<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  PhArticle,
  PhFloppyDisk,
  PhFolder,
  PhInfo,
  PhSpinner,
  PhTrash,
  PhX,
} from '@phosphor-icons/vue'
import type { Folder, LibraryDocumentPayload, Task } from '../../types'

const props = defineProps<{
  show: boolean
  document: Task | null
  folders: Folder[]
  isSaving: boolean
  isRemoving: boolean
  error: string
}>()

const emit = defineEmits<{
  close: []
  save: [payload: LibraryDocumentPayload]
  remove: []
}>()

const title = ref('')
const content = ref('')
const folderId = ref<string | null>(null)
const validationError = ref('')
const confirmingRemove = ref(false)

const isEditing = computed(() => Boolean(props.document))

const folderOptions = computed(() => {
  const childrenByParent = new Map<string, Folder[]>()
  props.folders.forEach((folder) => {
    const key = folder.parent_id || ''
    childrenByParent.set(key, [...(childrenByParent.get(key) || []), folder])
  })
  const result: Array<{ id: string; label: string }> = []
  const visit = (parentId: string, depth: number) => {
    const children = (childrenByParent.get(parentId) || [])
      .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
    children.forEach((folder) => {
      result.push({ id: folder.id, label: `${'　'.repeat(depth)}${folder.name}` })
      visit(folder.id, depth + 1)
    })
  }
  visit('', 0)
  return result
})

watch(
  () => [props.show, props.document] as const,
  ([show, document]) => {
    if (!show) return
    title.value = document?.title || document?.topic || ''
    content.value = document?.summary || ''
    folderId.value = document?.folder_id || null
    validationError.value = ''
    confirmingRemove.value = false
  },
  { immediate: true },
)

const submit = () => {
  const normalizedTitle = title.value.trim()
  if (!normalizedTitle) {
    validationError.value = '请填写文档题名'
    return
  }
  validationError.value = ''
  emit('save', {
    title: normalizedTitle,
    content: content.value,
    folder_id: folderId.value || null,
  })
}
</script>

<template>
  <Teleport to="body">
    <Transition name="editor-fade">
      <div v-if="show" class="editor-backdrop" @mousedown.self="emit('close')">
        <section class="editor-panel" role="dialog" aria-modal="true" aria-labelledby="library-editor-title">
          <header>
            <div class="editor-heading">
              <span class="editor-icon"><PhArticle :size="18" weight="duotone" /></span>
              <div>
                <h2 id="library-editor-title">{{ isEditing ? '编辑文档' : '新建文档' }}</h2>
                <p>{{ isEditing ? '修改会进入下一次 Git 文库快照' : '直接写入藏经阁，无需先创建采集任务' }}</p>
              </div>
            </div>
            <button class="icon-button" type="button" title="关闭" @click="emit('close')">
              <PhX :size="18" />
            </button>
          </header>

          <div class="editor-body">
            <label>
              <span>题名</span>
              <input v-model="title" maxlength="300" placeholder="例如：AI 组织协作笔记">
            </label>

            <label>
              <span>目录</span>
              <div class="select-wrap">
                <PhFolder :size="16" />
                <select v-model="folderId">
                  <option :value="null">未归档</option>
                  <option v-for="folder in folderOptions" :key="folder.id" :value="folder.id">
                    {{ folder.label }}
                  </option>
                </select>
              </div>
            </label>

            <label class="content-field">
              <span>Markdown 正文</span>
              <textarea
                v-model="content"
                spellcheck="false"
                placeholder="# 从这里开始写作"
              />
            </label>

            <p v-if="validationError || error" class="form-error">
              {{ validationError || error }}
            </p>

            <div v-if="isEditing" class="preserve-note">
              <PhInfo :size="16" />
              <span>从文库移除只会隐藏这篇文档；原采集任务、转写和素材仍会保留。</span>
            </div>
          </div>

          <footer>
            <div>
              <button
                v-if="isEditing && !confirmingRemove"
                class="danger-link"
                type="button"
                @click="confirmingRemove = true"
              >
                <PhTrash :size="15" />
                从文库移除
              </button>
              <div v-else-if="isEditing" class="remove-confirm">
                <span>确认移除？</span>
                <button type="button" @click="confirmingRemove = false">取消</button>
                <button type="button" :disabled="isRemoving" @click="emit('remove')">
                  {{ isRemoving ? '移除中' : '确认' }}
                </button>
              </div>
            </div>
            <div class="primary-actions">
              <button class="secondary-button" type="button" @click="emit('close')">取消</button>
              <button class="primary-button" type="button" :disabled="isSaving" @click="submit">
                <PhSpinner v-if="isSaving" :size="16" class="spin" />
                <PhFloppyDisk v-else :size="16" />
                {{ isSaving ? '保存中' : '保存文档' }}
              </button>
            </div>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.editor-backdrop { position: fixed; inset: 0; z-index: 80; display: grid; place-items: center; padding: 24px; background: rgba(15, 23, 42, .36); backdrop-filter: blur(3px); }
.editor-panel { width: min(760px, 100%); max-height: min(86dvh, 820px); display: flex; flex-direction: column; overflow: hidden; border: 1px solid #e2e8f0; border-radius: 18px; background: #fff; box-shadow: 0 24px 64px rgba(30, 64, 175, .16); color: #0f172a; }
.editor-panel > header { display: flex; align-items: center; justify-content: space-between; padding: 18px 20px; border-bottom: 1px solid #eef2f7; }
.editor-heading { display: flex; align-items: center; gap: 12px; }
.editor-icon { width: 38px; height: 38px; display: grid; place-items: center; border-radius: 11px; color: #2563eb; background: #eff6ff; }
h2 { margin: 0; font-size: 16px; font-weight: 650; }
.editor-heading p { margin: 3px 0 0; color: #64748b; font-size: 12px; }
.icon-button { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 9px; color: #94a3b8; }
.icon-button:hover { color: #475569; background: #f1f5f9; }
.editor-body { flex: 1; min-height: 0; overflow-y: auto; padding: 20px; display: grid; grid-template-columns: minmax(0, 1fr) 220px; gap: 16px; }
label { display: flex; flex-direction: column; gap: 7px; color: #475569; font-size: 12px; font-weight: 600; }
input, select, textarea { width: 100%; border: 1px solid #dbe3ee; border-radius: 10px; background: #fff; color: #0f172a; font: 13px/1.5 ui-sans-serif, system-ui, sans-serif; outline: none; transition: border-color .18s ease, box-shadow .18s ease; }
input { padding: 9px 11px; }
input:focus, select:focus, textarea:focus { border-color: #60a5fa; box-shadow: 0 0 0 3px rgba(59, 130, 246, .12); }
.select-wrap { position: relative; }
.select-wrap svg { position: absolute; left: 10px; top: 50%; z-index: 1; transform: translateY(-50%); color: #94a3b8; pointer-events: none; }
select { height: 40px; padding: 0 30px 0 34px; appearance: none; }
.content-field { grid-column: 1 / -1; }
textarea { min-height: 360px; resize: vertical; padding: 13px 14px; font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; line-height: 1.65; }
.form-error { grid-column: 1 / -1; margin: 0; padding: 9px 11px; border-radius: 9px; color: #b91c1c; background: #fef2f2; font-size: 12px; }
.preserve-note { grid-column: 1 / -1; display: flex; align-items: center; gap: 7px; color: #64748b; font-size: 11px; }
.editor-panel > footer { display: flex; align-items: center; justify-content: space-between; min-height: 66px; padding: 12px 20px; border-top: 1px solid #eef2f7; background: #f8fafc; }
.danger-link { display: flex; align-items: center; gap: 6px; color: #b91c1c; font-size: 12px; }
.danger-link:hover { color: #991b1b; }
.remove-confirm { display: flex; align-items: center; gap: 8px; color: #64748b; font-size: 12px; }
.remove-confirm button { padding: 5px 8px; border-radius: 7px; color: #475569; background: #e2e8f0; }
.remove-confirm button:last-child { color: #fff; background: #dc2626; }
.primary-actions { display: flex; gap: 8px; }
.secondary-button, .primary-button { min-height: 38px; display: flex; align-items: center; justify-content: center; gap: 7px; padding: 0 14px; border-radius: 9px; font-size: 12px; font-weight: 600; }
.secondary-button { color: #475569; border: 1px solid #dbe3ee; background: #fff; }
.secondary-button:hover { background: #f8fafc; }
.primary-button { color: #fff; background: #2563eb; box-shadow: 0 5px 14px rgba(37, 99, 235, .2); }
.primary-button:hover:not(:disabled) { background: #1d4ed8; }
.primary-button:disabled { opacity: .6; cursor: wait; }
.spin { animation: spin .8s linear infinite; }
.editor-fade-enter-active, .editor-fade-leave-active { transition: opacity .18s ease; }
.editor-fade-enter-from, .editor-fade-leave-to { opacity: 0; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 640px) {
  .editor-backdrop { padding: 0; align-items: end; }
  .editor-panel { width: 100%; max-height: 94dvh; border-radius: 18px 18px 0 0; }
  .editor-body { grid-template-columns: 1fr; }
  .content-field, .form-error, .preserve-note { grid-column: 1; }
  textarea { min-height: 300px; }
  .editor-panel > footer { align-items: flex-end; gap: 10px; }
}
</style>
