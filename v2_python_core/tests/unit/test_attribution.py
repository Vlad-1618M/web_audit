"""Tests for designer/creator attribution extraction."""
from webaudit.collectors.attribution import extract_attribution

def test_extracts_html_comment_credit():
    """Ensures Extracts HTML Comment Credit."""
    html = '<!-- Designed by Jane Developer --><html><body></body></html>'
    info = extract_attribution(html, base_url='https://example.com')
    assert info.name == 'Jane Developer'
    assert info.source == 'html_comment'

def test_extracts_meta_author():
    """Ensures Extracts Meta Author."""
    html = '<html><head><meta name="author" content="Acme Studio"></head><body></body></html>'
    info = extract_attribution(html, base_url='https://example.com')
    assert info.name == 'Acme Studio'
    assert info.source == 'meta_tag'

def test_extracts_visible_designed_by_with_link():
    """Ensures Extracts Visible Designed By With Link."""
    html = '\n    <html><body><footer><a href="https://designer.example/portfolio">Designed by Pat Lee</a></footer></body></html>\n    '
    info = extract_attribution(html, base_url='https://example.com')
    assert info.name == 'Pat Lee'
    assert info.link_url == 'https://designer.example/portfolio'
    assert info.source == 'footer_link'

def test_ignores_powered_by_claude_in_nav_title():
    """Ensures Ignores Powered By Claude In Nav Title."""
    html = '\n    <html><body>\n      <nav class="sidebar-nav">\n        <a href="/agent/" title="Muzar guide · powered by Claude">Agent</a>\n      </nav>\n      <section class="skills">\n        <a href="https://docs.anthropic.com/">Claude (Anthropic)</a>\n      </section>\n    </body></html>\n    '
    info = extract_attribution(html, base_url='https://muzar.io')
    assert not info.name

def test_ignores_powered_by_claude_in_footer_with_api_docs_link():
    """Ensures Ignores Powered By Claude In Footer With API Docs Link."""
    html = '\n    <html><body>\n      <footer class="main-footer">\n        <span>Powered by Claude</span>\n        <a href="https://docs.anthropic.com/">Claude</a>\n      </footer>\n    </body></html>\n    '
    info = extract_attribution(html, base_url='https://example.com')
    assert not info.name

def test_accepts_ai_designer_in_footer():
    """Ensures Accepts Ai Designer In Footer."""
    html = '\n    <html><body>\n      <footer class="site-footer">\n        <p>Designed by Midjourney Studio</p>\n      </footer>\n    </body></html>\n    '
    info = extract_attribution(html, base_url='https://example.com')
    assert info.name == 'Midjourney Studio'
    assert info.source == 'visible_text'

def test_accepts_designed_by_claude_in_html_comment():
    """Ensures Accepts Designed By Claude In HTML Comment."""
    html = '<!-- Designed by Claude for Acme Corp --><html><body></body></html>'
    info = extract_attribution(html, base_url='https://example.com')
    assert info.name == 'Claude for Acme Corp'

def test_powered_by_not_matched_in_body_outside_footer():
    """Ensures Powered By Not Matched In Body Outside Footer."""
    html = '\n    <html><body>\n      <main><p>Powered by OpenAI GPT</p></main>\n      <a href="https://platform.openai.com/docs/">OpenAI GPT</a>\n    </body></html>\n    '
    info = extract_attribution(html, base_url='https://example.com')
    assert not info.name
