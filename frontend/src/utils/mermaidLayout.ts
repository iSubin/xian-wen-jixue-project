/**
 * 统一 Mermaid SVG 布局，避免出现左右留白异常、裁剪和不居中。
 */
export const normalizeMermaidSvgLayout = (host: ParentNode) => {
  const svg = host.querySelector('svg') as SVGSVGElement | null
  if (!svg) return

  // Mermaid 会写入内联尺寸样式，这里覆盖为响应式且不拉伸变形。
  svg.style.setProperty('display', 'block')
  svg.style.setProperty('margin-left', 'auto')
  svg.style.setProperty('margin-right', 'auto')
  svg.style.setProperty('width', 'auto')
  svg.style.setProperty('max-width', '100%')
  svg.style.setProperty('height', 'auto')
  svg.style.setProperty('overflow', 'visible')
  svg.setAttribute('preserveAspectRatio', 'xMidYMin meet')
  svg.removeAttribute('width')
  svg.removeAttribute('height')

  // 只基于 Mermaid 真实图元层计算边界，避免 outer g/defs 导致的错误 bbox。
  const semanticSelectors = [
    'g.root',
    'g.nodes',
    'g.edgePaths',
    'g.edgeLabels',
    'g.clusters',
  ]
  const candidates = semanticSelectors.flatMap((selector) =>
    Array.from(svg.querySelectorAll(selector)) as SVGGraphicsElement[],
  )
  if (!candidates.length) return

  const toPoints = (box: DOMRect) => [
    { x: box.x, y: box.y },
    { x: box.x + box.width, y: box.y },
    { x: box.x, y: box.y + box.height },
    { x: box.x + box.width, y: box.y + box.height },
  ]

  let minX = Number.POSITIVE_INFINITY
  let minY = Number.POSITIVE_INFINITY
  let maxX = Number.NEGATIVE_INFINITY
  let maxY = Number.NEGATIVE_INFINITY

  try {
    for (const el of candidates) {
      if (typeof el.getBBox !== 'function') continue
      const box = el.getBBox()
      if (!Number.isFinite(box.width) || !Number.isFinite(box.height)) continue
      if (box.width <= 0 || box.height <= 0) continue

      const ctm = el.getCTM()
      const points = toPoints(box).map((point) => {
        if (!ctm) return point
        return {
          x: ctm.a * point.x + ctm.c * point.y + ctm.e,
          y: ctm.b * point.x + ctm.d * point.y + ctm.f,
        }
      })

      for (const point of points) {
        minX = Math.min(minX, point.x)
        minY = Math.min(minY, point.y)
        maxX = Math.max(maxX, point.x)
        maxY = Math.max(maxY, point.y)
      }
    }

    if (!Number.isFinite(minX) || !Number.isFinite(minY) || !Number.isFinite(maxX) || !Number.isFinite(maxY)) return
    const tightWidth = maxX - minX
    const tightHeight = maxY - minY
    if (tightWidth <= 0 || tightHeight <= 0) return

    const padding = 16
    const x = Math.floor(minX - padding)
    const y = Math.floor(minY - padding)
    const width = Math.ceil(tightWidth + padding * 2)
    const height = Math.ceil(tightHeight + padding * 2)
    svg.setAttribute('viewBox', `${x} ${y} ${width} ${height}`)
  } catch {
    // 某些浏览器或渲染时机下 getBBox 可能失败，静默回退到默认行为。
  }
}
