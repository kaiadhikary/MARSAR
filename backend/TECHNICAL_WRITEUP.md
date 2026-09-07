cat << 'EOF' > backend/TECHNICAL_WRITEUP.md
# TECHNICAL WRITE-UP: AI-POWERED BITCOIN TRAFFIC FORENSIC ENGINE

## 1. Approach
The platform correlates Bitcoin network-layer telemetry (src_ip, dst_ip, src_port, dst_port, geo_country, asn) with blockchain ledger records (txid, input/output addresses, BTC amounts, fees, script types) in a purely air-gapped Linux environment. By parsing bulk CSV, JSON, and XML files, the system builds an entity-transaction bipartite multigraph. Entity clustering merges fragmented addresses using multi-input ownership heuristics (CIOH), network broadcast co-location, and truncated SVD graph spectral embeddings.

## 2. Model Choice
* **Unsupervised Anomaly Detection:** An IsolationForest model isolates multi-dimensional outliers across transaction velocity, fee-to-principal ratios, output distribution entropy, and non-standard P2P ports.
* **Supervised Flow Classification:** A pre-trained GradientBoostingClassifier evaluated on 13 network-blockchain features computes the illicit class probability (P_illicit).
* **Laundering Topology Demixers:** Deterministic algorithmic models identify peeling chains (asymmetry ratios >= 4.0) and equal-denomination CoinJoin mixing structures.
* **Taint Propagation:** Multi-hop Haircut and Poison decay diffuses risk scores outward from designated OFAC, ransomware, and darknet market seed addresses.

## 3. Explainability Method
Every generated alert includes a structured JSON evidence ledger detailing:
* Relative feature deviation (z-score) isolating the primary variable triggering the anomaly.
* Decision-tree feature importance attribution weights identifying top contributing behavioral signals.
* Mathematical breakdown of the composite risk score combining seed taint, ML probability, peeling/mixing confidence, and network jurisdiction risk.
EOF