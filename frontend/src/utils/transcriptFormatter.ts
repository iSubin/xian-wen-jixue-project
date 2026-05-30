import OpenCC from 'opencc-js'
import { buildTimestampJumpUrl } from './videoTimeJump'

export interface TranscriptSegment {
  id: string
  timeLabel: string | null
  startSeconds: number | null
  jumpUrl: string | null
  text: string
}

export interface FormattedTranscript {
  hasTimestampedSegments: boolean
  segments: TranscriptSegment[]
  plainText: string
}

export interface TranscriptFormatOptions {
  videoUrl?: string
}

const compactTimestampPattern = /^(\d{2})(\d{2})(\d{2})(.*)$/
const colonTimestampPattern = /^(?:(\d{1,2}):)?([0-5]\d):([0-5]\d)\s*(.*)$/
const toSimplified = OpenCC.Converter({ from: 'hk', to: 'cn' })

const normalizeText = (text: string) => {
  return toSimplified(text || '')
    .replace(/\s+/g, ' ')
    .trim()
}

const formatSeconds = (totalSeconds: number) => {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds))
  const hours = Math.floor(safeSeconds / 3600)
  const minutes = Math.floor((safeSeconds % 3600) / 60)
  const seconds = safeSeconds % 60
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
}

const parseTranscriptLine = (line: string) => {
  const text = (line || '').trim()
  if (!text) return null

  const compactMatch = text.match(compactTimestampPattern)
  if (compactMatch) {
    const hours = Number(compactMatch[1])
    const minutes = Number(compactMatch[2])
    const seconds = Number(compactMatch[3])
    if (minutes < 60 && seconds < 60) {
      const totalSeconds = hours * 3600 + minutes * 60 + seconds
      return {
        startSeconds: totalSeconds,
        timeLabel: formatSeconds(totalSeconds),
        text: normalizeText(compactMatch[4] || ''),
      }
    }
  }

  const colonMatch = text.match(colonTimestampPattern)
  if (colonMatch) {
    const hours = Number(colonMatch[1] || 0)
    const minutes = Number(colonMatch[2])
    const seconds = Number(colonMatch[3])
    const totalSeconds = hours * 3600 + minutes * 60 + seconds
    return {
      startSeconds: totalSeconds,
      timeLabel: formatSeconds(totalSeconds),
      text: normalizeText(colonMatch[4] || ''),
    }
  }

  return {
    startSeconds: null,
    timeLabel: null,
    text: normalizeText(text),
  }
}

const createId = (segment: { startSeconds: number | null }, index: number) => {
  if (segment.startSeconds !== null) {
    return `t-${segment.startSeconds}-${index}`
  }
  return `p-${index}`
}

const buildSegmentJumpUrl = (videoUrl: string | undefined, startSeconds: number | null) => {
  if (startSeconds === null) return null
  return buildTimestampJumpUrl(videoUrl || '', startSeconds)
}

export const formatTranscriptForDisplay = (
  transcript: string,
  options?: TranscriptFormatOptions,
): FormattedTranscript => {
  const segments: TranscriptSegment[] = []

  for (const rawLine of (transcript || '').split(/\r?\n/)) {
    const parsed = parseTranscriptLine(rawLine)
    if (!parsed || !parsed.text) continue

    const previous = segments[segments.length - 1]
    if (parsed.startSeconds === null && previous && previous.startSeconds !== null) {
      previous.text = normalizeText(`${previous.text} ${parsed.text}`)
      continue
    }

    segments.push({
      id: createId(parsed, segments.length),
      timeLabel: parsed.timeLabel,
      startSeconds: parsed.startSeconds,
      jumpUrl: buildSegmentJumpUrl(options?.videoUrl, parsed.startSeconds),
      text: parsed.text,
    })
  }

  const hasTimestampedSegments = segments.some((segment) => segment.startSeconds !== null)
  const plainText = segments
    .map((segment) => {
      if (!hasTimestampedSegments || !segment.timeLabel) return segment.text
      return `[${segment.timeLabel}] ${segment.text}`
    })
    .join('\n')

  return {
    hasTimestampedSegments,
    segments,
    plainText,
  }
}

export const formatTranscriptAsText = (transcript: string) => {
  return formatTranscriptForDisplay(transcript).plainText
}

export const formatTranscriptAsPlainText = (transcript: string) => {
  return formatTranscriptForDisplay(transcript).segments
    .map((segment) => segment.text)
    .filter(Boolean)
    .join('\n')
}
