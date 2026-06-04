"""Tests for DNS card plain-English display."""
from webaudit.render.dns_display import build_dns_card, build_dns_cards

def test_spf_card_includes_description_and_summary():
    """Ensures Spf Card Includes Description And Summary."""
    card = build_dns_card('spf', 'v=spf1 include:_spf.mx.cloudflare.net ~all')
    assert card['label'] == 'SPF'
    assert 'spoofing' in card['description'].lower()
    assert card['summary_tone'] == 'good'
    assert 'Published' in card['summary']

def test_dmarc_none_is_warn():
    """Ensures Dmarc None Is Warn."""
    card = build_dns_card('dmarc', 'v=DMARC1; p=none;')
    assert card['summary_tone'] == 'warn'
    assert 'p=none' in card['summary']

def test_aaaa_formats_list():
    """Ensures Aaaa Formats List."""
    card = build_dns_card('aaaa', ['2606:4700::1', '2606:4700::2'])
    assert '2606:4700::1' in card['value']
    assert 'IPv6' in card['summary']

def test_build_dns_cards_skips_missing_keys():
    """Ensures Build DNS Cards Skips Missing Keys."""
    cards = build_dns_cards({'spf': 'v=spf1 -all', 'dmarc': None})
    assert [c['key'] for c in cards] == ['spf', 'dmarc']
