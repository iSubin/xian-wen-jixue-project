<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { PhArticle, PhSpinner, PhX } from '@phosphor-icons/vue'
import type { CreateWechatArticleRequest, Folder, SummaryMode, Task } from '../types'

const props = defineProps<{
  isOpen: boolean
  folders: Folder[]
  currentFolderId?: string | null
  summaryMode: Exclude<SummaryMode, 'auto'>
  isCreatingWechatArticle: boolean
  createWechatArticleTask: (payload: CreateWechatArticleRequest) => Promise<Task>
}>()

const emit = defineEmits<{
  close: []
  created: [task: Task]
}>()

const articleUrl = ref('')
const folderId = ref<string>('')
const errorMessage = ref('')

const isWechatUrl = (raw: string) => {
  try {
    return new URL(raw.trim()).hostname.toLowerCase() === 'mp.weixin.qq.com'
  } catch {
    return false
  }
}

const canSubmit = computed(() =>
  articleUrl.value.trim().length > 0
  && isWechatUrl(articleUrl.value)
  && !props.isCreatingWechatArticle
)

const resetState = () => {
  articleUrl.value = ''
  folderId.value = props.currentFolderId || ''
  errorMessage.value = ''
}

const handleSubmit = async () => {
  const url = articleUrl.value.trim()
  if (!isWechatUrl(url)) {
    errorMessage.value = '请输入有效的微信公众号文章链接'
    return
  }

  errorMessage.value = ''
  try {
    const task = await props.createWechatArticleTask({
      url,
      folder_id: folderId.value || null,
      summary_mode: props.summaryMode,
    })
    emit('created', task)
    resetState()
    emit('close')
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '公众号文章采集失败'
  }
}

watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    folderId.value = props.currentFolderId || ''
    errorMessage.value = ''
  }
})
</script>

<template>
  <Teleport to="body">
    <transition name="modal">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[72] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm"
        @click.self="emit('close')"
      >
        <section class="flex w-full max-w-xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
          <header class="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <PhArticle :size="22" weight="fill" />
              </div>
              <div>
                <h2 class="text-base font-semibold text-slate-900">公众号文章</h2>
                <p class="text-xs text-slate-500">采集单篇文章并生成学习笔记</p>
              </div>
            </div>
            <button
              class="flex h-9 w-9 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
              @click="emit('close')"
            >
              <PhX :size="20" />
            </button>
          </header>

          <div class="space-y-4 px-6 py-5">
            <label class="block">
              <span class="mb-1.5 block text-xs font-medium text-slate-500">文章链接</span>
              <input
                v-model="articleUrl"
                class="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100"
                placeholder="https://mp.weixin.qq.com/s/..."
              />
            </label>

            <label class="block">
              <span class="mb-1.5 block text-xs font-medium text-slate-500">保存到文件夹</span>
              <select
                v-model="folderId"
                class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100"
              >
                <option value="">根目录</option>
                <option v-for="folder in folders" :key="folder.id" :value="folder.id">
                  {{ folder.name }}
                </option>
              </select>
            </label>

            <p v-if="errorMessage" class="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600">
              {{ errorMessage }}
            </p>
          </div>

          <footer class="flex items-center justify-end gap-3 border-t border-slate-100 px-6 py-4">
            <button
              class="rounded-xl px-4 py-2 text-sm font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
              @click="emit('close')"
            >
              取消
            </button>
            <button
              class="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              :disabled="!canSubmit"
              @click="handleSubmit"
            >
              <PhSpinner v-if="isCreatingWechatArticle" :size="16" class="animate-spin" />
              采集并生成笔记
            </button>
          </footer>
        </section>
      </div>
    </transition>
  </Teleport>
</template>
