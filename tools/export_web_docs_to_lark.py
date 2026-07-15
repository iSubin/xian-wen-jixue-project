#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_markdown


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INCLUDE_PREFIXES = ("quickstart", "features", "practical", "advanced", "docs")
SECTION_TITLES = {
    "quickstart": "快速上手",
    "features": "功能详解",
    "practical": "实践案例",
    "advanced": "进阶内容",
    "docs": "文档资料",
}
SEGMENT_TITLES = {
    **SECTION_TITLES,
    "claude-md": "CLAUDE.md",
    "mcp": "MCP",
    "skill": "Skill",
    "subagent": "SubAgent",
    "hooks": "Hooks",
    "commands": "命令系统",
    "context": "上下文管理",
    "conversation": "对话管理",
    "cross-platform": "跨平台与远程",
    "file-operations": "文件与项目操作",
    "interaction": "交互方式",
    "plugins": "Plugins",
    "prompting": "提示工程",
    "reference": "参考资料",
    "security": "权限与安全",
    "settings": "系统配置",
    "workflow": "工作流",
    "changelog": "更新日志",
}
DEFAULT_PARENT_WIKI_URL = "https://zcnfhebiqluf.feishu.cn/wiki/NCTJwyCXPiATifkzgzMctKZpnYf"


@dataclass
class CapturedPage:
    url: str
    status: int
    title: str
    content_html: str
    text_length: int

    @property
    def path(self) -> str:
        return canonical_path(self.url)

    @property
    def section(self) -> str:
        parts = [part for part in self.path.split("/") if part]
        return parts[0] if parts else "home"


class CallbackHandler(BaseHTTPRequestHandler):
    payload: dict[str, Any] | None = None
    error: str | None = None
    event = threading.Event()

    def log_message(self, _: str, *args: Any) -> None:
        return

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length)
            CallbackHandler.payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            CallbackHandler.error = str(exc)
        finally:
            CallbackHandler.event.set()
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def canonical_url(url: str) -> str:
    parsed = urlparse(url)
    path = re.sub(r"/+", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def resolve_url(href: str, base_url: str) -> str:
    try:
        from urllib.parse import urljoin

        return canonical_url(urljoin(base_url, href))
    except Exception:
        return ""


def canonical_path(url: str) -> str:
    parsed = urlparse(canonical_url(url))
    return parsed.path or "/"


def is_valid_doc_path(url: str, include_prefixes: tuple[str, ...]) -> bool:
    path = canonical_path(url)
    if path == "/":
        return False
    first = path.strip("/").split("/", 1)[0]
    return first in include_prefixes


def is_allowed_discovery_url(url: str, origin: str, include_prefixes: tuple[str, ...]) -> bool:
    parsed = urlparse(url)
    if f"{parsed.scheme}://{parsed.netloc}" != origin:
        return False
    path = canonical_path(url)
    if path == "/":
        return True
    first = path.strip("/").split("/", 1)[0]
    return first in include_prefixes


def sanitize_title(title: str, fallback: str = "未命名页面") -> str:
    value = re.sub(r"\s+", " ", str(title or "")).strip()
    value = re.sub(r"[\\/:*?\"<>|#]", " ", value).strip()
    value = re.sub(r"\s+", " ", value)
    return (value or fallback)[:80]


def markdown_filename(page: CapturedPage, index: int) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", page.path.strip("/"))[:80].strip("-")
    return f"{index:03d}-{slug or 'page'}.md"


def clean_markdown(markdown: str) -> str:
    lines: list[str] = []
    blank = 0
    for line in markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = line.rstrip()
        if not stripped:
            blank += 1
            if blank <= 1:
                lines.append("")
            continue
        blank = 0
        lines.append(stripped)
    return "\n".join(lines).strip()


def page_to_markdown(page: CapturedPage) -> str:
    soup = BeautifulSoup(page.content_html or "", "lxml")
    for selector in ("script", "style", "noscript", "button", "svg"):
        for tag in soup.select(selector):
            tag.decompose()
    markdown = clean_markdown(html_to_markdown(str(soup), heading_style="ATX"))
    title = sanitize_title(page.title)
    if markdown.startswith(f"# {title}"):
        body = markdown
    else:
        body = f"# {title}\n\n{markdown}".strip()
    return f"> 原文链接：{page.url}\n\n{body}\n"


def extract_content_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "lxml")
    for selector in ("script", "style", "noscript", "header", "footer"):
        for tag in soup.select(selector):
            tag.decompose()

    content = soup.select_one(".mx-auto.flex.w-full")
    if content and len(content.get_text("\n", strip=True)) >= 120:
        return str(content)

    content = soup.select_one(".relative.pb-4")
    if content and len(content.get_text("\n", strip=True)) >= 120:
        title = soup.find("h1")
        if title:
            wrapper = BeautifulSoup("<div></div>", "lxml").div
            wrapper.append(BeautifulSoup(f"<h1>{title.get_text(' ', strip=True)}</h1>", "lxml"))
            wrapper.append(content)
            return str(wrapper)
        return str(content)

    main = soup.select_one("main article") or soup.select_one("article") or soup.select_one("main") or soup.body
    return str(main or "")


def extract_page_title(html: str, fallback_url: str) -> str:
    soup = BeautifulSoup(html or "", "lxml")
    h1 = soup.find("h1")
    if h1:
        return sanitize_title(h1.get_text(" ", strip=True))
    if soup.title:
        return sanitize_title(re.sub(r"\s+-\s+Claude Code.*$", "", soup.title.get_text(" ", strip=True)))
    return sanitize_title(canonical_path(fallback_url).rsplit("/", 1)[-1])


def discover_urls_with_requests(
    *,
    start_url: str,
    max_pages: int,
    include_prefixes: tuple[str, ...],
) -> list[str]:
    origin = f"{urlparse(start_url).scheme}://{urlparse(start_url).netloc}"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 Chrome/120 Safari/537.36"})
    queue = [canonical_url(start_url)]
    queued = set(queue)
    seen: set[str] = set()
    discovered: list[str] = []

    while queue and len(seen) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        if is_valid_doc_path(url, include_prefixes):
            discovered.append(url)
        try:
            response = session.get(url, timeout=20)
            if response.status_code >= 400:
                continue
            soup = BeautifulSoup(response.text, "lxml")
        except Exception:
            continue
        for anchor in soup.find_all("a", href=True):
            link = resolve_url(str(anchor.get("href") or ""), url)
            if not link or link in queued or link in seen:
                continue
            if is_allowed_discovery_url(link, origin, include_prefixes):
                queued.add(link)
                queue.append(link)
    return discovered[:max_pages]


def applescript_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def fetch_html_from_chrome(url: str, *, start_url: str) -> tuple[int, str]:
    origin = f"{urlparse(start_url).scheme}://{urlparse(start_url).netloc}"
    js = (
        "var xhr=new XMLHttpRequest();"
        f"xhr.open('GET',{json.dumps(url)},false);"
        "xhr.withCredentials=true;"
        "xhr.send();"
        "JSON.stringify({status:xhr.status,html:xhr.responseText||''})"
    )
    script = f"""
tell application "Google Chrome"
  activate
  if (count of windows) = 0 then make new window
  set resultText to ""
  set foundTab to false
  repeat with chromeWindow in windows
    repeat with chromeTab in tabs of chromeWindow
      try
        if (URL of chromeTab starts with {applescript_string(origin)}) then
          tell chromeTab
            set resultText to execute javascript {applescript_string(js)}
          end tell
          set foundTab to true
          exit repeat
        end if
      end try
    end repeat
    if foundTab then exit repeat
  end repeat
  if not foundTab then
    set URL of active tab of front window to {applescript_string(start_url)}
    repeat 80 times
      delay 0.5
      try
        tell active tab of front window
          set readyState to execute javascript "document.readyState"
        end tell
        if readyState is "complete" then exit repeat
      end try
    end repeat
    tell active tab of front window
      set resultText to execute javascript {applescript_string(js)}
    end tell
  end if
  return resultText
end tell
"""
    result = subprocess.run(["osascript", "-e", script], text=True, capture_output=True, timeout=45)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Chrome XHR 读取失败")
    data = json.loads(result.stdout)
    return int(data.get("status") or 0), str(data.get("html") or "")


def capture_pages_via_chrome_xhr(
    *,
    start_url: str,
    export_dir: Path,
    max_pages: int,
    include_prefixes: tuple[str, ...],
) -> dict[str, Any]:
    urls = discover_urls_with_requests(
        start_url=start_url,
        max_pages=max_pages,
        include_prefixes=include_prefixes,
    )
    pages: list[dict[str, Any]] = []
    for url in urls:
        try:
            status, html = fetch_html_from_chrome(url, start_url=start_url)
            content_html = extract_content_html(html)
            text_length = len(BeautifulSoup(content_html, "lxml").get_text("", strip=True))
            pages.append(
                {
                    "url": canonical_url(url),
                    "status": status,
                    "ok": 200 <= status < 300,
                    "title": extract_page_title(html, url),
                    "contentHtml": content_html,
                    "textLength": text_length,
                }
            )
        except Exception as exc:
            pages.append(
                {
                    "url": canonical_url(url),
                    "status": 0,
                    "ok": False,
                    "title": "",
                    "contentHtml": "",
                    "textLength": 0,
                    "error": str(exc),
                }
            )
        time.sleep(0.2)

    payload = {
        "startUrl": start_url,
        "capturedAt": datetime.now().isoformat(),
        "discoveredCount": len(urls),
        "pages": pages,
    }
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "capture.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def parse_captured_pages(payload: dict[str, Any], include_prefixes: tuple[str, ...]) -> list[CapturedPage]:
    pages: list[CapturedPage] = []
    seen_paths: set[str] = set()
    for raw in payload.get("pages") or []:
        url = canonical_url(str(raw.get("url") or ""))
        if not url or not is_valid_doc_path(url, include_prefixes):
            continue
        path = canonical_path(url)
        if path in seen_paths:
            continue
        status = int(raw.get("status") or 0)
        title = sanitize_title(raw.get("title") or raw.get("h1") or path.rsplit("/", 1)[-1])
        content_html = str(raw.get("contentHtml") or "")
        text_length = int(raw.get("textLength") or 0)
        if status != 200 or "404" in title or text_length < 120 or not content_html.strip():
            continue
        seen_paths.add(path)
        pages.append(CapturedPage(url=url, status=status, title=title, content_html=content_html, text_length=text_length))
    pages.sort(key=lambda page: page.path)
    return pages


def write_markdown_files_by_path(pages: list[CapturedPage], export_dir: Path) -> dict[str, Path]:
    pages_dir = export_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}
    for index, page in enumerate(pages, start=1):
        path = pages_dir / markdown_filename(page, index)
        path.write_text(page_to_markdown(page), encoding="utf-8")
        files[page.path] = path
    return files


def directory_markdown_path(export_dir: Path, path_key: str, title: str) -> Path:
    dirs_dir = export_dir / "directories"
    dirs_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", path_key.strip("/"))[:80].strip("-") or "root"
    path = dirs_dir / f"{slug}.md"
    path.write_text(
        f"# {title}\n\n此节点用于保持原网站目录层级，子页面按原路径挂载在当前节点下。\n",
        encoding="utf-8",
    )
    return path


def title_from_segment(segment: str) -> str:
    if segment in SEGMENT_TITLES:
        return SEGMENT_TITLES[segment]
    title = re.sub(r"[-_]+", " ", segment).strip()
    return sanitize_title(title or segment)


def dedupe_pages(pages: list[CapturedPage]) -> list[CapturedPage]:
    by_path = {page.path: page for page in pages}
    result: list[CapturedPage] = []
    for page in pages:
        if page.path.endswith("/index"):
            parent_path = page.path[: -len("/index")] or "/"
            parent = by_path.get(parent_path)
            if parent and parent.title == page.title:
                continue
        result.append(page)
    return result


def run_lark_cli(args: list[str], *, timeout: int = 180) -> dict[str, Any]:
    env = {
        **dict(**__import__("os").environ),
        "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1",
        "LARKSUITE_CLI_NO_SKILLS_NOTIFIER": "1",
    }
    retry_delays = [8, 16, 32, 60, 90]
    last_output = ""
    for attempt in range(len(retry_delays) + 1):
        result = subprocess.run(
            ["lark-cli", *args],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        output = f"{result.stdout}\n{result.stderr}".strip()
        last_output = output
        start = output.find("{")
        parsed: dict[str, Any] | None = None
        if start >= 0:
            try:
                decoder = json.JSONDecoder()
                decoded, _ = decoder.raw_decode(output[start:])
                if isinstance(decoded, dict):
                    parsed = decoded
            except json.JSONDecodeError:
                parsed = None
        if result.returncode == 0:
            return parsed or {"ok": True, "raw": output}

        error = (parsed or {}).get("error") or {}
        retryable = bool(error.get("retryable")) or str(error.get("subtype") or "") == "rate_limit"
        retryable = retryable or "rosetta error" in output.lower() or "SIGABRT" in output
        if retryable and attempt < len(retry_delays):
            time.sleep(retry_delays[attempt])
            continue
        raise RuntimeError(output or f"lark-cli exited with {result.returncode}")
    raise RuntimeError(last_output or "lark-cli failed")


def extract_wiki_token(wiki_url_or_token: str) -> str:
    value = wiki_url_or_token.strip()
    parsed = urlparse(value)
    if parsed.scheme and parsed.path:
        parts = [part for part in parsed.path.split("/") if part]
        if "wiki" in parts:
            index = parts.index("wiki")
            if index + 1 < len(parts):
                return parts[index + 1]
    return value.rstrip("/").split("/")[-1]


def create_lark_doc(parent_token: str, title: str, markdown_path: Path) -> dict[str, Any]:
    relative = markdown_path.resolve().relative_to(REPO_ROOT)
    return run_lark_cli(
        [
            "docs",
            "+create",
            "--as",
            "user",
            "--parent-token",
            parent_token,
            "--doc-format",
            "markdown",
            "--title",
            sanitize_title(title),
            "--content",
            f"@{relative.as_posix()}",
            "--format",
            "json",
        ],
        timeout=240,
    )


def resolve_wiki_node_from_doc(doc_token: str) -> dict[str, Any]:
    return run_lark_cli(
        [
            "wiki",
            "+node-get",
            "--as",
            "user",
            "--node-token",
            doc_token,
            "--obj-type",
            "docx",
            "--format",
            "json",
        ]
    )


def get_wiki_node(node_token: str) -> dict[str, Any]:
    return run_lark_cli(
        [
            "wiki",
            "+node-get",
            "--as",
            "user",
            "--node-token",
            node_token,
            "--format",
            "json",
        ]
    )


def list_child_nodes(space_id: str, parent_node_token: str) -> list[dict[str, Any]]:
    response = run_lark_cli(
        [
            "wiki",
            "+node-list",
            "--as",
            "user",
            "--space-id",
            space_id,
            "--parent-node-token",
            parent_node_token,
            "--page-all",
            "--format",
            "json",
        ]
    )
    return list(((response.get("data") or {}).get("nodes") or []))


def find_child_by_title(space_id: str, parent_node_token: str, title: str) -> dict[str, Any] | None:
    normalized = sanitize_title(title)
    for node in list_child_nodes(space_id, parent_node_token):
        if sanitize_title(str(node.get("title") or "")) == normalized:
            return node
    return None


def wiki_url_from_token(parent_wiki: str, node_token: str) -> str:
    parsed = urlparse(parent_wiki)
    host = parsed.netloc or "feishu.cn"
    scheme = parsed.scheme or "https"
    return f"{scheme}://{host}/wiki/{node_token}"


def created_doc_info(response: dict[str, Any]) -> tuple[str, str]:
    document = (((response or {}).get("data") or {}).get("document") or {})
    doc_token = str(document.get("document_id") or "")
    url = str(document.get("url") or "")
    if not doc_token:
        raise RuntimeError(f"飞书文档创建成功但未返回 document_id: {response}")
    return doc_token, url


def build_index_markdown(title: str, pages: list[CapturedPage]) -> str:
    lines = [
        f"# {title}",
        "",
        f"> 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 页面数量：{len(pages)}",
        "",
    ]
    current_section = ""
    for page in pages:
        section_title = SECTION_TITLES.get(page.section, page.section)
        if page.section != current_section:
            current_section = page.section
            lines.extend([f"## {section_title}", ""])
        lines.append(f"- {page.title}：{page.url}")
    return "\n".join(lines).strip() + "\n"


def build_path_titles(pages: list[CapturedPage]) -> dict[str, str]:
    page_by_path = {page.path: page for page in pages}
    path_keys: set[str] = set()
    for page in pages:
        parts = [part for part in page.path.strip("/").split("/") if part]
        for index in range(1, len(parts) + 1):
            path_keys.add("/" + "/".join(parts[:index]))

    titles: dict[str, str] = {}
    for path_key in sorted(path_keys):
        page = page_by_path.get(path_key)
        last_segment = path_key.strip("/").split("/")[-1]
        titles[path_key] = page.title if page else title_from_segment(last_segment)

    children_by_parent: dict[str, list[str]] = {}
    for path_key in path_keys:
        parts = [part for part in path_key.strip("/").split("/") if part]
        parent = "/" + "/".join(parts[:-1]) if len(parts) > 1 else "/"
        children_by_parent.setdefault(parent, []).append(path_key)

    for siblings in children_by_parent.values():
        by_title: dict[str, list[str]] = {}
        for path_key in siblings:
            by_title.setdefault(titles[path_key], []).append(path_key)
        for duplicated_title, duplicated_paths in by_title.items():
            if len(duplicated_paths) <= 1:
                continue
            used: set[str] = set()
            for path_key in sorted(duplicated_paths):
                last_segment = path_key.strip("/").split("/")[-1]
                candidate = title_from_segment(last_segment)
                if candidate in used:
                    candidate = f"{duplicated_title}（{last_segment}）"
                titles[path_key] = candidate
                used.add(candidate)
    return titles


def export_to_lark(
    *,
    pages: list[CapturedPage],
    export_dir: Path,
    parent_wiki: str,
    root_title: str,
    dry_run: bool,
) -> dict[str, Any]:
    pages = dedupe_pages(pages)
    pages_by_path = {page.path: page for page in pages}
    path_titles = build_path_titles(pages)
    markdown_by_path = write_markdown_files_by_path(pages, export_dir)
    parent_token = extract_wiki_token(parent_wiki)
    index_path = export_dir / "index.md"
    index_path.write_text(build_index_markdown(root_title, pages), encoding="utf-8")

    if dry_run:
        return {"dry_run": True, "parent_token": parent_token, "pages": len(pages), "index": str(index_path)}

    parent_node = get_wiki_node(parent_wiki)
    space_id = str(((parent_node.get("data") or {}).get("space_id")) or "")
    if not space_id:
        raise RuntimeError(f"无法解析父 Wiki 节点所属空间: {parent_node}")

    existing_root = find_child_by_title(space_id, parent_token, root_title)
    if existing_root:
        root_doc_token = str(existing_root.get("obj_token") or "")
        root_node_token = str(existing_root.get("node_token") or "")
        root_url = wiki_url_from_token(parent_wiki, root_node_token)
    else:
        root_response = create_lark_doc(parent_token, root_title, index_path)
        root_doc_token, root_url = created_doc_info(root_response)
        root_node = resolve_wiki_node_from_doc(root_doc_token)
        root_node_token = str(((root_node.get("data") or {}).get("node_token")) or "")
        if not root_node_token:
            raise RuntimeError(f"无法解析根文档对应的 Wiki 节点: {root_node}")

    result: dict[str, Any] = {
        "root": {"doc_token": root_doc_token, "node_token": root_node_token, "url": root_url},
        "directories": [],
        "pages": [],
    }

    node_cache: dict[str, dict[str, str]] = {
        "/": {"node_token": root_node_token, "doc_token": root_doc_token, "url": root_url, "title": root_title}
    }
    child_cache: dict[str, list[dict[str, Any]]] = {}

    def list_children_cached(parent_node_token: str) -> list[dict[str, Any]]:
        if parent_node_token not in child_cache:
            child_cache[parent_node_token] = list_child_nodes(space_id, parent_node_token)
        return child_cache[parent_node_token]

    def find_child_cached(parent_node_token: str, title: str) -> dict[str, Any] | None:
        normalized = sanitize_title(title)
        for node in list_children_cached(parent_node_token):
            if sanitize_title(str(node.get("title") or "")) == normalized:
                return node
        return None

    def ensure_path_node(path_key: str) -> dict[str, str]:
        if path_key in node_cache:
            return node_cache[path_key]

        parts = [part for part in path_key.strip("/").split("/") if part]
        if not parts:
            return node_cache["/"]

        parent_path = "/" + "/".join(parts[:-1]) if len(parts) > 1 else "/"
        parent = ensure_path_node(parent_path)
        page = pages_by_path.get(path_key)
        title = path_titles.get(path_key) or (page.title if page else title_from_segment(parts[-1]))
        markdown_path = markdown_by_path.get(path_key)
        if markdown_path is None:
            markdown_path = directory_markdown_path(export_dir, path_key, title)

        existing = find_child_cached(parent["node_token"], title)
        if existing:
            print(f"[lark-export] skip existing {path_key} -> {title}", file=sys.stderr, flush=True)
            node_info = {
                "title": title,
                "doc_token": str(existing.get("obj_token") or ""),
                "node_token": str(existing.get("node_token") or ""),
                "url": wiki_url_from_token(parent_wiki, str(existing.get("node_token") or "")),
            }
            node_info["skipped"] = "exists"
        else:
            print(f"[lark-export] create {path_key} -> {title}", file=sys.stderr, flush=True)
            response = create_lark_doc(parent["node_token"], title, markdown_path)
            doc_token, _ = created_doc_info(response)
            node = resolve_wiki_node_from_doc(doc_token)
            node_token = str(((node.get("data") or {}).get("node_token")) or "")
            if not node_token:
                raise RuntimeError(f"无法解析新建节点: {node}")
            child_cache.setdefault(parent["node_token"], []).append(
                {
                    "title": title,
                    "obj_token": doc_token,
                    "node_token": node_token,
                    "obj_type": "docx",
                    "node_type": "origin",
                    "space_id": space_id,
                }
            )
            node_info = {
                "title": title,
                "doc_token": doc_token,
                "node_token": node_token,
                "url": wiki_url_from_token(parent_wiki, node_token),
            }
            time.sleep(1.2)

        node_cache[path_key] = node_info
        if page:
            result["pages"].append({"path": path_key, **node_info})
        else:
            result["directories"].append({"path": path_key, **node_info})
        return node_info

    for page in pages:
        ensure_path_node(page.path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture a logged-in documentation site from Chrome and export it to Feishu Wiki.")
    parser.add_argument("--start-url", default="https://cccourse.yunbozs.com.cn/quickstart/first-task")
    parser.add_argument("--parent-wiki", default=DEFAULT_PARENT_WIKI_URL)
    parser.add_argument("--title", default="")
    parser.add_argument("--max-pages", type=int, default=360)
    parser.add_argument("--limit", type=int, default=0, help="Only export the first N valid pages; 0 means all.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-capture", action="store_true")
    parser.add_argument("--export-dir", default="")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    export_dir = Path(args.export_dir).resolve() if args.export_dir else REPO_ROOT / "temp" / "web-doc-exports" / timestamp
    include_prefixes = DEFAULT_INCLUDE_PREFIXES

    if args.skip_capture:
        payload = json.loads((export_dir / "capture.json").read_text(encoding="utf-8"))
    else:
        payload = capture_pages_via_chrome_xhr(
            start_url=args.start_url,
            export_dir=export_dir,
            max_pages=args.max_pages,
            include_prefixes=include_prefixes,
        )

    pages = parse_captured_pages(payload, include_prefixes)
    if args.limit > 0:
        pages = pages[: args.limit]
    root_title = args.title or f"Claude Code 从入门到精通（采集 {datetime.now().strftime('%Y-%m-%d')}）"
    result = export_to_lark(
        pages=pages,
        export_dir=export_dir,
        parent_wiki=args.parent_wiki,
        root_title=root_title,
        dry_run=args.dry_run,
    )
    (export_dir / "lark-export-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"export_dir": str(export_dir), "captured_pages": len(payload.get("pages") or []), "valid_pages": len(pages), "lark": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
