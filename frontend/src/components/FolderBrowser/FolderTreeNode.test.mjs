import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./FolderTreeNode.vue', import.meta.url), 'utf8')
const browserSource = await readFile(new URL('./FolderBrowser.vue', import.meta.url), 'utf8')

assert.match(source, /document\.addEventListener\('pointerdown', handleOutsideInteraction, true\)/)
assert.match(source, /document\.addEventListener\('focusin', handleOutsideInteraction, true\)/)
assert.match(source, /window\.addEventListener\('blur', closeMenu\)/)
assert.match(source, /document\.addEventListener\('visibilitychange', handleVisibilityChange\)/)
assert.match(source, /event\.key !== 'Escape'/)
assert.match(source, /onBeforeUnmount\(removeMenuDismissListeners\)/)
assert.match(source, /ref="menuButtonRef"/)
assert.match(source, /ref="menuRef"/)
assert.match(browserSource, /const expandedMap = ref<Record<string, boolean>>\(\{\}\)/)
assert.doesNotMatch(browserSource, /folder\.folder_type === 'auto'/)
