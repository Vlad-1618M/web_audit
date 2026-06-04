"""Tests for enhanced HTML DOM inventory — links, images, favicons."""
from webaudit.collectors.html import parse_html_inventory

def test_site_links_split_internal_external():
    """Ensures Site Links Split Internal External."""
    html = '\n    <html><body>\n      <a href="/about">About</a>\n      <a href="https://example.com/contact">Contact</a>\n      <a href="https://other.com/out">Out</a>\n    </body></html>\n    '
    inv = parse_html_inventory(html, target_url='https://example.com')
    assert inv.internal_link_count == 2
    assert inv.external_link_count == 1
    assert len(inv.site_links) == 3

def test_collects_favicon_and_og_image():
    """Ensures Collects Favicon And Og Image."""
    html = '\n    <html><head>\n      <link rel="icon" href="/favicon.ico">\n      <link rel="apple-touch-icon" href="/apple.png">\n      <meta property="og:image" content="https://example.com/og.jpg">\n      <meta name="twitter:image" content="https://example.com/twitter-card.png">\n    </head><body>\n      <img src="/logo.png">\n    </body></html>\n    '
    inv = parse_html_inventory(html, target_url='https://example.com')
    kinds = {item['kind'] for item in inv.images}
    urls = {item['url'] for item in inv.images}
    assert 'favicon' in kinds
    assert 'apple-touch-icon' in kinds
    assert 'og-image' in kinds
    assert 'twitter-image' in kinds
    assert 'https://example.com/favicon.ico' in urls
    assert 'https://example.com/logo.png' in urls
    assert 'https://example.com/twitter-card.png' in urls

def test_collects_lazy_loaded_and_picture_images():
    """Ensures Collects Lazy Loaded And Picture Images."""
    html = '\n    <html><body>\n      <img data-src="/lazy-logo.png" src="data:image/gif;base64,R0lGODlh">\n      <picture>\n        <source srcset="/hero-800.webp 800w, /hero-1200.webp 1200w">\n        <img src="/hero-fallback.png">\n      </picture>\n    </body></html>\n    '
    inv = parse_html_inventory(html, target_url='https://example.com')
    urls = {item['url'] for item in inv.images}
    kinds = {item['kind'] for item in inv.images}
    assert 'https://example.com/lazy-logo.png' in urls
    assert 'https://example.com/hero-fallback.png' in urls
    assert 'https://example.com/hero-800.webp' in urls
    assert 'img-data-src' in kinds
    assert 'picture-srcset' in kinds
