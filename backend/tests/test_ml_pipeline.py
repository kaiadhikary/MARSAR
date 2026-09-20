import numpy as np
from app.ml.feature_extractor import FeatureExtractor
from app.ml.inference import MLInferenceEngine
from app.reports.hashing import ForensicHasher


def test_feature_extraction_vector():
    extractor = FeatureExtractor()

    sample_tx = {
        "inputs": [{"address": "in_1", "amount": 5.0}],
        "outputs": [{"address": "out_1", "amount": 0.2}, {"address": "out_2", "amount": 4.799}],
        "total_input_btc": 5.0,
        "total_output_btc": 4.999,
        "fee": 0.001,
        "dst_port": 8333,
        "geo_asn": "AS12389 - Rostelecom",
        "geo_country": "RU",
        "script_type": "p2wpkh",
        "timestamp": 1700000000
    }

    vec, names = extractor.extract_from_record(sample_tx)

    assert isinstance(vec, np.ndarray)
    assert len(vec) == 13
    assert len(names) == 13
    assert vec[names.index("is_high_risk_country")] == 1.0
    assert vec[names.index("is_high_risk_asn")] == 1.0


def test_inference_and_explainability():
    engine = MLInferenceEngine()

    suspicious_tx = {
        "inputs": [{"address": "seed_in", "amount": 10.0}],
        "outputs": [{"address": "peel_out", "amount": 0.1}, {"address": "change_out", "amount": 9.89}],
        "total_input_btc": 10.0,
        "total_output_btc": 9.99,
        "fee": 0.01,
        "dst_port": 54321,  # Non-standard port
        "geo_asn": "AS12389",
        "geo_country": "RU",
        "script_type": "p2sh",
        "timestamp": 1700000000
    }

    prediction = engine.predict(suspicious_tx)

    assert "is_illicit" in prediction
    assert "illicit_probability" in prediction
    assert "confidence" in prediction
    assert len(prediction["top_contributing_features"]) > 0


def test_forensic_integrity_hashing():
    payload = {"txid": "tx_abc_123", "risk_score": 0.942, "status": "CONFIRMED"}
    digest = ForensicHasher.hash_payload(payload)

    assert isinstance(digest, str)
    assert len(digest) == 64  # SHA-256 hex string length
    assert ForensicHasher.verify_integrity(payload, digest) is True

    # Tampering check
    tampered_payload = {"txid": "tx_abc_123", "risk_score": 0.200, "status": "CONFIRMED"}
    assert ForensicHasher.verify_integrity(tampered_payload, digest) is False