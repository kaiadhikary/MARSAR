#!/usr/bin/env python3
"""Build the offline GeoIP/ASN lookup table used by MARSAR.

The converter never contacts a network service.  It intersects downloaded
IP2Location LITE country and ASN ranges so every emitted interval has the ASN
that actually covers that IP range.  Unknown ASN gaps are retained explicitly.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def _read_country(path: Path):
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.reader(stream):
            try:
                start, end = int(row[0]), int(row[1])
            except (IndexError, ValueError):
                continue
            if start <= end:
                rows.append((start, end, (row[2].strip() if len(row) > 2 else "") or "UNKNOWN"))
    return sorted(rows)


def _read_asn(path: Path):
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.reader(stream):
            try:
                start, end = int(row[0]), int(row[1])
            except (IndexError, ValueError):
                continue
            if start > end:
                continue
            number = row[3].strip() if len(row) > 3 else ""
            name = row[4].strip() if len(row) > 4 else ""
            label = f"{number} - {name}".strip(" -") or "UNKNOWN"
            rows.append((start, end, label))
    return sorted(rows)


def intersect_ranges(country_rows, asn_rows):
    """Yield disjoint country ranges split exactly at ASN boundaries."""
    index = 0
    for start, end, country in country_rows:
        while index < len(asn_rows) and asn_rows[index][1] < start:
            index += 1
        pos, cursor = start, index
        while cursor < len(asn_rows) and asn_rows[cursor][0] <= end:
            asn_start, asn_end, asn = asn_rows[cursor]
            if pos < asn_start:
                yield pos, min(end, asn_start - 1), country, "UNKNOWN"
            overlap_start, overlap_end = max(pos, asn_start), min(end, asn_end)
            if overlap_start <= overlap_end:
                yield overlap_start, overlap_end, country, asn
                pos = overlap_end + 1
            if asn_end >= end:
                break
            cursor += 1
        if pos <= end:
            yield pos, end, country, "UNKNOWN"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", required=True, type=Path)
    parser.add_argument("--asn", type=Path, help="Optional IP2Location ASN CSV")
    parser.add_argument("--out", type=Path, default=Path("data/geoip_database.csv"))
    args = parser.parse_args()
    countries = _read_country(args.country)
    asns = _read_asn(args.asn) if args.asn else []
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("ip_from", "ip_to", "country_code", "asn_name"))
        for row in intersect_ranges(countries, asns):
            writer.writerow(row)
    print(f"Wrote exact country/ASN intersections to {args.out}")


if __name__ == "__main__":
    main()
