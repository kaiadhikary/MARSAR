"""
MARSAR Unified Worker: Engine 1 (Ingestion) -> Engine 2 (Clustering) ->
Engine 3 (Demixing) -> Engine 4 (Typology) -> Engine 5 (Risk Scoring) ->
SQLite Persistence.

Streams live Bitcoin mempool transactions, applies CIOH clustering,
analyzes mixing patterns, scans for peeling-chain / scatter-gather /
velocity typologies, checks against OFAC/CryptoScamDB blacklist seeds,
computes a 4-layer weighted risk score (Engine 5), and persists forensic
graph + scoring state to SQLite.

Fixes applied vs. the previous version of this file (see handover notes):
  - `is_probable_coinjoin` is now imported from `app.engine.clustering`
    (where it actually lives). The old `from app.engine.demixing import
    is_probable_coinjoin` always raised ImportError and silently fell back
    to a much weaker "any duplicate output value, 3+ outputs" heuristic for
    every single transaction processed.
  - Cluster persistence now uses the return value of
    `clustering.process_tx()` (the resolved cluster root, or None when
    Engine 2's CoinJoin pre-filter skipped the union) instead of
    independently re-deriving a root address for *any* tx with >1 input.
    The old code persisted a cluster_merge for probable CoinJoins too,
    writing unrelated participants into `address_clusters` as if they were
    one entity — exactly what the pre-filter in clustering.py exists to
    prevent. That poisoning happened silently at the DB layer even though
    the DSU in memory was correct.
  - `solve_demix()` returns a `list[DemixLink]`, not a dict — the old
    `isinstance(demix_res, dict) and demix_res.get("solved")` check was
    always False and that whole telemetry branch was dead code. Now reads
    confirmed links directly off the list.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from app.ingestion.mempool_ws import consume_mempool
from app.engine.clustering import ClusteringEngine, is_probable_coinjoin
from app.engine.demixing import solve_demix, shannon_entropy
from app.engine.heuristics import TypologyEngine
from app.engine.scoring import compute_risk_score
from app.ml.feature_extractor import extract_features
from app.ml.inference import inference_engine
from app.db.sqlite_client import (
    init_db,
    load_seed_data,
    check_address_blacklist,
    persist_cluster_merge,
    persist_transaction,
    update_cluster_risk_score,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("marsar.worker")


def extract_input_addresses(tx: dict) -> list[str]:
    """Extracts public addresses from input UTXOs."""
    addrs = []
    raw_inputs = tx.get("inputs", tx.get("vin", []))
    for inp in raw_inputs:
        if isinstance(inp, dict):
            addr = inp.get("address") or inp.get("scriptpubkey_address")
            if not addr and isinstance(inp.get("prevout"), dict):
                addr = inp["prevout"].get("scriptpubkey_address")
            if addr:
                addrs.append(addr)
        elif isinstance(inp, str):
            addrs.append(inp)
    return addrs


def extract_output_addresses(tx: dict) -> list[str]:
    """Extracts public addresses from output UTXOs."""
    addrs = []
    raw_outputs = tx.get("outputs", tx.get("vout", []))
    for out in raw_outputs:
        if isinstance(out, dict):
            addr = out.get("address") or out.get("scriptpubkey_address")
            if addr:
                addrs.append(addr)
        elif isinstance(out, str):
            addrs.append(out)
    return addrs


def extract_address_values(tx: dict) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """Extract (address, satoshi value) pairs for graph/trace persistence."""
    inputs: list[tuple[str, int]] = []
    for inp in tx.get("inputs", tx.get("vin", [])):
        if not isinstance(inp, dict):
            continue
        addr = inp.get("address") or inp.get("scriptpubkey_address")
        if not addr and isinstance(inp.get("prevout"), dict):
            addr = inp["prevout"].get("scriptpubkey_address")
        value = inp.get("value_sats") or inp.get("value")
        if value is None and isinstance(inp.get("prevout"), dict):
            value = inp["prevout"].get("value", 0)
        try:
            value = int(value or 0)
        except (ValueError, TypeError):
            value = 0
        if addr:
            inputs.append((addr, value))

    outputs: list[tuple[str, int]] = []
    for out in tx.get("outputs", tx.get("vout", [])):
        if not isinstance(out, dict):
            continue
        addr = out.get("address") or out.get("scriptpubkey_address")
        try:
            value = int(out.get("value_sats") or out.get("value") or 0)
        except (ValueError, TypeError):
            value = 0
        if addr:
            outputs.append((addr, value))

    return inputs, outputs


def extract_sat_values(tx: dict) -> tuple[list[int], list[int], int]:
    """Extracts integer satoshi amounts and transaction fee for Engine 3."""
    input_values: list[int] = []
    raw_inputs = tx.get("inputs", tx.get("vin", []))
    for inp in raw_inputs:
        if isinstance(inp, dict):
            val = inp.get("value_sats") or inp.get("value")
            if val is None and isinstance(inp.get("prevout"), dict):
                val = inp["prevout"].get("value")
            if val is not None:
                try:
                    input_values.append(int(val))
                except (ValueError, TypeError):
                    pass

    output_values: list[int] = []
    raw_outputs = tx.get("outputs", tx.get("vout", []))
    for out in raw_outputs:
        if isinstance(out, dict):
            val = out.get("value_sats") or out.get("value")
            if val is not None:
                try:
                    output_values.append(int(val))
                except (ValueError, TypeError):
                    pass

    fee_val = tx.get("fee_sats") or tx.get("fee") or 0
    try:
        fee_sats = int(fee_val)
    except (ValueError, TypeError):
        fee_sats = 0

    return input_values, output_values, fee_sats


async def process_pipeline(
    queue: asyncio.Queue,
    clustering: ClusteringEngine,
    typology: TypologyEngine,
) -> None:
    """Feeds normalized transactions through Engines 1-4 and persists to SQLite."""
    while True:
        tx = await queue.get()
        try:
            txid = tx.get("txid", "unknown")
            num_inputs = tx.get("num_inputs", len(tx.get("inputs", tx.get("vin", []))))
            num_outputs = tx.get("num_outputs", len(tx.get("outputs", tx.get("vout", []))))
            fee_rate = tx.get("fee_rate_sat_vb", tx.get("fee_rate", 0.0)) or 0.0

            input_addrs = extract_input_addresses(tx)
            output_addrs = extract_output_addresses(tx)
            all_addrs = set(input_addrs + output_addrs)

            # -------------------------------------------------------------
            # STEP 1: OFAC / Threat Intelligence Blacklist Lookup
            # -------------------------------------------------------------
            blacklist_hit_count = 0
            for addr in all_addrs:
                hit = check_address_blacklist(addr)
                if hit:
                    blacklist_hit_count += 1
                    logger.critical(
                        "🚨 [AML ALERT - THREAT HIT] TX: %s... | Address: %s | Entity: %s | Category: %s | Source: %s",
                        txid[:12],
                        addr[:16],
                        hit.get("entity_label"),
                        hit.get("category"),
                        hit.get("source"),
                    )

            # -------------------------------------------------------------
            # STEP 2: ENGINE 2 - Heuristic Entity Clustering (CIOH)
            # -------------------------------------------------------------
            # process_tx() returns the resolved cluster root, or None when
            # its own CoinJoin pre-filter decided NOT to union these
            # inputs. Only persist a cluster merge when it actually
            # happened — persisting one unconditionally (the previous bug)
            # meant CoinJoin participants got written to address_clusters
            # as one entity even though the in-memory DSU correctly kept
            # them separate.
            cluster_root = clustering.process_tx(tx)
            total_tracked = len(clustering.stats.addresses_seen)

            if cluster_root is not None and len(input_addrs) > 1:
                persist_cluster_merge(str(cluster_root), input_addrs)

            # -------------------------------------------------------------
            # STEP 3: ENGINE 3 - Mixer Detection & Subset-Sum Demixing
            # -------------------------------------------------------------
            input_values, output_values, fee_sats = extract_sat_values(tx)
            entropy = shannon_entropy(output_values) if output_values else 0.0

            # is_probable_coinjoin lives in app.engine.clustering (the
            # previous version imported it from app.engine.demixing, which
            # doesn't define it — that import always failed and silently
            # fell back to a weaker duplicate-value heuristic below).
            try:
                is_mix = is_probable_coinjoin(tx)
            except Exception:
                is_mix = False
            if not is_mix and len(output_values) >= 3:
                is_mix = len(set(output_values)) < len(output_values)

            # Knapsack Subset-Sum Solver on multi-party transactions.
            # solve_demix() returns list[DemixLink], not a dict — the
            # previous version's `demix_res.get("solved")` check on this
            # list was always False (AttributeError-free only because it
            # was gated by an `isinstance(..., dict)` that never passed),
            # so no demix telemetry was ever actually logged.
            demix_links = []
            if 1 < len(input_values) <= 12 and 1 < len(output_values) <= 12 and sum(input_values) > 0:
                try:
                    demix_links = solve_demix(input_values, output_values, fee_sats)
                except Exception as demix_err:
                    logger.debug("Subset-sum solver skipped TX %s: %s", txid[:8], demix_err)
            confirmed_links = [l for l in demix_links if l.confidence == "confirmed"]

            # -------------------------------------------------------------
            # STEP 4: ENGINE 4 - Typology & Graph Structural Detection
            # -------------------------------------------------------------
            typology_findings = typology.process_tx(tx)
            for finding in typology_findings:
                if finding["type"] == "peeling_chain":
                    logger.warning(
                        "🔻 [PEELING CHAIN] %d hops, %s sats peeled | Chain: %s",
                        finding["hops"], finding["total_peeled_sats"],
                        " -> ".join(a[:10] + "…" for a in finding["chain"]),
                    )
                elif finding["type"] == "scatter_gather":
                    logger.warning(
                        "🕸️ [SCATTER-GATHER] Source %s... fanned out to %d addresses, "
                        "gathered at %s... within %.0fs",
                        finding["source_address"][:12], finding["fanout_count"],
                        (finding["gather_address"] or "?")[:12], finding["window_seconds"],
                    )
                elif finding["type"] == "rapid_velocity":
                    logger.warning(
                        "⚡ [RAPID VELOCITY] %s... spent %d consecutive hops in <%.0fs avg (avg %.1fs)",
                        finding["address"][:12], finding["consecutive_rapid_hops"],
                        typology.velocity_threshold_seconds, finding["avg_delta_seconds"],
                    )

            # -------------------------------------------------------------
            # STEP 5: ENGINE 5 - AI/ML Inference & 4-Layer Risk Scoring
            # -------------------------------------------------------------
            features = extract_features(
                tx,
                input_values=input_values,
                output_values=output_values,
                fee_rate=fee_rate,
                entropy=entropy,
                is_coinjoin=is_mix,
                cluster_member_count=len(input_addrs) if cluster_root is not None else 0,
                blacklist_hit_count=blacklist_hit_count,
                typology_finding_count=len(typology_findings),
            )
            ml_probability = inference_engine.predict_proba(features)
            risk = compute_risk_score(
                blacklist_hit=blacklist_hit_count > 0,
                typology_findings=typology_findings,
                ml_probability=ml_probability,
                is_coinjoin=is_mix,
                mixer_entropy=entropy,
            )

            cluster_id = f"entity_{str(cluster_root)[:16]}" if cluster_root is not None else None
            if cluster_id is not None:
                update_cluster_risk_score(cluster_id, risk.total)

            # -------------------------------------------------------------
            # STEP 6: Transaction Persistence
            # -------------------------------------------------------------
            tx_input_addrs, tx_output_addrs = extract_address_values(tx)
            persist_transaction(
                txid=txid,
                inputs_count=num_inputs,
                outputs_count=num_outputs,
                fee_rate=fee_rate,
                is_coinjoin=is_mix,
                entropy=entropy,
                cluster_id=cluster_id,
                risk_score=risk.total,
                blacklist_hit=blacklist_hit_count > 0,
                typology_flags=",".join(risk.flags),
                ml_probability=ml_probability,
                taint_score=risk.taint_score,
                typology_score=risk.typology_score,
                mixer_penalty_score=risk.mixer_penalty_score,
                risk_verdict=risk.verdict,
                input_addresses=tx_input_addrs,
                output_addresses=tx_output_addrs,
            )

            # -------------------------------------------------------------
            # STEP 7: Telemetry Logging
            # -------------------------------------------------------------
            if risk.verdict == "HIGH_RISK":
                logger.critical(
                    "🔴 [HIGH RISK] TX: %s... | Score: %.1f/100 | Flags: %s",
                    txid[:12], risk.total, ", ".join(risk.flags) or "none",
                )
            elif risk.verdict == "SUSPICIOUS":
                logger.warning(
                    "🟠 [SUSPICIOUS] TX: %s... | Score: %.1f/100 | Flags: %s",
                    txid[:12], risk.total, ", ".join(risk.flags) or "none",
                )
            elif is_mix and entropy < 1.5:
                logger.warning(
                    "🚨 [COINJOIN / MIXER DETECTED] TX: %s... | In: %d | Out: %d | Shannon Entropy: %.2f bits",
                    txid[:12], len(input_values), len(output_values), entropy
                )
            elif confirmed_links:
                logger.info(
                    "🔗 [DEMIX SOLVED] TX: %s... | Resolved %d input-output link(s) via Subset-Sum",
                    txid[:12], len(confirmed_links)
                )
            elif cluster_root is not None:
                logger.info(
                    "👥 [CIOH CLUSTER MERGE] TX: %s... | Merged %d inputs -> Root: %s... | Tracked Addrs: %d",
                    txid[:12], len(input_addrs), str(cluster_root)[:14], total_tracked
                )
            else:
                logger.info(
                    "⚡ [INGESTED & PERSISTED] TX: %s... | In: %d | Out: %d | Fee: %.2f sat/vB | Tracked Addrs: %d",
                    txid[:12], num_inputs, num_outputs, fee_rate, total_tracked
                )

        except Exception as exc:
            logger.warning("Pipeline skipped TX %s: %s", tx.get("txid", "unknown")[:8], exc)
        finally:
            queue.task_done()


async def main():
    logger.info("Initializing SQLite storage and threat intelligence index...")
    init_db()
    load_seed_data()

    queue = asyncio.Queue(maxsize=2000)
    clustering = ClusteringEngine()
    typology = TypologyEngine()

    logger.info(
        "Starting MARSAR Pipeline: Ingestion (E1) -> Clustering (E2) -> "
        "Demixing (E3) -> Typology (E4) -> Risk Scoring (E5) -> SQLite..."
    )
    await asyncio.gather(
        consume_mempool(queue),
        process_pipeline(queue, clustering, typology),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by operator.")
