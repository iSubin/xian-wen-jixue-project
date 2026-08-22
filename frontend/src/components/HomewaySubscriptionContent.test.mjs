import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const taskContentArea = await readFile(new URL('./TaskContentArea.vue', import.meta.url), 'utf8')
const taskViewModel = await readFile(new URL('../composables/useTaskViewModel.ts', import.meta.url), 'utf8')
const knowledgeTreeNode = await readFile(new URL('./KnowledgeLibrary/KnowledgeTreeNode.vue', import.meta.url), 'utf8')

assert.match(taskContentArea, /\['wechat_article', 'homeway_daily_digest', 'homeway_post'\]/)
assert.match(taskContentArea, /marked\.parse\(props\.task\.transcript\)/)
assert.match(taskContentArea, /v-html="compiledTranscriptMarkdown"/)
assert.match(taskViewModel, /\['homeway_daily_digest', 'homeway_post'\]/)
assert.match(taskViewModel, /activeTab\.value = 'transcript'/)
assert.match(knowledgeTreeNode, /source_type === 'homeway_post'/)
assert.match(knowledgeTreeNode, /replace\(\/\^\\d\{4\}-\\d\{2\}-\\d\{2\}\\s\+\//)
