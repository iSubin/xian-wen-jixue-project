from __future__ import annotations

import os
import re
import shutil
import subprocess
from threading import Lock
from typing import Any

from ..utils.logger import logger
from .transcriber import get_transcriber

_CUDA_DLL_PATTERN = re.compile(
    r"(cublas(?:Lt)?64_(\d+)\.dll|cudart64_(\d+)\.dll|cudnn64(?:_\d+)?\.dll)",
    re.IGNORECASE,
)


def _extract_missing_cuda_runtime_dll(error_text: str) -> tuple[str | None, str | None]:
    match = _CUDA_DLL_PATTERN.search(error_text or "")
    if not match:
        return (None, None)
    dll_name = match.group(1)
    cuda_major = match.group(2) or match.group(3)
    return (dll_name, cuda_major)


def _build_cuda_fix_message(missing_dll: str | None, cuda_major: str | None) -> str:
    lines = [
        "可处理步骤：",
        "1) 临时切换到 CPU 转录（可立即继续使用）。",
        "2) 安装与当前 fast-whisper/ctranslate2 匹配的 NVIDIA CUDA Runtime（Windows 需包含 cublas）。",
    ]
    if missing_dll:
        if cuda_major:
            lines.append(f"   当前缺失：{missing_dll}（对应 CUDA {cuda_major}）。")
        else:
            lines.append(f"   当前缺失：{missing_dll}。")
    lines.extend(
        [
            "3) 确认系统 PATH 含 CUDA bin 目录，例如：",
            r"   C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin",
            "4) 重启 ShengWen 后重新选择 CUDA。",
        ]
    )
    return "\n".join(lines)


def _detect_nvidia_gpu() -> bool:
    if shutil.which("nvidia-smi") is None:
        return False
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        return result.returncode == 0 and "GPU" in (result.stdout or "")
    except Exception:
        return False


def _detect_cuda_support() -> dict[str, Any]:
    has_nvidia_gpu = _detect_nvidia_gpu()

    torch_installed = False
    torch_cuda_built = False
    ctranslate2_installed = False
    ctranslate2_cuda_device_count = 0
    cuda_available = False
    reason = "unknown"
    message = "CUDA 状态未知。"

    try:
        import torch  # type: ignore

        torch_installed = True
        torch_cuda_built = bool(getattr(torch.version, "cuda", None))
        cuda_available = bool(torch.cuda.is_available())

        if cuda_available:
            try:
                import ctranslate2  # type: ignore

                ctranslate2_installed = True
                ctranslate2_cuda_device_count = int(ctranslate2.get_cuda_device_count())
                if ctranslate2_cuda_device_count > 0:
                    reason = "ok"
                    message = f"CUDA 可用（CTranslate2 检测到 {ctranslate2_cuda_device_count} 张 GPU），可使用 GPU 转录。"
                else:
                    cuda_available = False
                    reason = "ct2_no_cuda_device"
                    message = "检测到 PyTorch CUDA 可用，但 CTranslate2 未检测到可用 CUDA 设备。建议更新显卡驱动，或先切回 CPU。"
            except Exception as e:
                cuda_available = False
                error_text = str(e)
                if isinstance(e, ModuleNotFoundError):
                    reason = "ct2_missing"
                    message = (
                        "检测到 CUDA 环境，但缺少 CTranslate2（fast-whisper 依赖）。"
                        "\n可处理步骤：执行 `pip install ctranslate2` 后重启应用。"
                    )
                else:
                    missing_dll, cuda_major = _extract_missing_cuda_runtime_dll(error_text)
                    reason = "ct2_cuda_runtime_unavailable"
                    if missing_dll:
                        message = (
                            "检测到 CUDA 环境，但 fast-whisper CUDA 运行时不可用。"
                            f"\n缺少运行库：{missing_dll}"
                            f"\n{_build_cuda_fix_message(missing_dll, cuda_major)}"
                        )
                    else:
                        message = (
                            "检测到 CUDA 环境，但 fast-whisper CUDA 运行时不可用。"
                            f"\n原始错误：{error_text}"
                            "\n可处理步骤：先切换到 CPU；随后检查 CUDA Runtime 与驱动版本，并重启后重试。"
                        )
        elif not has_nvidia_gpu:
            reason = "no_gpu"
            message = "未检测到 NVIDIA 显卡（或驱动未正确安装）。"
        elif not torch_cuda_built:
            reason = "torch_cpu_only"
            message = "检测到 NVIDIA 显卡，但当前 PyTorch 为 CPU 版本（未启用 CUDA）。"
        else:
            reason = "cuda_runtime_unavailable"
            message = "检测到 NVIDIA 显卡，且 PyTorch 支持 CUDA，但当前 CUDA 运行时不可用（可能是驱动/运行库问题）。"
    except Exception:
        if has_nvidia_gpu:
            reason = "torch_missing"
            message = "检测到 NVIDIA 显卡，但未安装 PyTorch（或环境中不可导入）。"
        else:
            reason = "no_gpu"
            message = "未检测到 NVIDIA 显卡（或驱动未正确安装）。"

    return {
        "cuda_available": cuda_available,
        "has_nvidia_gpu": has_nvidia_gpu,
        "torch_installed": torch_installed,
        "torch_cuda_built": torch_cuda_built,
        "ctranslate2_installed": ctranslate2_installed,
        "ctranslate2_cuda_device_count": ctranslate2_cuda_device_count,
        "cuda_reason": reason,
        "cuda_message": message,
    }


def _sanitize_cookie_value(value: str | None) -> str:
    return (value or "").strip().replace("\r", "").replace("\n", "")


def _read_env_bilibili_sessdata() -> str:
    return _sanitize_cookie_value(os.getenv("BILIBILI_SESSDATA") or os.getenv("SESSDATA"))


def _mask_cookie_value(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return f"{value[:2]}****"
    return f"{value[:4]}****{value[-4:]}"


class TranscriptionSettingsManager:
    """运行时转录设置管理器。"""

    def __init__(
        self,
        initial_device: str,
        model_size: str,
        model_path: str | None = None,
        initial_enable_bilibili_subtitle_fetch: bool = True,
        initial_bilibili_sessdata: str = "",
    ):
        self._lock = Lock()
        self._device = initial_device
        self._model_size = model_size
        self._model_path = model_path
        self._enable_bilibili_subtitle_fetch = initial_enable_bilibili_subtitle_fetch
        self._bilibili_sessdata = _sanitize_cookie_value(initial_bilibili_sessdata)
        self._transcriber_worker: Any = None

    def bind_transcriber_worker(self, worker: Any) -> None:
        with self._lock:
            self._transcriber_worker = worker

    def resolve_bilibili_sessdata(self, task_override_sessdata: str | None = None) -> tuple[str, str]:
        task_override = _sanitize_cookie_value(task_override_sessdata)
        if task_override:
            return task_override, "task"

        with self._lock:
            global_sessdata = self._bilibili_sessdata
        if global_sessdata:
            return global_sessdata, "global"

        env_sessdata = _read_env_bilibili_sessdata()
        if env_sessdata:
            return env_sessdata, "env"

        return "", "none"

    def get_settings(self) -> dict[str, Any]:
        with self._lock:
            current_device = self._device
            enable_bilibili_subtitle_fetch = self._enable_bilibili_subtitle_fetch

        sessdata, source = self.resolve_bilibili_sessdata()
        cuda_diag = _detect_cuda_support()
        cuda_available = bool(cuda_diag["cuda_available"])
        devices = ["cpu"]
        if cuda_available:
            devices.append("cuda")

        return {
            "device": current_device,
            "cuda_available": cuda_available,
            "available_devices": devices,
            "has_nvidia_gpu": bool(cuda_diag["has_nvidia_gpu"]),
            "torch_installed": bool(cuda_diag["torch_installed"]),
            "torch_cuda_built": bool(cuda_diag["torch_cuda_built"]),
            "ctranslate2_installed": bool(cuda_diag["ctranslate2_installed"]),
            "ctranslate2_cuda_device_count": int(cuda_diag["ctranslate2_cuda_device_count"]),
            "cuda_reason": str(cuda_diag["cuda_reason"]),
            "cuda_message": str(cuda_diag["cuda_message"]),
            "enable_bilibili_subtitle_fetch": enable_bilibili_subtitle_fetch,
            "has_bilibili_sessdata": bool(sessdata),
            "bilibili_cookie_source": source,
            "bilibili_sessdata_masked": _mask_cookie_value(sessdata),
        }

    def _build_transcriber_kwargs(self, device: str) -> dict[str, str]:
        kwargs: dict[str, str] = {"device": device}
        if self._model_path:
            kwargs["model_size_or_path"] = self._model_path
        else:
            kwargs["model_size"] = self._model_size
        return kwargs

    def update_settings(
        self,
        device: str | None = None,
        enable_bilibili_subtitle_fetch: bool | None = None,
        bilibili_sessdata: str | None = None,
        clear_bilibili_sessdata: bool | None = None,
    ) -> dict[str, Any]:
        if (
            device is None
            and enable_bilibili_subtitle_fetch is None
            and bilibili_sessdata is None
            and clear_bilibili_sessdata is None
        ):
            raise ValueError("至少需要更新一个配置项")

        transcriber = None
        normalized = None

        if device is not None:
            normalized = (device or "").strip().lower()
            if normalized not in {"cpu", "cuda"}:
                raise ValueError("仅支持 cpu 或 cuda")
            if normalized == "cuda":
                cuda_diag = _detect_cuda_support()
                if not bool(cuda_diag["cuda_available"]):
                    raise ValueError(str(cuda_diag["cuda_message"]))

            # 先构建新 transcriber，成功后再切换，避免中间状态不可用
            try:
                logger.info(
                    "[TranscriptionSettingsManager] 正在重建转录器实例，若模型未缓存可能会触发下载，请稍候..."
                )
                transcriber = get_transcriber("fast_whisper", **self._build_transcriber_kwargs(normalized))
                logger.info("[TranscriptionSettingsManager] 转录器实例重建完成。")
            except Exception as e:
                raise ValueError(f"切换转录设备失败: {e}") from e

        with self._lock:
            if transcriber is not None:
                if self._transcriber_worker is None:
                    raise ValueError("TranscriberWorker 未初始化")
                self._transcriber_worker.update_transcriber(transcriber)
                self._device = normalized
                logger.info(f"[TranscriptionSettingsManager] 已更新转录设备: device={normalized}")

            if enable_bilibili_subtitle_fetch is not None:
                self._enable_bilibili_subtitle_fetch = bool(enable_bilibili_subtitle_fetch)
                logger.info(
                    "[TranscriptionSettingsManager] 已更新字幕直取开关: "
                    f"enable_bilibili_subtitle_fetch={self._enable_bilibili_subtitle_fetch}"
                )

            if clear_bilibili_sessdata:
                self._bilibili_sessdata = ""
                logger.info("[TranscriptionSettingsManager] 已清空全局 B 站 SESSDATA。")
            elif bilibili_sessdata is not None:
                self._bilibili_sessdata = _sanitize_cookie_value(bilibili_sessdata)
                logger.info(
                    "[TranscriptionSettingsManager] 已更新全局 B 站 SESSDATA。"
                    f" has_value={bool(self._bilibili_sessdata)}"
                )

        return self.get_settings()

    def get_runtime_state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "device": self._device,
                "enable_bilibili_subtitle_fetch": self._enable_bilibili_subtitle_fetch,
                "bilibili_sessdata": self._bilibili_sessdata,
            }

