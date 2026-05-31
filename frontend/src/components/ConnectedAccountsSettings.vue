<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { PhCheckCircle, PhFloppyDisk, PhKey, PhTrash } from '@phosphor-icons/vue'
import type {
  CaptureProviderInfo,
  ConnectedAccount,
  ConnectedAccountUpsertRequest,
} from '../types'

const props = defineProps<{
  captureProviders: CaptureProviderInfo[]
  connectedAccounts: ConnectedAccount[]
  isUpdatingConnectedAccount: boolean
  compact?: boolean
}>()

const emit = defineEmits<{
  upsertConnectedAccount: [provider: string, payload: ConnectedAccountUpsertRequest]
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
  domainLabel?: string
  domainPlaceholder?: string
}> = {
  bilibili: {
    credentialLabel: 'SESSDATA',
    secretKey: 'SESSDATA',
    placeholder: '粘贴 B 站 SESSDATA',
  },
  xiaoetong: {
    credentialLabel: 'Cookie Header',
    secretKey: 'cookie_header',
    placeholder: '粘贴小鹅通 Cookie Header',
    domainLabel: '适用域名',
    domainPlaceholder: '例如 appexpqpqic7617.h5.xiaoeknow.com',
  },
  homeway: {
    credentialLabel: 'web_qtstr',
    secretKey: 'web_qtstr',
    placeholder: '粘贴投研大师 web_qtstr',
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

        <div class="space-y-2">
          <input
            v-model="row.form.displayName"
            type="text"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            placeholder="显示名称"
            autocomplete="off"
          >

          <input
            v-if="row.meta.domainLabel"
            v-model="row.form.domainScope"
            type="text"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            :placeholder="row.meta.domainPlaceholder"
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
        </div>

        <div class="grid grid-cols-2 gap-2">
          <button
            @click="handleSave(row.provider)"
            :disabled="isUpdatingConnectedAccount || !row.form.secret.trim()"
            class="inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-800 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <PhFloppyDisk :size="14" />
            <span>{{ isUpdatingConnectedAccount ? '保存中' : '保存' }}</span>
          </button>
          <button
            @click="handleDelete(row.account)"
            :disabled="isUpdatingConnectedAccount || !row.account"
            class="inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <PhTrash :size="14" />
            <span>删除</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
