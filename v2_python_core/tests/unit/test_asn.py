"""Tests for ASN lookup via Team Cymru DNS."""
from unittest.mock import MagicMock
from webaudit.collectors.asn import lookup_asn

def _txt_answer(text: str) -> MagicMock:
    answer = MagicMock()
    answer.strings = [text.encode()]
    return answer

def test_lookup_asn_parses_cymru_response():
    """Ensures Lookup ASN Parses Cymru Response."""
    resolver = MagicMock()
    resolver.resolve.return_value = [_txt_answer('"15169 | 8.8.8.8 | 24 | US | arin | 2000-03-30"')]
    record = lookup_asn('8.8.8.8', resolver)
    assert record is not None
    assert record.asn == '15169'
    assert record.country == 'US'
    assert '8.8.8.8' in resolver.resolve.call_args[0][0]
