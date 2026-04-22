import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from deep_research_from_scratch.Helper import GenAIToken
from deep_research_from_scratch import utils as research_utils


class GenAITokenTests(unittest.TestCase):
    def tearDown(self) -> None:
        for attr in ("_shared_token", "_shared_expires_on", "_shared_refresh_threshold"):
            if hasattr(GenAIToken, attr):
                setattr(GenAIToken, attr, None)

    def test_reuses_shared_token_until_refresh_needed(self) -> None:
        future = int(time.time()) + 3600

        with patch.object(
            GenAIToken,
            "_get_token",
            side_effect=[("token-1", future), ("token-2", future)],
        ) as get_token:
            first = GenAIToken(refresh_threshold=60).token()
            second = GenAIToken(refresh_threshold=60).token()

        self.assertEqual(first, "token-1")
        self.assertEqual(second, "token-1")
        self.assertEqual(get_token.call_count, 1)

    def test_refreshes_shared_token_after_expiration(self) -> None:
        now = int(time.time())

        with patch.object(
            GenAIToken,
            "_get_token",
            side_effect=[("token-1", now + 3600), ("token-2", now + 7200)],
        ) as get_token:
            first = GenAIToken(refresh_threshold=60).token()
            GenAIToken._shared_expires_on = now
            second = GenAIToken(refresh_threshold=60).token()

        self.assertEqual(first, "token-1")
        self.assertEqual(second, "token-2")
        self.assertEqual(get_token.call_count, 2)


class SummarizationModelTests(unittest.TestCase):
    def test_summarization_builds_model_for_each_call(self) -> None:
        summary = SimpleNamespace(summary="short", key_excerpts="quote")
        structured_model = MagicMock()
        structured_model.invoke.return_value = summary

        model = MagicMock()
        model.with_structured_output.return_value = structured_model

        with patch.object(research_utils, "_build_summarization_model", return_value=model) as build_model:
            first = research_utils.summarize_webpage_content("first")
            second = research_utils.summarize_webpage_content("second")

        self.assertIn("<summary>\nshort\n</summary>", first)
        self.assertIn("<summary>\nshort\n</summary>", second)
        self.assertEqual(build_model.call_count, 2)


if __name__ == "__main__":
    unittest.main()