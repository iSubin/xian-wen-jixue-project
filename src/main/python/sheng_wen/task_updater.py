"""
统一的任务状态更新接口

解决数据库更新与WebSocket广播之间的竞态条件问题。
确保更新和通知的原子性，避免前端收到过期的状态数据。
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


async def update_and_notify(task_id: str, updates: Dict[str, Any]) -> dict | None:
    """
    原子性地更新任务并通知客户端

    这个函数确保：
    1. 数据库更新成功后才广播
    2. 广播的数据是刚更新的数据，避免重新读取导致的竞态条件
    3. 统一的错误处理和日志记录

    Args:
        task_id: 任务ID
        updates: 更新字段字典

    Returns:
        更新后的任务数据，如果任务不存在或更新失败返回None
    """
    from .db import db
    from .api import notify_task_update

    # 更新数据库
    updated_task = db.update_task(task_id, updates)

    if updated_task:
        # 使用刚更新的数据进行广播，避免重新读取可能导致的数据不一致
        await notify_task_update(task_id, task_data=updated_task)
        logger.debug(f"[TaskUpdater] 已更新并广播任务 {task_id}: {list(updates.keys())}")
    else:
        logger.warning(f"[TaskUpdater] 任务更新失败，未广播: {task_id}")

    return updated_task
