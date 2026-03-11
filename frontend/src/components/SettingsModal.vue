<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import {
  PhX,
  PhCpu,
  PhKey,
  PhFlask,
  PhSpinner,
  PhBrain,
  PhMicrophone,
  PhGitBranch,
} from '@phosphor-icons/vue'
import type { LLMProvider, LLMSettings, TranscriptionSettings, SummarizationSettings } from '../types'

const props = defineProps<{
  isOpen: boolean
  llmProviders: LLMProvider[]
  llmSettings: LLMSettings | null
  isUpdatingLlmSettings: boolean
  isTestingLlm: boolean
  transcriptionSettings: TranscriptionSettings | null
  isUpdatingTranscriptionSettings: boolean
  summarizationSettings: SummarizationSettings | null
  isUpdatingSummarizationSettings: boolean
}>()

const emit = defineEmits<{
  close: []
  updateLlmSettings: [payload: {
    provider: string
    base_url?: string
    api_key?: string
    model_id?: string
    temperature?: number
  }]
  testLlm: []
  updateTranscriptionSettings: [payload: {
    device?: 'cpu' | 'cuda'
    enable_bilibili_subtitle_fetch?: boolean
    bilibili_sessdata?: string
    clear_bilibili_sessdata?: boolean
  }]
  updateSummarizationSettings: [payload: {
    chunk_target_duration_sec?: number
    chunk_min_duration_sec?: number
    chunk_max_duration_sec?: number
    boundary_jump_sec?: number
    auto_chunk_min_audio_duration_sec?: number
    auto_chunk_min_transcript_lines?: number
    max_agent_value_chars?: number
    fallback_to_standard_on_agent_error?: boolean
  }]
}>()

const settingsTab = ref<'llm' | 'transcription' | 'summarization'>('llm')

// LLM 设置
const llmProvider = ref('')
const llmBaseUrl = ref('')
const llmModelId = ref('')
const llmTemperature = ref(0.7)
const llmApiKey = ref('')

// 转录设置
const transcriptionDevice = ref<'cpu' | 'cuda'>('cpu')
const enableBilibiliSubtitleFetch = ref(true)
const globalBilibiliSessdataInput = ref('')

// Agent 设置
const chunkTargetDurationSec = ref(20)
const chunkMinDurationSec = ref(10)
const chunkMaxDurationSec = ref(30)
const boundaryJumpSec = ref(10)
const autoChunkMinAudioDurationSec = ref(40)
const autoChunkMinTranscriptLines = ref(1800)
const maxAgentValueChars = ref(500)
const fallbackToStandardOnAgentError = ref(true)

const secondsToMinutes = (seconds: number) => {
  return Math.round((Number(seconds || 0) / 60) * 10) / 10
}

const minutesToSeconds = (minutes: number) => {
  return Math.round(Number(minutes || 0) * 60)
}

const bilibiliCookieSourceLabel = computed(() => {
  const source = props.transcriptionSettings?.bilibili_cookie_source || 'none'
  if (source === 'env') return '环境变量'
  if (source === 'config') return '配置文件'
  return '未设置'
})

watch(() => props.llmSettings, (settings) => {
  if (settings) {
    llmProvider.value = settings.provider || ''
    llmBaseUrl.value = settings.base_url || ''
    llmModelId.value = settings.model_id || ''
    llmTemperature.value = settings.temperature ?? 0.7
    llmApiKey.value = ''
  }
}, { immediate: true })

watch(() => props.transcriptionSettings, (settings) => {
  if (settings) {
    transcriptionDevice.value = settings.device || 'cpu'
    enableBilibiliSubtitleFetch.value = settings.enable_bilibili_subtitle_fetch ?? true
  }
}, { immediate: true })

watch(() => props.summarizationSettings, (settings) => {
  if (settings) {
    chunkTargetDurationSec.value = secondsToMinutes(settings.chunk_target_duration_sec)
    chunkMinDurationSec.value = secondsToMinutes(settings.chunk_min_duration_sec)
    chunkMaxDurationSec.value = secondsToMinutes(settings.chunk_max_duration_sec)
    boundaryJumpSec.value = settings.boundary_jump_sec
    autoChunkMinAudioDurationSec.value = secondsToMinutes(settings.auto_chunk_min_audio_duration_sec)
    autoChunkMinTranscriptLines.value = settings.auto_chunk_min_transcript_lines
    maxAgentValueChars.value = settings.max_agent_value_chars
    fallbackToStandardOnAgentError.value = settings.fallback_to_standard_on_agent_error
  }
}, { immediate: true })

const handleProviderPresetChange = () => {
  const provider = props.llmProviders.find(p => p.id === llmProvider.value)
  if (provider) {
    llmBaseUrl.value = provider.default_base_url || ''
    llmModelId.value = provider.default_model_id || ''
  }
}

const handleSaveLlmSettings = () => {
  const payload: {
    provider: string
    base_url?: string
    api_key?: string
    model_id?: string
    temperature?: number
  } = {
    provider: llmProvider.value,
    base_url: llmBaseUrl.value.trim(),
    model_id: llmModelId.value.trim(),
    temperature: llmTemperature.value,
  }

  if (llmApiKey.value.trim()) {
    payload.api_key = llmApiKey.value.trim()
  }

  emit('updateLlmSettings', payload)
  llmApiKey.value = ''
}

const handleSaveTranscriptionSettings = () => {
  const payload: {
    device?: 'cpu' | 'cuda'
    enable_bilibili_subtitle_fetch?: boolean
    bilibili_sessdata?: string
  } = {
    device: transcriptionDevice.value,
    enable_bilibili_subtitle_fetch: enableBilibiliSubtitleFetch.value
  }

  const cookie = globalBilibiliSessdataInput.value.trim()
  if (cookie) {
    payload.bilibili_sessdata = cookie
  }

  emit('updateTranscriptionSettings', payload)
  globalBilibiliSessdataInput.value = ''
}

const clearGlobalBilibiliSessdata = () => {
  emit('updateTranscriptionSettings', { clear_bilibili_sessdata: true })
}

const handleSaveSummarizationSettings = () => {
  emit('updateSummarizationSettings', {
    chunk_target_duration_sec: minutesToSeconds(chunkTargetDurationSec.value),
    chunk_min_duration_sec: minutesToSeconds(chunkMinDurationSec.value),
    chunk_max_duration_sec: minutesToSeconds(chunkMaxDurationSec.value),
    boundary_jump_sec: boundaryJumpSec.value,
    auto_chunk_min_audio_duration_sec: minutesToSeconds(autoChunkMinAudioDurationSec.value),
    auto_chunk_min_transcript_lines: autoChunkMinTranscriptLines.value,
    max_agent_value_chars: Math.max(100, Number(maxAgentValueChars.value || 0)),
    fallback_to_standard_on_agent_error: fallbackToStandardOnAgentError.value,
  })
}
</script>

<template>
  <!-- 遮罩层 -->
  <Transition name="modal-fade">
    <div
      v-if="isOpen"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex flex-col items-center justify-center p-4 gap-4"
      @click.self="emit('close')"
    >
      <!-- 弹窗主体 -->
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-4xl h-[85vh] flex flex-col md:flex-row overflow-hidden">
        <!-- 左侧导航栏 (桌面端) / 顶部导航 (移动端) -->
        <div class="md:w-48 shrink-0 bg-slate-50 border-b md:border-b-0 md:border-r border-slate-200 flex md:flex-col py-3 md:py-6 overflow-x-auto md:overflow-x-visible">
          <div class="hidden md:block px-4 mb-6">
            <h2 class="text-lg font-semibold text-slate-800">系统设置</h2>
          </div>

          <nav class="flex md:flex-col flex-1 px-3 gap-1 md:space-y-1 min-w-max md:min-w-0">
            <button
              @click="settingsTab = 'llm'"
              :class="[
                'flex items-center gap-2 md:gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap',
                settingsTab === 'llm'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-slate-600 hover:bg-white/50 hover:text-slate-800'
              ]"
            >
              <PhBrain :size="18" :weight="settingsTab === 'llm' ? 'fill' : 'regular'" />
              <span>LLM 配置</span>
            </button>

            <button
              @click="settingsTab = 'transcription'"
              :class="[
                'flex items-center gap-2 md:gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap',
                settingsTab === 'transcription'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-slate-600 hover:bg-white/50 hover:text-slate-800'
              ]"
            >
              <PhMicrophone :size="18" :weight="settingsTab === 'transcription' ? 'fill' : 'regular'" />
              <span>转录设置</span>
            </button>

            <button
              @click="settingsTab = 'summarization'"
              :class="[
                'flex items-center gap-2 md:gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap',
                settingsTab === 'summarization'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-slate-600 hover:bg-white/50 hover:text-slate-800'
              ]"
            >
              <PhGitBranch :size="18" :weight="settingsTab === 'summarization' ? 'fill' : 'regular'" />
              <span>Agent 设置</span>
            </button>
          </nav>

          <!-- 关闭按钮 (桌面端) -->
          <div class="hidden md:block px-3 pt-4 border-t border-slate-200">
            <button
              @click="emit('close')"
              class="w-full flex items-center justify-center gap-2 px-3 py-2.5 text-slate-600 hover:bg-white/50 hover:text-slate-800 rounded-lg text-sm font-medium transition-colors"
            >
              <PhX :size="18" />
              <span>关闭</span>
            </button>
          </div>
        </div>

        <!-- 右侧内容区 -->
        <div class="flex-1 flex flex-col min-w-0 min-h-0">
          <!-- 内容区 -->
          <div class="flex-1 overflow-y-auto px-4 md:px-6 py-4 md:py-6 custom-scrollbar min-h-0">
            <!-- LLM 设置 -->
            <div v-if="settingsTab === 'llm'" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">LLM 供应商</label>
              <div class="relative">
                <PhCpu :size="18" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <select
                  v-model="llmProvider"
                  :disabled="isTestingLlm || isUpdatingLlmSettings"
                  class="w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  @change="handleProviderPresetChange"
                >
                  <option value="" disabled>选择 LLM 供应商</option>
                  <option v-for="provider in llmProviders" :key="provider.id" :value="provider.id">
                    {{ provider.label }}
                  </option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">Base URL</label>
              <input
                v-model="llmBaseUrl"
                type="text"
                placeholder="https://api.example.com/v1"
                :disabled="isTestingLlm || isUpdatingLlmSettings"
                class="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">模型 ID</label>
              <input
                v-model="llmModelId"
                type="text"
                placeholder="gpt-4"
                :disabled="isTestingLlm || isUpdatingLlmSettings"
                class="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">Temperature ({{ llmTemperature }})</label>
              <input
                v-model.number="llmTemperature"
                type="range"
                min="0"
                max="2"
                step="0.1"
                :disabled="isTestingLlm || isUpdatingLlmSettings"
                class="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
              <p class="text-xs text-slate-500 mt-1">控制输出的随机性，0 = 确定性，2 = 最随机</p>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">API Key</label>
              <div class="relative">
                <PhKey :size="18" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  v-model="llmApiKey"
                  type="password"
                  placeholder="sk-..."
                  :disabled="isTestingLlm || isUpdatingLlmSettings"
                  class="w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
              </div>
              <p v-if="llmSettings?.has_api_key" class="text-xs text-emerald-600 mt-1">
                ✓ 已配置 API Key ({{ llmSettings.api_key_hint }})
              </p>
            </div>

            <div class="flex gap-3 pt-2">
              <button
                @click="handleSaveLlmSettings"
                :disabled="isTestingLlm || isUpdatingLlmSettings"
                class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <PhSpinner v-if="isUpdatingLlmSettings" :size="16" class="animate-spin" />
                <span>{{ isUpdatingLlmSettings ? '保存中...' : '保存配置' }}</span>
              </button>
              <button
                @click="emit('testLlm')"
                :disabled="isTestingLlm || isUpdatingLlmSettings"
                class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <PhFlask :size="16" />
                <span>{{ isTestingLlm ? '测试中...' : '测试连接' }}</span>
              </button>
            </div>
          </div>

          <!-- 转录设置 -->
          <div v-if="settingsTab === 'transcription'" class="space-y-4">
            <div v-if="transcriptionSettings" class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
              <div class="flex items-center justify-between gap-2 mb-2">
                <p class="text-sm font-medium text-slate-700">CUDA 状态</p>
                <span
                  :class="[
                    'text-xs px-2 py-0.5 rounded-full border',
                    transcriptionSettings.cuda_available
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      : 'border-amber-200 bg-amber-50 text-amber-700'
                  ]"
                >
                  {{ transcriptionSettings.cuda_available ? '可用' : '不可用' }}
                </span>
              </div>
              <p class="text-xs text-slate-600">
                {{ transcriptionSettings.cuda_message }}
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">计算设备</label>
              <div class="grid grid-cols-2 gap-3">
                <button
                  @click="transcriptionDevice = 'cpu'"
                  :class="[
                    'px-4 py-3 rounded-xl border-2 text-left transition-all',
                    transcriptionDevice === 'cpu'
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                  ]"
                >
                  <div class="font-medium">CPU</div>
                  <div class="text-xs text-slate-500 mt-0.5">通用处理器</div>
                </button>
                <button
                  @click="transcriptionDevice = 'cuda'"
                  :class="[
                    'px-4 py-3 rounded-xl border-2 text-left transition-all',
                    transcriptionDevice === 'cuda'
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                  ]"
                  :disabled="!transcriptionSettings?.cuda_available"
                >
                  <div class="font-medium">CUDA</div>
                  <div class="text-xs text-slate-500 mt-0.5">NVIDIA GPU 加速</div>
                </button>
              </div>
            </div>

            <!-- B站字幕提取 -->
            <div class="flex items-center justify-between gap-3 px-4 py-3 rounded-xl border border-slate-200 bg-slate-50">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-slate-700">优先使用 B 站字幕</p>
                <p class="text-xs text-slate-500 mt-0.5">
                  仅对 B 站链接生效；未获取到字幕时自动回退到下载+ASR
                </p>
              </div>
              <button
                @click="enableBilibiliSubtitleFetch = !enableBilibiliSubtitleFetch"
                :class="[
                  'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                  enableBilibiliSubtitleFetch ? 'bg-blue-500' : 'bg-slate-300'
                ]"
                role="switch"
                :aria-checked="enableBilibiliSubtitleFetch"
              >
                <span
                  :class="[
                    'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                    enableBilibiliSubtitleFetch ? 'translate-x-5' : 'translate-x-0'
                  ]"
                ></span>
              </button>
            </div>

            <!-- B站 SESSDATA -->
            <div class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 space-y-3">
              <div class="flex items-center justify-between gap-2">
                <p class="text-sm font-medium text-slate-700">全局 B 站 SESSDATA</p>
                <span class="text-xs px-2 py-0.5 rounded-full border border-slate-300 bg-white text-slate-600">
                  来源: {{ bilibiliCookieSourceLabel }}
                </span>
              </div>
              <p class="text-xs text-slate-500">
                当前: {{ transcriptionSettings?.bilibili_sessdata_masked || '未设置' }}
              </p>
              <div class="relative">
                <PhKey :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  v-model="globalBilibiliSessdataInput"
                  type="password"
                  placeholder="输入后保存到本机配置"
                  class="w-full pl-10 pr-3 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                >
              </div>
              <button
                @click="clearGlobalBilibiliSessdata"
                :disabled="isUpdatingTranscriptionSettings || !transcriptionSettings?.has_bilibili_sessdata"
                class="w-full bg-white hover:bg-slate-50 text-slate-600 py-2 rounded-xl text-xs font-medium border border-slate-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                清空已保存 Cookie
              </button>
            </div>

            <button
              @click="handleSaveTranscriptionSettings"
              :disabled="isUpdatingTranscriptionSettings"
              class="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PhSpinner v-if="isUpdatingTranscriptionSettings" :size="16" class="animate-spin" />
              <span>{{ isUpdatingTranscriptionSettings ? '保存中...' : '保存设置' }}</span>
            </button>
          </div>

          <!-- Agent 设置 -->
          <div v-if="settingsTab === 'summarization'" class="space-y-4">
            <div class="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3">
              <p class="text-sm font-semibold text-slate-800">Agent 分块怎么调</p>
              <p class="mt-1 text-xs text-slate-600 leading-relaxed">
                长视频会先切成几段再总结。先调"每块目标时长"，推荐 15~25 分钟。
              </p>
            </div>

            <div class="space-y-3">
              <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">核心参数</p>
              <div class="grid grid-cols-3 gap-3">
                <div>
                  <label class="block text-xs text-slate-600 mb-1.5">每块目标时长(分钟)</label>
                  <input
                    v-model.number="chunkTargetDurationSec"
                    type="number"
                    min="0.5"
                    step="0.5"
                    class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  >
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1.5">每块最短(分钟)</label>
                  <input
                    v-model.number="chunkMinDurationSec"
                    type="number"
                    min="0.5"
                    step="0.5"
                    class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  >
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1.5">每块最长(分钟)</label>
                  <input
                    v-model.number="chunkMaxDurationSec"
                    type="number"
                    min="0.5"
                    step="0.5"
                    class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  >
                </div>
              </div>
            </div>

            <div class="space-y-3">
              <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">自动分块触发</p>
              <p class="text-xs text-slate-500">满足任一条件，就会自动启用 Agent 分块。</p>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs text-slate-600 mb-1.5">音频时长达到(分钟)</label>
                  <input
                    v-model.number="autoChunkMinAudioDurationSec"
                    type="number"
                    min="5"
                    step="0.5"
                    class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  >
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1.5">转录行数达到(行)</label>
                  <input
                    v-model.number="autoChunkMinTranscriptLines"
                    type="number"
                    min="100"
                    step="50"
                    class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  >
                </div>
              </div>
            </div>

            <div class="space-y-3">
              <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">高级参数(一般不用改)</p>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs text-slate-600 mb-1.5">分块边界容错(秒)</label>
                  <input
                    v-model.number="boundaryJumpSec"
                    type="number"
                    min="1"
                    step="1"
                    class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  >
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1.5">前文摘要引用上限(字)</label>
                  <input
                    v-model.number="maxAgentValueChars"
                    type="number"
                    min="100"
                    step="50"
                    class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  >
                </div>
              </div>
            </div>

            <div class="flex items-center justify-between gap-3 px-4 py-3 rounded-xl border border-slate-200 bg-slate-50">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-slate-700">Agent 失败自动回退标准模式</p>
                <p class="text-xs text-slate-500 mt-0.5">
                  开启后遇到分块异常会自动降级，保证任务尽量产出结果。
                </p>
              </div>
              <button
                @click="fallbackToStandardOnAgentError = !fallbackToStandardOnAgentError"
                :class="[
                  'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                  fallbackToStandardOnAgentError ? 'bg-blue-500' : 'bg-slate-300'
                ]"
                role="switch"
                :aria-checked="fallbackToStandardOnAgentError"
              >
                <span
                  :class="[
                    'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                    fallbackToStandardOnAgentError ? 'translate-x-5' : 'translate-x-0'
                  ]"
                ></span>
              </button>
            </div>

            <button
              @click="handleSaveSummarizationSettings"
              :disabled="isUpdatingSummarizationSettings"
              class="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PhSpinner v-if="isUpdatingSummarizationSettings" :size="16" class="animate-spin" />
              <span>{{ isUpdatingSummarizationSettings ? '保存中...' : '保存设置' }}</span>
            </button>
          </div>
          </div>
        </div>
      </div>

      <!-- 移动端底部退出按钮 -->
      <button
        @click="emit('close')"
        class="md:hidden flex items-center justify-center gap-2 px-6 py-3 text-white text-sm font-medium transition-opacity hover:opacity-80"
      >
        <PhX :size="20" />
        <span>关闭</span>
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 200ms ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active > div,
.modal-fade-leave-active > div {
  transition: transform 200ms ease, opacity 200ms ease;
}

.modal-fade-enter-from > div,
.modal-fade-leave-to > div {
  transform: scale(0.95);
  opacity: 0;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

input[type="range"]::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
}

input[type="range"]::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: none;
}
</style>
