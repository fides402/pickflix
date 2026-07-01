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


def test_manifest_builds_real_chain_when_plugin_ref_present():
    chain = [
        {"plugin_type": "eq3", "plugin_ref": "/plugins/SomeEQ.vst3", "params": {"Gain": 0.7}},
    ]
    manifest = build_container_manifest(chain)
    assert manifest["ready"] is True
    assert manifest["chain"] == [{"bundle_path": "/plugins/SomeEQ.vst3", "parameters": {"Gain": 0.7}}]
