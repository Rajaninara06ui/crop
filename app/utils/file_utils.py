from __future__ import annotations
import os
import uuid
from pathlib import Path
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_upload_dir() -> Path:
    p = Path(settings.UPLOAD_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_temp_file(data: bytes, suffix: str = "") -> Path:
    upload_dir = get_upload_dir()
    filename = f"{uuid.uuid4().hex}{suffix}"
    path = upload_dir / filename
    path.write_bytes(data)
    logger.debug("Saved temp file: %%s (%%d bytes)", path, len(data))
    return path


def delete_file(path: Path | str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
        logger.debug("Deleted temp file: %%s", path)
    except Exception as exc:
        logger.warning("Could not delete file %%s: %%s", path, exc)


def human_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes //= 1024
    return f"{n_bytes:.1f} TB"
