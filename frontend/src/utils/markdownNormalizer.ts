const INLINE_CODE_BLOCK_MAX_LEN = 48
const INLINE_CODE_TOKEN_RE = /^[A-Za-z0-9_./:@+-]+$/

const extractInlineTokenCandidate = (raw: string): string | null => {
  const compact = (raw || '').replace(/\s+/g, '')
  if (!compact) return null
  if (compact.length > INLINE_CODE_BLOCK_MAX_LEN) return null
  if (!INLINE_CODE_TOKEN_RE.test(compact)) return null
  return compact
}

/**
 * 修复 AI 文本中偶发的“列表内短代码块”误渲染：
 * - 输入通常是 li > pre > code，内容仅为短命令（如 yt-dlp）；
 * - 期望渲染为行内 code，而不是整块 pre。
 */
export const normalizeAccidentalInlineCodeBlocks = (root: ParentNode) => {
  const blocks = Array.from(root.querySelectorAll('li pre')) as HTMLElement[]
  for (const pre of blocks) {
    if (pre.classList.contains('mermaid')) continue
    const code = pre.querySelector(':scope > code') as HTMLElement | null
    if (!code) continue

    const token = extractInlineTokenCandidate(code.textContent || '')
    if (!token) continue

    const li = pre.closest('li')
    if (!li) continue

    // 仅当当前 li 除此 pre 外还有可见文本时，才判定为“误块化”
    const liText = (li.textContent || '').replace(code.textContent || '', '').trim()
    if (!liText) continue

    const inline = document.createElement('code')
    inline.classList.add('ss-inline-code')
    inline.textContent = token
    pre.replaceWith(inline)
  }
}
