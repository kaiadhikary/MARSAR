from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader
from app.reports.evidence import EvidenceCollector
from app.reports.hashing import ForensicHasher


class ReportGenerator:
    """
    Renders standalone Suspicious Transaction Reports (STR) into HTML and Markdown.
    Runs entirely offline without external CDN stylesheets or remote assets[cite: 2].
    """

    def __init__(self):
        self.collector = EvidenceCollector()
        self.base_dir = Path(__file__).parent
        self.templates_dir = self.base_dir / "templates"
        self.output_dir = self.base_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True
        )

    def generate_html_str(self, txid: str) -> Optional[Dict[str, str]]:
        """
        Builds and saves an HTML investigative dossier for the specified TXID.
        Returns the file path and cryptographic integrity hash.
        """
        dossier = self.collector.collect_tx_dossier(txid)
        if not dossier:
            return None

        template = self.jinja_env.get_template("str_template.html")
        rendered_html = template.render(dossier=dossier)

        report_hash = ForensicHasher.hash_payload(rendered_html)
        filename = f"MARSAR-STR-{txid[:16]}.html"
        report_path = self.output_dir / filename

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)

        return {
            "report_path": str(report_path),
            "filename": filename,
            "chain_of_custody_hash": report_hash,
            "dossier_id": dossier["metadata"]["dossier_id"]
        }

    def generate_markdown_summary(self, txid: str) -> Optional[str]:
        """Generates a scannable Markdown summary for terminal and CLI review."""
        dossier = self.collector.collect_tx_dossier(txid)
        if not dossier:
            return None

        scoring = dossier["forensic_scoring"]
        net = dossier["network_layer"]
        bc = dossier["blockchain_layer"]

        md = f"""# FORENSIC INVESTIGATION REPORT (STR)
**Dossier ID:** `{dossier['metadata']['dossier_id']}`
**Target TXID:** `{bc['txid']}`
**Integrity Digest (SHA-256):** `{dossier['chain_of_custody_hash']}`

---

## 1. Risk Assessment & Classification
* **Composite Risk Score:** {scoring['composite_risk_score']:.4f}
* **Confidence Level:** {scoring['model_confidence']:.4f}
* **Primary Focus Area:** {scoring['primary_focus_area']}
* **Peeling Chain Detected:** {scoring['peeling_chain_flag']}
* **Mixer/CoinJoin Detected:** {scoring['mixer_coinjoin_flag']}
* **Seed Taint Exposure:** {scoring['taint_score']:.4f}
* **Unsupervised Anomaly Score:** {scoring['anomaly_score']:.4f}

## 2. Network-Layer Telemetry
* **Broadcast IP:** `{net['src_ip']}` -> `{net['dst_ip']}`
* **Ports:** `{net['src_port']}` -> `{net['dst_port']}`
* **Geo Location / Jurisdiction:** `{net['geo_country']}`
* **Autonomous System (ASN):** `{net['geo_asn']}`

## 3. Blockchain Flow Metrics
* **Total Transacted Volume:** {bc['total_input_btc']:.4f} BTC
* **Miner Fee:** {bc['fee_btc']:.6f} BTC
* **Input Count:** {len(bc['inputs'])}
* **Output Count:** {len(bc['outputs'])}
* **Script Type:** `{bc['script_type']}`
"""
        return md