import json

from app.services.plugin_scanner import scan_paths


def _make_fake_bundle(root, name: str, with_moduleinfo: bool) -> None:
    bundle = root / f"{name}.vst3" / "Contents"
    bundle.mkdir(parents=True)
    if with_moduleinfo:
        (bundle / "moduleinfo.json").write_text(
            json.dumps(
                {
                    "Factory Info": {"Vendor": "Surge Synth Team", "URL": "https://surge-synthesizer.github.io"},
                    "Classes": [{"Name": name, "Category": "Fx|EQ"}],
                }
            )
        )


def test_scan_reads_moduleinfo_metadata(tmp_path):
    _make_fake_bundle(tmp_path, "SurgeEQ", with_moduleinfo=True)
    plugins = scan_paths([str(tmp_path)])
    assert len(plugins) == 1
    p = plugins[0]
    assert p.name == "SurgeEQ"
    assert p.vendor == "Surge Synth Team"
    assert p.classes[0].category == "Fx|EQ"
    assert p.metadata_source == "moduleinfo.json"


def test_scan_falls_back_without_moduleinfo(tmp_path):
    _make_fake_bundle(tmp_path, "MysteryPlugin", with_moduleinfo=False)
    plugins = scan_paths([str(tmp_path)])
    assert len(plugins) == 1
    assert plugins[0].vendor == "Unknown"
    assert plugins[0].metadata_source == "filename-fallback"


def test_scan_ignores_missing_paths():
    assert scan_paths(["/nonexistent/path/xyz"]) == []
