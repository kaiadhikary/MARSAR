import json
import pytest
from app.db.sqlite_client import init_db, get_db_connection
from app.engine.scoring import RiskPropagationEngine
from app.engine.anomaly_detector import TransactionAnomalyDetector
from app.engine.alert_generator import generate_investigative_alerts


@pytest.fixture
def scored_db(monkeypatch, tmp_path):
    test_db_path = tmp_path / "test_score.db"
    monkeypatch.setattr("app.db.sqlite_client.DB_PATH", test_db_path)
    init_db()

    conn = get_db_connection()
    cur = conn.cursor()

    # Pre-seed illicit OFAC address
    cur.execute('''
    INSERT OR REPLACE INTO illicit_seeds (address, category, severity)
    VALUES ('illicit_seed_1', 'RANSOMWARE', 1.0)
    ''')

    # Seed transaction chain: illicit_seed_1 -> tx_hop_1 -> intermediary_wallet -> tx_hop_2 -> final_wallet
    cur.execute('''
    INSERT INTO transactions (
        txid, timestamp, src_ip, dst_ip, src_port, dst_port,
        fee, script_type, geo_country, geo_asn, inputs_json, outputs_json,
        total_input_btc, total_output_btc
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "tx_hop_1", 1700000000, "198.51.100.1", "104.28.16.5",
        50000, 8333, 0.0005, "p2wpkh", "RU", "AS12389",
        json.dumps([{"address": "illicit_seed_1", "amount": 5.0}]),
        json.dumps([{"address": "intermediary_wallet", "amount": 4.9995}]),
        5.0, 4.9995
    ))

    cur.execute('''
    INSERT INTO transactions (
        txid, timestamp, src_ip, dst_ip, src_port, dst_port,
        fee, script_type, geo_country, geo_asn, inputs_json, outputs_json,
        total_input_btc, total_output_btc
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "tx_hop_2", 1700000500, "198.51.100.1", "104.28.16.5",
        50001, 8333, 0.0005, "p2wpkh", "RU", "AS12389",
        json.dumps([{"address": "intermediary_wallet", "amount": 4.9995}]),
        json.dumps([{"address": "final_wallet", "amount": 4.9990}]),
        4.9995, 4.9990
    ))

    # Add extra benign transactions to allow IsolationForest variance
    for i in range(10):
        cur.execute('''
        INSERT INTO transactions (
            txid, timestamp, src_ip, dst_ip, src_port, dst_port,
            fee, script_type, geo_country, geo_asn, inputs_json, outputs_json,
            total_input_btc, total_output_btc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"tx_benign_{i}", 1700001000 + (i * 60), "192.0.2.10", "104.28.16.5",
            8333, 8333, 0.00005, "p2wpkh", "US", "AS15169",
            json.dumps([{"address": f"addr_benign_in_{i}", "amount": 0.1}]),
            json.dumps([{"address": f"addr_benign_out_{i}", "amount": 0.09995}]),
            0.1, 0.09995
        ))

    conn.commit()
    conn.close()
    yield test_db_path


def test_taint_propagation(scored_db):
    engine = RiskPropagationEngine(decay_factor=0.80)
    taint_scores = engine.propagate_taint()

    assert taint_scores.get("illicit_seed_1") == 1.0
    assert taint_scores.get("tx_hop_1") > 0.70
    assert taint_scores.get("intermediary_wallet") > 0.60
    assert taint_scores.get("tx_hop_2") > 0.40
    assert taint_scores.get("final_wallet") > 0.30
    assert taint_scores.get("addr_benign_in_0", 0.0) == 0.0


def test_anomaly_detection_execution(scored_db):
    detector = TransactionAnomalyDetector()
    results = detector.run_anomaly_detection()

    assert len(results) > 0
    assert "tx_hop_1" in results
    assert "anomaly_score" in results["tx_hop_1"]
    assert "primary_deviance" in results["tx_hop_1"]


def test_end_to_end_alert_generation(scored_db):
    alerts = generate_investigative_alerts()
    assert len(alerts) > 0

    conn = get_db_connection()
    top_alert = conn.execute("SELECT * FROM alerts ORDER BY risk_score DESC LIMIT 1").fetchone()
    conn.close()

    assert top_alert is not None
    assert top_alert["risk_score"] > 0.40
    explanation = json.loads(top_alert["explanation_json"])
    assert "risk_attribution" in explanation