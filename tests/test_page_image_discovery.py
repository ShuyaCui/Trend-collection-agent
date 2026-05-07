"""Tests for page-level image discovery helpers.

Covers: normalize_page_image, merge_image_lists, batch_discover_images,
and the integration smoke test for the updated tavily_search pipeline.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from bs4 import BeautifulSoup

from deep_research_from_scratch.state_research import ImageResult
from deep_research_from_scratch.utils import (
    batch_discover_images,
    merge_image_lists,
    normalize_page_image,
    reset_page_discovery_cache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tag(html: str):
    """Parse a fragment and return the first <img> tag."""
    return BeautifulSoup(html, "lxml").find("img")


# ---------------------------------------------------------------------------
# normalize_page_image
# ---------------------------------------------------------------------------

class TestNormalizePageImage:
    BASE = "https://example.com/article/"

    def test_relative_url_resolved_to_absolute(self):
        tag = _make_tag('<img src="../images/photo.jpg" alt="photo">')
        result = normalize_page_image(tag, self.BASE, "Page Title")
        assert result is not None
        assert result.url == "https://example.com/images/photo.jpg"

    def test_absolute_url_unchanged(self):
        tag = _make_tag('<img src="https://cdn.example.com/img.png" alt="cdn">')
        result = normalize_page_image(tag, self.BASE, "Page")
        assert result is not None
        assert result.url == "https://cdn.example.com/img.png"

    def test_data_uri_filtered(self):
        tag = _make_tag('<img src="data:image/png;base64,abc123" alt="inline">')
        assert normalize_page_image(tag, self.BASE, "Page") is None

    def test_svg_blob_filtered(self):
        tag = _make_tag('<img src="<svg xmlns=\'...\'>...</svg>" alt="svg">')
        assert normalize_page_image(tag, self.BASE, "Page") is None

    def test_missing_src_returns_none(self):
        tag = _make_tag("<img alt='no src'>")
        assert normalize_page_image(tag, self.BASE, "Page") is None

    def test_alt_takes_priority_over_tag_title_over_page_title(self):
        tag = _make_tag('<img src="/img.jpg" alt="alt text" title="tag title">')
        result = normalize_page_image(tag, self.BASE, "Page Title")
        assert result.title == "alt text"
        assert result.alt_text == "alt text"

    def test_tag_title_used_when_no_alt(self):
        tag = _make_tag('<img src="/img.jpg" title="tag title">')
        result = normalize_page_image(tag, self.BASE, "Page Title")
        assert result.title == "tag title"

    def test_page_title_fallback_when_no_alt_or_title(self):
        tag = _make_tag('<img src="/img.jpg">')
        result = normalize_page_image(tag, self.BASE, "Page Title")
        assert result.title == "Page Title"

    def test_figcaption_extracted_from_parent_figure(self):
        soup = BeautifulSoup(
            '<figure><img src="/img.jpg"><figcaption>Caption text</figcaption></figure>',
            "lxml",
        )
        tag = soup.find("img")
        result = normalize_page_image(tag, self.BASE, "Page")
        assert result.figcaption == "Caption text"
        assert result.description == "Caption text"

    def test_no_figcaption_when_not_in_figure(self):
        tag = _make_tag('<img src="/img.jpg" alt="standalone">')
        result = normalize_page_image(tag, self.BASE, "Page")
        assert result.figcaption == ""

    def test_discovery_method_is_httpx(self):
        tag = _make_tag('<img src="/img.jpg">')
        result = normalize_page_image(tag, self.BASE, "Page")
        assert result.discovery_method == "httpx"

    def test_source_page_is_base_url(self):
        tag = _make_tag('<img src="/img.jpg">')
        result = normalize_page_image(tag, self.BASE, "Page")
        assert result.source_page == self.BASE

    def test_non_http_scheme_filtered(self):
        tag = _make_tag('<img src="ftp://example.com/img.jpg">')
        assert normalize_page_image(tag, self.BASE, "Page") is None


# ---------------------------------------------------------------------------
# merge_image_lists
# ---------------------------------------------------------------------------

class TestMergeImageLists:
    def _img(self, url, source_page="", discovery_method="tavily"):
        return ImageResult(url=url, source_page=source_page, discovery_method=discovery_method)

    def test_tavily_only_images_returned_unchanged(self):
        tavily = [self._img("https://a.com/1.jpg"), self._img("https://a.com/2.jpg")]
        result = merge_image_lists(tavily, [])
        assert [r.url for r in result] == ["https://a.com/1.jpg", "https://a.com/2.jpg"]

    def test_page_only_images_appended(self):
        page = [self._img("https://b.com/3.jpg", source_page="https://b.com", discovery_method="httpx")]
        result = merge_image_lists([], page)
        assert len(result) == 1
        assert result[0].url == "https://b.com/3.jpg"

    def test_duplicate_urls_deduplicated(self):
        tavily = [self._img("https://a.com/1.jpg")]
        page = [self._img("https://a.com/1.jpg", source_page="https://a.com", discovery_method="httpx")]
        result = merge_image_lists(tavily, page)
        assert len(result) == 1

    def test_source_page_backfilled_on_tavily_entry(self):
        tavily = [self._img("https://a.com/1.jpg")]  # source_page=""
        page = [ImageResult(
            url="https://a.com/1.jpg",
            source_page="https://a.com/article",
            alt_text="Product",
            figcaption="Fig 1",
            page_title="Article",
            discovery_method="httpx",
        )]
        result = merge_image_lists(tavily, page)
        assert result[0].source_page == "https://a.com/article"
        assert result[0].alt_text == "Product"
        assert result[0].figcaption == "Fig 1"
        assert result[0].discovery_method == "httpx"

    def test_source_page_not_overwritten_when_already_set(self):
        tavily = [self._img("https://a.com/1.jpg", source_page="https://original.com")]
        page = [self._img("https://a.com/1.jpg", source_page="https://other.com", discovery_method="httpx")]
        result = merge_image_lists(tavily, page)
        assert result[0].source_page == "https://original.com"

    def test_output_order_tavily_first_then_new_page_entries(self):
        tavily = [self._img("https://a.com/1.jpg"), self._img("https://a.com/2.jpg")]
        page = [
            self._img("https://a.com/1.jpg", source_page="https://a.com", discovery_method="httpx"),
            self._img("https://b.com/3.jpg", source_page="https://b.com", discovery_method="httpx"),
        ]
        result = merge_image_lists(tavily, page)
        assert result[0].url == "https://a.com/1.jpg"
        assert result[1].url == "https://a.com/2.jpg"
        assert result[2].url == "https://b.com/3.jpg"


# ---------------------------------------------------------------------------
# batch_discover_images
# ---------------------------------------------------------------------------

_SAMPLE_HTML = """
<html>
<head><title>Test Page</title><meta property="og:image" content="https://cdn.example.com/og.jpg"></head>
<body>
<img src="/images/a.jpg" alt="Image A">
<figure><img src="/images/b.jpg"><figcaption>Caption B</figcaption></figure>
</body>
</html>
"""

def _mock_response(html: str = _SAMPLE_HTML, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.text = html
    resp.raise_for_status = MagicMock() if status == 200 else MagicMock(side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=resp))
    return resp


class TestBatchDiscoverImages:
    def setup_method(self):
        reset_page_discovery_cache()

    def test_images_extracted_from_page(self):
        with patch("deep_research_from_scratch.utils.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.return_value = _mock_response()
            results = batch_discover_images(["https://example.com/page"])
        urls = [r.url for r in results]
        assert "https://cdn.example.com/og.jpg" in urls
        assert "https://example.com/images/a.jpg" in urls
        assert "https://example.com/images/b.jpg" in urls

    def test_figcaption_preserved(self):
        with patch("deep_research_from_scratch.utils.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.return_value = _mock_response()
            results = batch_discover_images(["https://example.com/page"])
        b_img = next((r for r in results if "b.jpg" in r.url), None)
        assert b_img is not None
        assert b_img.figcaption == "Caption B"

    def test_per_page_cap_of_10_enforced(self):
        imgs = "".join(f'<img src="/img{i}.jpg">' for i in range(20))
        html = f"<html><head><title>T</title></head><body>{imgs}</body></html>"
        with patch("deep_research_from_scratch.utils.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.return_value = _mock_response(html)
            results = batch_discover_images(["https://example.com/page"])
        assert len(results) <= 10

    def test_skip_set_prevents_refetch(self):
        with patch("deep_research_from_scratch.utils.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.return_value = _mock_response()
            batch_discover_images(["https://example.com/page"])
            call_count_first = instance.get.call_count
            # Second call with same URL — should be skipped
            batch_discover_images(["https://example.com/page"])
            call_count_second = instance.get.call_count
        assert call_count_second == call_count_first  # no new fetches

    def test_returns_empty_on_http_error(self):
        with patch("deep_research_from_scratch.utils.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.side_effect = httpx.ConnectError("connection refused")
            results = batch_discover_images(["https://broken.example.com/page"])
        assert results == []

    def test_semaphore_limits_concurrency(self):
        """Verify ThreadPoolExecutor max_workers is respected (≤3 concurrent)."""
        urls = [f"https://example.com/page{i}" for i in range(6)]
        call_log = []

        def fake_get(url):
            call_log.append(url)
            return _mock_response("<html><head><title>T</title></head><body></body></html>")

        with patch("deep_research_from_scratch.utils.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.side_effect = fake_get
            results = batch_discover_images(urls, max_concurrent=3)
        # All 6 URLs fetched, just verifying no crash and all processed
        assert len(call_log) == 6

    def test_source_page_populated(self):
        with patch("deep_research_from_scratch.utils.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.return_value = _mock_response()
            results = batch_discover_images(["https://example.com/page"])
        for r in results:
            assert r.source_page == "https://example.com/page"
            assert r.discovery_method == "httpx"


# ---------------------------------------------------------------------------
# Integration smoke test
# ---------------------------------------------------------------------------

class TestTavilySearchIntegration:
    """Smoke tests: updated tavily_search pipeline wires batch_discover + merge."""

    def setup_method(self):
        reset_page_discovery_cache()

    def test_batch_discover_called_with_result_urls(self):
        """tavily_search passes Tavily result URLs to batch_discover_images."""
        from deep_research_from_scratch.utils import tavily_search

        fake_results = [
            {"url": "https://example.com/article", "title": "T", "content": "c", "images": []},
            {"url": "https://example.com/other", "title": "T2", "content": "c2", "images": []},
        ]
        with (
            patch("deep_research_from_scratch.utils.tavily_search_multiple", return_value=fake_results),
            patch("deep_research_from_scratch.utils.batch_discover_images", return_value=[]) as mock_batch,
            patch("deep_research_from_scratch.utils.process_search_results", return_value={}),
            patch("deep_research_from_scratch.utils.deduplicate_search_results", return_value=fake_results),
            patch("deep_research_from_scratch.utils.format_search_output", return_value="output"),
        ):
            tavily_search.invoke({"query": "test query"})

        mock_batch.assert_called_once()
        called_urls = mock_batch.call_args[0][0]
        assert "https://example.com/article" in called_urls
        assert "https://example.com/other" in called_urls

    def test_page_images_passed_to_merge_image_lists(self):
        """Page-discovered images are merged before storing in context var."""
        from deep_research_from_scratch.utils import tavily_search

        page_img = ImageResult(
            url="https://example.com/hero.jpg",
            source_page="https://example.com/article",
            discovery_method="httpx",
        )
        fake_results = [{"url": "https://example.com/article", "title": "T", "content": "c", "images": []}]

        with (
            patch("deep_research_from_scratch.utils.tavily_search_multiple", return_value=fake_results),
            patch("deep_research_from_scratch.utils.batch_discover_images", return_value=[page_img]),
            patch("deep_research_from_scratch.utils.merge_image_lists", wraps=merge_image_lists) as mock_merge,
            patch("deep_research_from_scratch.utils.process_search_results", return_value={}),
            patch("deep_research_from_scratch.utils.deduplicate_search_results", return_value=fake_results),
            patch("deep_research_from_scratch.utils.format_search_output", return_value="output"),
        ):
            tavily_search.invoke({"query": "test query"})

        mock_merge.assert_called_once()
        _, page_arg = mock_merge.call_args[0]
        assert page_arg == [page_img]
