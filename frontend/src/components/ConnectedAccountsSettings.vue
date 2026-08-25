<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { PhCheckCircle, PhDownloadSimple, PhFloppyDisk, PhKey, PhTrash } from '@phosphor-icons/vue'
import type {
  CaptureProviderInfo,
  ConnectedAccount,
  ConnectedAccountBrowserImportRequest,
  ConnectedAccountUpsertRequest,
} from '../types'

const props = defineProps<{
  captureProviders: CaptureProviderInfo[]
  connectedAccounts: ConnectedAccount[]
  isUpdatingConnectedAccount: boolean
  isImportingConnectedAccount: boolean
  compact?: boolean
}>()

const emit = defineEmits<{
  upsertConnectedAccount: [provider: string, payload: ConnectedAccountUpsertRequest]
  importConnectedAccountFromBrowser: [provider: string, payload: ConnectedAccountBrowserImportRequest]
  deleteConnectedAccount: [accountId: string]
}>()

type ProviderFormState = {
  displayName: string
  domainScope: string
  secret: string
}

const providerFallbacks: CaptureProviderInfo[] = [
  { id: 'bilibili', name: '哔哩哔哩', credential_types: ['sessdata_bundle'], supports_validate: true },
  { id: 'xiaoetong', name: '小鹅通', credential_types: ['cookie_header'], supports_validate: true },
  { id: 'homeway', name: '投研大师', credential_types: ['web_qtstr'], supports_validate: true },
]

const providerMeta: Record<string, {
  credentialLabel: string
  secretKey: string
  placeholder: string
  browserHint: string
  domainLabel?: string
  domainPlaceholder?: string
}> = {
  bilibili: {
    credentialLabel: 'SESSDATA',
    secretKey: 'SESSDATA',
    placeholder: '粘贴 B 站 SESSDATA',
    browserHint: '确认已在浏览器登录 bilibili.com 后点击获取。',
  },
  xiaoetong: {
    credentialLabel: 'Cookie Header',
    secretKey: 'cookie_header',
    placeholder: '粘贴小鹅通 Cookie Header',
    domainLabel: '视频链接或店铺域名',
    domainPlaceholder: '粘贴小鹅通视频链接，支持 xiaoeknow.com / xet.pomoho.com',
    browserHint: '先粘贴小鹅通视频链接或店铺域名，再读取浏览器登录态。',
  },
  homeway: {
    credentialLabel: 'web_qtstr',
    secretKey: 'web_qtstr',
    placeholder: '粘贴投研大师 web_qtstr',
    browserHint: '确认已在浏览器登录投研大师后点击获取。',
  },
}

const forms = ref<Record<string, ProviderFormState>>({})

const visibleProviders = computed(() => (
  props.captureProviders.length ? props.captureProviders : providerFallbacks
))

const accountByProvider = computed(() => {
  const mapping: Record<string, ConnectedAccount> = {}
  for (const account of props.connectedAccounts) {
    if (!mapping[account.provider]) {
      mapping[account.provider] = account
    }
  }
  return mapping
})

const getMeta = (providerId: string) => {
  return providerMeta[providerId] || {
    credentialLabel: '凭据',
    secretKey: 'credential',
    placeholder: '粘贴站点凭据',
    browserHint: '确认已在浏览器登录目标站点后点击获取。',
  }
}

const ensureForm = (provider: CaptureProviderInfo) => {
  const account = accountByProvider.value[provider.id]
  const existingForm = forms.value[provider.id]
  if (!existingForm) {
    forms.value[provider.id] = {
      displayName: account?.display_name || provider.name,
      domainScope: account?.domain_scope || '',
      secret: '',
    }
    return
  }
  existingForm.displayName = account?.display_name || existingForm.displayName || provider.name
  existingForm.domainScope = account?.domain_scope || existingForm.domainScope || ''
}

const syncForms = () => {
  for (const provider of visibleProviders.value) {
    ensureForm(provider)
  }
}

watch(
  () => [props.captureProviders, props.connectedAccounts],
  syncForms,
  { immediate: true, deep: true },
)

const getCredentialType = (provider: CaptureProviderInfo) => {
  return provider.credential_types[0] || getMeta(provider.id).secretKey
}

const getStatusLabel = (account?: ConnectedAccount) => {
  if (!account) return '未连接'
  if (account.status === 'connected') return '已连接'
  if (account.status === 'invalid') return '已失效'
  return account.status || '未知'
}

const getStatusClass = (account?: ConnectedAccount) => {
  if (!account) return 'border-slate-200 bg-slate-50 text-slate-500'
  if (account.status === 'connected') return 'border-emerald-200 bg-emerald-50 text-emerald-700'
  return 'border-amber-200 bg-amber-50 text-amber-700'
}

const providerRows = computed(() => visibleProviders.value.map((provider) => {
  ensureForm(provider)
  return {
    provider,
    meta: getMeta(provider.id),
    account: accountByProvider.value[provider.id],
    form: forms.value[provider.id] as ProviderFormState,
  }
}))

const handleSave = (provider: CaptureProviderInfo) => {
  const form = forms.value[provider.id]
  if (!form) return

  const secret = form.secret.trim()
  if (!secret) return

  const meta = getMeta(provider.id)
  const account = accountByProvider.value[provider.id]
  const domainScope = form.domainScope.trim()
  const payload: ConnectedAccountUpsertRequest = {
    account_id: account?.id,
    credential_type: getCredentialType(provider),
    payload: {
      [meta.secretKey]: secret,
    },
    display_name: form.displayName.trim() || provider.name,
    domain_scope: domainScope || undefined,
  }

  if (provider.id === 'xiaoetong' && domainScope) {
    payload.payload.host_scope = domainScope
  }

  emit('upsertConnectedAccount', provider.id, payload)
  form.secret = ''
}

const handleDelete = (account?: ConnectedAccount) => {
  if (!account) return
  emit('deleteConnectedAccount', account.id)
}

const canImportFromBrowser = (provider: CaptureProviderInfo) => {
  if (provider.id !== 'xiaoetong') return true
  return Boolean(forms.value[provider.id]?.domainScope?.trim())
}

const handleImportFromBrowser = (provider: CaptureProviderInfo) => {
  const form = forms.value[provider.id]
  const source = form?.domainScope?.trim() || ''
  emit('importConnectedAccountFromBrowser', provider.id, {
    source_url: source || undefined,
    domain_scope: source || undefined,
    display_name: form?.displayName?.trim() || provider.name,
  })
}
</script>

<template>
  <div class="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
    <div class="flex items-center justify-between gap-3 pb-2 border-b border-slate-100">
      <div class="flex items-center gap-2">
        <PhKey :size="18" class="text-blue-500" />
        <h3 class="text-sm font-semibold text-slate-800">采集账号</h3>
      </div>
      <span class="text-xs text-slate-500">
        {{ connectedAccounts.length }} 个已保存
      </span>
    </div>

    <div :class="compact ? 'space-y-3' : 'grid gap-3 lg:grid-cols-3'">
      <div
        v-for="row in providerRows"
        :key="row.provider.id"
        class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 space-y-3"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="text-sm font-semibold text-slate-800 truncate">{{ row.provider.name }}</p>
            <p class="text-xs text-slate-500 mt-0.5">{{ row.meta.credentialLabel }}</p>
          </div>
          <span
            :class="[
              'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium',
              getStatusClass(row.account)
            ]"
          >
            <PhCheckCircle v-if="row.account?.status === 'connected'" :size="12" />
            {{ getStatusLabel(row.account) }}
          </span>
        </div>

        <p class="min-h-[18px] text-xs text-slate-500 truncate">
          当前：{{ row.account?.secret_masked || '未保存' }}
        </p>
        <p class="text-xs leading-relaxed text-slate-500">
          {{ row.meta.browserHint }}
        </p>

        <div v-if="row.meta.domainLabel" class="space-y-2">
          <input
            v-model="row.form.domainScope"
            type="text"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            :placeholder="row.meta.domainPlaceholder"
            autocomplete="off"
          >
        </div>

        <div class="flex items-center gap-2">
          <button
            @click="handleImportFromBrowser(row.provider)"
            :disabled="isImportingConnectedAccount || !canImportFromBrowser(row.provider)"
            class="inline-flex min-w-0 flex-1 items-center justify-center gap-1.5 rounded-lg bg-blue-500 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <PhDownloadSimple :size="14" />
            <span>{{ isImportingConnectedAccount ? '读取中' : '从浏览器获取' }}</span>
          </button>
          <button
            v-if="row.account"
            @click="handleDelete(row.account)"
            :disabled="isUpdatingConnectedAccount || isImportingConnectedAccount"
            class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 transition-colors hover:bg-slate-50 hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-50"
            title="删除已保存账号"
          >
            <PhTrash :size="14" />
            <span class="sr-only">删除已保存账号</span>
          </button>
        </div>

        <details class="rounded-lg border border-slate-200 bg-white/70 px-3 py-2">
          <summary class="cursor-pointer select-none text-xs font-medium text-slate-500 transition-colors hover:text-slate-700">
            高级：手动填写
          </summary>

          <div class="mt-3 space-y-2">
            <input
              v-model="row.form.displayName"
              type="text"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              placeholder="显示名称"
              autocomplete="off"
            >

            <div class="relative">
              <PhKey :size="15" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                v-model="row.form.secret"
                type="password"
                class="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                :placeholder="row.meta.placeholder"
                autocomplete="off"
              >
            </div>

            <button
              @click="handleSave(row.provider)"
              :disabled="isUpdatingConnectedAccount || isImportingConnectedAccount || !row.form.secret.trim()"
              class="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-slate-800 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <PhFloppyDisk :size="14" />
              <span>{{ isUpdatingConnectedAccount ? '保存中' : '保存手动凭据' }}</span>
            </button>
          </div>
        </details>
      </div>
    </div>
  </div>
</template>
