import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest

from app.ingestion.bulk_parser import BulkDataParser, OfflineGeoIPResolver
from app.db.sqlite_client import init_db, get_db_connection


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    test_db_path = tmp_path / "test_marsar.db"
    monkeypatch.setattr("app.db.sqlite_client.DB_PATH", test_db_path)
    init_db()
    yield test_db_path


def test_offline_geoip_resolution():
    resolver = OfflineGeoIPResolver()

    country, asn = resolver.resolve("8.8.8.8")
    assert country == "US"
    assert asn == "UNKNOWN"  # country-only DB-IP lite has no ASN column

    country, asn = resolver.resolve("1.1.1.1")
    assert country == "AU"
    assert asn == "UNKNOWN"

    country, asn = resolver.resolve("198.51.100.15")
    assert country in {"UNKNOWN", "RU"}
    assert isinstance(asn, str)


def test_csv_parsing_and_db_ingest(temp_db):
    parser = BulkDataParser()

    csv_content = (
        "txid,timestamp,src_ip,dst_ip,src_port,dst_port,fee,script_type,geo_country,geo_asn,input_addresses,output_addresses,input_amounts,output_amounts\n"
        "tx_test_csv_1,1700000000,198.51.100.22,104.28.16.5,54122,8333,0.0002,p2wpkh,RU,AS12389,addr_in_1;addr_in_2,addr_out_1,1.0;0.5,1.4998\n"
    )

    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f_path = f.name

    records = parser.parse_csv(f_path)
    Path(f_path).unlink()

    assert len(records) == 1
    assert records[0]["txid"] == "tx_test_csv_1"
    assert records[0]["total_input_btc"] == 1.5
    assert len(records[0]["inputs"]) == 2
    assert len(records[0]["outputs"]) == 1

    count = parser.ingest_to_db(records)
    assert count == 1

    conn = get_db_connection()
    row = conn.execute("SELECT * FROM transactions WHERE txid = ?", ("tx_test_csv_1",)).fetchone()
    conn.close()

    assert row is not None
    assert row["src_ip"] == "198.51.100.22"
    assert row["geo_country"] == "RU"


def test_json_and_xml_parsing():
    parser = BulkDataParser()

    json_data = [{
        "txid": "tx_json_1",
        "timestamp": 1700001000,
        "src_ip": "203.0.113.9",
        "dst_ip": "104.28.16.5",
        "src_port": 40120,
        "dst_port": 8333,
        "fee": 0.0001,
        "script_type": "p2sh",
        "geo_country": "IR",
        "geo_asn": "AS58224",
        "inputs": [{"address": "in_a", "amount": 2.0}],
        "outputs": [{"address": "out_b", "amount": 1.9999}]
    }]

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(json_data, f)
        f_json = f.name

    records_json = parser.parse_json(f_json)
    Path(f_json).unlink()
    assert len(records_json) == 1
    assert records_json[0]["txid"] == "tx_json_1"

    xml_content = """<transactions>
        <transaction>
            <txid>tx_xml_1</txid>
            <timestamp>1700002000</timestamp>
            <src_ip>192.0.2.80</src_ip>
            <dst_ip>104.28.16.5</dst_ip>
            <src_port>35000</src_port>
            <dst_port>8333</dst_port>
            <fee>0.00005</fee>
            <script_type>p2wpkh</script_type>
            <geo_country>NL</geo_country>
            <geo_asn>AS49981</geo_asn>
            <inputs>
                <input><address>xml_in_1</address><amount>0.8</amount></input>
            </inputs>
            <outputs>
                <output><address>xml_out_1</address><amount>0.79995</amount></output>
            </outputs>
        </transaction>
    </transactions>"""

    with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False) as f:
        f.write(xml_content)
        f_xml = f.name

    records_xml = parser.parse_xml(f_xml)
    Path(f_xml).unlink()
    assert len(records_xml) == 1
    assert records_xml[0]["txid"] == "tx_xml_1"
    assert records_xml[0]["total_input_btc"] == 0.8