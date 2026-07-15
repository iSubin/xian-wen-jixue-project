from tools.export_web_docs_to_lark import (
    CapturedPage,
    build_directory_xml,
    build_index_xml,
    page_to_xml,
)


def make_page(path: str, title: str, body: str = "<p>正文内容</p>") -> CapturedPage:
    return CapturedPage(
        url=f"https://cccourse.yunbozs.com.cn{path}",
        status=200,
        title=title,
        content_html=f"<article><h1>{title}</h1>{body}</article>",
        text_length=200,
    )


def test_build_index_xml_creates_readable_portal_with_section_links() -> None:
    pages = [
        make_page("/quickstart/first-task", "你的第一个真实任务"),
        make_page("/features/mcp/concept", "MCP 概念"),
        make_page("/advanced/memory-system", "记忆系统"),
    ]
    url_by_path = {
        "/quickstart/first-task": "https://zcnfhebiqluf.feishu.cn/wiki/quick",
        "/features/mcp/concept": "https://zcnfhebiqluf.feishu.cn/wiki/mcp",
        "/advanced/memory-system": "https://zcnfhebiqluf.feishu.cn/wiki/memory",
    }

    xml = build_index_xml("Claude Code 从入门到精通", pages, url_by_path)

    assert "<title>Claude Code 从入门到精通</title>" in xml
    assert '<callout emoji="📚"' in xml
    assert "<grid>" in xml
    assert '<a href="https://zcnfhebiqluf.feishu.cn/wiki/quick">你的第一个真实任务</a>' in xml
    assert '<h2>完整目录</h2>' in xml


def test_build_directory_xml_uses_child_navigation_and_sub_page_list() -> None:
    url_by_path = {
        "/quickstart/first-task": "https://zcnfhebiqluf.feishu.cn/wiki/first",
        "/quickstart/next-steps": "https://zcnfhebiqluf.feishu.cn/wiki/next",
    }
    path_titles = {
        "/quickstart/first-task": "你的第一个真实任务",
        "/quickstart/next-steps": "进阶指引",
    }

    xml = build_directory_xml("/quickstart", "快速上手", path_titles, url_by_path)

    assert "<title>快速上手</title>" in xml
    assert '<callout emoji="🗂️"' in xml
    assert '<a href="https://zcnfhebiqluf.feishu.cn/wiki/first">你的第一个真实任务</a>' in xml
    assert "<sub-page-list></sub-page-list>" in xml


def test_page_to_xml_preserves_source_navigation_and_resolved_links() -> None:
    page = make_page(
        "/quickstart/first-task",
        "你的第一个真实任务",
        """
        <p>体验 <a href="/features/mcp/concept">MCP</a> 的协同工作。</p>
        <pre><code>claude</code></pre>
        """,
    )

    xml = page_to_xml(
        page,
        link_resolver=lambda href, _base_url: "https://zcnfhebiqluf.feishu.cn/wiki/mcp"
        if href == "/features/mcp/concept"
        else None,
        previous_url="https://zcnfhebiqluf.feishu.cn/wiki/prev",
        next_url="https://zcnfhebiqluf.feishu.cn/wiki/next",
    )

    assert "<title>你的第一个真实任务</title>" in xml
    assert '<callout emoji="📝"' in xml
    assert '<a href="https://zcnfhebiqluf.feishu.cn/wiki/mcp">MCP</a>' in xml
    assert '<a href="https://zcnfhebiqluf.feishu.cn/wiki/prev">上一篇</a>' in xml
    assert '<a href="https://zcnfhebiqluf.feishu.cn/wiki/next">下一篇</a>' in xml
    assert '<pre lang="text"><code>claude</code></pre>' in xml
    assert "来源" not in xml
    assert "查看原文" not in xml
    assert page.url not in xml


def test_page_to_xml_omits_source_attribution() -> None:
    page = make_page(
        "/quickstart/first-task",
        "你的第一个真实任务",
        "<p>正文内容</p>",
    )

    xml = page_to_xml(page)

    assert "原文链接" not in xml
    assert "来源" not in xml
    assert "原文页面" not in xml
    assert "查看原文" not in xml
    assert "本文由原网页采集生成" not in xml
    assert page.url not in xml


def test_page_to_xml_preserves_block_card_links() -> None:
    page = make_page(
        "/quickstart/next-steps",
        "进阶指引",
        """
        <div>
          <a href="/features/claude-md/what-is-claude-md">
            <p>核心工具</p>
            <p>CLAUDE.md、Skill、MCP、Hooks</p>
          </a>
        </div>
        """,
    )

    xml = page_to_xml(
        page,
        link_resolver=lambda href, _base_url: "https://zcnfhebiqluf.feishu.cn/wiki/tools"
        if href == "/features/claude-md/what-is-claude-md"
        else None,
    )

    assert (
        '<p><a href="https://zcnfhebiqluf.feishu.cn/wiki/tools">'
        "核心工具 CLAUDE.md、Skill、MCP、Hooks</a></p>"
    ) in xml


def test_page_to_xml_keeps_text_for_unmapped_source_site_links() -> None:
    page = make_page(
        "/quickstart/next-steps",
        "进阶指引",
        """
        <div>
          <a href="/practical/development">
            <p>软件开发</p>
            <p>产品规划、工具开发、桌面与移动应用</p>
          </a>
        </div>
        """,
    )

    xml = page_to_xml(page, link_resolver=lambda _href, _base_url: None)

    assert "<p>软件开发 产品规划、工具开发、桌面与移动应用</p>" in xml
    assert "https://cccourse.yunbozs.com.cn/practical/development" not in xml


def test_page_to_xml_handles_list_whitespace_nodes() -> None:
    page = make_page(
        "/features/list",
        "列表页面",
        """
        <ul>
          <li>第一项</li>
          <li>
            第二项
            <ul><li>子项</li></ul>
          </li>
        </ul>
        """,
    )

    xml = page_to_xml(page)

    assert "<li>第一项</li>" in xml
    assert "<li>第二项<ul><li>子项</li></ul></li>" in xml


def test_page_to_xml_preserves_pre_inside_figure() -> None:
    page = make_page(
        "/features/code",
        "代码页面",
        """
        <figure>
          <button>Copy</button>
          <pre><code>claude</code></pre>
        </figure>
        """,
    )

    xml = page_to_xml(page)

    assert "<p>Copy" not in xml
    assert '<pre lang="text"><code>claude</code></pre>' in xml


def test_page_to_xml_removes_source_navigation_chrome() -> None:
    page = make_page(
        "/features/nav",
        "导航页面",
        """
        <div class="docs-nav"><a href="/prev">Previous</a><a href="/next">Next</a></div>
        <p>正文</p>
        """,
    )

    xml = page_to_xml(page)

    assert "Previous" not in xml
    assert "Next" not in xml
    assert "<p>正文</p>" in xml


def test_page_to_xml_polishes_task_completion_section() -> None:
    page = make_page(
        "/quickstart/first-task",
        "你的第一个真实任务",
        """
        <h2>任务完成后</h2>
        <p><strong>关于 <a href="/quickstart/config/memory">Memory</a></strong>：Claude 会自动保存这次的工作经验。</p>
        <p><strong>下一步</strong>：接下来看看<a href="/quickstart/next-steps">进阶指引</a>，了解更深入的用法。</p>
        <p>Hooks</p>
        <p>进阶指引</p>
        """,
    )

    xml = page_to_xml(
        page,
        link_resolver=lambda href, _base_url: {
            "/quickstart/config/memory": "https://zcnfhebiqluf.feishu.cn/wiki/memory",
            "/quickstart/next-steps": "https://zcnfhebiqluf.feishu.cn/wiki/next",
        }.get(href),
    )

    assert "<h2>任务完成后</h2>" in xml
    assert '<callout emoji="✅" background-color="light-green" border-color="green">' in xml
    assert "<h3>经验会自动沉淀</h3>" in xml
    assert '<a href="https://zcnfhebiqluf.feishu.cn/wiki/memory">Memory</a>' in xml
    assert '<callout emoji="🏁" background-color="light-blue" border-color="blue">' in xml
    assert "<h3>继续进阶</h3>" in xml
    assert '<a href="https://zcnfhebiqluf.feishu.cn/wiki/next">进阶指引</a>' in xml
    assert "<p>Hooks</p>" not in xml
    assert "<p>进阶指引</p>" not in xml
