#!/usr/bin/env python3
"""
Synthetic Dataset Generator for NTRO Problem Statement 5.
Generates correlated Bitcoin network-layer telemetry and blockchain-layer ledger data
in CSV, JSON, and XML formats matching required forensic fields.
"""

import csv
import json
import random
import time
import xml.etree.ElementTree as ET
from pathlib import Path


def generate_datasets(output_dir: str = "data"):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    # Known seeds representing designated illicit nodes
    seeds = [
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "1CounterpartyXXXXXXXXXXXXXXXUWLpVr",
        "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"
    ]

    records = []
    base_time = int(time.time()) - 100000

    # 1. Peeling-Chain Laundering Pattern (5 iterative hops with high asymmetry)
    curr_addr = seeds[0]
    for hop in range(5):
        txid = f"tx_ransom_peel_hop_{hop}_{random.randint(1000, 9999)}"
        peeled = round(random.uniform(0.08, 0.25), 5)
        change = round(random.uniform(2.0, 2.5) - (hop * 0.3), 5)
        next_addr = f"addr_peel_change_hop_{hop + 1}"

        records.append({
            "txid": txid,
            "timestamp": base_time + (hop * 600),
            "src_ip": "198.51.100.24",
            "dst_ip": "104.28.16.5",
            "src_port": 45210 + hop,
            "dst_port": 8333,
            "fee": 0.00025,
            "script_type": "p2wpkh",
            "geo_country": "RU",
            "geo_asn": "AS12389 - Rostelecom",
            "input_addresses": [curr_addr],
            "input_amounts": [round(peeled + change + 0.00025, 5)],
            "output_addresses": [f"addr_cashout_peel_{hop + 1}", next_addr],
            "output_amounts": [peeled, change]
        })
        curr_addr = next_addr

    # 2. CoinJoin Mixer Topology (Equal output amounts across distinct parties)
    records.append({
        "txid": "tx_coinjoin_mixer_9981",
        "timestamp": base_time + 4000,
        "src_ip": "203.0.113.88",
        "dst_ip": "104.28.16.5",
        "src_port": 50122,
        "dst_port": 8333,
        "fee": 0.00040,
        "script_type": "p2sh",
        "geo_country": "IR",
        "geo_asn": "AS58224 - TIC",
        "input_addresses": ["addr_mix_in_1", "addr_mix_in_2", "addr_mix_in_3", "addr_mix_in_4"],
        "input_amounts": [0.501, 0.502, 0.501, 0.503],
        "output_addresses": ["addr_clean_out_1", "addr_clean_out_2", "addr_clean_out_3", "addr_clean_out_4"],
        "output_amounts": [0.500, 0.500, 0.500, 0.500]
    })

    # 3. Common-Input-Ownership (CIOH) Clustering Signatures
    records.append({
        "txid": "tx_cioh_consolidation_01",
        "timestamp": base_time + 5000,
        "src_ip": "194.26.29.11",
        "dst_ip": "104.28.16.5",
        "src_port": 55120,
        "dst_port": 8333,
        "fee": 0.00030,
        "script_type": "p2wsh",
        "geo_country": "SC",
        "geo_asn": "AS51852 - Private Layer",
        "input_addresses": ["addr_clustered_entity_a1", "addr_clustered_entity_a2", "addr_clustered_entity_a3"],
        "input_amounts": [1.20, 2.40, 0.80],
        "output_addresses": ["addr_vault_target"],
        "output_amounts": [4.39970]
    })

    # 4. Statistically Unusual / Outlier Transaction (Isolation Forest target)
    records.append({
        "txid": "tx_outlier_high_urgency_01",
        "timestamp": base_time + 6500,
        "src_ip": "185.220.101.5",
        "dst_ip": "104.28.16.5",
        "src_port": 61234,
        "dst_port": 49152,  # Non-standard P2P port
        "fee": 0.04500,     # Urgently high miner fee
        "script_type": "p2pkh",
        "geo_country": "DE",
        "geo_asn": "AS205100 - Tor Exit Relay",
        "input_addresses": ["addr_anomalous_funder"],
        "input_amounts": [0.15000],
        "output_addresses": ["addr_anomalous_recipient"],
        "output_amounts": [0.10500]
    })

    # 5. Benign Background Payment Traffic
    for i in range(25):
        in_amt = round(random.uniform(0.05, 1.8), 5)
        out_amt = round(in_amt - 0.00005, 5)
        records.append({
            "txid": f"tx_benign_transfer_{i:02d}_{random.randint(1000, 9999)}",
            "timestamp": base_time + 10000 + (i * 300),
            "src_ip": f"192.0.2.{random.randint(2, 250)}",
            "dst_ip": "104.28.16.5",
            "src_port": random.randint(30000, 60000),
            "dst_port": 8333,
            "fee": 0.00005,
            "script_type": "p2wpkh",
            "geo_country": "US",
            "geo_asn": "AS15169 - Google LLC",
            "input_addresses": [f"addr_benign_user_{i}"],
            "input_amounts": [in_amt],
            "output_addresses": [f"addr_merchant_wallet_{i}"],
            "output_amounts": [out_amt]
        })

    # --- Write CSV ---
    csv_file = out_path / "bitcoin_telemetry.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "txid", "timestamp", "src_ip", "dst_ip", "src_port", "dst_port",
            "fee", "script_type", "geo_country", "geo_asn",
            "input_addresses", "output_addresses", "input_amounts", "output_amounts"
        ])
        for r in records:
            writer.writerow([
                r["txid"], r["timestamp"], r["src_ip"], r["dst_ip"], r["src_port"], r["dst_port"],
                r["fee"], r["script_type"], r["geo_country"], r["geo_asn"],
                ";".join(r["input_addresses"]), ";".join(r["output_addresses"]),
                ";".join(map(str, r["input_amounts"])), ";".join(map(str, r["output_amounts"]))
            ])

    # --- Write JSON ---
    json_file = out_path / "bitcoin_telemetry.json"
    json_data = []
    for r in records:
        json_data.append({
            "txid": r["txid"],
            "timestamp": r["timestamp"],
            "src_ip": r["src_ip"],
            "dst_ip": r["dst_ip"],
            "src_port": r["src_port"],
            "dst_port": r["dst_port"],
            "fee": r["fee"],
            "script_type": r["script_type"],
            "geo_country": r["geo_country"],
            "geo_asn": r["geo_asn"],
            "inputs": [{"address": a, "amount": amt} for a, amt in zip(r["input_addresses"], r["input_amounts"])],
            "outputs": [{"address": a, "amount": amt} for a, amt in zip(r["output_addresses"], r["output_amounts"])]
        })
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    # --- Write XML ---
    xml_file = out_path / "bitcoin_telemetry.xml"
    root = ET.Element("transactions")
    for r in records:
        tx_node = ET.SubElement(root, "transaction")
        ET.SubElement(tx_node, "txid").text = r["txid"]
        ET.SubElement(tx_node, "timestamp").text = str(r["timestamp"])
        ET.SubElement(tx_node, "src_ip").text = r["src_ip"]
        ET.SubElement(tx_node, "dst_ip").text = r["dst_ip"]
        ET.SubElement(tx_node, "src_port").text = str(r["src_port"])
        ET.SubElement(tx_node, "dst_port").text = str(r["dst_port"])
        ET.SubElement(tx_node, "fee").text = str(r["fee"])
        ET.SubElement(tx_node, "script_type").text = r["script_type"]
        ET.SubElement(tx_node, "geo_country").text = r["geo_country"]
        ET.SubElement(tx_node, "geo_asn").text = r["geo_asn"]

        inputs_node = ET.SubElement(tx_node, "inputs")
        for a, amt in zip(r["input_addresses"], r["input_amounts"]):
            in_item = ET.SubElement(inputs_node, "input")
            ET.SubElement(in_item, "address").text = a
            ET.SubElement(in_item, "amount").text = str(amt)

        outputs_node = ET.SubElement(tx_node, "outputs")
        for a, amt in zip(r["output_addresses"], r["output_amounts"]):
            out_item = ET.SubElement(outputs_node, "output")
            ET.SubElement(out_item, "address").text = a
            ET.SubElement(out_item, "amount").text = str(amt)

    ET.ElementTree(root).write(xml_file, encoding="utf-8", xml_declaration=True)
    print(f"[+] Synthetic datasets created successfully in '{output_dir}/' ({len(records)} transactions per format)")


if __name__ == "__main__":
    generate_datasets()