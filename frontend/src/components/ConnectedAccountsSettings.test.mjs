import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./ConnectedAccountsSettings.vue', import.meta.url), 'utf8')

assert.match(source, /高级：手动填写/)
assert.match(source, /保存手动凭据/)
assert.doesNotMatch(source, /class="grid grid-cols-2 gap-2"/)
assert.doesNotMatch(source, /<span>\{\{ isUpdatingConnectedAccount \? '保存中' : '保存' \}\}<\/span>/)
