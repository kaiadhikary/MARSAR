import hashlib
import json
from typing import Any, Dict


class ForensicHasher:
    """
    Cryptographic chain-of-custody verification engine.
    Computes deterministic SHA-256 digests for evidence payloads and generated reports
    to ensure tamper-evident integrity for forensic analysis.
    """

    @staticmethod
    def hash_payload(data: Any) -> str:
        """Computes a deterministic SHA-256 hash of a dictionary or string."""
        if isinstance(data, dict) or isinstance(data, list):
            serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        elif isinstance(data, str):
            serialized = data
        elif isinstance(data, bytes):
            return hashlib.sha256(data).hexdigest()
        else:
            serialized = str(data)

        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_integrity(data: Any, expected_hash: str) -> bool:
        """Verifies whether data matches an expected SHA-256 digest."""
        computed = ForensicHasher.hash_payload(data)
        return computed.lower() == expected_hash.lower()