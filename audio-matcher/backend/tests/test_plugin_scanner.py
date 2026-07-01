import json

from app.services.plugin_scanner import audio_module_cid, scan_paths


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


def test_scan_finds_vst2_dlls(tmp_path):
    (tmp_path / "SomeVST2Synth.dll").write_bytes(b"fake dll bytes")
    plugins = scan_paths([str(tmp_path)])
    assert len(plugins) == 1
    p = plugins[0]
    assert p.format == "VST2"
    assert p.name == "SomeVST2Synth"
    assert p.metadata_source == "filename-fallback"
    assert p.bundle_path.endswith("SomeVST2Synth.dll")


def test_scan_finds_both_vst3_and_vst2_in_same_folder(tmp_path):
    _make_fake_bundle(tmp_path, "SomeVST3", with_moduleinfo=False)
    (tmp_path / "SomeVST2.dll").write_bytes(b"fake")
    plugins = scan_paths([str(tmp_path)])
    formats = {p.format for p in plugins}
    assert formats == {"VST3", "VST2"}


def test_vst3_entries_default_to_vst3_format(tmp_path):
    _make_fake_bundle(tmp_path, "SurgeEQ", with_moduleinfo=True)
    plugins = scan_paths([str(tmp_path)])
    assert plugins[0].format == "VST3"


def _make_bundle_with_cid(root, name: str, cid: str, category: str = "Audio Module Class"):
    bundle = root / f"{name}.vst3" / "Contents"
    bundle.mkdir(parents=True)
    (bundle / "moduleinfo.json").write_text(
        json.dumps(
            {
                "Factory Info": {"Vendor": "Test Vendor"},
                "Classes": [{"Name": name, "Category": category, "CID": cid}],
            }
        )
    )


def test_audio_module_cid_extracted_from_moduleinfo(tmp_path):
    cid = "AABBCCDD11223344AABBCCDD11223344"
    _make_bundle_with_cid(tmp_path, "ContainerVST3", cid)
    plugins = scan_paths([str(tmp_path)])
    assert audio_module_cid(plugins[0]) == cid


def test_audio_module_cid_falls_back_to_first_class_if_no_audio_module_category(tmp_path):
    cid = "00112233445566778899AABBCCDDEEFF"
    _make_bundle_with_cid(tmp_path, "OtherPlugin", cid, category="Fx|Dynamics")
    plugins = scan_paths([str(tmp_path)])
    assert audio_module_cid(plugins[0]) == cid
