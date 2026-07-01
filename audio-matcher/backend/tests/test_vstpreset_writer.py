from app.services.vstpreset_writer import read_vstpreset, write_vstpreset


def test_round_trip_component_state_only(tmp_path):
    out = tmp_path / "test.vstpreset"
    class_id = "AABBCCDD11223344AABBCCDD11223344"
    write_vstpreset(out, class_id, component_state=b'{"chain": []}')

    result = read_vstpreset(out)
    assert result["version"] == 1
    assert result["class_id_hex"] == class_id
    assert result["chunks"]["Comp"] == b'{"chain": []}'
    assert "Cont" not in result["chunks"]


def test_round_trip_with_controller_state(tmp_path):
    out = tmp_path / "test.vstpreset"
    write_vstpreset(out, "00" * 16, component_state=b"COMPDATA", controller_state=b"CONTDATA")

    result = read_vstpreset(out)
    assert result["chunks"]["Comp"] == b"COMPDATA"
    assert result["chunks"]["Cont"] == b"CONTDATA"


def test_rejects_malformed_class_id_hex(tmp_path):
    out = tmp_path / "test.vstpreset"
    try:
        write_vstpreset(out, "not-valid-hex", component_state=b"x")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_header_is_48_bytes(tmp_path):
    out = tmp_path / "test.vstpreset"
    write_vstpreset(out, "AA" * 16, component_state=b"X")
    data = out.read_bytes()
    assert data[0:4] == b"VST3"
    # class id (32 ascii hex chars) must start right at byte 8
    assert data[8:40] == b"AA" * 16
