import { useCallback, useEffect } from 'react'
import { message } from 'antd'
import { useConversationStore } from '@/stores/conversationStore'
import type { ConversationMessage } from '@/api/conversations'
import * as conversationApi from '@/api/conversations'

/**
 * useConversation — 对话管理 hook
 *
 * 提供对话列表的 CRUD 操作以及消息查询能力。
 */
export function useConversation() {
  const {
    conversations,
    currentId,
    loading,
    total,
    fetchConversations,
    selectConversation,
    createConversation,
    deleteConversation,
  } = useConversationStore()

  /** 组件挂载时自动加载对话列表 */
  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  /** 获取当前选中的对话详情 */
  const currentConversation = conversations.find((c) => c.id === currentId) ?? null

  /** 新建对话 */
  const create = useCallback(
    async (title: string, workspaceType?: string) => {
      const conv = await createConversation(title, workspaceType)
      if (conv) {
        message.success('对话已创建')
      }
      return conv
    },
    [createConversation],
  )

  /** 删除对话 */
  const remove = useCallback(
    async (id: number) => {
      await deleteConversation(id)
      message.success('对话已删除')
    },
    [deleteConversation],
  )

  /** 获取指定对话的消息列表 */
  const getMessages = useCallback(
    async (conversationId: number, page = 1, pageSize = 50): Promise<ConversationMessage[]> => {
      try {
        const res = await conversationApi.getConversationMessages(conversationId, page, pageSize)
        return res.data
      } catch {
        return []
      }
    },
    [],
  )

  return {
    conversations,
    currentId,
    currentConversation,
    loading,
    total,
    selectConversation,
    fetchConversations,
    create,
    remove,
    getMessages,
  }
}