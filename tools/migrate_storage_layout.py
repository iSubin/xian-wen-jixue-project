#!/usr/bin/env python3
"""把历史 temp/ 与 download/ 内容无损迁移到 data/、runtime/ 分层目录。"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.main.python.xianwen.db import db  # noqa: E402
from src.main.python.xianwen.storage import (  # noqa: E402
    describe_managed_asset,
    ensure_storage_layout,
    get_data_root,
    get_runtime_root,
    get_task_assets_root,
    get_task_work_dir,
    preserve_article_source,
    preserve_original_file,
    sha256_file,
)
from src.main.python.xianwen.utils.media import (  # noqa: E402
    AUDIO_MEDIA_EXTENSIONS,
    VIDEO_MEDIA_EXTENSIONS,
)


def _inventory(roots: list[Path]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            items.append({"path": str(path), "size": path.stat().st_size})
    return items


def _unique_target(target: Path, source: Path) -> Path:
    if not target.exists():
        return target
    if target.stat().st_size == source.stat().st_size and sha256_file(target) == sha256_file(source):
        return target.parent / f"{target.stem}__duplicate_{sha256_file(source)[:8]}{target.suffix}"
    return target.parent / f"{target.stem}__legacy_{sha256_file(source)[:8]}{target.suffix}"


def _move(source: Path, target: Path, moves: list[dict[str, Any]]) -> Path:
    size = source.stat().st_size
    target.parent.mkdir(parents=True, exist_ok=True)
    resolved_target = _unique_target(target, source)
    shutil.move(str(source), str(resolved_target))
    if not resolved_target.is_file() or resolved_target.stat().st_size != size:
        raise RuntimeError(f"迁移校验失败: {source} -> {resolved_target}")
    moves.append({"from": str(source), "to": str(resolved_target), "size": size})
    return resolved_target


def _task_for_file(path: Path, tasks: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    name = path.name
    candidates = [task for task_id, task in tasks.items() if name == task_id or name.startswith(f"{task_id}_") or name.startswith(f"{task_id}.")]
    return max(candidates, key=lambda task: len(str(task.get("id") or ""))) if candidates else None


def _register(record: dict[str, Any], registered: list[dict[str, Any]]) -> None:
    db.upsert_content_asset(record)
    registered.append(record)


def _migrate_task_assets(
    legacy_assets: Path,
    tasks: dict[str, dict[str, Any]],
    moves: list[dict[str, Any]],
    registered: list[dict[str, Any]],
) -> None:
    if not legacy_assets.is_dir():
        return
    target_root = get_task_assets_root()
    for source in sorted(item for item in legacy_assets.rglob("*") if item.is_file()):
        relative = source.relative_to(legacy_assets)
        target = _move(source, target_root / relative, moves)
        task_id = relative.parts[0] if relative.parts else "legacy"
        task = tasks.get(task_id)
        if not task:
            continue
        is_original_image = "images" in relative.parts or "homeway" in relative.parts
        record = describe_managed_asset(
            target,
            task_id=task_id,
            role="original" if is_original_image else "derived",
            asset_type="image" if is_original_image else "frame",
            source_url=str(task.get("source_url") or task.get("video_url") or ""),
        )
        _register(record, registered)


def _migrate_root_file(
    source: Path,
    tasks: dict[str, dict[str, Any]],
    moves: list[dict[str, Any]],
    registered: list[dict[str, Any]],
) -> None:
    task = _task_for_file(source, tasks)
    task_id = str((task or {}).get("id") or "")
    suffix = source.suffix.lower()
    title = str((task or {}).get("title") or source.stem)
    source_url = str((task or {}).get("source_url") or (task or {}).get("video_url") or "")
    source_type = str((task or {}).get("source_type") or "legacy")

    if suffix in VIDEO_MEDIA_EXTENSIONS:
        owner_id = task_id or f"legacy-{sha256_file(source)[:12]}"
        before_size = source.stat().st_size
        target, record = preserve_original_file(
            source,
            task_id=owner_id,
            title=title,
            source_url=source_url,
            source_type=source_type,
            move=True,
            asset_type="video",
        )
        if source.exists():
            target = _move(source, get_runtime_root() / "migration-duplicates" / source.name, moves)
        else:
            moves.append({"from": str(source), "to": str(target), "size": before_size})
        _register(record, registered)
        return

    if suffix in AUDIO_MEDIA_EXTENSIONS and task and str(task.get("video_url") or "").startswith("file://"):
        before_size = source.stat().st_size
        target, record = preserve_original_file(
            source,
            task_id=task_id,
            title=title,
            source_url=source_url,
            source_type="local_file",
            move=True,
            asset_type="audio",
        )
        if source.exists():
            target = _move(source, get_runtime_root() / "migration-duplicates" / source.name, moves)
        else:
            moves.append({"from": str(source), "to": str(target), "size": before_size})
        _register(record, registered)
        return

    if task and source.name.endswith("_wechat_article.md"):
        markdown = source.read_text(encoding="utf-8", errors="replace")
        records = preserve_article_source(
            task_id=task_id,
            content_id=task_id,
            title=title,
            source_url=source_url,
            source_type="wechat_article",
            raw_markdown=markdown,
            asset_paths=(get_task_assets_root() / task_id).rglob("*") if (get_task_assets_root() / task_id).exists() else (),
        )
        for record in records:
            _register(record, registered)

    if task:
        target = get_task_work_dir(task_id) / "legacy" / source.name
    else:
        target = get_runtime_root() / "legacy-unassigned" / source.name
    _move(source, target, moves)


def _preserve_historical_homeway(registered: list[dict[str, Any]]) -> None:
    for subscription in db.list_content_subscriptions("local-user"):
        display_name = str(subscription.get("display_name") or "投研大师")
        for item in db.list_subscription_items(str(subscription["id"])):
            if not item.get("raw_markdown"):
                continue
            digest_task_id = str(item.get("digest_task_id") or "")
            if not digest_task_id:
                digest_task_id = f"homeway-digest-{str(subscription['id'])[:12]}-{str(item.get('digest_date') or '').replace('-', '')}"
            image_paths = []
            for image in item.get("image_manifest") or []:
                relative = str(image.get("relative_path") or "")
                if relative:
                    image_paths.append(get_task_assets_root() / relative)
            published_at = str(item.get("published_at") or "")[:16].replace("T", " ")
            title = f"{display_name}｜{published_at}｜{str(item.get('preview_text') or '')[:48]}"
            records = preserve_article_source(
                task_id=digest_task_id,
                content_id=f"homeway-{item.get('external_item_id')}",
                title=title,
                source_url=str(item.get("source_url") or ""),
                source_type="homeway_article",
                raw_html=str(item.get("raw_html") or ""),
                raw_markdown=str(item.get("raw_markdown") or ""),
                asset_paths=image_paths,
            )
            for record in records:
                _register(record, registered)


def _remove_empty_directories(root: Path) -> None:
    if not root.exists():
        return
    directories = (item for item in root.rglob("*") if item.is_dir())
    for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    try:
        root.rmdir()
    except OSError:
        pass


def migrate(*, apply: bool) -> dict[str, Any]:
    legacy_temp = PROJECT_ROOT / "temp"
    legacy_download = PROJECT_ROOT / "download"
    before = _inventory([legacy_temp, legacy_download])
    plan = {
        "version": 1,
        "mode": "apply" if apply else "dry-run",
        "legacy_file_count": len(before),
        "legacy_bytes": sum(item["size"] for item in before),
        "target_layout": {
            "originals": str(get_data_root() / "originals"),
            "assets": str(get_task_assets_root()),
            "downloads": str(get_runtime_root() / "downloads"),
            "uploads": str(get_runtime_root() / "uploads"),
            "task_work": str(get_runtime_root() / "tasks"),
        },
    }
    if not apply:
        return plan

    ensure_storage_layout()
    tasks = {str(task.get("id") or ""): task for task in db.list_tasks()}
    moves: list[dict[str, Any]] = []
    registered: list[dict[str, Any]] = []
    _migrate_task_assets(legacy_temp / "task-assets", tasks, moves, registered)
    if legacy_temp.is_dir():
        for source in sorted(item for item in legacy_temp.iterdir() if item.is_file()):
            _migrate_root_file(source, tasks, moves, registered)
    if legacy_download.is_dir():
        for source in sorted(item for item in legacy_download.rglob("*") if item.is_file()):
            _migrate_root_file(source, tasks, moves, registered)
    _preserve_historical_homeway(registered)

    for move in moves:
        target = Path(move["to"])
        if not target.is_file() or target.stat().st_size != move["size"]:
            raise RuntimeError(f"迁移后复核失败: {move}")
    _remove_empty_directories(legacy_temp)
    _remove_empty_directories(legacy_download)

    report = {
        **plan,
        "completed_at": datetime.utcnow().isoformat() + "Z",
        "moved_file_count": len(moves),
        "moved_bytes": sum(move["size"] for move in moves),
        "registered_asset_count": len(registered),
        "legacy_temp_exists": legacy_temp.exists(),
        "legacy_download_exists": legacy_download.exists(),
        "moves": moves,
    }
    report_dir = get_data_root() / "migrations"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "storage-layout-v1.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="执行迁移；默认只展示计划")
    args = parser.parse_args()
    result = migrate(apply=args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
