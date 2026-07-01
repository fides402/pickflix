from app.services import plugin_defs


def test_register_real_plugin_bounds_are_unit_normalized():
    plugin_defs.register_real_plugin("real:test-eq", "/path/To/TestEQ.vst3", ["Gain", "Freq", "Q"])
    try:
        assert plugin_defs.is_real_plugin("real:test-eq")
        assert plugin_defs.bounds("real:test-eq") == [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0)]
        assert plugin_defs.param_names("real:test-eq") == ["0", "1", "2"]
        assert plugin_defs.default_params("real:test-eq") == {"0": 0.5, "1": 0.5, "2": 0.5}
        assert plugin_defs.real_plugin_bundle_path("real:test-eq") == "/path/To/TestEQ.vst3"
        assert plugin_defs.real_plugin_display_names("real:test-eq") == ["Gain", "Freq", "Q"]
    finally:
        del plugin_defs._REAL_PLUGIN_REGISTRY["real:test-eq"]


def test_simulated_types_unaffected_by_real_registry():
    assert not plugin_defs.is_real_plugin("eq3")
    assert plugin_defs.bounds("eq3")[1] == (-12, 12)  # band1_gain_db, unchanged
