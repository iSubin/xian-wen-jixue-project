from __future__ import annotations

import re
from dataclasses import dataclass


TIMESTAMP_PATTERN = re.compile(r"^(\d{6})")


@dataclass
class TranscriptChunk:
    index: int
    text: str
    start_timestamp_sec: int
    end_timestamp_sec: int
    line_count: int

    @property
    def duration_sec(self) -> int:
        return max(0, self.end_timestamp_sec - self.start_timestamp_sec)

    @property
    def time_range_hms(self) -> str:
        return f"{_sec_to_hms(self.start_timestamp_sec)}-{_sec_to_hms(self.end_timestamp_sec)}"


def _sec_to_hms(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def parse_timestamp_sec(line: str) -> int | None:
    match = TIMESTAMP_PATTERN.match((line or "").strip())
    if not match:
        return None
    raw = match.group(1)
    try:
        hours = int(raw[0:2])
        minutes = int(raw[2:4])
        seconds = int(raw[4:6])
    except (TypeError, ValueError):
        return None
    if minutes >= 60 or seconds >= 60:
        return None
    return hours * 3600 + minutes * 60 + seconds


def count_timestamp_lines(transcript_text: str) -> int:
    count = 0
    for line in (transcript_text or "").splitlines():
        if parse_timestamp_sec(line) is not None:
            count += 1
    return count


def split_transcript_into_chunks(
    transcript_text: str,
    target_duration_sec: int,
    min_duration_sec: int,
    max_duration_sec: int,
    boundary_jump_sec: int,
) -> list[TranscriptChunk]:
    lines = []
    for line in (transcript_text or "").splitlines():
        ts = parse_timestamp_sec(line)
        if ts is None:
            continue
        lines.append((ts, line))

    if not lines:
        raise ValueError("转录文本中未找到有效时间戳行，无法进行分块总结。")

    if len(lines) == 1:
        only_ts, only_line = lines[0]
        return [
            TranscriptChunk(
                index=0,
                text=only_line,
                start_timestamp_sec=only_ts,
                end_timestamp_sec=only_ts,
                line_count=1,
            )
        ]

    chunks: list[TranscriptChunk] = []
    start_idx = 0
    start_ts = lines[0][0]
    i = 1
    while i < len(lines):
        current_ts = lines[i][0]
        duration = current_ts - start_ts

        if duration >= max_duration_sec:
            _append_chunk(chunks, lines, start_idx, i)
            start_idx = i
            start_ts = lines[i][0]
            i += 1
            continue

        if duration >= target_duration_sec:
            split_idx = i
            search_end = min(i + 50, len(lines) - 1)
            j = i
            while j <= search_end:
                gap = lines[j][0] - lines[j - 1][0]
                if gap >= boundary_jump_sec:
                    split_idx = j
                    break
                if lines[j][0] - start_ts >= max_duration_sec:
                    split_idx = j
                    break
                j += 1

            _append_chunk(chunks, lines, start_idx, split_idx)
            start_idx = split_idx
            start_ts = lines[start_idx][0]
            i = start_idx + 1
            continue

        i += 1

    if start_idx < len(lines):
        _append_chunk(chunks, lines, start_idx, len(lines))

    if len(chunks) >= 2 and chunks[-1].duration_sec < min_duration_sec:
        prev = chunks[-2]
        tail = chunks[-1]
        merged_lines = prev.text.splitlines() + tail.text.splitlines()
        chunks[-2] = TranscriptChunk(
            index=prev.index,
            text="\n".join(merged_lines),
            start_timestamp_sec=prev.start_timestamp_sec,
            end_timestamp_sec=tail.end_timestamp_sec,
            line_count=len(merged_lines),
        )
        chunks.pop()
        for idx, chunk in enumerate(chunks):
            chunk.index = idx

    return chunks


def _append_chunk(
    chunks: list[TranscriptChunk],
    lines: list[tuple[int, str]],
    start_idx: int,
    end_idx: int,
) -> None:
    if end_idx <= start_idx:
        return
    chunk_lines = lines[start_idx:end_idx]
    text_lines = [line for _, line in chunk_lines]
    chunks.append(
        TranscriptChunk(
            index=len(chunks),
            text="\n".join(text_lines),
            start_timestamp_sec=chunk_lines[0][0],
            end_timestamp_sec=chunk_lines[-1][0],
            line_count=len(text_lines),
        )
    )


def tail_timestamp_lines(chunk: TranscriptChunk, n: int) -> str:
    lines = chunk.text.splitlines()
    if n <= 0:
        return ""
    return "\n".join(lines[-n:])
