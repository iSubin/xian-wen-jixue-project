import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./TaskInfoModal.vue', import.meta.url), 'utf8')

assert.match(source, /任务属性/)
assert.match(source, /emit\('retry', selectedTask\.id\)/)
assert.match(source, /失败后补录/)
assert.match(source, /TaskStatus\.FAILED/)
assert.match(source, /TaskStatus\.COMPLETED/)
assert.match(source, /\{\{ isRetrying \? '提交中' : '重试' \}\}/)
