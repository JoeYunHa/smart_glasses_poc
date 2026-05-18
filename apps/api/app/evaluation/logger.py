"""Per-request evaluation log writer.

Logs are stored as newline-delimited JSON in data/logs/eval.jsonl.
"""

import json
import os
from pathlib import Path

from app.config import settings
from app.schemas.log import EvaluationLog

_log_path: Path | None = None


def _get_log_path() -> Path:
    global _log_path
    if _log_path is None:
        p = Path(settings.log_dir)
        p.mkdir(parents=True, exist_ok=True)
        _log_path = p / "eval.jsonl"
    return _log_path


async def write_log(log: EvaluationLog) -> None:
    path = _get_log_path()
    record = log.model_dump(mode="json")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_logs(limit: int = 100) -> list[dict]:
    path = _get_log_path()
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines[-limit:]]


def clear_logs() -> int:
    """eval.jsonl을 초기화하고 삭제된 레코드 수를 반환한다."""
    path = _get_log_path()
    if not path.exists():
        return 0
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    count = len([l for l in lines if l.strip()])
    path.write_text("", encoding="utf-8")
    return count
