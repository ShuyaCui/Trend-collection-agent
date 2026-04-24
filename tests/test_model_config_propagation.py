import unittest
from unittest.mock import MagicMock, patch

from deep_research_from_scratch import research_agent
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


if __name__ == "__main__":
    unittest.main()