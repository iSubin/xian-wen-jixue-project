"""先闻继学本地内容存储布局与原始物料固化。"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from .utils.project_root import get_project_root


def _configured_root(env_name: str, default_name: str) -> Path:
    configured = str(os.getenv(env_name) or "").strip()
    if not configured:
        return get_project_root() / default_name
    path = Path(configured).expanduser()
    return path if path.is_absolute() else get_project_root() / path


def get_data_root() -> Path:
    """长期保留的数据根目录，可通过 XIANWEN_DATA_DIR 覆盖。"""
    return _configured_root("XIANWEN_DATA_DIR", "data")


def get_runtime_root() -> Path:
    """可再生运行态根目录，可通过 XIANWEN_RUNTIME_DIR 覆盖。"""
    return _configured_root("XIANWEN_RUNTIME_DIR", "runtime")


def get_exports_root() -> Path:
    return _configured_root("XIANWEN_EXPORTS_DIR", "exports")


def get_originals_root() -> Path:
    return get_data_root() / "originals"


def get_task_assets_root() -> Path:
    return get_data_root() / "assets"


def get_task_assets_dir(task_id: str) -> Path:
    path = get_task_assets_root() / _safe_identifier(task_id, "task")
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_task_download_dir(task_id: str) -> Path:
    path = get_runtime_root() / "downloads" / _safe_identifier(task_id, "task")
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_task_upload_dir(task_id: str) -> Path:
    path = get_runtime_root() / "uploads" / _safe_identifier(task_id, "task")
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_task_work_dir(task_id: str) -> Path:
    path = get_runtime_root() / "tasks" / _safe_identifier(task_id, "task")
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_chunk_debug_dir() -> Path:
    path = get_runtime_root() / "debug" / "chunks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_storage_layout() -> None:
    for path in (
        get_originals_root(),
        get_task_assets_root(),
        get_runtime_root() / "downloads",
        get_runtime_root() / "uploads",
        get_runtime_root() / "tasks",
        get_runtime_root() / "debug" / "chunks",
        get_exports_root(),
    ):
        path.mkdir(parents=True, exist_ok=True)


def _safe_identifier(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(value or "")).strip("._-")
    return cleaned[:120] or fallback


def safe_title_component(value: str, fallback: str = "未命名内容") -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", " ", str(value or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(".")
    return (cleaned or fallback)[:100]


def infer_provider(source_url: str = "", source_type: str = "") -> str:
    kind = str(source_type or "").lower()
    host = (urlparse(str(source_url or "")).hostname or "").lower()
    if "wechat" in kind or "weixin" in host:
        return "wechat"
    if "homeway" in kind or "homeway.com.cn" in host or "vhallyun.com" in host:
        return "homeway"
    if "bilibili" in kind or "bilibili.com" in host or "b23.tv" in host:
        return "bilibili"
    if "xiaoet" in kind or "xiaoeknow.com" in host:
        return "xiaoetong"
    if kind in {"upload", "local_file", "local"} or str(source_url or "").startswith("file://"):
        return "local"
    return _safe_identifier(kind, "generic")


def _content_suffix(content_id: str) -> str:
    cleaned = _safe_identifier(content_id, uuid.uuid4().hex)
    return cleaned[-12:]


def get_original_bundle_dir(
    *,
    content_id: str,
    title: str,
    source_url: str = "",
    source_type: str = "",
    captured_at: datetime | None = None,
) -> Path:
    captured = captured_at or datetime.utcnow()
    provider = infer_provider(source_url, source_type)
    directory = f"{safe_title_component(title)}__{_content_suffix(content_id)}"
    path = get_originals_root() / provider / f"{captured.year:04d}" / directory
    path.mkdir(parents=True, exist_ok=True)
    return path


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_to_data(path: Path) -> str:
    return path.resolve().relative_to(get_data_root().resolve()).as_posix()


def _asset_record(
    path: Path,
    *,
    task_id: str,
    role: str,
    asset_type: str,
    source_url: str = "",
    original_filename: str = "",
) -> dict[str, Any]:
    return {
        "id": uuid.uuid4().hex,
        "task_id": task_id,
        "role": role,
        "asset_type": asset_type,
        "relative_path": _relative_to_data(path),
        "original_filename": original_filename or path.name,
        "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "source_url": source_url or None,
        "status": "available",
    }


def describe_managed_asset(
    path: str | os.PathLike[str],
    *,
    task_id: str,
    role: str,
    asset_type: str,
    source_url: str = "",
    original_filename: str = "",
) -> dict[str, Any]:
    """为 data/ 下已经存在的物料生成可登记记录。"""
    resolved = Path(path)
    if not resolved.is_file():
        raise FileNotFoundError(f"内容物料不存在: {resolved}")
    resolved.resolve().relative_to(get_data_root().resolve())
    return _asset_record(
        resolved,
        task_id=task_id,
        role=role,
        asset_type=asset_type,
        source_url=source_url,
        original_filename=original_filename,
    )


def _write_manifest(bundle_dir: Path, metadata: dict[str, Any], records: Iterable[dict[str, Any]]) -> None:
    manifest_path = bundle_dir / "manifest.json"
    existing: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    assets = {
        str(item.get("relative_path")): item
        for item in existing.get("assets", [])
        if isinstance(item, dict) and item.get("relative_path")
    }
    for record in records:
        assets[str(record["relative_path"])] = {
            key: value
            for key, value in record.items()
            if key not in {"id", "task_id", "status"} and value is not None
        }
    payload = {
        "version": 1,
        **{key: value for key, value in metadata.items() if value not in {None, ""}},
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "assets": sorted(assets.values(), key=lambda item: str(item.get("relative_path"))),
    }
    fd, temp_name = tempfile.mkstemp(prefix="manifest-", suffix=".json", dir=bundle_dir)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp_path, manifest_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def preserve_original_file(
    source_path: str | os.PathLike[str],
    *,
    task_id: str,
    title: str,
    source_url: str = "",
    source_type: str = "video",
    move: bool = True,
    asset_type: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(f"原始物料不存在: {source}")
    bundle_dir = get_original_bundle_dir(
        content_id=task_id,
        title=title,
        source_url=source_url,
        source_type=source_type,
    )
    suffix = source.suffix.lower()
    target = bundle_dir / f"source{suffix}"
    if source.resolve() != target.resolve():
        if target.exists():
            if sha256_file(source) != sha256_file(target):
                target = bundle_dir / f"source__{uuid.uuid4().hex[:8]}{suffix}"
        if not target.exists():
            if move:
                shutil.move(str(source), str(target))
            else:
                shutil.copy2(source, target)
    resolved_type = asset_type or ("audio" if suffix in {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".opus"} else "video")
    record = _asset_record(
        target,
        task_id=task_id,
        role="original",
        asset_type=resolved_type,
        source_url=source_url,
        original_filename=source.name,
    )
    _write_manifest(
        bundle_dir,
        {
            "content_id": task_id,
            "title": title,
            "source_type": source_type,
            "source_url": source_url,
            "captured_at": datetime.utcnow().isoformat() + "Z",
        },
        [record],
    )
    return target, record


def _write_preserved_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f"{path.stem}-", suffix=path.suffix, dir=path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def preserve_article_source(
    *,
    task_id: str,
    content_id: str,
    title: str,
    source_url: str,
    source_type: str,
    raw_html: str = "",
    raw_markdown: str = "",
    asset_paths: Iterable[str | os.PathLike[str]] = (),
) -> list[dict[str, Any]]:
    bundle_dir = get_original_bundle_dir(
        content_id=content_id,
        title=title,
        source_url=source_url,
        source_type=source_type,
    )
    records: list[dict[str, Any]] = []
    if raw_html:
        html_path = bundle_dir / "article.html"
        _write_preserved_text(html_path, raw_html)
        records.append(
            _asset_record(
                html_path,
                task_id=task_id,
                role="original",
                asset_type="article_html",
                source_url=source_url,
            )
        )
    if raw_markdown:
        markdown_path = bundle_dir / "original.md"
        _write_preserved_text(markdown_path, raw_markdown)
        records.append(
            _asset_record(
                markdown_path,
                task_id=task_id,
                role="original",
                asset_type="article_markdown",
                source_url=source_url,
            )
        )
    for raw_path in asset_paths:
        path = Path(raw_path)
        if path.is_file() and path.resolve().is_relative_to(get_data_root().resolve()):
            records.append(
                _asset_record(
                    path,
                    task_id=task_id,
                    role="original",
                    asset_type="image",
                    source_url=source_url,
                )
            )
    _write_manifest(
        bundle_dir,
        {
            "content_id": content_id,
            "task_id": task_id,
            "title": title,
            "source_type": source_type,
            "source_url": source_url,
            "captured_at": datetime.utcnow().isoformat() + "Z",
        },
        records,
    )
    return records


def resolve_data_path(relative_path: str) -> Path:
    candidate = (get_data_root() / str(relative_path or "")).resolve()
    candidate.relative_to(get_data_root().resolve())
    return candidate
