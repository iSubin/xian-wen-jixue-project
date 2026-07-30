from pathlib import Path


def _read_version_from_root() -> str:
    root = Path(__file__).resolve().parents[4]
    version_file = root / "VERSION"
    try:
        version = version_file.read_text(encoding="utf-8").strip()
        if version:
            return version
    except Exception:
        pass
    return "0.0.0"


APP_VERSION = _read_version_from_root()
