import { onMounted, ref } from 'vue'
import axios from 'axios'
import type { GitSettings, GitSettingsUpdate, GitSyncResult } from '../types'


const normalizeBase = (base?: string) => (base || '').trim().replace(/\/+$/, '')
const apiBaseUrl = normalizeBase(import.meta.env.VITE_API_BASE_URL)

const errorMessage = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    if (error.message) return `${fallback}：${error.message}`
  }
  return fallback
}

export function useGitSync() {
  const gitSettings = ref<GitSettings | null>(null)
  const gitSyncResult = ref<GitSyncResult | null>(null)
  const gitError = ref('')
  const isLoadingGitSettings = ref(false)
  const isSavingGitSettings = ref(false)
  const isTestingGit = ref(false)
  const isSyncingGit = ref(false)

  const fetchGitSettings = async () => {
    isLoadingGitSettings.value = true
    gitError.value = ''
    try {
      const response = await axios.get(`${apiBaseUrl}/git/settings`)
      gitSettings.value = response.data
    } catch (error) {
      gitError.value = errorMessage(error, '读取 Git 设置失败')
    } finally {
      isLoadingGitSettings.value = false
    }
  }

  const saveGitSettings = async (payload: GitSettingsUpdate) => {
    isSavingGitSettings.value = true
    gitError.value = ''
    try {
      const response = await axios.put(`${apiBaseUrl}/git/settings`, payload)
      gitSettings.value = response.data
      return true
    } catch (error) {
      gitError.value = errorMessage(error, '保存 Git 设置失败')
      return false
    } finally {
      isSavingGitSettings.value = false
    }
  }

  const testGit = async () => {
    isTestingGit.value = true
    gitError.value = ''
    try {
      await axios.post(`${apiBaseUrl}/git/test`)
      await fetchGitSettings()
      return true
    } catch (error) {
      gitError.value = errorMessage(error, 'Git 连接测试失败')
      await fetchGitSettings()
      return false
    } finally {
      isTestingGit.value = false
    }
  }

  const syncGit = async () => {
    isSyncingGit.value = true
    gitError.value = ''
    gitSyncResult.value = null
    try {
      const response = await axios.post(`${apiBaseUrl}/git/sync`)
      gitSyncResult.value = response.data
      await fetchGitSettings()
      return true
    } catch (error) {
      gitError.value = errorMessage(error, '文库同步失败')
      await fetchGitSettings()
      return false
    } finally {
      isSyncingGit.value = false
    }
  }

  const deleteGitSettings = async () => {
    gitError.value = ''
    try {
      await axios.delete(`${apiBaseUrl}/git/settings`)
      gitSettings.value = null
      gitSyncResult.value = null
      await fetchGitSettings()
      return true
    } catch (error) {
      gitError.value = errorMessage(error, '删除 Git 设置失败')
      return false
    }
  }

  onMounted(fetchGitSettings)

  return {
    gitSettings,
    gitSyncResult,
    gitError,
    isLoadingGitSettings,
    isSavingGitSettings,
    isTestingGit,
    isSyncingGit,
    fetchGitSettings,
    saveGitSettings,
    testGit,
    syncGit,
    deleteGitSettings,
  }
}
