from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

import yaml

from .metadata import MAX_SURFACE_ATTEMPTS, parse_dt, validate_metadata


@dataclass
class DreamRecord:
    metadata: dict
    body: str
    path: Path

    @property
    def dream_id(self) -> str:
        return str(self.metadata["dream_id"])

    @property
    def generated_at(self) -> datetime:
        return parse_dt(str(self.metadata["generated_at"]))

    @property
    def surfaced(self) -> bool:
        return bool(self.metadata.get("surfaced", False))


class DreamStorage:
    def __init__(self, dreams_dir: Path, logs_dir: Path):
        self.dreams_dir = dreams_dir
        self.logs_dir = logs_dir
        self.dreams_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def write(self, metadata: dict, body: str) -> DreamRecord:
        validate_metadata(metadata)
        dream_id = str(metadata["dream_id"])
        path = self.dreams_dir / f"{dream_id}.md"
        text = "---\n"
        text += yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
        text += "---\n"
        text += body.strip() + "\n"
        path.write_text(text, encoding="utf-8")
        return DreamRecord(metadata=metadata, body=body.strip(), path=path)

    def update(self, record: DreamRecord, **metadata_updates: object) -> DreamRecord:
        metadata = dict(record.metadata)
        metadata.update(metadata_updates)
        return self.write(metadata, record.body)

    def list(self) -> list[DreamRecord]:
        records = []
        for path in sorted(self.dreams_dir.glob("dream_*.md")):
            try:
                records.append(self.read(path))
            except Exception as exc:
                self.log_event("read_error", {"path": str(path), "error": str(exc)})
        return records

    def read(self, path: Path) -> DreamRecord:
        text = path.read_text(encoding="utf-8")
        metadata, body = self._split_frontmatter(text)
        validate_metadata(metadata)
        return DreamRecord(metadata=metadata, body=body.strip(), path=path)

    def delete(self, record: DreamRecord, reason: str) -> None:
        if record.path.exists():
            record.path.unlink()
        self.log_event(
            "dream_event",
            {
                "dream_id": record.dream_id,
                "generated_at": record.metadata.get("generated_at"),
                "deleted_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "deletion_reason": reason,
            },
        )
        self.log_event(
            "deleted",
            {
                "dream_id": record.dream_id,
                "generated_at": record.metadata.get("generated_at"),
                "deleted_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "deletion_reason": reason,
            },
        )

    def cleanup_exhausted(self, max_attempts: int = MAX_SURFACE_ATTEMPTS) -> int:
        deleted = 0
        reason = f"unsurfaced_after_{max_attempts}_attempts"
        for record in self.list():
            attempts = int(record.metadata.get("surface_attempts", 0))
            if not record.surfaced and attempts >= max_attempts:
                self.delete(record, reason=reason)
                deleted += 1
        return deleted

    def status(self, now: datetime) -> dict:
        records = self.list()
        pending = [r for r in records if not r.surfaced]
        # Surfaced dreams are destroyed immediately on surface (spec section 6),
        # so the live count must come from the event log, not the filesystem.
        surfaced = self.count_event("surfaced")
        deleted = self.count_event("deleted")
        oldest_age = None
        if pending:
            oldest_age = max((now - r.generated_at).total_seconds() / 3600 for r in pending)
        return {
            "pending": len(pending),
            "surfaced": surfaced,
            "deleted": deleted,
            "oldest_pending_age_hours": oldest_age,
        }

    def log_event(self, event: str, payload: dict) -> None:
        entry = {"event": event, **payload}
        with (self.logs_dir / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

    def count_event(self, event_name: str) -> int:
        path = self.logs_dir / "events.jsonl"
        if not path.exists():
            return 0
        count = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                if json.loads(line).get("event") == event_name:
                    count += 1
            except json.JSONDecodeError:
                continue
        return count

    def count_deleted_events(self) -> int:
        return self.count_event("deleted")

    @staticmethod
    def _split_frontmatter(text: str) -> tuple[dict, str]:
        if not text.startswith("---\n"):
            raise ValueError("Dream record is missing YAML frontmatter")
        _, rest = text.split("---\n", 1)
        raw_meta, body = rest.split("---\n", 1)
        metadata = yaml.safe_load(raw_meta) or {}
        if not isinstance(metadata, dict):
            raise ValueError("Dream metadata frontmatter must be a mapping")
        return metadata, body
