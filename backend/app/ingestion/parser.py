"""
Raw UTXO payload decoder.

mempool.space's WebSocket already hands us JSON (not raw hex), so "decoding"
here means normalizing their transaction schema into BTIF's internal
structured format: a flat dict with TXID, input UTXO pointers, output
addresses/amounts, fee rate, and locktime, ready for the clustering and
scoring engines downstream.

If you swap the ingestion source to a raw P2P node feed later, this is the
module that would grow real hex/script deserialization.
"""
from __future__ import annotations

from typing import Any


class ParsedInput:
    __slots__ = ("prev_txid", "prev_vout", "address", "value_sats")

    def __init__(self, prev_txid: str | None, prev_vout: int | None,
                 address: str | None, value_sats: int | None):
        self.prev_txid = prev_txid
        self.prev_vout = prev_vout
        self.address = address
        self.value_sats = value_sats

    def to_dict(self) -> dict:
        return {
            "prev_txid": self.prev_txid,
            "prev_vout": self.prev_vout,
            "address": self.address,
            "value_sats": self.value_sats,
        }


class ParsedOutput:
    __slots__ = ("address", "value_sats", "script_type", "vout_index")

    def __init__(self, address: str | None, value_sats: int,
                 script_type: str | None, vout_index: int):
        self.address = address
        self.value_sats = value_sats
        self.script_type = script_type
        self.vout_index = vout_index

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "value_sats": self.value_sats,
            "script_type": self.script_type,
            "vout_index": self.vout_index,
        }


def parse_raw_tx(raw_tx: dict[str, Any]) -> dict:
    """
    Normalize a single mempool.space transaction object into BTIF's internal
    structured transaction dict.

    Expected (esplora-style) shape of `raw_tx`, as returned by mempool.space:
        {
          "txid": "...",
          "vin": [{"txid": "...", "vout": 0, "prevout": {"scriptpubkey_address": "...", "value": 12345}}, ...],
          "vout": [{"scriptpubkey_address": "...", "value": 12345, "scriptpubkey_type": "v0_p2wpkh"}, ...],
          "fee": 1500,
          "weight": 560,
          "locktime": 0
        }

    Returns a flat dict consumed by the clustering, demixing, and scoring
    engines. Unknown/missing fields degrade to None rather than raising, so a
    single malformed tx never takes down the ingestion queue.
    """
    txid = raw_tx.get("txid")

    inputs: list[dict] = []
    total_input_sats = 0
    for vin in raw_tx.get("vin", []):
        prevout = vin.get("prevout") or {}
        value = prevout.get("value")
        parsed_input = ParsedInput(
            prev_txid=vin.get("txid"),
            prev_vout=vin.get("vout"),
            address=prevout.get("scriptpubkey_address"),
            value_sats=value,
        )
        inputs.append(parsed_input.to_dict())
        if isinstance(value, int):
            total_input_sats += value

    outputs: list[dict] = []
    total_output_sats = 0
    for idx, vout in enumerate(raw_tx.get("vout", [])):
        value = vout.get("value", 0)
        parsed_output = ParsedOutput(
            address=vout.get("scriptpubkey_address"),
            value_sats=value,
            script_type=vout.get("scriptpubkey_type"),
            vout_index=idx,
        )
        outputs.append(parsed_output.to_dict())
        total_output_sats += value or 0

    fee_sats = raw_tx.get("fee")
    weight = raw_tx.get("weight")
    fee_rate_sat_vb = None
    if fee_sats is not None and weight:
        # weight is in weight units (vB * 4); vsize = weight / 4
        vsize = weight / 4
        if vsize > 0:
            fee_rate_sat_vb = round(fee_sats / vsize, 2)

    return {
        "txid": txid,
        "inputs": inputs,
        "outputs": outputs,
        "num_inputs": len(inputs),
        "num_outputs": len(outputs),
        "total_input_sats": total_input_sats or None,
        "total_output_sats": total_output_sats or None,
        "fee_sats": fee_sats,
        "fee_rate_sat_vb": fee_rate_sat_vb,
        "locktime": raw_tx.get("locktime"),
        "confirmed": bool(raw_tx.get("status", {}).get("confirmed", False)),
    }


def parse_batch(raw_txs: list[dict[str, Any]]) -> list[dict]:
    """Parse a list of raw tx payloads, skipping any that fail to parse."""
    parsed = []
    for raw_tx in raw_txs:
        try:
            parsed.append(parse_raw_tx(raw_tx))
        except Exception:
            # Never let one malformed transaction stall the ingestion pipeline.
            continue
    return parsed
