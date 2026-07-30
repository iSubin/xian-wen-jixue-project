from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import ffmpeg

from .summarization.chunker import parse_timestamp_sec
from .utils.ffmpeg_helper import FFmpegHelper
from .utils.logger import logger


TIMESTAMP_MARK_RE = re.compile(r"[（(]\s*(?:见\s*)?(\d{1,2}):([0-5]\d):([0-5]\d)\s*[）)]")


@dataclass(frozen=True)
class FrameCandidate:
    seconds: int
    label: str
    filename: str


@dataclass(frozen=True)
class FrameReference:
    seconds: int
    label: str
    filename: str
    public_url: str


FrameWriter = Callable[[str, int, str], None]


def _normalize_time_label(hours: str, minutes: str, seconds: str) -> str:
    return f"{int(hours):02d}:{minutes}:{seconds}"


def _seconds_to_time_label(total_seconds: int) -> str:
    hours = max(0, int(total_seconds)) // 3600
    minutes = (max(0, int(total_seconds)) % 3600) // 60
    seconds = max(0, int(total_seconds)) % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _to_seconds(hours: str, minutes: str, seconds: str) -> int:
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def _frame_filename(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    sec = seconds % 60
    return f"frame_{hours:02d}{minutes:02d}{sec:02d}.jpg"


def _candidate_from_seconds(seconds: int) -> FrameCandidate:
    return FrameCandidate(
        seconds=seconds,
        label=_seconds_to_time_label(seconds),
        filename=_frame_filename(seconds),
    )


def select_frame_candidates(
    markdown: str,
    max_frames: int = 12,
    min_interval_sec: int = 30,
) -> list[FrameCandidate]:
    selected: list[FrameCandidate] = []
    seen_seconds: set[int] = set()

    for match in TIMESTAMP_MARK_RE.finditer(markdown or ""):
        seconds = _to_seconds(match.group(1), match.group(2), match.group(3))
        if seconds in seen_seconds:
            continue
        if any(abs(seconds - candidate.seconds) < min_interval_sec for candidate in selected):
            continue

        seen_seconds.add(seconds)
        selected.append(
            FrameCandidate(
                seconds=seconds,
                label=_normalize_time_label(match.group(1), match.group(2), match.group(3)),
                filename=_frame_filename(seconds),
            )
        )
        if len(selected) >= max_frames:
            break

    return selected


def select_transcript_frame_candidates(
    transcript_text: str,
    max_frames: int = 12,
    min_interval_sec: int = 30,
    preferred_count: int | None = None,
) -> list[FrameCandidate]:
    timestamps: list[int] = []
    seen: set[int] = set()
    for line in (transcript_text or "").splitlines():
        seconds = parse_timestamp_sec(line)
        if seconds is None or seconds in seen:
            continue
        timestamps.append(seconds)
        seen.add(seconds)

    if not timestamps:
        return []

    target_count = min(max_frames, len(timestamps))
    if preferred_count is not None:
        target_count = min(target_count, max(1, int(preferred_count)))
    if target_count <= 0:
        return []

    selected: list[int] = []
    selected_indices: set[int] = set()
    for index in _even_sample_indices(len(timestamps), target_count):
        seconds = timestamps[index]
        if _can_select_second(seconds, selected, min_interval_sec):
            selected.append(seconds)
            selected_indices.add(index)

    if len(selected) < target_count:
        for index, seconds in enumerate(timestamps):
            if index in selected_indices:
                continue
            if not _can_select_second(seconds, selected, min_interval_sec):
                continue
            selected.append(seconds)
            if len(selected) >= target_count:
                break

    selected.sort()
    return [_candidate_from_seconds(seconds) for seconds in selected]


def _even_sample_indices(total: int, count: int) -> list[int]:
    if total <= 0 or count <= 0:
        return []
    if count >= total:
        return list(range(total))
    return [
        min(total - 1, int(((i + 1) * total) / (count + 1)))
        for i in range(count)
    ]


def _can_select_second(seconds: int, selected: list[int], min_interval_sec: int) -> bool:
    return not any(abs(seconds - existing) < min_interval_sec for existing in selected)


def _append_supplemental_candidates(
    candidates: list[FrameCandidate],
    transcript_text: str,
    preferred_count: int,
    max_frames: int,
    min_interval_sec: int,
) -> list[FrameCandidate]:
    if preferred_count <= 0 or len(candidates) >= max_frames:
        return candidates

    supplement_count = min(preferred_count, max_frames - len(candidates))
    fallback_candidates = select_transcript_frame_candidates(
        transcript_text,
        max_frames=max_frames,
        min_interval_sec=min_interval_sec,
        preferred_count=supplement_count,
    )
    merged = list(candidates)
    for fallback in fallback_candidates:
        if len(merged) >= max_frames:
            break
        if any(abs(fallback.seconds - existing.seconds) < min_interval_sec for existing in merged):
            continue
        merged.append(fallback)
    return merged


def write_high_quality_frame(video_path: str, seconds: int, output_path: str) -> None:
    if not FFmpegHelper.configure_ffmpeg_python():
        raise RuntimeError("ffmpeg 不可用，无法抽取视频截图。")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    (
        ffmpeg
        .input(video_path, ss=max(0, int(seconds)))
        .output(output_path, vframes=1, **{"q:v": 2})
        .overwrite_output()
        .run(quiet=True)
    )


def _public_frame_url(public_url_base: str, task_id: str, filename: str) -> str:
    return f"{public_url_base.rstrip('/')}/{task_id}/frames/{filename}"


def _insert_frame_references(markdown: str, references: list[FrameReference]) -> str:
    if not references:
        return markdown

    refs_by_second = {reference.seconds: reference for reference in references}
    inserted_seconds: set[int] = set()
    output_lines: list[str] = []

    for line in (markdown or "").splitlines():
        output_lines.append(line)

        line_refs: list[FrameReference] = []
        for match in TIMESTAMP_MARK_RE.finditer(line):
            seconds = _to_seconds(match.group(1), match.group(2), match.group(3))
            reference = refs_by_second.get(seconds)
            if reference and seconds not in inserted_seconds:
                line_refs.append(reference)
                inserted_seconds.add(seconds)

        for reference in line_refs:
            output_lines.append("")
            output_lines.append(f"![关键画面 {reference.label}]({reference.public_url})")

    remaining = [reference for reference in references if reference.seconds not in inserted_seconds]
    if remaining:
        return _insert_references_after_headings("\n".join(output_lines), remaining)

    return "\n".join(output_lines)


def _insert_references_after_headings(markdown: str, references: list[FrameReference]) -> str:
    if not references:
        return markdown

    output_lines: list[str] = []
    ref_index = 0
    for line in (markdown or "").splitlines():
        output_lines.append(line)
        if ref_index >= len(references):
            continue
        if re.match(r"^##(?!#)\s+\S", line.strip()):
            reference = references[ref_index]
            output_lines.append("")
            output_lines.append(f"![关键画面 {reference.label}]({reference.public_url})")
            ref_index += 1

    if ref_index == 0:
        return _insert_references_after_paragraphs(markdown, references)

    return "\n".join(output_lines)


def _insert_references_after_paragraphs(markdown: str, references: list[FrameReference]) -> str:
    lines = (markdown or "").splitlines()
    if not lines:
        return markdown

    paragraph_end_indices = [
        index
        for index, line in enumerate(lines)
        if line.strip() and (index == len(lines) - 1 or not lines[index + 1].strip())
    ]
    if not paragraph_end_indices:
        paragraph_end_indices = [0]

    insertion_indices = [
        paragraph_end_indices[index]
        for index in _even_sample_indices(len(paragraph_end_indices), min(len(paragraph_end_indices), len(references)))
    ]
    refs_by_index = {
        line_index: references[ref_index]
        for ref_index, line_index in enumerate(insertion_indices)
    }

    output_lines: list[str] = []
    for index, line in enumerate(lines):
        output_lines.append(line)
        reference = refs_by_index.get(index)
        if reference:
            output_lines.append("")
            output_lines.append(f"![关键画面 {reference.label}]({reference.public_url})")

    return "\n".join(output_lines)


def _preferred_fallback_frame_count(markdown: str, max_frames: int) -> int:
    heading_count = sum(
        1
        for line in (markdown or "").splitlines()
        if re.match(r"^##(?!#)\s+\S", line.strip())
    )
    if heading_count > 0:
        return min(max_frames, heading_count, 6)
    return min(max_frames, 4)


def enrich_summary_with_video_frames(
    summary: str,
    task_id: str,
    video_path: str | None,
    transcript_text: str | None = None,
    assets_root: str | os.PathLike[str] = "temp/task-assets",
    public_url_base: str = "/task-assets",
    frame_writer: FrameWriter = write_high_quality_frame,
    max_frames: int = 12,
    min_interval_sec: int = 30,
) -> str:
    if not summary or not task_id or not video_path or not os.path.exists(video_path):
        return summary

    preferred_fallback_count = _preferred_fallback_frame_count(summary, max_frames)
    candidates = select_frame_candidates(
        summary,
        max_frames=max_frames,
        min_interval_sec=min_interval_sec,
    )
    if not candidates:
        candidates = select_transcript_frame_candidates(
            transcript_text or "",
            max_frames=max_frames,
            min_interval_sec=min_interval_sec,
            preferred_count=preferred_fallback_count,
        )
    elif transcript_text and len(candidates) < preferred_fallback_count:
        candidates = _append_supplemental_candidates(
            candidates,
            transcript_text,
            preferred_fallback_count,
            max_frames,
            min_interval_sec,
        )
    if not candidates:
        return summary

    frame_dir = Path(assets_root) / task_id / "frames"
    references: list[FrameReference] = []
    for candidate in candidates:
        output_path = frame_dir / candidate.filename
        try:
            frame_writer(str(video_path), candidate.seconds, str(output_path))
        except Exception as exc:
            logger.warning(
                "[FrameEnricher] 抽取视频截图失败: "
                f"task_id={task_id}, seconds={candidate.seconds}, error={exc}"
            )
            continue

        if not output_path.exists() or output_path.stat().st_size <= 0:
            continue

        references.append(
            FrameReference(
                seconds=candidate.seconds,
                label=candidate.label,
                filename=candidate.filename,
                public_url=_public_frame_url(public_url_base, task_id, candidate.filename),
            )
        )

    return _insert_frame_references(summary, references)
