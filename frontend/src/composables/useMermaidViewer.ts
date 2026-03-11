import { nextTick, onUnmounted, ref, watch, type Ref } from 'vue'

type MermaidViewerModalRef = {
  stage: HTMLElement | null
  viewport: HTMLElement | null
}

const MIN_SCALE = 0.05
const MAX_SCALE = 8
const FIT_PADDING = 64

export function useMermaidViewer(modalRef: Ref<MermaidViewerModalRef | null>) {
  const showMermaidViewer = ref(false)
  const currentMermaidSvg = ref('')
  const currentZoom = ref(1)

  let diagramWidth = 1
  let diagramHeight = 1

  let scale = 1
  let offsetX = 0
  let offsetY = 0

  let isDragging = false
  let isPinching = false
  let lastClientX = 0
  let lastClientY = 0
  let pinchStartDistance = 0
  let pinchStartScale = 1

  const activePointers = new Map<number, { x: number; y: number }>()

  let removeStageListeners: (() => void) | null = null

  const getStage = () => modalRef.value?.stage ?? null
  const getViewport = () => modalRef.value?.viewport ?? null

  const clamp = (value: number, min: number, max: number) => {
    return Math.min(max, Math.max(min, value))
  }

  const getDistance = (p1: { x: number; y: number }, p2: { x: number; y: number }) => {
    const dx = p1.x - p2.x
    const dy = p1.y - p2.y
    return Math.hypot(dx, dy)
  }

  const getFirstTwoPointers = () => {
    const points = Array.from(activePointers.values())
    const p1 = points[0]
    const p2 = points[1]
    if (!p1 || !p2) return null
    return [p1, p2] as const
  }

  const parseNumber = (value: string | null) => {
    if (!value) return NaN
    const parsed = Number.parseFloat(value)
    return Number.isFinite(parsed) ? parsed : NaN
  }

  const updateZoom = (targetScale: number) => {
    scale = clamp(targetScale, MIN_SCALE, MAX_SCALE)
    currentZoom.value = scale
  }

  const applyTransform = () => {
    const viewport = getViewport()
    if (!viewport) return
    viewport.style.transform = `translate3d(${offsetX}px, ${offsetY}px, 0) scale(${scale})`
  }

  const centerAtScale = (targetScale: number) => {
    const stage = getStage()
    if (!stage) return
    const safeScale = Number.isFinite(targetScale) && targetScale > 0 ? targetScale : 1
    updateZoom(safeScale)
    offsetX = (stage.clientWidth - diagramWidth * scale) / 2
    offsetY = (stage.clientHeight - diagramHeight * scale) / 2
    applyTransform()
  }

  const measureDiagramSize = () => {
    const viewport = getViewport()
    const svg = viewport?.querySelector('svg') as SVGSVGElement | null
    if (!svg) return false

    // Remove responsive constraints so the viewer can scale freely.
    svg.style.maxWidth = 'none'
    svg.style.maxHeight = 'none'
    svg.style.width = 'auto'
    svg.style.height = 'auto'

    let measured = false
    const viewBox = svg.viewBox?.baseVal
    if (viewBox && viewBox.width > 0 && viewBox.height > 0) {
      diagramWidth = viewBox.width
      diagramHeight = viewBox.height
      measured = true
    }

    if (!measured) {
      const widthAttr = parseNumber(svg.getAttribute('width'))
      const heightAttr = parseNumber(svg.getAttribute('height'))
      if (widthAttr > 0 && heightAttr > 0) {
        diagramWidth = widthAttr
        diagramHeight = heightAttr
        measured = true
      }
    }

    if (!measured) {
      try {
        const bbox = svg.getBBox()
        if (bbox.width > 0 && bbox.height > 0) {
          diagramWidth = bbox.width
          diagramHeight = bbox.height
          measured = true
        }
      } catch (_error) {
        // Ignore and continue with fallback.
      }
    }

    if (!measured) {
      const rect = svg.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0) {
        diagramWidth = rect.width
        diagramHeight = rect.height
        measured = true
      }
    }

    if (!measured) {
      diagramWidth = 1200
      diagramHeight = 800
    }

    // Important: some Mermaid SVGs use width="100%", which collapses in absolute containers.
    // Force a concrete size baseline so the preview is always visible.
    if (viewport) {
      viewport.style.width = `${diagramWidth}px`
      viewport.style.height = `${diagramHeight}px`
    }
    svg.setAttribute('width', `${diagramWidth}`)
    svg.setAttribute('height', `${diagramHeight}`)
    if (!svg.getAttribute('viewBox')) {
      svg.setAttribute('viewBox', `0 0 ${diagramWidth} ${diagramHeight}`)
    }
    svg.style.width = `${diagramWidth}px`
    svg.style.height = `${diagramHeight}px`
    return true
  }

  const zoomAt = (targetScale: number, stageX: number, stageY: number) => {
    const nextScale = clamp(targetScale, MIN_SCALE, MAX_SCALE)
    if (Math.abs(nextScale - scale) < 0.0001) return

    const contentX = (stageX - offsetX) / scale
    const contentY = (stageY - offsetY) / scale

    updateZoom(nextScale)
    offsetX = stageX - contentX * scale
    offsetY = stageY - contentY * scale
    applyTransform()
  }

  const fitView = () => {
    const stage = getStage()
    if (!stage) return

    const availableWidth = Math.max(1, stage.clientWidth - FIT_PADDING * 2)
    const availableHeight = Math.max(1, stage.clientHeight - FIT_PADDING * 2)
    const fitScale = Math.min(availableWidth / diagramWidth, availableHeight / diagramHeight)
    centerAtScale(fitScale)
  }

  const resetView = () => {
    centerAtScale(1)
  }

  const zoomIn = () => {
    const stage = getStage()
    if (!stage) return
    const centerX = stage.clientWidth / 2
    const centerY = stage.clientHeight / 2
    zoomAt(scale * 1.2, centerX, centerY)
  }

  const zoomOut = () => {
    const stage = getStage()
    if (!stage) return
    const centerX = stage.clientWidth / 2
    const centerY = stage.clientHeight / 2
    zoomAt(scale / 1.2, centerX, centerY)
  }

  const cleanupStageInteraction = () => {
    if (removeStageListeners) {
      removeStageListeners()
      removeStageListeners = null
    }
    isDragging = false
    isPinching = false
    pinchStartDistance = 0
    pinchStartScale = 1
    activePointers.clear()
  }

  const bindStageInteraction = () => {
    const stage = getStage()
    if (!stage) return

    cleanupStageInteraction()
    stage.style.cursor = 'grab'
    stage.style.touchAction = 'none'

    const handlePointerDown = (event: PointerEvent) => {
      if (event.pointerType === 'mouse' && event.button !== 0) return
      event.preventDefault()
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY })
      stage.setPointerCapture(event.pointerId)

      if (activePointers.size === 1) {
        isPinching = false
        isDragging = true
        lastClientX = event.clientX
        lastClientY = event.clientY
        stage.style.cursor = 'grabbing'
        return
      }

      if (activePointers.size >= 2) {
        const pair = getFirstTwoPointers()
        if (!pair) return
        const [p1, p2] = pair
        isDragging = false
        isPinching = true
        pinchStartDistance = Math.max(1, getDistance(p1, p2))
        pinchStartScale = scale
        stage.style.cursor = 'grabbing'
      }
    }

    const handlePointerMove = (event: PointerEvent) => {
      if (!activePointers.has(event.pointerId)) return
      event.preventDefault()
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY })

      if (isPinching && activePointers.size >= 2) {
        const pair = getFirstTwoPointers()
        if (!pair) return
        const [p1, p2] = pair
        const currentDistance = Math.max(1, getDistance(p1, p2))
        const ratio = currentDistance / Math.max(1, pinchStartDistance)
        const rect = stage.getBoundingClientRect()
        const stageX = (p1.x + p2.x) / 2 - rect.left
        const stageY = (p1.y + p2.y) / 2 - rect.top
        zoomAt(pinchStartScale * ratio, stageX, stageY)
        return
      }

      if (!isDragging || activePointers.size !== 1) return
      const deltaX = event.clientX - lastClientX
      const deltaY = event.clientY - lastClientY
      lastClientX = event.clientX
      lastClientY = event.clientY
      offsetX += deltaX
      offsetY += deltaY
      applyTransform()
    }

    const handlePointerUp = (event: PointerEvent) => {
      if (activePointers.has(event.pointerId)) {
        event.preventDefault()
        activePointers.delete(event.pointerId)
      }
      if (stage.hasPointerCapture(event.pointerId)) {
        stage.releasePointerCapture(event.pointerId)
      }

      if (activePointers.size === 0) {
        isDragging = false
        isPinching = false
        pinchStartDistance = 0
        pinchStartScale = scale
        stage.style.cursor = 'grab'
        return
      }

      if (activePointers.size === 1) {
        const remaining = Array.from(activePointers.values())[0]
        if (!remaining) return
        isPinching = false
        isDragging = true
        lastClientX = remaining.x
        lastClientY = remaining.y
        pinchStartDistance = 0
        pinchStartScale = scale
        stage.style.cursor = 'grabbing'
        return
      }

      const pair = getFirstTwoPointers()
      if (!pair) return
      const [p1, p2] = pair
      isDragging = false
      isPinching = true
      pinchStartDistance = Math.max(1, getDistance(p1, p2))
      pinchStartScale = scale
      stage.style.cursor = 'grabbing'
    }

    const handleWheel = (event: WheelEvent) => {
      event.preventDefault()
      const rect = stage.getBoundingClientRect()
      const stageX = event.clientX - rect.left
      const stageY = event.clientY - rect.top
      const wheelFactor = Math.exp(-event.deltaY * 0.0015)
      zoomAt(scale * wheelFactor, stageX, stageY)
    }

    stage.addEventListener('pointerdown', handlePointerDown)
    stage.addEventListener('pointermove', handlePointerMove)
    stage.addEventListener('pointerup', handlePointerUp)
    stage.addEventListener('pointercancel', handlePointerUp)
    stage.addEventListener('pointerleave', handlePointerUp)
    stage.addEventListener('wheel', handleWheel, { passive: false })

    removeStageListeners = () => {
      stage.removeEventListener('pointerdown', handlePointerDown)
      stage.removeEventListener('pointermove', handlePointerMove)
      stage.removeEventListener('pointerup', handlePointerUp)
      stage.removeEventListener('pointercancel', handlePointerUp)
      stage.removeEventListener('pointerleave', handlePointerUp)
      stage.removeEventListener('wheel', handleWheel)
      stage.style.cursor = 'default'
    }
  }

  const handleKeydown = (event: KeyboardEvent) => {
    if (!showMermaidViewer.value) return

    if (event.key === 'Escape') {
      event.preventDefault()
      closeMermaidViewer()
      return
    }

    if (event.key === '+' || event.key === '=') {
      event.preventDefault()
      zoomIn()
      return
    }

    if (event.key === '-' || event.key === '_') {
      event.preventDefault()
      zoomOut()
      return
    }

    if (event.key === '0') {
      event.preventDefault()
      resetView()
      return
    }

    if (event.key.toLowerCase() === 'f') {
      event.preventDefault()
      fitView()
    }
  }

  const initViewer = async () => {
    await nextTick()
    await nextTick()
    const viewport = getViewport()
    const stage = getStage()
    if (!viewport || !stage) return

    measureDiagramSize()
    bindStageInteraction()
    fitView()
  }

  const openMermaidViewer = (source: MouseEvent | HTMLElement) => {
    let targetElement: HTMLElement | null = null

    if (source instanceof MouseEvent) {
      targetElement = source.currentTarget as HTMLElement | null
    } else {
      targetElement = source
    }

    if (!targetElement) return

    const svg = targetElement.querySelector('svg')
    if (!svg) return

    currentMermaidSvg.value = svg.outerHTML
    showMermaidViewer.value = true
  }

  const openSvgMarkup = (svgMarkup: string) => {
    const trimmed = svgMarkup.trim()
    if (!trimmed) return
    currentMermaidSvg.value = trimmed
    showMermaidViewer.value = true
  }

  const closeMermaidViewer = () => {
    showMermaidViewer.value = false
    currentZoom.value = 1
  }

  watch(showMermaidViewer, async (visible) => {
    if (visible) {
      await initViewer()
      window.addEventListener('keydown', handleKeydown)
    } else {
      window.removeEventListener('keydown', handleKeydown)
      cleanupStageInteraction()
    }
  })

  watch(currentMermaidSvg, async () => {
    if (!showMermaidViewer.value) return
    await initViewer()
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
    cleanupStageInteraction()
  })

  return {
    showMermaidViewer,
    currentMermaidSvg,
    currentZoom,
    openMermaidViewer,
    openSvgMarkup,
    closeMermaidViewer,
    resetView,
    fitView,
    zoomIn,
    zoomOut,
  }
}
