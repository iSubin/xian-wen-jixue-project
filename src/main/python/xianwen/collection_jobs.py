import re
from typing import Any, Dict, Iterable, List

from .db import TaskStatus
from .wechat_article import WechatAccountHistory


TERMINAL_STATUSES = {TaskStatus.COMPLETED.value, TaskStatus.FAILED.value}
RUNNING_STATUSES = {
    TaskStatus.DOWNLOADING.value,
    TaskStatus.UPLOADING.value,
    TaskStatus.TRANSCRIBING.value,
    TaskStatus.SUMMARIZING.value,
}


def extract_urls_from_text(text: str) -> List[str]:
    """Extract unique HTTP(S) URLs from pasted text while preserving order."""
    seen: set[str] = set()
    urls: List[str] = []
    for match in re.finditer(r"https?://[^\s<>\"]+", text or "", re.IGNORECASE):
        url = match.group(0).strip().rstrip("),.;，。；）】》>]")
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def _clean_title(value: Any, fallback: str) -> str:
    title = str(value or "").strip()
    return title or fallback


def build_bilibili_parts_collection(source_url: str, video_info: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Bilibili multi-part video info into generic collection preview data."""
    title = _clean_title(video_info.get("title"), "B 站合集")
    raw_parts = video_info.get("parts") or []
    items = []
    for order, part in enumerate(raw_parts):
        if not isinstance(part, dict):
            continue
        part_index = int(part.get("index") if part.get("index") is not None else order)
        part_title = _clean_title(part.get("title"), f"第 {part_index + 1} 集")
        items.append(
            {
                "provider": "bilibili",
                "source_url": source_url,
                "title": f"P{part_index + 1} {part_title}",
                "part_index": part_index,
                "duration": int(part.get("duration") or 0),
            }
        )

    if not items:
        items.append(
            {
                "provider": "bilibili",
                "source_url": source_url,
                "title": title,
                "part_index": None,
                "duration": int(video_info.get("duration") or 0),
            }
        )

    return {
        "provider": "bilibili",
        "source_type": "bilibili_multi_part" if len(items) > 1 else "single_url",
        "source_url": source_url,
        "title": title,
        "total_items": len(items),
        "items": items,
    }


def build_wechat_history_collection(history: WechatAccountHistory) -> Dict[str, Any]:
    """Convert a WeChat public account history preview into collection preview data."""
    account_name = _clean_title(history.account_name, "微信公众号")
    items = []
    for order, article in enumerate(history.items):
        items.append(
            {
                "provider": "wechat",
                "source_url": article.source_url,
                "title": _clean_title(article.title, f"第 {order + 1} 篇"),
                "part_index": order,
                "duration": None,
            }
        )

    return {
        "provider": "wechat",
        "source_type": "wechat_account_history",
        "source_url": history.source_url,
        "title": f"{account_name} - 公众号历史文章",
        "total_items": len(items),
        "items": items,
    }


def derive_collection_status(items: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    item_list = list(items or [])
    total = len(item_list)
    completed = 0
    failed = 0
    running = 0
    linked = 0

    for item in item_list:
        task = item.get("task")
        status = str((task or {}).get("status") or item.get("status") or "PENDING")
        if item.get("task_id") or task:
            linked += 1
        if status == TaskStatus.COMPLETED.value:
            completed += 1
        elif status == TaskStatus.FAILED.value:
            failed += 1
        elif status in RUNNING_STATUSES:
            running += 1

    if total > 0 and completed == total:
        status = "COMPLETED"
    elif total > 0 and failed > 0 and completed + failed == total:
        status = "FAILED"
    elif running > 0 or linked > 0:
        status = "RUNNING"
    else:
        status = "PENDING"

    return {
        "status": status,
        "total_items": total,
        "completed_items": completed,
        "failed_items": failed,
        "running_items": running,
    }


def build_aggregate_markdown(job: Dict[str, Any], items: Iterable[Dict[str, Any]]) -> str:
    title = _clean_title(job.get("title"), "合集笔记")
    sorted_items = sorted(list(items or []), key=lambda item: int(item.get("sort_order") or 0))
    lines = [f"# {title}", ""]

    completed = 0
    for index, item in enumerate(sorted_items, start=1):
        item_title = _clean_title(item.get("title"), f"第 {index} 集")
        task = item.get("task") or {}
        status = str(task.get("status") or item.get("status") or "PENDING")
        lines.extend([f"## {index}. {item_title}", ""])
        if status == TaskStatus.COMPLETED.value and str(task.get("summary") or "").strip():
            lines.append(str(task.get("summary")).strip())
            completed += 1
        else:
            lines.append(f"> 暂未完成，当前状态：{status}")
        lines.append("")

    lines.insert(2, f"> 已完成 {completed}/{len(sorted_items)} 个条目。")
    lines.insert(3, "")
    return "\n".join(lines).strip() + "\n"
