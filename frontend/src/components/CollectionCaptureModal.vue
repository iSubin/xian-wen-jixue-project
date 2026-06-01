<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  PhBooks,
  PhCheck,
  PhLink,
  PhSpinner,
  PhX,
} from '@phosphor-icons/vue'
import type {
  CollectionJob,
  CollectionPreview,
  CollectionPreviewItem,
  CreateCollectionRequest,
  SummaryMode,
} from '../types'

const props = defineProps<{
  isOpen: boolean
  summaryMode: Exclude<SummaryMode, 'auto'>
  isCreatingCollection: boolean
  previewCollection: (source: string, title?: string) => Promise<CollectionPreview>
  createCollection: (payload: CreateCollectionRequest) => Promise<CollectionJob>
}>()

const emit = defineEmits<{
  close: []
  created: [job: CollectionJob]
}>()

const sourceInput = ref('')
const titleInput = ref('')
const preview = ref<CollectionPreview | null>(null)
const selectedItemKeys = ref<Set<string>>(new Set())
const isPreviewing = ref(false)
const errorMessage = ref('')

const itemKey = (item: CollectionPreviewItem, index: number) =>
  `${index}:${item.provider}:${item.source_url}:${item.part_index ?? 'single'}`

const selectedItems = computed(() => {
  if (!preview.value) return []
  return preview.value.items.filter((item, index) => selectedItemKeys.value.has(itemKey(item, index)))
})

const selectedDuration = computed(() =>
  selectedItems.value.reduce((total, item) => total + Number(item.duration || 0), 0)
)

const selectedDurationLabel = computed(() => {
  const total = selectedDuration.value
  if (!total) return ''
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  if (hours > 0) return `${hours} 小时 ${minutes} 分钟`
  return `${minutes} 分钟`
})

const canCreate = computed(() => Boolean(preview.value && selectedItems.value.length > 0 && !props.isCreatingCollection))

const resetState = () => {
  sourceInput.value = ''
  titleInput.value = ''
  preview.value = null
  selectedItemKeys.value = new Set()
  isPreviewing.value = false
  errorMessage.value = ''
}

const selectAll = () => {
  if (!preview.value) return
  selectedItemKeys.value = new Set(preview.value.items.map((item, index) => itemKey(item, index)))
}

const clearSelection = () => {
  selectedItemKeys.value = new Set()
}

const toggleItem = (item: CollectionPreviewItem, index: number) => {
  const key = itemKey(item, index)
  const next = new Set(selectedItemKeys.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  selectedItemKeys.value = next
}

const handlePreview = async () => {
  const source = sourceInput.value.trim()
  if (!source) {
    errorMessage.value = '请先粘贴合集链接或视频链接列表'
    return
  }

  isPreviewing.value = true
  errorMessage.value = ''
  try {
    const result = await props.previewCollection(source, titleInput.value.trim() || undefined)
    preview.value = result
    if (!titleInput.value.trim()) {
      titleInput.value = result.title
    }
    selectedItemKeys.value = new Set(result.items.map((item, index) => itemKey(item, index)))
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '合集预览失败'
  } finally {
    isPreviewing.value = false
  }
}

const handleCreate = async () => {
  if (!preview.value || selectedItems.value.length === 0) return

  errorMessage.value = ''
  try {
    const payload: CreateCollectionRequest = {
      provider: preview.value.provider,
      source_type: preview.value.source_type,
      source_url: preview.value.source_url,
      title: titleInput.value.trim() || preview.value.title,
      quality: 'audio_only',
      summary_mode: props.summaryMode,
      items: selectedItems.value,
    }
    const job = await props.createCollection(payload)
    emit('created', job)
    resetState()
    emit('close')
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '创建合集任务失败'
  }
}

watch(() => props.isOpen, (isOpen) => {
  if (!isOpen) return
  errorMessage.value = ''
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
        <section class="flex max-h-[90dvh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
          <header class="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                <PhBooks :size="22" weight="fill" />
              </div>
              <div>
                <h2 class="text-base font-semibold text-slate-900">合集采集</h2>
                <p class="text-xs text-slate-500">批量提交视频，完成后聚合成知识文档</p>
              </div>
            </div>
            <button
              class="flex h-9 w-9 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
              @click="emit('close')"
            >
              <PhX :size="20" />
            </button>
          </header>

          <div class="flex-1 overflow-y-auto px-6 py-5">
            <div class="grid gap-4 md:grid-cols-[1fr_260px]">
              <div class="space-y-3">
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-500">粘贴 B 站合集 / 多 P / 视频链接列表</span>
                  <textarea
                    v-model="sourceInput"
                    rows="7"
                    class="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm leading-6 text-slate-700 outline-none transition focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-100"
                    placeholder="可以粘贴一个 B 站多 P 链接，也可以一行一个视频链接。后续这里会扩展小鹅通、投研大师等合集入口。"
                  ></textarea>
                </label>

                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-500">合集名称</span>
                  <input
                    v-model="titleInput"
                    class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none transition focus:border-blue-300 focus:ring-4 focus:ring-blue-100"
                    placeholder="留空则使用解析到的标题"
                  >
                </label>
              </div>

              <aside class="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p class="text-xs font-semibold uppercase tracking-wide text-slate-400">当前策略</p>
                <div class="mt-3 space-y-3 text-sm">
                  <div class="flex items-center justify-between">
                    <span class="text-slate-500">模式</span>
                    <span class="rounded-lg bg-white px-2 py-1 text-xs font-medium text-slate-700">
                      {{ summaryMode === 'agent' ? 'Agent 模式' : '标准模式' }}
                    </span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-slate-500">条目</span>
                    <span class="font-medium text-slate-800">{{ selectedItems.length }} / {{ preview?.total_items || 0 }}</span>
                  </div>
                  <div v-if="selectedDurationLabel" class="flex items-center justify-between">
                    <span class="text-slate-500">总时长</span>
                    <span class="font-medium text-slate-800">{{ selectedDurationLabel }}</span>
                  </div>
                </div>

                <button
                  class="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-3 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="isPreviewing || !sourceInput.trim()"
                  @click="handlePreview"
                >
                  <PhSpinner v-if="isPreviewing" :size="16" class="animate-spin" />
                  <PhLink v-else :size="16" />
                  {{ isPreviewing ? '解析中...' : '解析合集' }}
                </button>
              </aside>
            </div>

            <p v-if="errorMessage" class="mt-4 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">
              {{ errorMessage }}
            </p>

            <div v-if="preview" class="mt-5">
              <div class="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h3 class="text-sm font-semibold text-slate-800">{{ preview.title }}</h3>
                  <p class="text-xs text-slate-500">{{ preview.provider }} · {{ preview.source_type }} · 共 {{ preview.total_items }} 条</p>
                </div>
                <div class="flex items-center gap-2">
                  <button class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-50" @click="selectAll">全选</button>
                  <button class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-100" @click="clearSelection">清空</button>
                </div>
              </div>

              <div class="max-h-[32dvh] space-y-2 overflow-y-auto pr-1">
                <button
                  v-for="(item, index) in preview.items"
                  :key="itemKey(item, index)"
                  type="button"
                  class="flex w-full items-start gap-3 rounded-xl border px-3 py-3 text-left transition"
                  :class="selectedItemKeys.has(itemKey(item, index))
                    ? 'border-blue-300 bg-blue-50/60'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'"
                  @click="toggleItem(item, index)"
                >
                  <span
                    class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border"
                    :class="selectedItemKeys.has(itemKey(item, index))
                      ? 'border-blue-500 bg-blue-500 text-white'
                      : 'border-slate-300 bg-white text-transparent'"
                  >
                    <PhCheck :size="13" weight="bold" />
                  </span>
                  <span class="min-w-0 flex-1">
                    <span class="block truncate text-sm font-medium text-slate-800">{{ item.title }}</span>
                    <span class="mt-0.5 block truncate text-xs text-slate-500">{{ item.source_url }}</span>
                  </span>
                  <span v-if="item.duration" class="shrink-0 rounded-lg bg-white px-2 py-1 text-xs text-slate-500">
                    {{ Math.round(item.duration / 60) }} 分钟
                  </span>
                </button>
              </div>
            </div>
          </div>

          <footer class="flex items-center justify-between gap-3 border-t border-slate-100 bg-slate-50 px-6 py-4">
            <p class="text-xs text-slate-500">第一版会为每个条目创建独立任务，并自动归入同一个文件夹。</p>
            <div class="flex items-center gap-2">
              <button
                class="rounded-xl px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-white hover:text-slate-900"
                @click="emit('close')"
              >
                取消
              </button>
              <button
                class="flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm shadow-blue-100 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="!canCreate"
                @click="handleCreate"
              >
                <PhSpinner v-if="isCreatingCollection" :size="16" class="animate-spin" />
                创建合集任务
              </button>
            </div>
          </footer>
        </section>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.18s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active section,
.modal-leave-active section {
  transition: transform 0.18s ease;
}

.modal-enter-from section,
.modal-leave-to section {
  transform: scale(0.97);
}
</style>
