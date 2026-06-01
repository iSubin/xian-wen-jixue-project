import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./CollectionCaptureModal.vue', import.meta.url), 'utf8')

assert.match(source, /合集采集/)
assert.match(source, /粘贴 B 站合集/)
assert.match(source, /previewCollection/)
assert.match(source, /createCollection/)
assert.match(source, /selectedItemKeys/)
