from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable
from urllib.parse import urlparse

from .utils.project_root import get_project_root


MANIFEST_NAME = ".xianwen-manifest.json"
DEFAULT_ROOT_PATH = "先闻继学"
_BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
_SCP_REPOSITORY_PATTERN = re.compile(
    r"^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:[A-Za-z0-9._~/-]+(?:\.git)?$"
)
_INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class GitSyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeneratedFile:
    content: bytes
    task_id: str | None = None
    content_directory: str | None = None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


def validate_repository_url(value: str) -> str:
    repository_url = str(value or "").strip()
    if not repository_url or "\n" in repository_url or "\r" in repository_url:
        raise GitSyncError("Git 仓库地址不能为空")
    if _SCP_REPOSITORY_PATTERN.fullmatch(repository_url):
        return repository_url

    parsed = urlparse(repository_url)
    if parsed.scheme != "ssh" or not parsed.hostname or not parsed.path:
        raise GitSyncError("Deploy Key 仅支持 SSH 仓库地址，例如 git@github.com:owner/repo.git")
    if parsed.password:
        raise GitSyncError("仓库地址中不能包含密码")
    return repository_url


def validate_branch(value: str) -> str:
    branch = str(value or "").strip()
    if (
        not _BRANCH_PATTERN.fullmatch(branch)
        or ".." in branch
        or "@{" in branch
        or branch.endswith(("/", ".", ".lock"))
    ):
        raise GitSyncError("Git 分支名不合法")
    return branch


def validate_root_path(value: str) -> str:
    raw = str(value or DEFAULT_ROOT_PATH).strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", "..", ".git"} for part in path.parts)
    ):
        raise GitSyncError("文档目录必须是仓库内的相对路径")
    return path.as_posix()


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: Dict[str, str] | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitSyncError(f"系统缺少命令：{command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitSyncError(f"命令执行超时：{command[0]}") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "未知错误").strip()
        if len(detail) > 1200:
            detail = detail[-1200:]
        raise GitSyncError(detail)
    return result


def _write_private_key(directory: Path, private_key: str) -> Path:
    normalized = str(private_key or "").strip()
    if "PRIVATE KEY-----" not in normalized:
        raise GitSyncError("请上传 OpenSSH 或 PEM 格式的 SSH 私钥")
    key_path = directory / "deploy_key"
    descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(normalized)
        handle.write("\n")
    return key_path


def derive_public_key(private_key: str) -> str:
    with tempfile.TemporaryDirectory(prefix="xianwen-key-") as temp_dir:
        key_path = _write_private_key(Path(temp_dir), private_key)
        try:
            result = _run(["ssh-keygen", "-y", "-f", str(key_path)], timeout=15)
        except GitSyncError as exc:
            raise GitSyncError("Deploy Key 私钥无效，或私钥带有暂不支持的口令") from exc
        public_key = result.stdout.strip()
        if not public_key.startswith(("ssh-", "ecdsa-")):
            raise GitSyncError("无法从私钥解析公钥")
        return public_key


def _git_environment(key_path: Path) -> Dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = " ".join(
        [
            "ssh",
            "-i",
            shlex.quote(str(key_path)),
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "LogLevel=ERROR",
        ]
    )
    return env


def test_git_connection(repository_url: str, branch: str, private_key: str) -> Dict[str, Any]:
    repository_url = validate_repository_url(repository_url)
    branch = validate_branch(branch)
    public_key = derive_public_key(private_key)

    with tempfile.TemporaryDirectory(prefix="xianwen-git-test-") as temp_dir:
        key_path = _write_private_key(Path(temp_dir), private_key)
        result = _run(
            ["git", "ls-remote", "--heads", repository_url, f"refs/heads/{branch}"],
            env=_git_environment(key_path),
            timeout=45,
        )
        if not result.stdout.strip():
            raise GitSyncError(f"已连接仓库，但没有找到分支 {branch}")
    return {"success": True, "branch": branch, "public_key": public_key}


def _safe_component(value: str, fallback: str) -> str:
    normalized = _INVALID_PATH_CHARS.sub("-", str(value or "").strip())
    normalized = re.sub(r"\s+", " ", normalized).strip(" .")
    if not normalized:
        normalized = fallback
    if normalized.startswith("."):
        normalized = normalized.lstrip(".") or fallback
    return normalized[:120]


def _folder_components(folders: list[Dict[str, Any]]) -> Dict[str, str]:
    grouped: Dict[tuple[str, str], list[Dict[str, Any]]] = {}
    for folder in folders:
        base = _safe_component(folder.get("name") or "", "未命名目录")
        key = (str(folder.get("parent_id") or ""), base)
        grouped.setdefault(key, []).append(folder)

    result: Dict[str, str] = {}
    for (_, base), siblings in grouped.items():
        siblings.sort(key=lambda item: str(item.get("id") or ""))
        for folder in siblings:
            folder_id = str(folder.get("id") or "")
            result[folder_id] = base if len(siblings) == 1 else f"{base}-{folder_id[:6]}"
    return result


def _build_folder_paths(folders: list[Dict[str, Any]]) -> Dict[str, PurePosixPath]:
    by_id = {str(folder.get("id") or ""): folder for folder in folders}
    components = _folder_components(folders)
    resolved: Dict[str, PurePosixPath] = {}

    def resolve(folder_id: str, stack: set[str]) -> PurePosixPath:
        if folder_id in resolved:
            return resolved[folder_id]
        folder = by_id.get(folder_id)
        if not folder or folder_id in stack:
            return PurePosixPath("未归档")

        component = components.get(folder_id, "未命名目录")
        parent_id = str(folder.get("parent_id") or "")
        if parent_id and parent_id in by_id:
            parent = resolve(parent_id, stack | {folder_id})
            path = parent / component
        else:
            path = PurePosixPath(component)
        resolved[folder_id] = path
        return path

    for current_id in by_id:
        resolve(current_id, set())
    return resolved


def _frontmatter_value(value: Any) -> str:
    if value is None:
        return '""'
    return json.dumps(str(value), ensure_ascii=False)


def _metadata_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            payload = json.loads(value)
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _source_title(task: Dict[str, Any]) -> str:
    source_meta = _metadata_dict(task.get("source_meta"))
    title = str(
        task.get("title")
        or source_meta.get("title")
        or task.get("topic")
        or "未命名内容"
    ).strip()
    return re.sub(r"\s+", " ", title) or "未命名内容"


def _public_source_url(task: Dict[str, Any]) -> str:
    source_url = str(task.get("source_url") or task.get("video_url") or "").strip()
    return "" if source_url.startswith("file://") else source_url


def _raw_document_name(task: Dict[str, Any]) -> str:
    source_type = str(task.get("source_type") or "video").strip().lower()
    if source_type in {"article", "wechat_article", "web_article", "document"}:
        return "原始正文.md"
    return "原始逐字稿.md"


def _render_document(task: Dict[str, Any], summary: str, raw_document_name: str | None) -> str:
    title = _source_title(task)
    source_url = _public_source_url(task)
    source_meta = _metadata_dict(task.get("source_meta"))
    author = str(
        task.get("author_name")
        or source_meta.get("author")
        or source_meta.get("account_name")
        or ""
    ).strip()
    published_at = str(
        source_meta.get("published_at")
        or source_meta.get("publish_time")
        or ""
    ).strip()
    lines = [
        "---",
        f"xianwen_id: {_frontmatter_value(task.get('id'))}",
        f"title: {_frontmatter_value(title)}",
        f"source_type: {_frontmatter_value(task.get('source_type') or 'video')}",
        f"source_url: {_frontmatter_value(source_url)}",
        f"author: {_frontmatter_value(author)}",
        f"published_at: {_frontmatter_value(published_at)}",
        f"captured_at: {_frontmatter_value(task.get('created_at'))}",
        f"updated_at: {_frontmatter_value(task.get('latest_modified_at'))}",
        "tags:",
        "  - 先闻继学",
        "  - 知识采集",
        "---",
        "",
        f"# {title}",
        "",
    ]
    source_details: list[str] = []
    if author:
        source_details.append(author)
    if published_at:
        source_details.append(published_at)
    if source_url:
        source_details.append(f"[查看原始来源]({source_url})")
    if source_details or raw_document_name:
        lines.append("> [!info] 内容来源")
        if source_details:
            lines.append(f"> {' · '.join(source_details)}")
        if raw_document_name:
            lines.append(f"> 原始材料：[[{raw_document_name[:-3]}]]")
        lines.append("")
    if summary:
        lines.extend(["## 整理稿", "", summary.strip(), ""])
    return "\n".join(lines).rstrip() + "\n"


def _render_raw_document(
    task: Dict[str, Any],
    transcript: str,
    raw_document_name: str,
    main_note_name: str,
) -> str:
    title = _source_title(task)
    raw_title = raw_document_name[:-3]
    lines = [
        f"# {raw_title}",
        "",
        f"> 对应整理稿：{_obsidian_link(main_note_name, title)}",
        "",
        transcript.strip(),
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _assign_content_directory_names(
    tasks: list[Dict[str, Any]],
    existing_names: Dict[str, str] | None,
) -> Dict[str, str]:
    existing_names = existing_names or {}
    assigned: Dict[str, str] = {}
    used: set[str] = set()

    for task in tasks:
        task_id = str(task.get("id") or "")
        previous_name = str(existing_names.get(task_id) or "").strip()
        if not previous_name:
            continue
        safe_name = _safe_component(previous_name, "未命名内容")
        if safe_name in used:
            continue
        assigned[task_id] = safe_name
        used.add(safe_name)

    for task in tasks:
        task_id = str(task.get("id") or "")
        if task_id in assigned:
            continue
        base_name = _safe_component(_source_title(task), "未命名内容")
        directory_name = base_name
        if directory_name in used:
            suffix = _safe_component(task_id[:8], "内容")
            postfix = f"__{suffix}"
            directory_name = f"{base_name[: 120 - len(postfix)].rstrip(' .')}{postfix}"
            counter = 2
            while directory_name in used:
                postfix = f"__{suffix}-{counter}"
                directory_name = f"{base_name[: 120 - len(postfix)].rstrip(' .')}{postfix}"
                counter += 1
        assigned[task_id] = directory_name
        used.add(directory_name)
    return assigned


def _obsidian_link(path: PurePosixPath | str, title: str) -> str:
    value = PurePosixPath(path).as_posix()
    if value.endswith(".md"):
        value = value[:-3]
    label = str(title or value).replace("|", "｜").replace("]", "］").replace("[", "［")
    return f"[[{value}|{label}]]"


def build_library_files(
    task_db: Any,
    *,
    include_transcript: bool = True,
    project_root: Path | None = None,
    content_directory_names: Dict[str, str] | None = None,
) -> tuple[Dict[str, GeneratedFile], int]:
    folders = task_db.list_folders()
    folder_paths = _build_folder_paths(folders)
    tasks = task_db.list_library_documents()
    tasks.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")))
    directory_names = _assign_content_directory_names(tasks, content_directory_names)

    generated: Dict[str, GeneratedFile] = {}
    document_index: list[tuple[str, str, str]] = []
    root = project_root or get_project_root()

    for task in tasks:
        task_id = str(task.get("id") or "")
        folder_id = str(task.get("folder_id") or "")
        title = _source_title(task)
        directory_name = directory_names[task_id]
        content_root = PurePosixPath("内容") / directory_name
        relative_path = (content_root / f"{directory_name}.md").as_posix()

        summary = str(task.get("summary") or "")
        transcript = str(task.get("transcript") or "")
        asset_root = content_root / "assets"
        asset_reference = "assets/"
        source_asset_prefix = f"/task-assets/{task_id}/"
        summary = summary.replace(source_asset_prefix, asset_reference)
        transcript = transcript.replace(source_asset_prefix, asset_reference)

        raw_document_name = _raw_document_name(task) if include_transcript and transcript else None
        content = _render_document(task, summary, raw_document_name)
        generated[relative_path] = GeneratedFile(
            content.encode("utf-8"),
            task_id=task_id,
            content_directory=directory_name,
        )
        document_index.append((relative_path, title, folder_id))

        if raw_document_name:
            raw_path = (content_root / raw_document_name).as_posix()
            raw_content = _render_raw_document(task, transcript, raw_document_name, directory_name)
            generated[raw_path] = GeneratedFile(
                raw_content.encode("utf-8"),
                task_id=task_id,
                content_directory=directory_name,
            )

        local_asset_dir = root / "temp" / "task-assets" / task_id
        if local_asset_dir.is_dir():
            referenced_content = summary + (transcript if include_transcript else "")
            for asset in sorted(path for path in local_asset_dir.rglob("*") if path.is_file()):
                asset_rel = asset.relative_to(local_asset_dir).as_posix()
                if asset_rel not in referenced_content:
                    continue
                target_rel = (asset_root / asset_rel).as_posix()
                generated[target_rel] = GeneratedFile(
                    asset.read_bytes(),
                    task_id=task_id,
                    content_directory=directory_name,
                )

    folders_by_parent: Dict[str, list[Dict[str, Any]]] = {}
    for folder in folders:
        parent_id = str(folder.get("parent_id") or "")
        folders_by_parent.setdefault(parent_id, []).append(folder)
    for children in folders_by_parent.values():
        children.sort(key=lambda item: (int(item.get("sort_order") or 0), str(item.get("name") or "")))

    documents_by_folder: Dict[str, list[tuple[str, str]]] = {}
    for path, title, folder_id in document_index:
        documents_by_folder.setdefault(folder_id, []).append((path, title))
    for documents in documents_by_folder.values():
        documents.sort(key=lambda item: item[1])

    for folder in folders:
        folder_id = str(folder.get("id") or "")
        folder_path = folder_paths.get(folder_id, PurePosixPath("未归档"))
        index_path = PurePosixPath("藏经阁") / folder_path / "_目录.md"
        lines = [f"# {folder.get('name') or '未命名目录'}", ""]
        child_folders = folders_by_parent.get(folder_id, [])
        if child_folders:
            lines.extend(["## 子目录", ""])
            for child in child_folders:
                child_path = folder_paths.get(str(child.get("id") or ""), PurePosixPath("未归档"))
                lines.append(
                    f"- {_obsidian_link(PurePosixPath('藏经阁') / child_path / '_目录.md', str(child.get('name') or '未命名目录'))}"
                )
            lines.append("")
        documents = documents_by_folder.get(folder_id, [])
        if documents:
            lines.extend(["## 内容", ""])
            for path, document_title in documents:
                lines.append(f"- {_obsidian_link(path, document_title)}")
            lines.append("")
        if not child_folders and not documents:
            lines.extend(["> 此目录暂无内容。", ""])
        generated[index_path.as_posix()] = GeneratedFile("\n".join(lines).encode("utf-8"))

    library_lines = ["# 藏经阁", "", "> 内容正文只在 `内容/` 保存一份；藏经阁通过目录索引组织阅读。", ""]
    root_folders = folders_by_parent.get("", [])
    if root_folders:
        library_lines.extend(["## 目录", ""])
        for folder in root_folders:
            folder_path = folder_paths.get(str(folder.get("id") or ""), PurePosixPath("未归档"))
            library_lines.append(
                f"- {_obsidian_link(PurePosixPath('藏经阁') / folder_path / '_目录.md', str(folder.get('name') or '未命名目录'))}"
            )
        library_lines.append("")
    unfiled = documents_by_folder.get("", [])
    if unfiled:
        library_lines.extend(["## 未归档", ""])
        for path, document_title in unfiled:
            library_lines.append(f"- {_obsidian_link(path, document_title)}")
        library_lines.append("")
    generated["藏经阁/_索引.md"] = GeneratedFile("\n".join(library_lines).encode("utf-8"))

    index_lines = [
        "# 先闻继学 · 知识库",
        "",
        "> 先闻万象，继学不息。",
        "",
        f"共收录 **{len(document_index)}** 篇内容。正文按原始标题归档，目录与专题只负责组织关系。",
        "",
        f"- {_obsidian_link('藏经阁/_索引.md', '进入藏经阁')}",
        "- `专题/` 将用于后续专题管理，并引用 `内容/` 中的同一份正文。",
        "",
        "## 全部内容",
        "",
    ]
    for path, title, _ in sorted(document_index, key=lambda item: item[1]):
        index_lines.append(f"- {_obsidian_link(path, title)}")
    index_lines.append("")
    generated["_索引.md"] = GeneratedFile("\n".join(index_lines).encode("utf-8"))
    return generated, len(document_index)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(root_dir: Path) -> Dict[str, Any]:
    path = root_dir / MANIFEST_NAME
    if not path.exists():
        return {"version": 2, "files": {}, "content_directories": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("files"), dict):
            if not isinstance(payload.get("content_directories"), dict):
                payload["content_directories"] = {}
            return payload
    except (OSError, json.JSONDecodeError):
        pass
    return {"version": 2, "files": {}, "content_directories": {}}


def _cleanup_empty_directories(root_dir: Path) -> None:
    for directory in sorted(
        (path for path in root_dir.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            continue


def apply_managed_files(
    repository_dir: Path,
    root_path: str,
    generated: Dict[str, GeneratedFile],
) -> Dict[str, Any]:
    root_path = validate_root_path(root_path)
    root_dir = repository_dir / Path(*PurePosixPath(root_path).parts)
    root_dir.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest(root_dir)
    previous_files = manifest.get("files") or {}
    next_files: Dict[str, Dict[str, Any]] = {}
    content_directories: Dict[str, str] = {}
    conflicts: list[str] = []
    created = 0
    updated = 0
    adopted = 0
    removed = 0

    for relative_path, artifact in sorted(generated.items()):
        if artifact.task_id and artifact.content_directory:
            content_directories[artifact.task_id] = artifact.content_directory
        target = root_dir / Path(*PurePosixPath(relative_path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        desired_hash = artifact.sha256
        previous = previous_files.get(relative_path)
        current_hash = _file_sha256(target) if target.is_file() else None

        if current_hash is not None:
            previous_hash = str((previous or {}).get("sha256") or "")
            externally_modified = bool(previous_hash and current_hash != previous_hash)
            unmanaged_collision = not previous and current_hash != desired_hash
            if (externally_modified or unmanaged_collision) and current_hash != desired_hash:
                conflicts.append(relative_path)
                if previous:
                    next_files[relative_path] = previous
                continue
            if current_hash == desired_hash:
                if not previous:
                    adopted += 1
                next_files[relative_path] = {
                    "sha256": desired_hash,
                    "task_id": artifact.task_id,
                }
                continue

        target.write_bytes(artifact.content)
        if current_hash is None:
            created += 1
        else:
            updated += 1
        next_files[relative_path] = {
            "sha256": desired_hash,
            "task_id": artifact.task_id,
        }

    for relative_path, previous in sorted(previous_files.items()):
        if relative_path in generated:
            continue
        target = root_dir / Path(*PurePosixPath(relative_path).parts)
        if not target.exists():
            continue
        previous_hash = str((previous or {}).get("sha256") or "")
        if target.is_file() and previous_hash and _file_sha256(target) == previous_hash:
            target.unlink()
            removed += 1
        else:
            conflicts.append(relative_path)
            next_files[relative_path] = previous

    manifest_payload = {
        "version": 2,
        "product": "先闻继学",
        "content_directories": dict(sorted(content_directories.items())),
        "files": next_files,
    }
    manifest_path = root_dir / MANIFEST_NAME
    serialized_manifest = (
        json.dumps(manifest_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    if not manifest_path.exists() or manifest_path.read_text(encoding="utf-8") != serialized_manifest:
        manifest_path.write_text(serialized_manifest, encoding="utf-8")
    _cleanup_empty_directories(root_dir)

    return {
        "created": created,
        "updated": updated,
        "adopted": adopted,
        "removed": removed,
        "conflicts": sorted(set(conflicts)),
    }


def sync_library_to_git(
    task_db: Any,
    *,
    repository_url: str,
    branch: str,
    root_path: str,
    private_key: str,
    author_name: str,
    author_email: str,
    include_transcript: bool,
) -> Dict[str, Any]:
    repository_url = validate_repository_url(repository_url)
    branch = validate_branch(branch)
    root_path = validate_root_path(root_path)
    derive_public_key(private_key)
    with tempfile.TemporaryDirectory(prefix="xianwen-git-sync-") as temp_dir:
        temp_path = Path(temp_dir)
        key_path = _write_private_key(temp_path, private_key)
        repository_dir = temp_path / "repository"
        env = _git_environment(key_path)
        _run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--single-branch",
                "--branch",
                branch,
                repository_url,
                str(repository_dir),
            ],
            env=env,
            timeout=120,
        )
        root_dir = repository_dir / Path(*PurePosixPath(root_path).parts)
        manifest = _load_manifest(root_dir)
        generated, document_count = build_library_files(
            task_db,
            include_transcript=include_transcript,
            content_directory_names=manifest.get("content_directories") or {},
        )
        result = apply_managed_files(repository_dir, root_path, generated)
        _run(["git", "config", "user.name", author_name or "先闻继学"], cwd=repository_dir)
        _run(
            ["git", "config", "user.email", author_email or "xianwen@localhost"],
            cwd=repository_dir,
        )
        _run(["git", "add", "--", root_path], cwd=repository_dir)
        status = _run(
            ["git", "status", "--porcelain", "--", root_path],
            cwd=repository_dir,
        ).stdout.strip()

        committed = bool(status)
        commit_sha = ""
        if committed:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            _run(
                ["git", "commit", "-m", f"docs: 同步先闻继学文库 {timestamp}"],
                cwd=repository_dir,
            )
            commit_sha = _run(
                ["git", "rev-parse", "HEAD"],
                cwd=repository_dir,
            ).stdout.strip()
            _run(["git", "push", "origin", branch], cwd=repository_dir, env=env, timeout=120)

    return {
        "success": True,
        "document_count": document_count,
        "committed": committed,
        "commit_sha": commit_sha,
        **result,
    }
