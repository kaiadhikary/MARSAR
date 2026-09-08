# MARSAR Hardening Notes

This package remains an offline forensic lead-generation prototype. Scores and
heuristic results are investigative evidence, not determinations of criminal
conduct or ownership.

## GeoIP and ASN preparation

Download IP2Location LITE DB1 Country and (optionally) ASN CSV files during a
controlled development step. Do not place them in the deployed runtime image.
Build the local lookup database once:

```text
python tools/build_geoip_database.py --country IP2LOCATION-LITE-DB1.CSV --asn IP2LOCATION-LITE-ASN.CSV --out data/geoip_database.csv
```

The builder splits each country range at every ASN boundary, so it does not
attribute an entire country range to the ASN that happens to cover its first
IP. `OfflineGeoIPResolver` uses a binary search and returns `UNKNOWN` for an
unmatched or invalid IP. It never guesses a country or an ASN.

## Detection language

Common-input ownership is the only automatic ownership-clustering link. Shared
IP and graph similarity are supporting leads; they do not merge wallets because
shared exchange, VPN, or hosting infrastructure is not ownership evidence.

CoinJoin output is described as a `COINJOIN_LIKE_PATTERN`. Equal denominations
and multiple inputs are useful indicators but cannot confirm a mixer service.

## Model lifecycle

`train_elliptic_xgboost.py` currently trains an sklearn
`GradientBoostingClassifier` on synthetic demonstration distributions. Despite
the historical filename, it is not XGBoost and it is not trained on Elliptic.
Do not publish its validation metrics as real-world Bitcoin crime-detection
performance.

The trainer saves a feature-median baseline together with the model. The
inference endpoint reports local counterfactual sensitivity: it replaces one
feature with that baseline and measures the probability change for the specific
transaction. This is per-transaction evidence, not a global feature-importance
claim and not SHAP.

For a future real-data model, create a separate blockchain-only training schema
from labelled sources, keep network telemetry in a separate model or anomaly
engine, freeze a holdout set, version candidate artifacts, and deploy only a
validated local artifact. The production MARSAR runtime should continue to make
no external calls.

## Dashboard integration

The backend now supplies the contracts consumed by the bundled frontend:

- `GET /api/v1/graph/expand/{address}`
- `GET /api/v1/compliance/transactions`
- `GET /api/v1/compliance/flagged`
- `POST /api/v1/export-str`

The login helper now sends the backend's documented `{ "passkey": "..." }`
payload. The HTML export endpoint returns the dossier as a download and exposes
the transaction, risk, verdict, SHA-256 evidence hash, and creation time in
response headers.
