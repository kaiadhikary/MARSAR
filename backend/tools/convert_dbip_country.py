#!/usr/bin/env python3
"""Convert DB-IP country-lite CSV into MARSAR's offline geoip_database.csv schema.

DB-IP lite format (no header):
  start_ip,end_ip,country_code   # dotted IPv4 strings

MARSAR runtime format (header required):
  ip_from,ip_to,country_code,asn_name   # integer IPv4 bounds; ASN optional
"""
from __future__ import annotations

import argparse
import csv
import ipaddress
from pathlib import Path


def convert_dbip_country(source: Path, output: Path) -> int:
    written = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with source.open("r", encoding="utf-8-sig", newline="") as fin, output.open(
        "w", encoding="utf-8", newline=""
    ) as fout:
        writer = csv.writer(fout)
        writer.writerow(("ip_from", "ip_to", "country_code", "asn_name"))
        for row in csv.reader(fin):
            if len(row) < 3:
                continue
            start_ip, end_ip, country = row[0].strip(), row[1].strip(), row[2].strip()
            if not country or country.upper() == "ZZ":
                country = "UNKNOWN"
            try:
                ip_from = int(ipaddress.IPv4Address(start_ip))
                ip_to = int(ipaddress.IPv4Address(end_ip))
            except (ipaddress.AddressValueError, ValueError):
                continue
            if ip_from > ip_to:
                continue
            writer.writerow((ip_from, ip_to, country, "UNKNOWN"))
            written += 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.home() / "OneDrive" / "Desktop" / "dbip-country-lite-2026-09.csv",
        help="DB-IP country-lite CSV (dotted IPv4 ranges)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "geoip_database.csv",
        help="MARSAR geoip_database.csv output path",
    )
    args = parser.parse_args()
    if not args.source.exists():
        alt = Path.home() / "Desktop" / args.source.name
        if alt.exists():
            args.source = alt
        else:
            raise FileNotFoundError(f"DB-IP source not found: {args.source}")
    count = convert_dbip_country(args.source, args.out)
    print(f"Wrote {count:,} country ranges to {args.out}")


if __name__ == "__main__":
    main()
