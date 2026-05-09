import pytest
from unittest.mock import AsyncMock, patch
from bs4 import BeautifulSoup

from app.crawler import make_id, has_keyword, scrape_clive_emson
from app.config import settings


def test_make_id_is_deterministic():
    a = make_id("rightmove", "https://example.com/1")
    b = make_id("rightmove", "https://example.com/1")
    assert a == b


def test_make_id_differs_by_source():
    a = make_id("rightmove", "https://example.com/1")
    b = make_id("otm",       "https://example.com/1")
    assert a != b


def test_make_id_differs_by_url():
    a = make_id("rightmove", "https://example.com/1")
    b = make_id("rightmove", "https://example.com/2")
    assert a != b


def test_make_id_is_hex_32_chars():
    result = make_id("source", "https://example.com")
    assert len(result) == 32
    assert all(c in "0123456789abcdef" for c in result)


def test_has_keyword_church():
    assert has_keyword("Beautiful former church for sale") is True


def test_has_keyword_chapel():
    assert has_keyword("Victorian chapel conversion") is True


def test_has_keyword_case_insensitive():
    assert has_keyword("CHURCH CONVERSION") is True
    assert has_keyword("Chapel Street") is True


def test_has_keyword_no_match():
    assert has_keyword("3-bed semi in Maidstone") is False


def test_has_keyword_empty():
    assert has_keyword("") is False


def test_has_keyword_vestry():
    assert has_keyword("includes vestry and bell tower") is True


def test_has_keyword_ecclesiastical():
    assert has_keyword("Ecclesiastical property for development") is True


MOCK_CLIVE_EMSON_HTML = """
<html><body>
  <article class="lot">
    <h3 class="lot-title">Former Methodist Chapel, Kent</h3>
    <span class="guide-price">£120,000+</span>
    <span class="address">Sittingbourne, Kent</span>
    <a href="/lots/12345">View Lot</a>
  </article>
  <article class="lot">
    <h3 class="lot-title">3 Bedroom House, Essex</h3>
    <span class="guide-price">£250,000+</span>
    <span class="address">Chelmsford, Essex</span>
    <a href="/lots/99999">View Lot</a>
  </article>
</body></html>
"""


@pytest.mark.asyncio
async def test_clive_emson_filters_by_keyword():
    mock_client = AsyncMock()
    with patch("app.crawler.fetch_html") as mock_fetch:
        mock_fetch.return_value = BeautifulSoup(MOCK_CLIVE_EMSON_HTML, "lxml")
        results = await scrape_clive_emson(mock_client)

    assert len(results) == 1
    assert "Chapel" in results[0]["title"]
    assert results[0]["source"] == "Clive Emson Auctions"
    assert results[0]["price"] == "£120,000+"
    assert results[0]["location"] == "Sittingbourne, Kent"


@pytest.mark.asyncio
async def test_clive_emson_returns_empty_on_fetch_failure():
    mock_client = AsyncMock()
    with patch("app.crawler.fetch_html", return_value=None):
        results = await scrape_clive_emson(mock_client)
    assert results == []


@pytest.mark.asyncio
async def test_clive_emson_id_format():
    mock_client = AsyncMock()
    with patch("app.crawler.fetch_html") as mock_fetch:
        mock_fetch.return_value = BeautifulSoup(MOCK_CLIVE_EMSON_HTML, "lxml")
        results = await scrape_clive_emson(mock_client)
    for r in results:
        assert len(r["id"]) == 32


def test_keywords_not_empty():
    assert len(settings.KEYWORDS) > 0


def test_request_delay_positive():
    assert settings.REQUEST_DELAY_SECONDS > 0


def test_env_is_valid():
    assert settings.ENV in ("dev", "staging", "prod")
    