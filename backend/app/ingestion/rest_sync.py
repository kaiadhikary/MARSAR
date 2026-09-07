"""
External REST Sync Service (Disabled / Airgap Mode).
Outbound HTTP polling is disabled to enforce offline isolation.
"""

import logging

logger = logging.getLogger(__name__)


class RESTSyncService:
    def __init__(self, *args, **kwargs):
        logger.warning(
            "[AIRGAP GUARD] RESTSyncService is disabled. "
            "All telemetry must be ingested through local CSV, JSON, or XML files."
        )

    async def sync_latest_blocks(self):
        raise RuntimeError("Outbound REST synchronization is disabled in offline mode.")