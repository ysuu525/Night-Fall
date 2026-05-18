from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class NightFallConfig:
    repo_root: Path
    ombre_home: Path | None
    data_dir: Path
    min_surface_age_hours: float = 3.0
    spontaneous_after_hours: float = 24.0
    surface_threshold: float = 0.82
    spontaneous_chance: float = 0.02
    selection_limit: int = 5

    @property
    def dreams_dir(self) -> Path:
        return self.data_dir / "dreams"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_config_path() -> Path:
    return repo_root() / ".nightfall.yaml"


def load_raw_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or Path(os.environ.get("NIGHT_FALL_CONFIG", default_config_path()))
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Night Fall config must be a YAML mapping: {config_path}")
    return data


def save_local_config(ombre_home: Path, path: Path | None = None) -> Path:
    config_path = path or default_config_path()
    payload = {"ombre_home": str(ombre_home.resolve())}
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path


def _float_env(name: str, fallback: float) -> float:
    value = os.environ.get(name)
    if value in (None, ""):
        return fallback
    try:
        return float(value)
    except ValueError:
        return fallback


def _int_env(name: str, fallback: int) -> int:
    value = os.environ.get(name)
    if value in (None, ""):
        return fallback
    try:
        return int(value)
    except ValueError:
        return fallback


def _resolve_ombre_home(raw: dict[str, Any]) -> Path | None:
    candidates: list[str | Path | None] = [
        os.environ.get("OMBRE_HOME"),
        raw.get("ombre_home"),
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser().resolve()
            if (path / "server.py").exists():
                return path
            raise FileNotFoundError(f"OMBRE_HOME does not contain server.py: {path}")
    return None


def _resolve_data_dir(raw: dict[str, Any]) -> Path:
    if os.environ.get("NIGHT_FALL_DATA_DIR"):
        return Path(os.environ["NIGHT_FALL_DATA_DIR"]).expanduser().resolve()
    if raw.get("data_dir"):
        return Path(raw["data_dir"]).expanduser().resolve()
    if os.environ.get("OMBRE_BUCKETS_DIR"):
        return (Path(os.environ["OMBRE_BUCKETS_DIR"]).expanduser().resolve() / "night_fall")
    return repo_root() / "data"


def load_config(require_ombre: bool = True) -> NightFallConfig:
    raw = load_raw_config()
    ombre_home = _resolve_ombre_home(raw)
    if require_ombre and ombre_home is None:
        raise FileNotFoundError(
            "Night Fall needs an existing Ombre install. Set OMBRE_HOME or run "
            "python scripts/install_local.py."
        )

    cfg = NightFallConfig(
        repo_root=repo_root(),
        ombre_home=ombre_home,
        data_dir=_resolve_data_dir(raw),
        min_surface_age_hours=_float_env(
            "NIGHT_FALL_MIN_SURFACE_AGE_HOURS",
            float(raw.get("min_surface_age_hours", 3.0)),
        ),
        spontaneous_after_hours=_float_env(
            "NIGHT_FALL_SPONTANEOUS_AFTER_HOURS",
            float(raw.get("spontaneous_after_hours", 24.0)),
        ),
        surface_threshold=_float_env(
            "NIGHT_FALL_SURFACE_THRESHOLD",
            float(raw.get("surface_threshold", 0.82)),
        ),
        spontaneous_chance=_float_env(
            "NIGHT_FALL_SPONTANEOUS_CHANCE",
            float(raw.get("spontaneous_chance", 0.02)),
        ),
        selection_limit=_int_env("NIGHT_FALL_SELECTION_LIMIT", int(raw.get("selection_limit", 5))),
    )
    cfg.dreams_dir.mkdir(parents=True, exist_ok=True)
    cfg.logs_dir.mkdir(parents=True, exist_ok=True)
    return cfg
