import { onBeforeUnmount, onMounted, ref } from 'vue'
import axios from 'axios'
import type {
  ContentSubscription,
  ContentSubscriptionCreateRequest,
  ContentSubscriptionPreview,
} from '../types'

const normalizeBase = (base?: string) => (base || '').trim().replace(/\/+$/, '')
const apiBaseUrl = normalizeBase(import.meta.env.VITE_API_BASE_URL)

const errorMessage = (error: unknown, fallback: string) => {
  if (!axios.isAxiosError(error)) return fallback
  const detail = error.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  return error.message ? `${fallback}：${error.message}` : fallback
}

export function useSubscriptions() {
  const subscriptions = ref<ContentSubscription[]>([])
  const preview = ref<ContentSubscriptionPreview | null>(null)
  const isLoading = ref(false)
  const isPreviewing = ref(false)
  const isCreating = ref(false)
  const activePollingId = ref('')
  const error = ref('')

  const fetchSubscriptions = async () => {
    isLoading.value = true
    try {
      const response = await axios.get(`${apiBaseUrl}/subscriptions`)
      subscriptions.value = response.data
      error.value = ''
    } catch (err) {
      error.value = errorMessage(err, '获取订阅列表失败')
    } finally {
      isLoading.value = false
    }
  }

  const previewSubscription = async (sourceUrl: string, connectedAccountId?: string) => {
    isPreviewing.value = true
    preview.value = null
    error.value = ''
    try {
      const response = await axios.post(`${apiBaseUrl}/subscriptions/preview`, {
        source_url: sourceUrl,
        connected_account_id: connectedAccountId || undefined,
      })
      preview.value = response.data
      return response.data as ContentSubscriptionPreview
    } catch (err) {
      error.value = errorMessage(err, '识别订阅来源失败')
      return null
    } finally {
      isPreviewing.value = false
    }
  }

  const createSubscription = async (payload: ContentSubscriptionCreateRequest) => {
    isCreating.value = true
    error.value = ''
    try {
      const response = await axios.post(`${apiBaseUrl}/subscriptions`, payload)
      await fetchSubscriptions()
      return response.data as ContentSubscription
    } catch (err) {
      error.value = errorMessage(err, '创建订阅失败')
      return null
    } finally {
      isCreating.value = false
    }
  }

  const pollSubscription = async (subscriptionId: string) => {
    activePollingId.value = subscriptionId
    error.value = ''
    try {
      const response = await axios.post(`${apiBaseUrl}/subscriptions/${subscriptionId}/poll`, {
        reconciliation: false,
        build_digest: true,
      })
      await fetchSubscriptions()
      return response.data
    } catch (err) {
      error.value = errorMessage(err, '检查订阅更新失败')
      await fetchSubscriptions()
      return null
    } finally {
      activePollingId.value = ''
    }
  }

  const setSubscriptionStatus = async (subscriptionId: string, status: 'ACTIVE' | 'PAUSED') => {
    error.value = ''
    try {
      await axios.patch(`${apiBaseUrl}/subscriptions/${subscriptionId}`, { status })
      await fetchSubscriptions()
      return true
    } catch (err) {
      error.value = errorMessage(err, status === 'PAUSED' ? '暂停订阅失败' : '继续订阅失败')
      return false
    }
  }

  const deleteSubscription = async (subscriptionId: string) => {
    error.value = ''
    try {
      await axios.delete(`${apiBaseUrl}/subscriptions/${subscriptionId}`)
      await fetchSubscriptions()
      return true
    } catch (err) {
      error.value = errorMessage(err, '取消订阅失败')
      return false
    }
  }

  const clearPreview = () => {
    preview.value = null
    error.value = ''
  }

  const handleSubscriptionUpdate = () => {
    fetchSubscriptions()
  }

  onMounted(() => {
    window.addEventListener('xianwen:subscription-update', handleSubscriptionUpdate)
    fetchSubscriptions()
  })
  onBeforeUnmount(() => {
    window.removeEventListener('xianwen:subscription-update', handleSubscriptionUpdate)
  })

  return {
    subscriptions,
    preview,
    isLoading,
    isPreviewing,
    isCreating,
    activePollingId,
    error,
    fetchSubscriptions,
    previewSubscription,
    createSubscription,
    pollSubscription,
    setSubscriptionStatus,
    deleteSubscription,
    clearPreview,
  }
}
