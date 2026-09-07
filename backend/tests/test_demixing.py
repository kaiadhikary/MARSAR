from app.engine.demixing import LaunderingDetector


def test_peeling_chain_detection():
    detector = LaunderingDetector()

    # Typical peeling transaction: 1 input, 2 outputs with 1 small peel and 1 large change
    inputs = [{"address": "peel_source", "amount": 10.0}]
    outputs = [
        {"address": "cashout_exchange", "amount": 0.25},
        {"address": "peel_change_hop_1", "amount": 9.7498}
    ]

    is_peeling, conf, meta = detector.detect_peeling_chain(inputs, outputs)

    assert is_peeling is True
    assert conf >= 0.70
    assert meta["pattern"] == "PEELING_CHAIN"
    assert meta["peeled_amount"] == 0.25
    assert meta["change_amount"] == 9.7498
    assert meta["asymmetry_ratio"] >= 4.0


def test_balanced_transfer_not_peeling():
    detector = LaunderingDetector()

    # Balanced payment (e.g. 50/50 split or small ratio)
    inputs = [{"address": "normal_wallet", "amount": 2.0}]
    outputs = [
        {"address": "dst_1", "amount": 1.1},
        {"address": "dst_2", "amount": 0.899}
    ]

    is_peeling, conf, _ = detector.detect_peeling_chain(inputs, outputs)
    assert is_peeling is False
    assert conf == 0.0


def test_coinjoin_mixer_detection():
    detector = LaunderingDetector()

    # Multi-party CoinJoin transaction with equal denominations
    inputs = [
        {"address": "user_a", "amount": 0.51},
        {"address": "user_b", "amount": 0.505},
        {"address": "user_c", "amount": 0.52},
        {"address": "user_d", "amount": 0.515}
    ]
    outputs = [
        {"address": "clean_a", "amount": 0.5},
        {"address": "clean_b", "amount": 0.5},
        {"address": "clean_c", "amount": 0.5},
        {"address": "clean_d", "amount": 0.5}
    ]

    is_mixer, conf, meta = detector.detect_coinjoin_mixer(inputs, outputs)

    assert is_mixer is True
    assert conf >= 0.80
    assert meta["pattern"] == "COINJOIN_MIXER"
    assert meta["mixing_participants"] == 4
    assert meta["uniform_denominations"].get(0.5) == 4