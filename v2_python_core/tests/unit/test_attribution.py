"""Tests for designer/creator attribution extraction."""

from webaudit.collectors.attribution import extract_attribution


def test_extracts_html_comment_credit():
    html = "<!-- Designed by Jane Developer --><html><body></body></html>"
    info = extract_attribution(html, base_url="https://example.com")
    assert info.name == "Jane Developer"
    assert info.source == "html_comment"


def test_extracts_meta_author():
    html = '<html><head><meta name="author" content="Acme Studio"></head><body></body></html>'
    info = extract_attribution(html, base_url="https://example.com")
    assert info.name == "Acme Studio"
    assert info.source == "meta_tag"


def test_extracts_visible_designed_by_with_link():
    html = """
    <html><body><footer><a href="https://designer.example/portfolio">Designed by Pat Lee</a></footer></body></html>
    """
    info = extract_attribution(html, base_url="https://example.com")
    assert info.name == "Pat Lee"
    assert info.link_url == "https://designer.example/portfolio"
    assert info.source == "footer_link"


def test_ignores_powered_by_claude_in_nav_title():
    html = """
    <html><body>
      <nav class="sidebar-nav">
        <a href="/agent/" title="Muzar guide · powered by Claude">Agent</a>
      </nav>
      <section class="skills">
        <a href="https://docs.anthropic.com/">Claude (Anthropic)</a>
      </section>
    </body></html>
    """
    info = extract_attribution(html, base_url="https://muzar.io")
    assert not info.name


def test_ignores_powered_by_claude_in_footer_with_api_docs_link():
    html = """
    <html><body>
      <footer class="main-footer">
        <span>Powered by Claude</span>
        <a href="https://docs.anthropic.com/">Claude</a>
      </footer>
    </body></html>
    """
    info = extract_attribution(html, base_url="https://example.com")
    assert not info.name


def test_accepts_ai_designer_in_footer():
    html = """
    <html><body>
      <footer class="site-footer">
        <p>Designed by Midjourney Studio</p>
      </footer>
    </body></html>
    """
    info = extract_attribution(html, base_url="https://example.com")
    assert info.name == "Midjourney Studio"
    assert info.source == "visible_text"


def test_accepts_designed_by_claude_in_html_comment():
    html = "<!-- Designed by Claude for Acme Corp --><html><body></body></html>"
    info = extract_attribution(html, base_url="https://example.com")
    assert info.name == "Claude for Acme Corp"


def test_powered_by_not_matched_in_body_outside_footer():
    html = """
    <html><body>
      <main><p>Powered by OpenAI GPT</p></main>
      <a href="https://platform.openai.com/docs/">OpenAI GPT</a>
    </body></html>
    """
    info = extract_attribution(html, base_url="https://example.com")
    assert not info.name
