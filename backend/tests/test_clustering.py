import json
import pytest
from app.db.sqlite_client import init_db, get_db_connection
from app.engine.clustering import EntityClusterEngine, DisjointSetUnion


@pytest.fixture
def clustered_db(monkeypatch, tmp_path):
    test_db_path = tmp_path / "test_cluster.db"
    monkeypatch.setattr("app.db.sqlite_client.DB_PATH", test_db_path)
    init_db()
    yield test_db_path


def test_disjoint_set_union():
    dsu = DisjointSetUnion()
    dsu.union("wallet_A", "wallet_B")
    dsu.union("wallet_B", "wallet_C")
    dsu.union("wallet_X", "wallet_Y")

    assert dsu.find("wallet_A") == dsu.find("wallet_C")
    assert dsu.find("wallet_A") != dsu.find("wallet_X")


def test_cioh_entity_clustering(clustered_db):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
    INSERT INTO transactions (
        txid, timestamp, src_ip, dst_ip, src_port, dst_port,
        fee, script_type, geo_country, geo_asn, inputs_json, outputs_json,
        total_input_btc, total_output_btc
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "tx_multi_input_1", 1700000000, "198.51.100.5", "104.28.16.5",
        51000, 8333, 0.0001, "p2wpkh", "RU", "AS12389",
        json.dumps([{"address": "wallet_1", "amount": 1.0}, {"address": "wallet_2", "amount": 0.5}]),
        json.dumps([{"address": "wallet_out", "amount": 1.4999}]),
        1.5, 1.4999
    ))

    cur.execute('''
    INSERT INTO transactions (
        txid, timestamp, src_ip, dst_ip, src_port, dst_port,
        fee, script_type, geo_country, geo_asn, inputs_json, outputs_json,
        total_input_btc, total_output_btc
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "tx_multi_input_2", 1700000100, "198.51.100.5", "104.28.16.5",
        51001, 8333, 0.0001, "p2wpkh", "RU", "AS12389",
        json.dumps([{"address": "wallet_2", "amount": 0.4}, {"address": "wallet_3", "amount": 0.6}]),
        json.dumps([{"address": "wallet_out_2", "amount": 0.9999}]),
        1.0, 0.9999
    ))
    conn.commit()
    conn.close()

    engine = EntityClusterEngine()
    clusters = engine.run_clustering()

    conn = get_db_connection()
    c1 = conn.execute("SELECT cluster_id FROM entity_clusters WHERE wallet_address = 'wallet_1'").fetchone()[0]
    c2 = conn.execute("SELECT cluster_id FROM entity_clusters WHERE wallet_address = 'wallet_2'").fetchone()[0]
    c3 = conn.execute("SELECT cluster_id FROM entity_clusters WHERE wallet_address = 'wallet_3'").fetchone()[0]
    conn.close()

    assert c1 == c2 == c3