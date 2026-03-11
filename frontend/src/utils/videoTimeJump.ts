const normalizeHost = (inputHost: string) => {
  return inputHost.trim().toLowerCase().replace(/^www\./, '')
}

export const toTimestampSeconds = (hh: string, mm: string, ss: string): number => {
  return Number(hh) * 3600 + Number(mm) * 60 + Number(ss)
}

export const buildTimestampJumpUrl = (videoUrl: string, seconds: number): string | null => {
  const source = (videoUrl || '').trim()
  if (!source || !Number.isFinite(seconds) || seconds < 0) {
    return null
  }

  try {
    const url = new URL(source)
    const host = normalizeHost(url.hostname)

    if (host === 'youtube.com' || host.endsWith('.youtube.com') || host === 'youtu.be') {
      url.searchParams.set('t', `${Math.floor(seconds)}s`)
      return url.toString()
    }

    if (host === 'bilibili.com' || host.endsWith('.bilibili.com') || host === 'b23.tv') {
      url.searchParams.set('t', String(Math.floor(seconds)))
      return url.toString()
    }

    return null
  } catch {
    return null
  }
}
