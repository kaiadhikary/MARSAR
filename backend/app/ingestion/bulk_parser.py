import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Tuple
from app.db.sqlite_client import get_db_connection


class OfflineGeoIPResolver:
    """
    Offline GeoIP & ASN Resolver integrating downloadable local CSV databases
    with embedded subnet fallback tables.
    """
    def __init__(self, geoip_csv_path: str | None = None):
        self.subnet_table = {
            "198.51.100": ("RU", "AS12389 - Rostelecom"),
            "203.0.113": ("IR", "AS58224 - TIC"),
            "192.0.2": ("NL", "AS49981 - WorldStream"),
            "104.28": ("US", "AS13335 - Cloudflare"),
            "185.220": ("DE", "AS205100 - Tor Exit Node"),
            "194.26": ("SC", "AS51852 - Private Layer"),
            "45.33": ("US", "AS63949 - Linode"),
            "195.123": ("LV", "AS50360 - BalticServers")
        }
        # Load downloadable offline GeoIP DB if supplied
        # Resolve relative to the application, not the caller's working directory.
        db_path = Path(geoip_csv_path) if geoip_csv_path else Path(__file__).resolve().parents[2] / "data" / "geoip_database.csv"
        if db_path.exists():
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        prefix = row.get("subnet_prefix")
                        country = row.get("country_code")
                        asn = row.get("asn_name")
                        if prefix and country and asn:
                            self.subnet_table[prefix.strip()] = (country.strip(), asn.strip())
            except Exception:
                pass

    def resolve(self, ip: str) -> Tuple[str, str]:
        if not ip or ip == "UNKNOWN":
            return "UNKNOWN", "UNKNOWN"
        parts = ip.strip().split(".")
        if len(parts) == 4:
            slash_24 = f"{parts[0]}.{parts[1]}.{parts[2]}"
            slash_16 = f"{parts[0]}.{parts[1]}"
            if slash_24 in self.subnet_table:
                return self.subnet_table[slash_24]
            if slash_16 in self.subnet_table:
                return self.subnet_table[slash_16]
        return "US", "AS15169 - Google LLC"


class BulkDataParser:
    def __init__(self):
        self.geo_resolver = OfflineGeoIPResolver()

    def _normalize_lists(self, addrs: List[str], amts: List[float]) -> Tuple[List[Dict[str, Any]], float]:
        pairs = []
        total = 0.0
        for i in range(max(len(addrs), len(amts))):
            addr = addrs[i] if i < len(addrs) else f"UNKNOWN_ADDR_{i}"
            amt = float(amts[i]) if i < len(amts) else 0.0
            pairs.append({"address": addr, "amount": amt})
            total += amt
        return pairs, round(total, 8)

    def parse_csv(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                txid = (row.get("txid") or "").strip()
                if not txid:
                    continue

                in_addrs = [a.strip() for a in (row.get("input_addresses") or "").split(";") if a.strip()]
                out_addrs = [a.strip() for a in (row.get("output_addresses") or "").split(";") if a.strip()]

                in_amts = []
                for a in (row.get("input_amounts") or "").split(";"):
                    if a.strip():
                        try:
                            in_amts.append(float(a.strip()))
                        except ValueError:
                            in_amts.append(0.0)

                out_amts = []
                for a in (row.get("output_amounts") or "").split(";"):
                    if a.strip():
                        try:
                            out_amts.append(float(a.strip()))
                        except ValueError:
                            out_amts.append(0.0)

                src_ip = (row.get("src_ip") or "UNKNOWN").strip()
                dst_ip = (row.get("dst_ip") or "UNKNOWN").strip()
                country = (row.get("geo_country") or "").strip()
                asn = (row.get("geo_asn") or "").strip()

                if not country or not asn or country == "UNKNOWN":
                    country, asn = self.geo_resolver.resolve(src_ip)

                inputs, total_in = self._normalize_lists(in_addrs, in_amts)
                outputs, total_out = self._normalize_lists(out_addrs, out_amts)

                try:
                    fee_val = float(row.get("fee") or 0.0001)
                except ValueError:
                    fee_val = 0.0001

                records.append({
                    "txid": txid,
                    "timestamp": int(row.get("timestamp") or 0),
                    "src_ip": src_ip or "UNKNOWN",
                    "dst_ip": dst_ip or "UNKNOWN",
                    "src_port": int(row.get("src_port") or 8333),
                    "dst_port": int(row.get("dst_port") or 8333),
                    "fee": fee_val,
                    "script_type": row.get("script_type") or "p2wpkh",
                    "geo_country": country,
                    "geo_asn": asn,
                    "inputs": inputs,
                    "outputs": outputs,
                    "total_input_btc": total_in,
                    "total_output_btc": total_out
                })
        return records

    def parse_json(self, file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "transactions" in data:
            data = data["transactions"]

        records = []
        for row in data:
            txid = (row.get("txid") or "").strip()
            if not txid:
                continue

            src_ip = (row.get("src_ip") or "UNKNOWN").strip()
            dst_ip = (row.get("dst_ip") or "UNKNOWN").strip()
            country = (row.get("geo_country") or "").strip()
            asn = (row.get("geo_asn") or "").strip()

            if not country or not asn:
                country, asn = self.geo_resolver.resolve(src_ip)

            inputs = row.get("inputs", [])
            outputs = row.get("outputs", [])

            total_in = round(sum(float(i.get("amount") or 0.0) for i in inputs), 8)
            total_out = round(sum(float(o.get("amount") or 0.0) for o in outputs), 8)

            records.append({
                "txid": txid,
                "timestamp": int(row.get("timestamp") or 0),
                "src_ip": src_ip or "UNKNOWN",
                "dst_ip": dst_ip or "UNKNOWN",
                "src_port": int(row.get("src_port") or 8333),
                "dst_port": int(row.get("dst_port") or 8333),
                "fee": float(row.get("fee") or 0.0001),
                "script_type": row.get("script_type") or "p2wpkh",
                "geo_country": country,
                "geo_asn": asn,
                "inputs": inputs,
                "outputs": outputs,
                "total_input_btc": total_in,
                "total_output_btc": total_out
            })
        return records

    def parse_xml(self, file_path: str) -> List[Dict[str, Any]]:
        def _get_text(elem, default=""):
            return elem.text.strip() if (elem is not None and elem.text) else default

        def _get_float(elem, default=0.0):
            val = _get_text(elem)
            try:
                return float(val) if val else default
            except ValueError:
                return default

        def _get_int(elem, default=0):
            val = _get_text(elem)
            try:
                return int(val) if val else default
            except ValueError:
                return default

        tree = ET.parse(file_path)
        root = tree.getroot()
        records = []

        for tx_elem in root.findall("transaction"):
            txid = _get_text(tx_elem.find("txid"))
            if not txid:
                continue

            ts = _get_int(tx_elem.find("timestamp"), 0)
            src_ip = _get_text(tx_elem.find("src_ip"), "UNKNOWN")
            dst_ip = _get_text(tx_elem.find("dst_ip"), "UNKNOWN")
            src_port = _get_int(tx_elem.find("src_port"), 8333)
            dst_port = _get_int(tx_elem.find("dst_port"), 8333)
            fee = _get_float(tx_elem.find("fee"), 0.0001)
            script_type = _get_text(tx_elem.find("script_type"), "p2wpkh")

            country = _get_text(tx_elem.find("geo_country"))
            asn = _get_text(tx_elem.find("geo_asn"))
            if not country or not asn:
                country, asn = self.geo_resolver.resolve(src_ip)

            inputs = []
            inputs_tag = tx_elem.find("inputs")
            if inputs_tag is not None:
                for in_node in inputs_tag.findall("input"):
                    addr = _get_text(in_node.find("address"), "UNKNOWN")
                    amt = _get_float(in_node.find("amount"), 0.0)
                    inputs.append({"address": addr, "amount": amt})

            outputs = []
            outputs_tag = tx_elem.find("outputs")
            if outputs_tag is not None:
                for out_node in outputs_tag.findall("output"):
                    addr = _get_text(out_node.find("address"), "UNKNOWN")
                    amt = _get_float(out_node.find("amount"), 0.0)
                    outputs.append({"address": addr, "amount": amt})

            total_in = round(sum(i["amount"] for i in inputs), 8)
            total_out = round(sum(o["amount"] for o in outputs), 8)

            records.append({
                "txid": txid,
                "timestamp": ts,
                "src_ip": src_ip or "UNKNOWN",
                "dst_ip": dst_ip or "UNKNOWN",
                "src_port": src_port,
                "dst_port": dst_port,
                "fee": fee,
                "script_type": script_type,
                "geo_country": country,
                "geo_asn": asn,
                "inputs": inputs,
                "outputs": outputs,
                "total_input_btc": total_in,
                "total_output_btc": total_out
            })
        return records

    def ingest_to_db(self, records: List[Dict[str, Any]]) -> int:
        if not records:
            return 0
        conn = get_db_connection()
        cur = conn.cursor()
        for r in records:
            cur.execute('''
                INSERT OR REPLACE INTO transactions (
                    txid, timestamp, src_ip, dst_ip, src_port, dst_port,
                    fee, script_type, geo_country, geo_asn,
                    inputs_json, outputs_json, total_input_btc, total_output_btc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                r["txid"], r["timestamp"], r["src_ip"], r["dst_ip"],
                r["src_port"], r["dst_port"], r["fee"], r["script_type"],
                r["geo_country"], r["geo_asn"],
                json.dumps(r["inputs"]), json.dumps(r["outputs"]),
                r["total_input_btc"], r["total_output_btc"]
            ))
        conn.commit()
        conn.close()
        return len(records)

    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse one supported offline bulk file, selected by its extension."""
        suffix = Path(file_path).suffix.lower()
        parsers = {".csv": self.parse_csv, ".json": self.parse_json, ".xml": self.parse_xml}
        if suffix not in parsers:
            raise ValueError("Unsupported dataset format. Use CSV, JSON, or XML.")
        return parsers[suffix](file_path)
