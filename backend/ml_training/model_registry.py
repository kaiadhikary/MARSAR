"""Versioned local model registry. Promotion is an explicit operator action."""
from __future__ import annotations

import json
import shutil
from pathlib import Path


def register(model_path: Path, metadata: dict, registry: Path, version: str, promote: bool = False) -> Path:
    target = registry / version
    target.mkdir(parents=True, exist_ok=False)
    shutil.copy2(model_path, target / "bitcoin_gbdt.joblib")
    (target / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    if promote:
        current = registry / "current"
        current.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target / "bitcoin_gbdt.joblib", current / "bitcoin_gbdt.joblib")
        (current / "metadata.json").write_text((target / "metadata.json").read_text(encoding="utf-8"), encoding="utf-8")
        (registry / "current.json").write_text(json.dumps({"version": version}), encoding="utf-8")
    return target
