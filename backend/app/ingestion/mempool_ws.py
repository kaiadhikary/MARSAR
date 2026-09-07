"""
Live WebSocket Scraper (Disabled / Airgap Mode).
Live socket connections to external nodes are disabled to meet NTRO offline criteria.
"""

import logging

logger = logging.getLogger(__name__)


class MempoolWebSocketClient:
    def __init__(self, *args, **kwargs):
        logger.warning(
            "[AIRGAP GUARD] MempoolWebSocketClient is disabled. "
            "The system is operating in pure offline mode per NTRO guidelines."
        )

    async def connect(self):
        raise RuntimeError("Online WebSocket ingestion is disabled in this offline environment.")

    async def listen(self):
        return