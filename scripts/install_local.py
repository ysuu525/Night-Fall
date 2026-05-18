from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from night_fall.config import save_local_config


def _default_ombre_home() -> Path | None:
    sibling = REPO_ROOT.parent / "Ombre-Brain"
    if (sibling / "server.py").exists():
        return sibling.resolve()
    return None


def main() -> None:
    print("Night Fall local installer")
    print("This configures Night Fall to load your existing Ombre Brain folder.")
    detected = _default_ombre_home()
    prompt = "Path to Ombre-Brain"
    if detected:
        prompt += f" [{detected}]"
    prompt += ": "
    answer = input(prompt).strip()
    ombre_home = Path(answer).expanduser() if answer else detected
    if ombre_home is None:
        raise SystemExit("No Ombre path provided.")
    ombre_home = ombre_home.resolve()
    if not (ombre_home / "server.py").exists():
        raise SystemExit(f"That folder does not contain server.py: {ombre_home}")

    config_path = save_local_config(ombre_home)
    print(f"Saved config: {config_path}")
    print("")
    print("Start Ombre with Night Fall:")
    print("  python -m night_fall.launcher")


if __name__ == "__main__":
    main()
