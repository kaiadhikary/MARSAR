"""
Ingestion module for offline Bitcoin transaction and network metadata.
Provides multi-format bulk parsing (CSV, JSON, XML) and offline GeoIP/ASN resolution.
"""

from app.ingestion.bulk_parser import BulkDataParser, OfflineGeoIPResolver

__all__ = ["BulkDataParser", "OfflineGeoIPResolver"]