from __future__ import annotations

import json
import re
from dataclasses import dataclass


STATE_OPS_BLOCK_PATTERN = re.compile(r"```state_ops\s*(.*?)```", re.DOTALL | re.IGNORECASE)
OPT_TOOLS_PATTERN = re.compile(r"\{\{opt-tools\s*(.*?)\}\}", re.DOTALL | re.IGNORECASE)


@dataclass
class StateOp:
    action: str  # set | append | remove
    key: str
    value: str = ""


def strip_state_instruction_blocks(summary_text: str) -> str:
    text = summary_text or ""
    text = STATE_OPS_BLOCK_PATTERN.sub("", text)
    text = OPT_TOOLS_PATTERN.sub("", text)
    return text.strip()


def parse_state_ops(summary_text: str) -> tuple[list[StateOp], list[str]]:
    ops: list[StateOp] = []
    warnings: list[str] = []

    for block in STATE_OPS_BLOCK_PATTERN.findall(summary_text or ""):
        parsed, block_warnings = _parse_json_state_ops_block(block)
        ops.extend(parsed)
        warnings.extend(block_warnings)

    opt_block_match = OPT_TOOLS_PATTERN.search(summary_text or "")
    if opt_block_match:
        parsed, block_warnings = _parse_opt_tools_block(opt_block_match.group(1))
        ops.extend(parsed)
        warnings.extend(block_warnings)

    return ops, warnings


def _parse_json_state_ops_block(block: str) -> tuple[list[StateOp], list[str]]:
    warnings: list[str] = []
    raw = (block or "").strip()
    if not raw:
        return ([], warnings)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return ([], [f"state_ops JSON 解析失败: {e.msg}"])

    action = str(data.get("action") or "").strip().lower()
    payload = data.get("data")
    if not isinstance(payload, dict):
        return ([], [f"state_ops 缺少 data 对象: action={action}"])

    if action in {"update", "set"}:
        items: list[StateOp] = []
        for key, value in payload.items():
            items.append(StateOp(action="set", key=str(key), value=str(value)))
        return (items, warnings)

    if action == "append":
        key = str(payload.get("key") or "")
        value = str(payload.get("value") or "")
        if not key.strip():
            return ([], ["state_ops append 缺少 key"])
        return ([StateOp(action="append", key=key, value=value)], warnings)

    if action in {"delete", "remove"}:
        keys = payload.get("keys")
        if isinstance(keys, list):
            removed = [StateOp(action="remove", key=str(key), value="") for key in keys if str(key).strip()]
            return (removed, warnings)
        key = str(payload.get("key") or "")
        value = str(payload.get("value") or "")
        if key.strip():
            return ([StateOp(action="remove", key=key, value=value)], warnings)
        return ([], ["state_ops remove 缺少 key/keys"])

    return ([], [f"未知 state_ops action: {action}"])


def _parse_opt_tools_block(block: str) -> tuple[list[StateOp], list[str]]:
    warnings: list[str] = []
    ops: list[StateOp] = []
    for raw_line in (block or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^(set|append|remove)\s*:\s*(.+?)\s*=\s*\"(.*)\"\s*$", line, re.IGNORECASE)
        if not match:
            warnings.append(f"opt-tools 行解析失败: {line}")
            continue
        action = match.group(1).lower()
        key = match.group(2).strip()
        value = match.group(3)
        ops.append(StateOp(action=action, key=key, value=value))
    return (ops, warnings)

