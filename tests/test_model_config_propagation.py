import unittest
from unittest.mock import MagicMock, patch

from requests.exceptions import SSLError

from deep_research_from_scratch import multi_agent_supervisor
from deep_research_from_scratch import research_agent
from deep_research_from_scratch import research_agent_full
from deep_research_from_scratch import research_agent_mcp
from deep_research_from_scratch import research_agent_scope
from deep_research_from_scratch import utils as research_utils


class SummarizationRuntimeConfigTests(unittest.TestCase):
    def tearDown(self) -> None:
        if hasattr(research_utils, "set_runtime_config"):
            research_utils.set_runtime_config({})

    def test_summarization_model_falls_back_to_runtime_research_model(self) -> None:
        research_utils.set_runtime_config(
            {"research_model": "azure_openai:GPT-54-2026-03-05"}
        )

        with patch.object(research_utils, "init_chat_model") as init_chat_model:
            research_utils._build_summarization_model()

        kwargs = init_chat_model.call_args.kwargs
        self.assertEqual(kwargs["model"], "azure_openai:GPT-54-2026-03-05")
        self.assertEqual(kwargs["azure_deployment"], "GPT-54-2026-03-05")

    def test_summarization_model_prefers_explicit_runtime_override(self) -> None:
        research_utils.set_runtime_config(
            {
                "research_model": "azure_openai:GPT-54-2026-03-05",
                "summarization_model": "azure_openai:GPT-54-MINI-2026-03-17",
            }
        )

        with patch.object(research_utils, "init_chat_model") as init_chat_model:
            research_utils._build_summarization_model()

        kwargs = init_chat_model.call_args.kwargs
        self.assertEqual(kwargs["model"], "azure_openai:GPT-54-MINI-2026-03-17")
        self.assertEqual(kwargs["azure_deployment"], "GPT-54-MINI-2026-03-17")


class ResearchAgentRuntimeConfigTests(unittest.TestCase):
    def test_llm_call_sets_runtime_config_for_tools(self) -> None:
        model = MagicMock()
        model_with_tools = MagicMock()
        model_with_tools.invoke.return_value = "ok"
        model.bind_tools.return_value = model_with_tools
        configurable = {
            "research_model": "azure_openai:GPT-54-2026-03-05",
            "summarization_model": "azure_openai:GPT-54-MINI-2026-03-17",
        }

        with patch.object(research_agent, "_build_model", return_value=model), patch.object(
            research_agent, "set_runtime_config"
        ) as set_runtime_config:
            research_agent.llm_call(
                {"researcher_messages": ["placeholder"]},
                {"configurable": configurable},
            )

        set_runtime_config.assert_called_once_with(configurable)


class ScopeModelNormalizationTests(unittest.TestCase):
    def test_scope_model_normalizes_lowercase_deployment_names(self) -> None:
        with patch.object(research_agent_scope, "init_chat_model") as init_chat_model:
            research_agent_scope._build_model("azure_openai:gpt-54-2026-03-05")

        kwargs = init_chat_model.call_args.kwargs
        self.assertEqual(kwargs["model"], "azure_openai:GPT-54-2026-03-05")
        self.assertEqual(kwargs["azure_deployment"], "GPT-54-2026-03-05")

    def test_scope_model_leaves_bare_model_ids_unchanged(self) -> None:
        self.assertEqual(
            research_agent_scope._normalize_model_id("gpt-54-2026-03-05"),
            "gpt-54-2026-03-05",
        )


class AdditionalModelNormalizationTests(unittest.TestCase):
    def test_runtime_model_builders_normalize_lowercase_deployments(self) -> None:
        test_cases = [
            (research_agent, "azure_openai:gpt-54-2026-03-05", "GPT-54-2026-03-05"),
            (research_agent_mcp, "azure_openai:gpt-5.2", "GPT-5.2"),
            (multi_agent_supervisor, "azure_openai:gpt-5.3", "GPT-5.3"),
            (research_agent_full, "azure_openai:gpt-5.3", "GPT-5.3"),
        ]

        for module, model_id, expected_deployment in test_cases:
            with self.subTest(module=module.__name__, model_id=model_id), patch.object(
                module, "init_chat_model"
            ) as init_chat_model:
                module._build_model(model_id)

            kwargs = init_chat_model.call_args.kwargs
            self.assertEqual(kwargs["model"], f"azure_openai:{expected_deployment}")
            self.assertEqual(kwargs["azure_deployment"], expected_deployment)

    def test_summarization_model_normalizes_lowercase_runtime_override(self) -> None:
        research_utils.set_runtime_config(
            {"summarization_model": "azure_openai:gpt-54-mini-2026-03-17"}
        )

        with patch.object(research_utils, "init_chat_model") as init_chat_model:
            research_utils._build_summarization_model()

        kwargs = init_chat_model.call_args.kwargs
        self.assertEqual(kwargs["model"], "azure_openai:GPT-54-MINI-2026-03-17")
        self.assertEqual(kwargs["azure_deployment"], "GPT-54-MINI-2026-03-17")


class TavilySslFallbackTests(unittest.TestCase):
    def test_tavily_search_retries_once_on_ssl_error(self) -> None:
        with patch.object(
            research_utils.tavily_client,
            "search",
            side_effect=[
                SSLError("certificate verify failed"),
                {"results": [], "images": []},
            ],
        ) as mock_search:
            results = research_utils.tavily_search_multiple(["test query"])

        self.assertEqual(results, [{"results": [], "images": []}])
        self.assertEqual(mock_search.call_count, 2)


if __name__ == "__main__":
    unittest.main()