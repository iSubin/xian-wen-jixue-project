from __future__ import annotations

import re

from .chunker import TranscriptChunk
from .state_manager import DynamicStateManager
from .protocol import strip_state_instruction_blocks


def generate_structure_overview(previous_chunk_summaries: list[str]) -> str:
    if not previous_chunk_summaries:
        return ""

    lines: list[str] = []
    for idx, summary in enumerate(previous_chunk_summaries):
        cleaned = strip_state_instruction_blocks(summary)
        headers = re.findall(r"^(#{1,6})\s+(.+)$", cleaned, flags=re.MULTILINE)
        if not headers:
            continue
        lines.append(f"### 块 {idx + 1}")
        for level_mark, text in headers:
            level = len(level_mark)
            indent = "  " * max(0, level - 1)
            lines.append(f"{indent}- {text.strip()}")
    return "\n".join(lines)


def build_chunk_user_prompt(
    chunk: TranscriptChunk,
    chunk_index: int,
    total_chunks: int,
    dynamic_state: DynamicStateManager,
    structure_overview: str,
) -> str:
    lines: list[str] = []
    lines.append("## 当前处理状态")
    lines.append(f"- 总共 {total_chunks} 块，当前处理第 {chunk_index + 1} 块")
    lines.append(f"- 当前块时间范围: `{chunk.time_range_hms}`")
    if chunk_index == 0:
        lines.append("- 这是第一块，请在文首添加主题标签 `{{...}}`")
    elif chunk_index == total_chunks - 1:
        lines.append("- 这是最后一块，请注意自然收尾")
    else:
        lines.append("- 这是中间块，请保持自然续写与风格一致")

    lines.append("")
    lines.append(dynamic_state.format_for_prompt())

    if structure_overview and chunk_index > 0:
        lines.append("")
        lines.append("## 已总结结构概览")
        lines.append("```markdown")
        lines.append(structure_overview)
        lines.append("➡️ 当前在这！⬅️")
        lines.append("```")

    lines.append("")
    lines.append("## 当前块转录文本")
    lines.append("```plaintext")
    lines.append(chunk.text)
    lines.append("```")
    return "\n".join(lines)

