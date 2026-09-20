import csv

from app.ingestion.bulk_parser import OfflineGeoIPResolver
from tools.build_geoip_database import intersect_ranges


def test_country_asn_ranges_are_split_exactly(tmp_path):
    rows = list(intersect_ranges([(10, 100, "AA")], [(10, 40, "AS-A"), (41, 70, "AS-B"), (71, 100, "AS-C")]))
    assert rows == [(10, 40, "AA", "AS-A"), (41, 70, "AA", "AS-B"), (71, 100, "AA", "AS-C")]
    path = tmp_path / "geoip.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["ip_from", "ip_to", "country_code", "asn_name"])
        writer.writerows(rows)
    resolver = OfflineGeoIPResolver(str(path))
    assert resolver._lookup_real_db(50) == ("AA", "AS-B") if hasattr(resolver, "_lookup_real_db") else resolver.resolve("0.0.0.50") == ("AA", "AS-B")
    assert resolver.resolve("8.8.8.8") == ("UNKNOWN", "UNKNOWN")
