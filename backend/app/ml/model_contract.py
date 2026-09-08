"""Offline model artifact contract shared by training and inference."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

FEATURE_SCHEMA_VERSION = "blockchain_network_v1"


class ModelContractError(RuntimeError):
    pass


def validate_model_contract(model: Any, expected_schema: str = FEATURE_SCHEMA_VERSION) -> Dict[str, Any]:
    metadata = getattr(model, "marsar_metadata_", None)
    if not isinstance(metadata, dict):
        raise ModelContractError("Model artifact has no MARSAR metadata. Retrain it through ml_training before deployment.")
    if metadata.get("feature_schema") != expected_schema:
        raise ModelContractError(f"Model schema {metadata.get('feature_schema')!r} is incompatible with runtime schema {expected_schema!r}.")
    return metadata
