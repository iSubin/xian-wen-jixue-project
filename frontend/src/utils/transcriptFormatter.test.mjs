import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { pathToFileURL } from 'node:url'
import { build } from 'esbuild'

const outfile = new URL('../../node_modules/.tmp/transcriptFormatter.test.mjs', import.meta.url)
await mkdir(new URL('../../node_modules/.tmp/', import.meta.url), { recursive: true })

await build({
  entryPoints: [new URL('./transcriptFormatter.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'esm',
  outfile: outfile.pathname,
})

const {
  formatTranscriptForDisplay,
  formatTranscriptAsText,
  formatTranscriptAsPlainText,
} = await import(`${pathToFileURL(outfile.pathname).href}?t=${Date.now()}`)

const transcript = [
  '000000經過昨天市場大幅度下跌以後',
  '000010創業板今天還是比較強',
  '這一行是上一句的補充',
  '000125科創板頂部形態相對明顯',
].join('\n')

const formatted = formatTranscriptForDisplay(transcript)

assert.equal(formatted.hasTimestampedSegments, true)
assert.equal(formatted.segments.length, 3)
assert.equal(formatted.segments[0].timeLabel, '00:00:00')
assert.equal(formatted.segments[1].timeLabel, '00:00:10')
assert.equal(formatted.segments[2].timeLabel, '00:01:25')
assert.equal(formatted.segments[0].text, '经过昨天市场大幅度下跌以后')
assert.equal(formatted.segments[1].text, '创业板今天还是比较强 这一行是上一句的补充')
assert.equal(formatted.plainText.includes('經過'), false)
assert.equal(formatted.plainText.includes('经过'), true)
assert.equal(formatted.segments[1].jumpUrl, null)

const linked = formatTranscriptForDisplay(
  transcript,
  { videoUrl: 'https://www.bilibili.com/video/BV1C7Gt6mEAw/?spm_id_from=333.40164.0.0' },
)
assert.equal(new URL(linked.segments[1].jumpUrl).searchParams.get('t'), '10')
assert.equal(linked.segments[1].jumpUrl.includes('BV1C7Gt6mEAw'), true)

const exported = formatTranscriptAsText(transcript)
assert.equal(exported.split('\n')[0], '[00:00:00] 经过昨天市场大幅度下跌以后')
assert.equal(exported.split('\n')[1], '[00:00:10] 创业板今天还是比较强 这一行是上一句的补充')

const plainExported = formatTranscriptAsPlainText(transcript)
assert.equal(plainExported.split('\n')[0], '经过昨天市场大幅度下跌以后')
assert.equal(plainExported.split('\n')[1], '创业板今天还是比较强 这一行是上一句的补充')
assert.equal(plainExported.includes('[00:00:00]'), false)
assert.equal(plainExported.includes('000010'), false)
assert.equal(plainExported.includes('經過'), false)

const plain = formatTranscriptForDisplay('沒有時間戳的原文\n第二段')
assert.equal(plain.hasTimestampedSegments, false)
assert.equal(plain.segments[0].text, '没有时间戳的原文')
assert.equal(plain.segments[1].text, '第二段')
