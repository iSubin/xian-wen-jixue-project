import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./CollectionCaptureModal.vue', import.meta.url), 'utf8')

assert.match(source, /批量采集/)
assert.match(source, /小鹅通已购课时/)
assert.match(source, /xiaoet_video_list/)
assert.match(source, /公众号文章/)
assert.match(source, /历史文章/)
assert.match(source, /解析来源/)
assert.match(source, /previewCollection/)
assert.match(source, /createCollection/)
assert.match(source, /selectedItemKeys/)
