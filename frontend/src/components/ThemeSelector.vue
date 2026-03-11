<script setup lang="ts">
/**
 * Markdown 主题选择器组件
 *
 * 功能：
 * 1. 展示所有预设主题
 * 2. 点击切换主题
 * 3. 导入自定义 CSS 主题
 * 4. 导出当前主题为 CSS 文件
 */

import { ref } from 'vue'
import { PhPalette, PhDownload, PhUploadSimple } from '@phosphor-icons/vue'
import { useMarkdownTheme } from '../composables/useMarkdownTheme'
import { useToast } from '../composables/useToast'

const { currentThemeId, themeList, setTheme, importTheme, exportTheme } = useMarkdownTheme()
const { success, error: toastError } = useToast()

// 自定义主题输入
const customCSS = ref('')
const customThemeName = ref('')
const showCustomImport = ref(false)

/**
 * 导入自定义主题
 */
const handleImport = () => {
  if (!customCSS.value.trim()) {
    toastError('请输入 CSS 代码')
    return
  }

  try {
    importTheme(customCSS.value, customThemeName.value || '自定义主题')
    success('主题导入成功')
    customCSS.value = ''
    customThemeName.value = ''
    showCustomImport.value = false
  } catch (e) {
    toastError('主题导入失败：未找到有效的 CSS 变量')
  }
}

/**
 * 导出当前主题为 CSS 文件
 */
const handleExport = () => {
  try {
    const css = exportTheme(currentThemeId.value)

    // 创建下载
    const blob = new Blob([css], { type: 'text/css' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `markdown-theme-${currentThemeId.value}.css`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)

    success('主题已导出')
  } catch (e) {
    toastError('导出失败')
  }
}

/**
 * 切换自定义导入面板
 */
const toggleCustomImport = () => {
  showCustomImport.value = !showCustomImport.value
}

/**
 * 获取主题预览色块颜色
 */
const getThemePreviewColor = (themeId: string) => {
  const theme = themeList.value.find(t => t.id === themeId)
  if (!theme) return '#4f46e5'

  const linkColor = theme.cssVariables['--md-link-color']
  return linkColor || '#4f46e5'
}
</script>

<template>
  <div class="theme-selector p-4 space-y-4">
    <!-- 标题 -->
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold text-slate-700 flex items-center gap-2">
        <PhPalette :size="18" class="text-primary" />
        Markdown 样式主题
      </h3>
      <button
        @click="handleExport"
        class="text-xs text-slate-500 hover:text-primary transition-colors flex items-center gap-1"
        title="导出当前主题"
      >
        <PhDownload :size="14" />
        导出
      </button>
    </div>

    <!-- 预设主题网格 -->
    <div class="grid grid-cols-2 gap-2">
      <button
        v-for="theme in themeList"
        :key="theme.id"
        @click="setTheme(theme.id as any)"
        class="theme-option group relative p-3 rounded-lg border-2 transition-all text-left hover:shadow-sm"
        :class="currentThemeId === theme.id ? 'border-primary bg-primary/5' : 'border-gray-200 hover:border-gray-300'"
      >
        <!-- 主题指示点 -->
        <div
          class="absolute top-2 right-2 w-2 h-2 rounded-full"
          :style="{ backgroundColor: getThemePreviewColor(theme.id) }"
        ></div>

        <div class="font-medium text-sm text-slate-800 pr-4">{{ theme.name }}</div>
        <div class="text-xs text-slate-500 mt-1 line-clamp-2">{{ theme.description }}</div>

        <!-- 选中标记 -->
        <div
          v-if="currentThemeId === theme.id"
          class="absolute top-2 left-2 w-4 h-4 bg-primary rounded-full flex items-center justify-center"
        >
          <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
          </svg>
        </div>
      </button>
    </div>

    <!-- 自定义导入按钮 -->
    <button
      @click="toggleCustomImport"
      class="w-full px-3 py-2 border border-dashed border-gray-300 text-slate-600 text-sm rounded-lg hover:border-primary hover:text-primary transition-colors flex items-center justify-center gap-2"
    >
      <PhUploadSimple :size="16" />
      导入自定义样式
    </button>

    <!-- 自定义导入面板 -->
    <div
      v-if="showCustomImport"
      class="space-y-3 p-3 bg-gray-50 rounded-lg border border-gray-200"
    >
      <div>
        <label class="text-xs font-medium text-slate-700 block mb-1.5">主题名称</label>
        <input
          v-model="customThemeName"
          type="text"
          placeholder="例如：我的自定义主题"
          class="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded focus:border-primary focus:ring-1 focus:ring-primary outline-none"
        />
      </div>

      <div>
        <label class="text-xs font-medium text-slate-700 block mb-1.5">CSS 变量代码</label>
        <textarea
          v-model="customCSS"
          placeholder="粘贴 CSS 变量代码，例如：&#10;--md-text-color: #333333;&#10;--md-heading-color: #111111;&#10;--md-link-color: #007bff;"
          class="w-full px-2.5 py-2 text-xs border border-gray-300 rounded resize-none font-mono focus:border-primary focus:ring-1 focus:ring-primary outline-none"
          rows="6"
        ></textarea>
      </div>

      <div class="flex gap-2">
        <button
          @click="handleImport"
          class="flex-1 px-3 py-1.5 bg-primary text-white text-sm rounded hover:bg-primary/90 transition-colors"
        >
          导入主题
        </button>
        <button
          @click="toggleCustomImport"
          class="px-3 py-1.5 border border-gray-300 text-slate-600 text-sm rounded hover:bg-gray-100 transition-colors"
        >
          取消
        </button>
      </div>
    </div>

    <!-- 说明文字 -->
    <p class="text-xs text-slate-400 text-center">
      主题会同时影响前端显示和一键成图效果
    </p>
  </div>
</template>

<style scoped>
.theme-option {
  position: relative;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
