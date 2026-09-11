#!/usr/bin/env python3
"""
Synthetic Dataset Generator for NTRO Problem Statement 5.
Generates correlated Bitcoin network-layer telemetry and blockchain-layer ledger data
in CSV, JSON, and XML formats matching required forensic fields.

SCALED UP from the original 30-ish-transaction demo set to >=1000 transactions
by default, entirely offline (no API calls, no downloads) - this only needs
Python's own `random` module. Every IP used is drawn from the same 6 ranges
already in data/geoip_database.csv (US/Cloudflare, DE/Tor, NL/WorldStream,
SC/PrivateLayer, RU/Rostelecom, IR/TIC), so GeoIP resolution engages
meaningfully across the whole dataset - not just the handful of illustrative
anomaly examples.

Also adds a scatter-gather (layering) pattern, which the original generator
didn't produce at all despite the engine supporting detection for it, and a
ground_truth.csv sidecar (txid -> injected pattern) so you can evaluate your
own detector's precision/recall against known answers. That sidecar is never
fed into the pipeline itself - a real detector obviously doesn't get the
answer key, this is purely for your own evaluation.
"""

import csv
import json
import random
import time
import xml.etree.ElementTree as ET
from pathlib import Path

# All 6 pools line up with the ranges in data/geoip_database.csv, so real
# range-based GeoIP resolution is exercised across the whole dataset.
GEO_POOLS = {
    "US": {"prefix": "104.28.", "asn": "AS13335 - Cloudflare"},
    "DE": {"prefix": "185.220.", "asn": "AS205100 - Tor Exit Node"},
    "NL": {"prefix": "192.0.2.", "asn": "AS49981 - WorldStream"},
    "SC": {"prefix": "194.26.", "asn": "AS51852 - Private Layer"},
    "RU": {"prefix": "198.51.100.", "asn": "AS12389 - Rostelecom"},
    "IR": {"prefix": "203.0.113.", "asn": "AS58224 - TIC"},
}
# Benign traffic is weighted mostly toward "clean-looking" pools but
# deliberately includes some RU/IR/DE traffic too - a real detector needs to
# key off actual behavioral patterns (peeling, mixing, velocity), not just
# "this IP's country looks suspicious", or the challenge is trivial.
BENIGN_POOL_WEIGHTS = [("US", 35), ("NL", 30), ("SC", 15), ("RU", 10), ("IR", 5), ("DE", 5)]


def _random_ip(prefix: str) -> str:
    octets_needed = 4 - prefix.count(".")
    return prefix + ".".join(str(random.randint(1, 254)) for _ in range(octets_needed))


def _weighted_pool() -> str:
    names, weights = zip(*BENIGN_POOL_WEIGHTS)
    return random.choices(names, weights=weights, k=1)[0]


def _addr(prefix: str = "addr") -> str:
    return f"{prefix}_{random.randint(10_000_000, 99_999_999):08d}"


def generate_datasets(
    output_dir: str = "data",
    num_benign: int = 900,
    num_peeling_chains: int = 6,
    peeling_chain_hops: int = 5,
    num_coinjoin: int = 10,
    num_cioh: int = 10,
    num_outliers: int = 10,
    num_geo_anomalies: int = 15,
    num_scatter_gather: int = 5,
    scatter_fanout: int = 15,
    seed: int = 42,
):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    random.seed(seed)

    seeds = [
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "1CounterpartyXXXXXXXXXXXXXXXUWLpVr",
        "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
    ]

    records = []
    ground_truth = []  # (txid, pattern, detail) - sidecar only, never ingested
    base_time = int(time.time()) - 500_000
    t = base_time

    def emit(pattern, **kwargs):
        nonlocal t
        records.append(kwargs)
        if pattern:
            ground_truth.append((kwargs["txid"], pattern, kwargs.get("_detail", "")))

    # ---------------------------------------------------------------
    # 1. Peeling-chain laundering (multiple independent chains)
    # ---------------------------------------------------------------
    for chain_i in range(num_peeling_chains):
        pool = random.choice(["RU", "IR", "DE"])  # laundering ops skew toward these pools
        geo = GEO_POOLS[pool]
        curr_addr = seeds[chain_i % len(seeds)]
        t += random.randint(200, 2000)
        chain_txids = []
        for hop in range(peeling_chain_hops):
            txid = f"tx_ransom_peel_{chain_i}_{hop}_{random.randint(1000, 9999)}"
            peeled = round(random.uniform(0.05, 0.30), 5)
            change = round(random.uniform(1.5, 3.0) - (hop * 0.25), 5)
            next_addr = f"addr_peel_change_c{chain_i}_hop_{hop + 1}"
            t += random.randint(20, 90)  # rapid hops
            emit(
                "peeling_chain",
                txid=txid, timestamp=t, src_ip=_random_ip(geo["prefix"]), dst_ip="104.28.16.5",
                src_port=random.randint(40000, 60000), dst_port=8333,
                fee=0.00025, script_type="p2wpkh", geo_country=pool, geo_asn=geo["asn"],
                input_addresses=[curr_addr], input_amounts=[round(peeled + change + 0.00025, 5)],
                output_addresses=[f"addr_cashout_peel_c{chain_i}_{hop + 1}", next_addr],
                output_amounts=[peeled, change],
                _detail=f"chain {chain_i}, hop {hop}",
            )
            chain_txids.append(txid)
            curr_addr = next_addr

    # ---------------------------------------------------------------
    # 2. CoinJoin mixer topology (equal outputs across distinct parties)
    # ---------------------------------------------------------------
    for i in range(num_coinjoin):
        pool = random.choice(["IR", "DE", "SC"])
        geo = GEO_POOLS[pool]
        n = random.choice([4, 5, 6, 8])
        denom = round(random.choice([0.1, 0.25, 0.5, 1.0]), 5)
        t += random.randint(300, 3000)
        emit(
            "coinjoin",
            txid=f"tx_coinjoin_mixer_{i}_{random.randint(1000,9999)}", timestamp=t,
            src_ip=_random_ip(geo["prefix"]), dst_ip="104.28.16.5",
            src_port=random.randint(40000, 60000), dst_port=8333,
            fee=round(0.0001 * n, 5), script_type="p2sh", geo_country=pool, geo_asn=geo["asn"],
            input_addresses=[_addr("mix_in") for _ in range(n)],
            input_amounts=[round(denom + random.uniform(0.0005, 0.003), 5) for _ in range(n)],
            output_addresses=[_addr("clean_out") for _ in range(n)],
            output_amounts=[denom] * n,
            _detail=f"{n}-participant mix, denom={denom} BTC",
        )

    # ---------------------------------------------------------------
    # 3. Common-Input-Ownership (CIOH) consolidation signatures
    # ---------------------------------------------------------------
    for i in range(num_cioh):
        pool = random.choice(list(GEO_POOLS.keys()))
        geo = GEO_POOLS[pool]
        n = random.randint(3, 6)
        amounts = [round(random.uniform(0.3, 3.0), 5) for _ in range(n)]
        total = round(sum(amounts) - 0.0003, 5)
        t += random.randint(300, 3000)
        emit(
            "cioh_consolidation",
            txid=f"tx_cioh_consolidation_{i}_{random.randint(1000,9999)}", timestamp=t,
            src_ip=_random_ip(geo["prefix"]), dst_ip="104.28.16.5",
            src_port=random.randint(40000, 60000), dst_port=8333,
            fee=0.0003, script_type="p2wsh", geo_country=pool, geo_asn=geo["asn"],
            input_addresses=[_addr("clustered_entity") for _ in range(n)],
            input_amounts=amounts,
            output_addresses=[_addr("vault_target")],
            output_amounts=[total],
            _detail=f"{n} inputs consolidated by one entity",
        )

    # ---------------------------------------------------------------
    # 4. Statistically unusual outlier transactions (Isolation Forest target)
    # ---------------------------------------------------------------
    for i in range(num_outliers):
        t += random.randint(300, 3000)
        emit(
            "outlier",
            txid=f"tx_outlier_high_urgency_{i}_{random.randint(1000,9999)}", timestamp=t,
            src_ip=_random_ip(GEO_POOLS["DE"]["prefix"]), dst_ip="104.28.16.5",
            src_port=random.randint(40000, 65000), dst_port=49152,  # non-standard P2P port
            fee=round(random.uniform(0.02, 0.06), 5),  # urgently high miner fee
            script_type="p2pkh", geo_country="DE", geo_asn=GEO_POOLS["DE"]["asn"],
            input_addresses=[_addr("anomalous_funder")], input_amounts=[round(random.uniform(0.1, 0.3), 5)],
            output_addresses=[_addr("anomalous_recipient")], output_amounts=[round(random.uniform(0.08, 0.25), 5)],
            _detail="non-standard port + urgent fee",
        )

    # ---------------------------------------------------------------
    # 5. Geo anomalies: a normally-benign wallet suddenly transacts from a
    #    high-risk pool (impossible-travel / account-takeover signature)
    # ---------------------------------------------------------------
    for i in range(num_geo_anomalies):
        pool = random.choice(["RU", "IR", "DE"])
        geo = GEO_POOLS[pool]
        t += random.randint(100, 1000)
        emit(
            "geo_anomaly",
            txid=f"tx_geo_anomaly_{i}_{random.randint(1000,9999)}", timestamp=t,
            src_ip=_random_ip(geo["prefix"]), dst_ip="104.28.16.5",
            src_port=random.randint(40000, 60000), dst_port=8333,
            fee=0.0002, script_type="p2wpkh", geo_country=pool, geo_asn=geo["asn"],
            input_addresses=[_addr("previously_benign_wallet")], input_amounts=[round(random.uniform(0.2, 2.0), 5)],
            output_addresses=[_addr("recipient")], output_amounts=[round(random.uniform(0.19, 1.99), 5)],
            _detail=f"unexpected jump to {pool}",
        )

    # ---------------------------------------------------------------
    # 6. Scatter-gather / layering: 1 -> N fresh addresses -> 1 (NEW - the
    #    original generator never produced this pattern at all)
    # ---------------------------------------------------------------
    for i in range(num_scatter_gather):
        pool = random.choice(["RU", "IR", "SC"])
        geo = GEO_POOLS[pool]
        source = _addr("scatter_source")
        total = round(scatter_fanout * random.uniform(0.05, 0.3), 5)
        per_addr = round((total - 0.0005) / scatter_fanout, 5)
        layer_addrs = [_addr("layer") for _ in range(scatter_fanout)]

        t += random.randint(300, 3000)
        scatter_txid = f"tx_scatter_{i}_{random.randint(1000,9999)}"
        emit(
            "scatter_gather",
            txid=scatter_txid, timestamp=t, src_ip=_random_ip(geo["prefix"]), dst_ip="104.28.16.5",
            src_port=random.randint(40000, 60000), dst_port=8333,
            fee=0.0005, script_type="p2wpkh", geo_country=pool, geo_asn=geo["asn"],
            input_addresses=[source], input_amounts=[total],
            output_addresses=layer_addrs, output_amounts=[per_addr] * scatter_fanout,
            _detail=f"fan-out to {scatter_fanout} addresses",
        )

        gather_addr = _addr("gather_deposit")
        for addr in layer_addrs:
            t += random.randint(60, 1800)  # converge within ~30 min
            spend = round(per_addr * 0.97, 5)
            emit(
                "scatter_gather",
                txid=f"tx_gather_{i}_{random.randint(100000,999999)}", timestamp=t,
                src_ip=_random_ip(geo["prefix"]), dst_ip="104.28.16.5",
                src_port=random.randint(40000, 60000), dst_port=8333,
                fee=0.0001, script_type="p2wpkh", geo_country=pool, geo_asn=geo["asn"],
                input_addresses=[addr], input_amounts=[per_addr],
                output_addresses=[gather_addr], output_amounts=[spend],
                _detail=f"converges into gather event {i} (source tx {scatter_txid})",
            )

    # ---------------------------------------------------------------
    # 7. Benign background payment traffic (the majority of the dataset)
    # ---------------------------------------------------------------
    for i in range(num_benign):
        pool = _weighted_pool()
        geo = GEO_POOLS[pool]
        in_amt = round(random.uniform(0.01, 2.5), 5)
        out_amt = round(in_amt - random.uniform(0.00003, 0.0001), 5)
        t += random.randint(10, 600)
        emit(
            None,  # not an injected anomaly - no ground-truth row
            txid=f"tx_benign_transfer_{i:04d}_{random.randint(1000, 9999)}", timestamp=t,
            src_ip=_random_ip(geo["prefix"]), dst_ip="104.28.16.5",
            src_port=random.randint(30000, 60000), dst_port=8333,
            fee=round(random.uniform(0.00003, 0.0001), 5), script_type=random.choice(["p2wpkh", "p2pkh", "p2sh"]),
            geo_country=pool, geo_asn=geo["asn"],
            input_addresses=[_addr("benign_user")], input_amounts=[in_amt],
            output_addresses=[_addr("merchant_wallet")], output_amounts=[out_amt],
        )

    # Shuffle so anomalies aren't clustered by generation order - a real
    # bulk export wouldn't be sorted that way, and a detector shouldn't get
    # a free hint from record position.
    random.shuffle(records)

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
            "txid": r["txid"], "timestamp": r["timestamp"], "src_ip": r["src_ip"], "dst_ip": r["dst_ip"],
            "src_port": r["src_port"], "dst_port": r["dst_port"], "fee": r["fee"], "script_type": r["script_type"],
            "geo_country": r["geo_country"], "geo_asn": r["geo_asn"],
            "inputs": [{"address": a, "amount": amt} for a, amt in zip(r["input_addresses"], r["input_amounts"])],
            "outputs": [{"address": a, "amount": amt} for a, amt in zip(r["output_addresses"], r["output_amounts"])],
        })
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    # --- Write XML ---
    xml_file = out_path / "bitcoin_telemetry.xml"
    root = ET.Element("transactions")
    for r in records:
        tx_node = ET.SubElement(root, "transaction")
        for key in ("txid", "timestamp", "src_ip", "dst_ip", "src_port", "dst_port",
                    "fee", "script_type", "geo_country", "geo_asn"):
            ET.SubElement(tx_node, key).text = str(r[key])
        inputs_node = ET.SubElement(tx_node, "inputs")
        for a, amt in zip(r["input_addresses"], r["input_amounts"]):
            item = ET.SubElement(inputs_node, "input")
            ET.SubElement(item, "address").text = a
            ET.SubElement(item, "amount").text = str(amt)
        outputs_node = ET.SubElement(tx_node, "outputs")
        for a, amt in zip(r["output_addresses"], r["output_amounts"]):
            item = ET.SubElement(outputs_node, "output")
            ET.SubElement(item, "address").text = a
            ET.SubElement(item, "amount").text = str(amt)
    ET.ElementTree(root).write(xml_file, encoding="utf-8", xml_declaration=True)

    # --- Write ground truth sidecar (NOT part of the ingested dataset) ---
    gt_file = out_path / "ground_truth.csv"
    with open(gt_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["txid", "injected_pattern", "detail"])
        writer.writerows(ground_truth)

    print(f"[+] Synthetic datasets created in '{output_dir}/': {len(records)} transactions per format "
          f"({len(ground_truth)} labeled anomalies, {len(records) - len(ground_truth)} benign)")
    print(f"[+] Ground truth (for your own evaluation only, never ingested): {gt_file}")


if __name__ == "__main__":
    generate_datasets()
