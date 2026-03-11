export const formatDuration = (seconds?: number) => {
  if (!seconds || Number.isNaN(seconds) || seconds <= 0) return '--'
  const total = Math.round(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  if (h > 0) return `${pad(h)}:${pad(m)}:${pad(s)}`
  return `${pad(m)}:${pad(s)}`
}

export const formatTranscriptionDuration = (seconds?: number) => {
  if (!seconds || Number.isNaN(seconds) || seconds <= 0) return '--'
  return `${seconds.toFixed(1)}s`
}

export const formatConversionRatio = (audioSeconds?: number, transcriptionSeconds?: number) => {
  if (
    !audioSeconds
    || Number.isNaN(audioSeconds)
    || audioSeconds <= 0
    || !transcriptionSeconds
    || Number.isNaN(transcriptionSeconds)
    || transcriptionSeconds <= 0
  ) {
    return '--'
  }
  return (audioSeconds / transcriptionSeconds).toFixed(2)
}

export const formatDateTime = (date: string | Date) => {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleString([], {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export const countWords = (markdown: string) => {
  if (!markdown) return 0
  const plain = markdown
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`[^`]*`/g, ' ')
    .replace(/!\[[^\]]*\]\([^)]+\)/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/[>#*_~\-|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  const cjkCount = (plain.match(/[\u4E00-\u9FFF]/g) || []).length
  const latinWords = (plain.replace(/[\u4E00-\u9FFF]/g, ' ').match(/[A-Za-z0-9]+/g) || []).length
  return cjkCount + latinWords
}

export const stripDoubleBracePlaceholders = (text: string) => {
  if (!text) return ''
  return text
    .replace(/\{\{[\s\S]*?\}\}/g, '')
    .replace(/<p>\s*<\/p>/g, '')
    .trim()
}
