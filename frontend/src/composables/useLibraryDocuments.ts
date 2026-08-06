import { ref } from 'vue'
import axios from 'axios'
import type { LibraryDocumentPayload, Task } from '../types'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')

const resolveError = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
  }
  return fallback
}

export function useLibraryDocuments() {
  const isSavingDocument = ref(false)
  const isRemovingDocument = ref(false)
  const libraryDocumentError = ref('')

  const createDocument = async (payload: LibraryDocumentPayload): Promise<Task | null> => {
    isSavingDocument.value = true
    libraryDocumentError.value = ''
    try {
      const response = await axios.post(`${apiBaseUrl}/library/documents`, payload)
      return response.data
    } catch (error) {
      libraryDocumentError.value = resolveError(error, '文档创建失败')
      return null
    } finally {
      isSavingDocument.value = false
    }
  }

  const updateDocument = async (
    documentId: string,
    payload: LibraryDocumentPayload,
  ): Promise<Task | null> => {
    isSavingDocument.value = true
    libraryDocumentError.value = ''
    try {
      const response = await axios.patch(
        `${apiBaseUrl}/library/documents/${encodeURIComponent(documentId)}`,
        payload,
      )
      return response.data
    } catch (error) {
      libraryDocumentError.value = resolveError(error, '文档更新失败')
      return null
    } finally {
      isSavingDocument.value = false
    }
  }

  const removeDocument = async (documentId: string): Promise<boolean> => {
    isRemovingDocument.value = true
    libraryDocumentError.value = ''
    try {
      await axios.delete(`${apiBaseUrl}/library/documents/${encodeURIComponent(documentId)}`)
      return true
    } catch (error) {
      libraryDocumentError.value = resolveError(error, '无法从文库移除文档')
      return false
    } finally {
      isRemovingDocument.value = false
    }
  }

  return {
    isSavingDocument,
    isRemovingDocument,
    libraryDocumentError,
    createDocument,
    updateDocument,
    removeDocument,
  }
}
