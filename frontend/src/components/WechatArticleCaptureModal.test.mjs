import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const modal = await readFile(new URL('./WechatArticleCaptureModal.vue', import.meta.url), 'utf8')
const sidebar = await readFile(new URL('./Sidebar.vue', import.meta.url), 'utf8')
const taskCard = await readFile(new URL('./FolderBrowser/TaskCard.vue', import.meta.url), 'utf8')
const taskContentArea = await readFile(new URL('./TaskContentArea.vue', import.meta.url), 'utf8')

assert.match(modal, /公众号文章/)
assert.match(modal, /mp\.weixin\.qq\.com/)
assert.match(modal, /createWechatArticleTask/)
assert.match(modal, /采集并生成笔记/)
assert.match(sidebar, /openWechatArticleCapture/)
assert.match(taskCard, /wechat_article/)
assert.match(taskCard, /公众号/)
assert.match(taskContentArea, /文章原文/)
assert.match(taskContentArea, /下载原文/)
