import json

from app.services.container_export import (
    ContainerClassIdUnavailableError,
    build_container_manifest,
    write_container_vstpreset,
)
from app.services.plugin_scanner import scan_paths
from app.services.vstpreset_writer import read_vstpreset

CID = "AABBCCDD11223344AABBCCDD11223344"


def _make_container_bundle(root, cid: str | None = CID):
    bundle = root / "AudioMatcherContainer.vst3" / "Contents"
    bundle.mkdir(parents=True)
    classes = [{"Name": "Audio Matcher Container", "Category": "Audio Module Class"}]
    if cid:
        classes[0]["CID"] = cid
    (bundle / "moduleinfo.json").write_text(
        json.dumps({"Factory Info": {"Vendor": "AudioMatcher"}, "Classes": classes})
    )


def test_write_container_vstpreset_round_trips_manifest(tmp_path):
    _make_container_bundle(tmp_path)
    container_plugin = scan_paths([str(tmp_path)])[0]

    chain = [
        {
            "plugin_type": "real:someeq",
            "plugin_ref": "/fake/SomeEQ.vst3",
            "params": {"0": 0.7},
            "state_chunk_base64": "aGVsbG8gd29ybGQ=",
        },
    ]
    manifest = build_container_manifest(chain)
    assert manifest["ready"]

    out_path = tmp_path / "chain.vstpreset"
    write_container_vstpreset(container_plugin, manifest, out_path)

    result = read_vstpreset(out_path)
    assert result["class_id_hex"] == CID
    recovered = json.loads(result["chunks"]["Comp"].rstrip(b"\x00").decode("utf-8"))
    assert recovered == manifest


def test_write_container_vstpreset_raises_without_cid(tmp_path):
    _make_container_bundle(tmp_path, cid=None)
    container_plugin = scan_paths([str(tmp_path)])[0]
    manifest = {"chain": [{"bundle_path": "/x", "state_chunk_base64": "eA=="}], "ready": True}

    try:
        write_container_vstpreset(container_plugin, manifest, tmp_path / "out.vstpreset")
        assert False, "expected ContainerClassIdUnavailableError"
    except ContainerClassIdUnavailableError:
        pass
