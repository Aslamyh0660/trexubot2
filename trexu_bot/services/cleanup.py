from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def cleanup_old_files(base_dirs: list[Path], max_age_days: int) -> int:
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)
    removed = 0
    for base_dir in base_dirs:
        if not base_dir.exists():
            continue
        for path in base_dir.rglob('*'):
            if not path.is_file():
                continue
            try:
                modified = datetime.utcfromtimestamp(path.stat().st_mtime)
                if modified < cutoff:
                    path.unlink(missing_ok=True)
                    removed += 1
            except Exception:
                logger.exception('Failed to cleanup file %s', path)
    return removed
