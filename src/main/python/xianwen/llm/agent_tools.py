"""Agent tool definitions and executor for the built-in AI assistant.

Defines all available API operations as OpenAI function-calling tool schemas,
and maps them to execution handlers that call the existing FastAPI endpoint
functions directly (Python function calls, not HTTP).
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..db import db

# ──────────────────────────────────────────────────
#  Tool definitions (OpenAI function-calling format)
# ──────────────────────────────────────────────────

AGENT_TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "获取所有任务列表。每个任务包含 id、标题、状态、主题、所属文件夹等关键信息。用于了解当前有哪些任务。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_task",
            "description": "获取单个任务的完整详情，包括总结全文和音频时长。用于深入了解某个任务的内容。注意：返回的总结可能很长。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "任务ID"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "创建新文件夹。用于组织归类任务。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "文件夹名称"},
                    "parent_id": {"type": "string", "description": "父文件夹ID，null表示顶层文件夹"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_folders",
            "description": "获取所有文件夹列表及其包含的任务数量。用于了解现有的文件夹结构。",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_tasks": {
                        "type": "boolean",
                        "description": "是否包含每个文件夹内的任务ID列表",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assign_task_to_folder",
            "description": "将任务分配到文件夹。folder_id 为 null 则取消分配（移出文件夹）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "任务ID"},
                    "folder_id": {"type": "string", "description": "文件夹ID，null表示取消分配"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_task",
            "description": "删除任务及其所有数据。不可恢复，需谨慎使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "要删除的任务ID"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "re_summarize",
            "description": "重新生成任务总结。用于切换模型后重新总结，或总结质量不满意时重新生成。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "任务ID"},
                    "summary_mode": {
                        "type": "string",
                        "description": "总结模式：standard（标准）、agent（分块智能）、auto（自动选择）",
                    },
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "更新任务的主题标签。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "任务ID"},
                    "topic": {"type": "string", "description": "新的主题标签"},
                },
                "required": ["task_id", "topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_folder",
            "description": "删除文件夹。文件夹内的任务不会被删除，但会取消文件夹分配。",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_id": {"type": "string", "description": "要删除的文件夹ID"},
                },
                "required": ["folder_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rename_folder",
            "description": "重命名文件夹。",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_id": {"type": "string", "description": "文件夹ID"},
                    "name": {"type": "string", "description": "新名称"},
                },
                "required": ["folder_id", "name"],
            },
        },
    },
]

# Read-only tools that the agent can execute without user confirmation
READ_ONLY_TOOL_NAMES = {"list_tasks", "get_task", "list_folders"}

# ──────────────────────────────────────────────────
#  Result truncation helpers
# ──────────────────────────────────────────────────

MAX_SUMMARY_CHARS = 2000
MAX_TRANSCRIPT_CHARS = 500
MAX_TASK_LIST_ITEMS = 50


def _truncate_task_for_llm(task: dict, full: bool = False) -> dict:
    """Truncate a task dict to fit within LLM context window.

    Args:
        task: Raw task dict from db
        full: If True, include full summary (still truncated to MAX_SUMMARY_CHARS)
    """
    result = {
        "id": task.get("id"),
        "title": task.get("title"),
        "status": task.get("status"),
        "topic": task.get("topic"),
        "folder_id": task.get("folder_id"),
        "author_name": task.get("author_name"),
        "audio_duration": task.get("audio_duration"),
        "created_at": _fmt_dt(task.get("created_at")),
    }
    summary = task.get("summary") or ""
    if full and summary:
        result["summary"] = summary[:MAX_SUMMARY_CHARS]
        if len(summary) > MAX_SUMMARY_CHARS:
            result["summary"] += "\n...(总结已截断)"
    elif summary:
        result["summary_excerpt"] = summary[:200] + ("..." if len(summary) > 200 else "")
    transcript = task.get("transcript") or ""
    if full and transcript:
        result["transcript_excerpt"] = transcript[:MAX_TRANSCRIPT_CHARS]
    return result


def _fmt_dt(val: Any) -> str | None:
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val) if val else None


# ──────────────────────────────────────────────────
#  Tool executor
# ──────────────────────────────────────────────────

async def execute_tool_call(name: str, args: dict) -> dict:
    """Execute a tool call by name with given arguments.

    Uses the db module directly for read operations, and calls
    FastAPI handler functions for write operations (to trigger side
    effects like WebSocket broadcasts and worker queuing).

    Returns a dict with the result, truncated for LLM consumption.
    """
    handler = _TOOL_HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}

    try:
        result = await handler(args)
        return result
    except Exception as e:
        return {"error": f"Tool execution failed: {name} - {str(e)}"}


async def _handle_list_tasks(args: dict) -> dict:
    tasks = db.list_tasks()
    tasks_sorted = sorted(tasks, key=lambda x: x.get("created_at") or "", reverse=True)
    truncated = [_truncate_task_for_llm(t) for t in tasks_sorted[:MAX_TASK_LIST_ITEMS]]
    return {
        "total": len(tasks_sorted),
        "tasks": truncated,
        "note": f"显示前 {min(len(tasks_sorted), MAX_TASK_LIST_ITEMS)} 个任务" if len(tasks_sorted) > MAX_TASK_LIST_ITEMS else None,
    }


async def _handle_get_task(args: dict) -> dict:
    task_id = args.get("task_id")
    if not task_id:
        return {"error": "task_id is required"}
    task = db.get_task(task_id)
    if not task:
        return {"error": f"Task not found: {task_id}"}
    return _truncate_task_for_llm(task, full=True)


async def _handle_create_folder(args: dict) -> dict:
    # Import here to avoid circular dependency and get the actual handler
    from ..api import create_folder, FolderCreate
    folder_in = FolderCreate(
        name=args.get("name", ""),
        parent_id=args.get("parent_id"),
    )
    result = await create_folder(folder_in)
    if isinstance(result, dict):
        return {"id": result.get("id"), "name": result.get("name"), "folder_type": result.get("folder_type")}
    return {"result": str(result)}


async def _handle_list_folders(args: dict) -> dict:
    include_tasks = args.get("include_tasks", False)
    folders = db.list_folders()
    result_list = []
    for f in folders:
        item = {
            "id": f.get("id"),
            "name": f.get("name"),
            "folder_type": f.get("folder_type"),
            "parent_id": f.get("parent_id"),
        }
        if include_tasks:
            item["task_ids"] = [t.get("id") for t in db.list_tasks_in_folder(f.get("id"))]
            item["task_count"] = len(item["task_ids"])
        else:
            # Always include count for convenience
            tasks_in = db.list_tasks_in_folder(f.get("id"))
            item["task_count"] = len(tasks_in)
        result_list.append(item)
    return {"folders": result_list}


async def _handle_assign_task_to_folder(args: dict) -> dict:
    from ..api import assign_task_folder, TaskFolderAssign
    task_id = args.get("task_id", "")
    folder_id = args.get("folder_id")  # Can be None to unassign
    payload = TaskFolderAssign(folder_id=folder_id)
    result = await assign_task_folder(task_id, payload)
    if isinstance(result, dict):
        return {
            "task_id": result.get("id"),
            "title": result.get("title"),
            "folder_id": result.get("folder_id"),
        }
    return {"result": str(result)}


async def _handle_delete_task(args: dict) -> dict:
    from ..api import delete_task
    task_id = args.get("task_id", "")
    # delete_task raises HTTPException(204) on success, so we catch it
    try:
        await delete_task(task_id)
        return {"success": True, "task_id": task_id}
    except Exception:
        # FastAPI returns 204 No Content for successful delete, which
        # may raise an exception in direct call context
        return {"success": True, "task_id": task_id}


async def _handle_re_summarize(args: dict) -> dict:
    from ..api import re_summarize_task, ReSummarizeRequest
    task_id = args.get("task_id", "")
    summary_mode = args.get("summary_mode")
    payload = ReSummarizeRequest(summary_mode=summary_mode) if summary_mode else None
    result = await re_summarize_task(task_id, payload)
    if isinstance(result, dict):
        return {
            "task_id": result.get("id"),
            "title": result.get("title"),
            "status": result.get("status"),
        }
    return {"result": str(result)}


async def _handle_update_task(args: dict) -> dict:
    from ..api import update_task, TaskUpdate
    task_id = args.get("task_id", "")
    topic = args.get("topic")
    task_update = TaskUpdate(topic=topic)
    result = await update_task(task_id, task_update)
    if isinstance(result, dict):
        return {
            "task_id": result.get("id"),
            "title": result.get("title"),
            "topic": result.get("topic"),
        }
    return {"result": str(result)}


async def _handle_delete_folder(args: dict) -> dict:
    from ..api import delete_folder
    folder_id = args.get("folder_id", "")
    try:
        await delete_folder(folder_id)
        return {"success": True, "folder_id": folder_id}
    except Exception:
        return {"success": True, "folder_id": folder_id}


async def _handle_rename_folder(args: dict) -> dict:
    from ..api import update_folder, FolderUpdate
    folder_id = args.get("folder_id", "")
    new_name = args.get("name", "")
    folder_update = FolderUpdate(name=new_name)
    result = await update_folder(folder_id, folder_update)
    if isinstance(result, dict):
        return {
            "id": result.get("id"),
            "name": result.get("name"),
        }
    return {"result": str(result)}


# Handler registry
_TOOL_HANDLERS: dict[str, callable] = {
    "list_tasks": _handle_list_tasks,
    "get_task": _handle_get_task,
    "create_folder": _handle_create_folder,
    "list_folders": _handle_list_folders,
    "assign_task_to_folder": _handle_assign_task_to_folder,
    "delete_task": _handle_delete_task,
    "re_summarize": _handle_re_summarize,
    "update_task": _handle_update_task,
    "delete_folder": _handle_delete_folder,
    "rename_folder": _handle_rename_folder,
}


def format_tool_call_for_display(name: str, args: dict) -> str:
    """Convert a tool call to a human-readable Chinese description."""
    m = {
        "list_tasks": lambda a: "查看所有任务列表",
        "get_task": lambda a: f"查看任务详情「{a.get('task_id', '?')}」",
        "create_folder": lambda a: f"创建文件夹「{a.get('name', '?')}」",
        "list_folders": lambda a: "查看文件夹列表",
        "assign_task_to_folder": lambda a: f"将任务「{a.get('task_id', '?')}」分配到文件夹「{a.get('folder_id', '未分配')}」",
        "delete_task": lambda a: f"⚠️ 删除任务「{a.get('task_id', '?')}」",
        "re_summarize": lambda a: f"重新总结任务「{a.get('task_id', '?')}」（模式：{a.get('summary_mode', 'auto')}）",
        "update_task": lambda a: f"更新任务「{a.get('task_id', '?')}」的主题为「{a.get('topic', '?')}」",
        "delete_folder": lambda a: f"⚠️ 删除文件夹「{a.get('folder_id', '?')}」",
        "rename_folder": lambda a: f"将文件夹「{a.get('folder_id', '?')}」重命名为「{a.get('name', '?')}」",
    }
    fn = m.get(name)
    if fn:
        return fn(args)
    return f"{name}({json.dumps(args, ensure_ascii=False)})"