<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  PhCheckCircle,
  PhClock,
  PhLink,
  PhPlayCircle,
  PhPlus,
  PhSpinner,
  PhTrash,
  PhWarning,
  PhX,
} from '@phosphor-icons/vue'
import { useSubscriptions } from '../composables/useSubscriptions'
import type {
  ConnectedAccount,
  ContentSubscription,
  ContentSubscriptionInitialSyncMode,
  SettingsModalTab,
} from '../types'

const props = defineProps<{
  connectedAccounts: ConnectedAccount[]
}>()

const emit = defineEmits<{
  changed: []
  openSettings: [tab: SettingsModalTab]
}>()

const {
  subscriptions,
  preview,
  isLoading,
  isPreviewing,
  isCreating,
  activePollingId,
  error,
  previewSubscription,
  createSubscription,
  pollSubscription,
  setSubscriptionStatus,
  deleteSubscription,
  clearPreview,
} = useSubscriptions()

const isAdding = ref(false)
const isInitialSyncing = ref(false)
const sourceUrl = ref('')
const initialSyncMode = ref<ContentSubscriptionInitialSyncMode>('from_now')
const digestTime = ref('20:30')

const homewayAccount = computed(() =>
  [...props.connectedAccounts]
    .reverse()
    .find(account => account.provider === 'homeway' && account.credential_type === 'web_qtstr') || null,
)

const statusInfo = (subscription: ContentSubscription) => {
  if (subscription.status === 'ACTIVE') return { label: '正常', tone: 'success' }
  if (subscription.status === 'PAUSED') return { label: '已暂停', tone: 'muted' }
  if (subscription.status === 'AUTH_REQUIRED') return { label: '需要重新登录', tone: 'warning' }
  if (subscription.status === 'DEGRADED') return { label: '部分异常', tone: 'warning' }
  return { label: '异常', tone: 'danger' }
}

const formatDateTime = (value?: string | null) => {
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleString([], {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const resetCreateForm = () => {
  sourceUrl.value = ''
  initialSyncMode.value = 'from_now'
  digestTime.value = '20:30'
  isAdding.value = false
  clearPreview()
}

const handlePreview = async () => {
  if (!sourceUrl.value.trim()) return
  await previewSubscription(sourceUrl.value.trim(), homewayAccount.value?.id)
}

const handleCreate = async () => {
  if (!preview.value || !homewayAccount.value) return
  isInitialSyncing.value = true
  try {
    const subscription = await createSubscription({
      source_url: preview.value.source_url,
      connected_account_id: homewayAccount.value.id,
      initial_sync_mode: initialSyncMode.value,
      digest_time: digestTime.value,
      timezone: 'Asia/Shanghai',
    })
    if (!subscription) return
    emit('changed')
    await pollSubscription(subscription.id)
    emit('changed')
    resetCreateForm()
  } finally {
    isInitialSyncing.value = false
  }
}

const handlePoll = async (subscriptionId: string) => {
  if (await pollSubscription(subscriptionId)) emit('changed')
}

const toggleSubscription = async (subscription: ContentSubscription) => {
  const target = subscription.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE'
  if (await setSubscriptionStatus(subscription.id, target)) emit('changed')
}

const removeSubscription = async (subscription: ContentSubscription) => {
  if (!window.confirm(`取消订阅“${subscription.display_name}”？历史内容和 Git 文库不会删除。`)) return
  if (await deleteSubscription(subscription.id)) emit('changed')
}
</script>

<template>
  <section class="h-full min-h-0 flex flex-col bg-[#fbfcfe]">
    <div class="px-4 py-3 border-b border-slate-100 bg-white">
      <div class="flex items-center justify-between gap-3">
        <div>
          <h2 class="text-sm font-semibold text-slate-800">内容订阅</h2>
          <p class="mt-0.5 text-[11px] text-slate-400">持续来源，按日期归档每一篇独立帖子</p>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-blue-700"
          @click="isAdding = !isAdding; clearPreview()"
        >
          <PhX v-if="isAdding" :size="13" />
          <PhPlus v-else :size="13" weight="bold" />
          {{ isAdding ? '收起' : '添加' }}
        </button>
      </div>
    </div>

    <div class="flex-1 min-h-0 overflow-y-auto p-4 custom-scrollbar space-y-3">
      <div
        v-if="isAdding"
        class="rounded-2xl border border-blue-100 bg-white p-3 shadow-sm space-y-3"
      >
        <div>
          <label class="text-[11px] font-semibold text-slate-500">讲师主页</label>
          <div class="relative mt-1.5">
            <PhLink :size="15" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              v-model="sourceUrl"
              type="url"
              placeholder="https://tyds.homeway.com.cn/#/GraphicLecturer?..."
              class="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-9 pr-3 text-xs text-slate-700 outline-none transition focus:border-blue-300 focus:ring-2 focus:ring-blue-100"
              @keydown.enter.prevent="handlePreview"
            >
          </div>
        </div>

        <div
          v-if="!homewayAccount"
          class="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800"
        >
          <div class="flex items-start gap-2">
            <PhWarning :size="16" class="mt-0.5 shrink-0" />
            <div>
              <p class="font-semibold">需要投研大师账号</p>
              <p class="mt-1 leading-5 text-amber-700">先从浏览器导入 <code>web_qtstr</code>，系统只采集该账号明确有权阅读的内容。</p>
              <button type="button" class="mt-1.5 font-semibold underline" @click="emit('openSettings', 'accounts')">
                打开采集账号设置
              </button>
            </div>
          </div>
        </div>
        <div v-else class="flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
          <PhCheckCircle :size="15" weight="fill" />
          已连接 {{ homewayAccount.display_name || '投研大师' }}
        </div>

        <button
          type="button"
          :disabled="!sourceUrl.trim() || isPreviewing"
          class="w-full rounded-xl border border-blue-200 bg-blue-50 py-2 text-xs font-semibold text-blue-700 transition hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-50"
          @click="handlePreview"
        >
          <PhSpinner v-if="isPreviewing" :size="14" class="mr-1 inline animate-spin" />
          {{ isPreviewing ? '正在识别' : '识别订阅来源' }}
        </button>

        <div v-if="preview" class="rounded-xl border border-slate-100 bg-slate-50/80 p-3">
          <div class="flex items-center gap-2.5">
            <img
              v-if="preview.avatar_url"
              :src="preview.avatar_url"
              alt=""
              class="h-10 w-10 rounded-xl object-cover ring-1 ring-slate-200"
            >
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold text-slate-800">{{ preview.display_name }}</p>
              <p class="text-[11px] text-slate-400">投研大师 · {{ preview.text_menu_name }}文字</p>
            </div>
          </div>

          <div class="mt-3 grid grid-cols-2 gap-2">
            <label class="text-[10px] font-semibold text-slate-500">
              首次同步
              <select
                v-model="initialSyncMode"
                class="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs font-normal text-slate-700 outline-none"
              >
                <option value="from_now">从现在开始</option>
                <option value="today">补采今天</option>
                <option value="last_7_days">补采最近 7 天</option>
              </select>
            </label>
            <label class="text-[10px] font-semibold text-slate-500">
              每日归档时间
              <input
                v-model="digestTime"
                type="time"
                class="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs font-normal text-slate-700 outline-none"
              >
            </label>
          </div>

          <button
            type="button"
            :disabled="!homewayAccount || isCreating || isInitialSyncing"
            class="mt-3 w-full rounded-xl bg-blue-600 py-2.5 text-xs font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            @click="handleCreate"
          >
            <PhSpinner v-if="isCreating || isInitialSyncing" :size="14" class="mr-1 inline animate-spin" />
            {{ isInitialSyncing ? '正在首次同步' : isCreating ? '正在创建' : '创建并首次同步' }}
          </button>
        </div>
      </div>

      <div v-if="error" class="rounded-xl border border-red-100 bg-red-50 px-3 py-2.5 text-xs leading-5 text-red-700">
        {{ error }}
      </div>

      <div v-if="isLoading && subscriptions.length === 0" class="py-12 text-center text-xs text-slate-400">
        <PhSpinner :size="20" class="mx-auto mb-2 animate-spin" />
        正在读取订阅
      </div>

      <div
        v-else-if="subscriptions.length === 0 && !isAdding"
        class="rounded-2xl border border-dashed border-slate-200 bg-white px-5 py-12 text-center"
      >
        <PhClock :size="28" class="mx-auto text-slate-300" />
        <p class="mt-3 text-sm font-semibold text-slate-600">还没有内容订阅</p>
        <p class="mt-1 text-xs leading-5 text-slate-400">添加持续更新的作者主页，先闻继学会按日期整理每一篇独立帖子。</p>
      </div>

      <article
        v-for="subscription in subscriptions"
        :key="subscription.id"
        class="rounded-2xl border border-slate-100 bg-white p-3.5 shadow-sm"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="truncate text-sm font-semibold text-slate-800">{{ subscription.display_name }}</h3>
            <p class="mt-0.5 text-[11px] text-slate-400">投研大师 · 每日 {{ subscription.digest_time }} 归档</p>
          </div>
          <span :class="['status-pill', statusInfo(subscription).tone]">
            {{ statusInfo(subscription).label }}
          </span>
        </div>

        <div class="mt-3 grid grid-cols-3 divide-x divide-slate-100 rounded-xl bg-slate-50 py-2.5 text-center">
          <div>
            <p class="text-base font-semibold text-slate-800">{{ subscription.today_item_count }}</p>
            <p class="text-[10px] text-slate-400">今日条目</p>
          </div>
          <div>
            <p class="text-base font-semibold text-slate-800">{{ subscription.captured_item_count }}</p>
            <p class="text-[10px] text-slate-400">已采集</p>
          </div>
          <div>
            <p class="text-base font-semibold" :class="subscription.locked_item_count ? 'text-amber-600' : 'text-slate-800'">
              {{ subscription.locked_item_count }}
            </p>
            <p class="text-[10px] text-slate-400">权限锁定</p>
          </div>
        </div>

        <dl class="mt-3 space-y-1.5 text-[11px]">
          <div class="flex justify-between gap-3">
            <dt class="text-slate-400">最近成功</dt>
            <dd class="text-right text-slate-600">{{ formatDateTime(subscription.last_success_at) }}</dd>
          </div>
          <div class="flex justify-between gap-3">
            <dt class="text-slate-400">下次检查</dt>
            <dd class="text-right text-slate-600">{{ formatDateTime(subscription.next_poll_at) }}</dd>
          </div>
        </dl>

        <p
          v-if="subscription.last_error"
          class="mt-2 line-clamp-2 rounded-lg bg-red-50 px-2.5 py-2 text-[10px] leading-4 text-red-600"
        >
          {{ subscription.last_error }}
        </p>

        <div class="mt-3 flex items-center gap-2">
          <button
            type="button"
            :disabled="activePollingId === subscription.id"
            class="flex-1 rounded-lg border border-blue-100 bg-blue-50 py-2 text-[11px] font-semibold text-blue-700 transition hover:bg-blue-100 disabled:opacity-50"
            @click="handlePoll(subscription.id)"
          >
            <PhSpinner v-if="activePollingId === subscription.id" :size="13" class="mr-1 inline animate-spin" />
            <PhPlayCircle v-else :size="13" class="mr-1 inline" />
            {{ activePollingId === subscription.id ? '检查中' : '立即检查' }}
          </button>
          <button
            type="button"
            class="rounded-lg border border-slate-200 px-2.5 py-2 text-[11px] font-semibold text-slate-500 transition hover:bg-slate-50"
            @click="toggleSubscription(subscription)"
          >
            {{ subscription.status === 'ACTIVE' ? '暂停' : '继续' }}
          </button>
          <button
            type="button"
            class="rounded-lg border border-red-100 p-2 text-red-400 transition hover:bg-red-50 hover:text-red-600"
            title="取消订阅"
            @click="removeSubscription(subscription)"
          >
            <PhTrash :size="14" />
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.status-pill {
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 10px;
  font-weight: 700;
  line-height: 1.2;
  white-space: nowrap;
}
.status-pill.success { background: #ecfdf5; color: #047857; }
.status-pill.muted { background: #f1f5f9; color: #64748b; }
.status-pill.warning { background: #fffbeb; color: #b45309; }
.status-pill.danger { background: #fef2f2; color: #b91c1c; }
</style>
