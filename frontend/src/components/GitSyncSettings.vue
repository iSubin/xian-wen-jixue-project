<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  PhCheckCircle,
  PhCloudArrowUp,
  PhCopy,
  PhFileArrowUp,
  PhFloppyDisk,
  PhGitBranch,
  PhKey,
  PhSpinner,
  PhTrash,
  PhWarning,
} from '@phosphor-icons/vue'
import type { GitSettings, GitSettingsUpdate, GitSyncResult } from '../types'

const props = defineProps<{
  settings: GitSettings | null
  result: GitSyncResult | null
  error: string
  isLoading: boolean
  isSaving: boolean
  isTesting: boolean
  isSyncing: boolean
}>()

const emit = defineEmits<{
  save: [payload: GitSettingsUpdate]
  test: []
  sync: []
  remove: []
}>()

const repositoryUrl = ref('')
const branch = ref('main')
const rootPath = ref('先闻继学')
const authorName = ref('先闻继学')
const authorEmail = ref('xianwen@localhost')
const includeTranscript = ref(true)
const autoSync = ref(true)
const privateKey = ref('')
const keyFileName = ref('')
const copied = ref(false)

watch(
  () => props.settings,
  settings => {
    if (!settings) return
    repositoryUrl.value = settings.repository_url || ''
    branch.value = settings.branch || 'main'
    rootPath.value = settings.root_path || '先闻继学'
    authorName.value = settings.author_name || '先闻继学'
    authorEmail.value = settings.author_email || 'xianwen@localhost'
    includeTranscript.value = settings.include_transcript
    autoSync.value = settings.configured ? settings.auto_sync : true
  },
  { immediate: true },
)

const canSave = computed(() =>
  repositoryUrl.value.trim()
  && branch.value.trim()
  && rootPath.value.trim()
  && authorName.value.trim()
  && authorEmail.value.trim()
  && (props.settings?.has_private_key || privateKey.value.trim()),
)

const statusLabel = computed(() => {
  if (!props.settings?.configured) return '尚未配置'
  if (props.settings.status === 'error') return '连接异常'
  if (props.settings.status === 'syncing') return '正在归档'
  if (props.settings.status === 'pending_sync') return '等待归档'
  return '已安全连接'
})

const onKeyFile = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  privateKey.value = await file.text()
  keyFileName.value = file.name
}

const save = () => {
  const payload: GitSettingsUpdate = {
    repository_url: repositoryUrl.value.trim(),
    branch: branch.value.trim(),
    root_path: rootPath.value.trim(),
    author_name: authorName.value.trim(),
    author_email: authorEmail.value.trim(),
    include_transcript: includeTranscript.value,
    auto_sync: autoSync.value,
  }
  if (privateKey.value.trim()) payload.private_key = privateKey.value.trim()
  emit('save', payload)
  privateKey.value = ''
  keyFileName.value = ''
}

const copyPublicKey = async () => {
  if (!props.settings?.public_key) return
  await navigator.clipboard.writeText(props.settings.public_key)
  copied.value = true
  window.setTimeout(() => { copied.value = false }, 1600)
}
</script>

<template>
  <div class="git-scroll">
    <section class="git-hero">
      <div>
        <p class="eyebrow">GIT PUBLISHER</p>
        <h3>把文库交还给你自己</h3>
        <p>按目录生成 Markdown，推送到私人仓库，再由 Obsidian 接续阅读、批注与生长。</p>
      </div>
      <div :class="['status-seal', settings?.status === 'error' ? 'status-error' : '']">
        <PhSpinner v-if="settings?.status === 'syncing'" :size="17" class="animate-spin" />
        <PhCheckCircle v-else-if="settings?.configured && settings.status !== 'error'" :size="17" weight="fill" />
        <PhWarning v-else-if="settings?.status === 'error'" :size="17" weight="fill" />
        <PhGitBranch v-else :size="17" />
        {{ statusLabel }}
      </div>
    </section>

    <div v-if="isLoading" class="loading-line">
      <PhSpinner :size="16" class="animate-spin" /> 正在读取 Git 设置
    </div>

    <section class="git-card">
      <div class="section-title">
        <span>一</span>
        <div>
          <h4>仓库落点</h4>
          <p>Deploy Key 仅支持 SSH 地址，目标分支需要已经存在。</p>
        </div>
      </div>

      <label>
        <span>SSH 仓库地址</span>
        <input v-model="repositoryUrl" placeholder="git@github.com:owner/knowledge.git">
      </label>
      <div class="field-grid">
        <label>
          <span>分支</span>
          <input v-model="branch" placeholder="main">
        </label>
        <label>
          <span>仓库内文库目录</span>
          <input v-model="rootPath" placeholder="先闻继学">
        </label>
      </div>
      <div class="field-grid">
        <label>
          <span>提交署名</span>
          <input v-model="authorName">
        </label>
        <label>
          <span>提交邮箱</span>
          <input v-model="authorEmail">
        </label>
      </div>
    </section>

    <section class="git-card">
      <div class="section-title">
        <span>二</span>
        <div>
          <h4>Deploy Key 私钥</h4>
          <p>私钥加密保存在本机数据库，接口永不返回明文。</p>
        </div>
      </div>

      <label class="key-drop">
        <PhFileArrowUp :size="24" />
        <strong>{{ keyFileName || (settings?.has_private_key ? '已保存私钥，可重新上传替换' : '选择 Deploy Key 私钥文件') }}</strong>
        <small>支持 OpenSSH / PEM，无口令私钥</small>
        <input type="file" class="sr-only" @change="onKeyFile">
      </label>

      <div v-if="settings?.public_key" class="public-key">
        <div>
          <span>对应公钥</span>
          <small>把它添加到 GitHub / GitLab 仓库的 Deploy Keys，并开启写权限。</small>
        </div>
        <button type="button" @click="copyPublicKey">
          <PhCopy :size="15" /> {{ copied ? '已复制' : '复制公钥' }}
        </button>
        <code>{{ settings.public_key }}</code>
      </div>
    </section>

    <section class="git-card">
      <div class="section-title">
        <span>三</span>
        <div>
          <h4>文档内容</h4>
          <p>内容按原始标题建立目录；整理稿与原始材料保持适合 Obsidian 阅读的结构。</p>
        </div>
      </div>
      <button type="button" class="transcript-toggle" @click="autoSync = !autoSync">
        <span>
          <strong>采集完成后自动归档</strong>
          <small>后台合并短时间内的变更；归档失败不会影响采集结果。</small>
        </span>
        <i :class="{ on: autoSync }"><b /></i>
      </button>
      <button type="button" class="transcript-toggle" @click="includeTranscript = !includeTranscript">
        <span>
          <strong>附带原始转写</strong>
          <small>关闭后，Git 中只保留整理稿，不生成原始逐字稿或原始正文。</small>
        </span>
        <i :class="{ on: includeTranscript }"><b /></i>
      </button>
      <p class="safety-note">
        <PhKey :size="15" />
        已在 Obsidian 修改过的文件不会被覆盖；同步结果会把它列为冲突，等待你人工决定。
      </p>
    </section>

    <div v-if="error" class="error-panel">
      <PhWarning :size="17" weight="fill" />
      <span>{{ error }}</span>
    </div>

    <div v-if="result" class="result-panel">
      <PhCheckCircle :size="18" weight="fill" />
      <div>
        <strong>{{ result.committed ? '文库已推送' : '文库已是最新' }}</strong>
        <p>
          {{ result.document_count }} 篇文档 · 新增 {{ result.created }} · 更新 {{ result.updated }}
          <template v-if="result.conflicts.length"> · {{ result.conflicts.length }} 个冲突已保留</template>
        </p>
        <code v-if="result.commit_sha">{{ result.commit_sha.slice(0, 12) }}</code>
      </div>
    </div>

    <div class="actions">
      <button type="button" class="save-action" :disabled="!canSave || isSaving" @click="save">
        <PhSpinner v-if="isSaving" :size="16" class="animate-spin" />
        <PhFloppyDisk v-else :size="16" />
        {{ isSaving ? '保存中' : '保存设置' }}
      </button>
      <button type="button" class="test-action" :disabled="!settings?.configured || isTesting" @click="emit('test')">
        <PhSpinner v-if="isTesting" :size="16" class="animate-spin" />
        <PhGitBranch v-else :size="16" />
        {{ isTesting ? '连接中' : '测试连接' }}
      </button>
      <button type="button" class="sync-action" :disabled="!settings?.configured || isSyncing" @click="emit('sync')">
        <PhSpinner v-if="isSyncing" :size="16" class="animate-spin" />
        <PhCloudArrowUp v-else :size="17" weight="fill" />
        {{ isSyncing ? '正在推送' : '同步整座文库' }}
      </button>
    </div>

    <button
      v-if="settings?.configured"
      type="button"
      class="remove-action"
      @click="emit('remove')"
    >
      <PhTrash :size="14" /> 删除 Git 配置与本机私钥
    </button>
  </div>
</template>

<style scoped>
.git-scroll {
  --paper: #f6f0e3;
  --paper-deep: #ede3d1;
  --ink: #302b24;
  --muted: #7c7367;
  --cinnabar: #a84735;
  color: var(--ink);
  font-family: "Noto Serif SC", "Songti SC", STSong, serif;
}
.git-hero {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 24px;
  padding: 22px; border: 1px solid #dfd2bd; border-radius: 4px;
  background: linear-gradient(110deg, #fbf8ef, var(--paper));
  box-shadow: inset 4px 0 0 var(--cinnabar);
}
.eyebrow { margin: 0 0 7px; color: var(--cinnabar); font: 700 10px/1.2 ui-monospace, monospace; letter-spacing: .22em; }
.git-hero h3 { margin: 0; font-size: 22px; letter-spacing: .08em; }
.git-hero p { margin: 8px 0 0; color: var(--muted); font-size: 13px; line-height: 1.8; }
.status-seal { display: flex; align-items: center; gap: 6px; white-space: nowrap; border: 1px solid #799070; color: #53684c; padding: 7px 10px; font-size: 12px; background: #f2f5eb; }
.status-error { color: var(--cinnabar); border-color: #c98d82; background: #fbefec; }
.git-card { margin-top: 14px; padding: 18px; border: 1px solid #e1d7c6; background: #fffdfa; }
.section-title { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 15px; }
.section-title > span { display: grid; place-items: center; width: 25px; height: 25px; color: white; background: var(--ink); font-size: 12px; }
.section-title h4 { margin: 0; font-size: 15px; letter-spacing: .06em; }
.section-title p { margin: 4px 0 0; color: var(--muted); font: 12px/1.6 ui-sans-serif, system-ui, sans-serif; }
label > span, .public-key span { display: block; margin-bottom: 6px; color: #625a50; font: 600 12px/1.2 ui-sans-serif, system-ui, sans-serif; }
input { width: 100%; box-sizing: border-box; border: 1px solid #d9cfbf; background: #fbfaf6; padding: 10px 11px; color: var(--ink); font: 13px/1.3 ui-monospace, monospace; outline: none; }
input:focus { border-color: var(--cinnabar); box-shadow: 0 0 0 2px rgba(168, 71, 53, .1); }
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
.key-drop { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 110px; border: 1px dashed #bbae99; background: var(--paper); cursor: pointer; transition: .18s ease; }
.key-drop:hover { border-color: var(--cinnabar); background: #f8eee6; transform: translateY(-1px); }
.key-drop strong { margin-top: 8px; font: 600 13px/1.4 ui-sans-serif, system-ui, sans-serif; }
.key-drop small, .public-key small { color: var(--muted); font: 11px/1.5 ui-sans-serif, system-ui, sans-serif; }
.public-key { position: relative; margin-top: 12px; padding: 12px; border-left: 3px solid #768e6d; background: #f4f6ef; }
.public-key button { position: absolute; top: 10px; right: 10px; display: flex; gap: 5px; color: #52664c; font: 600 11px/1 ui-sans-serif, system-ui, sans-serif; }
.public-key code { display: block; margin-top: 9px; padding-right: 80px; word-break: break-all; color: #4b5547; font-size: 10px; }
.transcript-toggle { width: 100%; display: flex; align-items: center; justify-content: space-between; text-align: left; padding: 12px; border: 1px solid #ded4c4; background: #fbfaf6; }
.transcript-toggle + .transcript-toggle { margin-top: 8px; }
.transcript-toggle span { display: flex; flex-direction: column; gap: 4px; }
.transcript-toggle strong { font: 600 13px/1.3 ui-sans-serif, system-ui, sans-serif; }
.transcript-toggle small { color: var(--muted); font: 11px/1.4 ui-sans-serif, system-ui, sans-serif; }
.transcript-toggle i { width: 38px; height: 21px; padding: 2px; border-radius: 20px; background: #c8c0b4; transition: .2s; }
.transcript-toggle i b { display: block; width: 17px; height: 17px; border-radius: 50%; background: white; transition: .2s; }
.transcript-toggle i.on { background: var(--cinnabar); }
.transcript-toggle i.on b { transform: translateX(17px); }
.safety-note { display: flex; gap: 7px; margin: 12px 0 0; color: #6a6257; font: 11px/1.6 ui-sans-serif, system-ui, sans-serif; }
.actions { display: grid; grid-template-columns: 1fr 1fr 1.35fr; gap: 9px; margin-top: 15px; }
.actions button, .remove-action { display: flex; align-items: center; justify-content: center; gap: 7px; padding: 11px; font: 600 12px/1 ui-sans-serif, system-ui, sans-serif; transition: .18s ease; }
.actions button:disabled { opacity: .45; cursor: not-allowed; }
.save-action { background: var(--ink); color: white; }
.test-action { border: 1px solid #bfb3a1; color: #554e45; background: #fffdfa; }
.sync-action { color: white; background: var(--cinnabar); box-shadow: 0 6px 18px rgba(168, 71, 53, .18); }
.actions button:not(:disabled):hover { transform: translateY(-1px); filter: brightness(.97); }
.remove-action { margin: 15px auto 0; color: #a45a50; }
.error-panel, .result-panel { display: flex; gap: 9px; margin-top: 14px; padding: 12px; font: 12px/1.5 ui-sans-serif, system-ui, sans-serif; }
.error-panel { color: #9b4438; border: 1px solid #e5beb7; background: #fff2ef; }
.result-panel { color: #4e6548; border: 1px solid #cbd9c5; background: #f4f8f0; }
.result-panel strong, .result-panel p { display: block; margin: 0; }
.result-panel code { font-size: 10px; }
.loading-line { display: flex; align-items: center; gap: 7px; padding: 16px; color: var(--muted); font-size: 12px; }
@media (max-width: 700px) {
  .git-hero { flex-direction: column; }
  .field-grid, .actions { grid-template-columns: 1fr; }
}
</style>
