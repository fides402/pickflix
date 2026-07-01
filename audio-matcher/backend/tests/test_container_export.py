from app.services.container_export import build_container_manifest


def test_manifest_marks_simulated_only_chain_unresolved():
    chain = [
        {"plugin_type": "eq3", "params": {"band1_gain_db": 2.0}},
        {"plugin_type": "compressor", "params": {"ratio": 3.0}},
    ]
    manifest = build_container_manifest(chain)
    assert manifest["ready"] is False
    assert manifest["unresolved_simulated_stages"] == ["eq3", "compressor"]
    assert manifest["chain"] == []


def test_manifest_falls_back_to_named_params_without_state_chunk():
    chain = [
        {"plugin_type": "eq3", "plugin_ref": "/plugins/SomeEQ.vst3", "params": {"Gain": 0.7}},
    ]
    manifest = build_container_manifest(chain)
    assert manifest["ready"] is True
    assert manifest["chain"] == [{"bundle_path": "/plugins/SomeEQ.vst3", "parameters": {"Gain": 0.7}}]


def test_manifest_prefers_raw_state_chunk_over_named_params():
    chain = [
        {
            "plugin_type": "real:someeq",
            "plugin_ref": "/plugins/SomeEQ.vst3",
            "params": {"0": 0.7},
            "state_chunk_base64": "QUJD",
        },
    ]
    manifest = build_container_manifest(chain)
    assert manifest["ready"] is True
    assert manifest["chain"] == [{"bundle_path": "/plugins/SomeEQ.vst3", "state_chunk_base64": "QUJD"}]
