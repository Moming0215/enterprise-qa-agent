import pytest

from src.output_format import parse_final


def test_parse_plain_and_fenced_json():
    assert parse_final('{"status":"answered"}') == {"status": "answered"}
    assert parse_final('```json\n{"status":"answered"}\n```') == {"status": "answered"}


@pytest.mark.parametrize("content", ["", "not json", "[]", '{"a":1}{"a":2}'])
def test_reject_non_object_or_multiple_outputs(content):
    with pytest.raises(ValueError):
        parse_final(content)
