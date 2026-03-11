import { replaceTimestampMarksWithChips } from './markdownTimestampChips'

export interface MarkdownPostProcessOptions {
  videoUrl?: string
}

/**
 * 在 Markdown HTML 编译后做统一后处理：
 * - 为行内 code 标记专用类，避免被第三方 prose 默认样式误伤；
 * - 清理行内 code 中异常换行，保持前端与一键成图输出一致；
 * - 将 `(见 HH:MM:SS)` / `（见 HH:MM:SS）` 替换为可点击时间芯片（支持主流视频站跳转）。
 */
export const postProcessCompiledMarkdown = (html: string, options?: MarkdownPostProcessOptions): string => {
  if (!html) {
    return html
  }

  const template = document.createElement('template')
  template.innerHTML = html

  const codeNodes = Array.from(template.content.querySelectorAll('code')) as HTMLElement[]
  for (const code of codeNodes) {
    if (code.closest('pre')) {
      code.classList.add('ss-block-code')
      continue
    }

    code.classList.add('ss-inline-code')
    if (code.textContent) {
      code.textContent = code.textContent.replace(/\s+/g, ' ')
    }
  }

  replaceTimestampMarksWithChips(template.content, { videoUrl: options?.videoUrl })

  return template.innerHTML
}
