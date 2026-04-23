import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage
from langgraph.graph import END

from deep_research_from_scratch.multi_agent_supervisor import supervisor_tools


class _StubThinkTool:
    def invoke(self, _args: dict) -> str:
        return "Reflection recorded."


class SupervisorToolsTests(unittest.IsolatedAsyncioTestCase):
    async def test_think_only_tool_calls_return_empty_images(self) -> None:
        state = {
            "supervisor_messages": [
                AIMessage(
                    content="I should reflect before deciding.",
                    tool_calls=[
                        {
                            "name": "think_tool",
                            "args": {"reflection": "Consider whether parallel research is needed."},
                            "id": "call_think_1",
                        }
                    ],
                )
            ],
            "research_iterations": 1,
            "images": [],
        }

        with patch(
            "deep_research_from_scratch.multi_agent_supervisor.think_tool",
            new=_StubThinkTool(),
        ):
            result = await supervisor_tools(state, config={"configurable": {}})

        self.assertEqual(result.goto, "supervisor")
        self.assertEqual(result.update["images"], [])
        self.assertEqual(result.update["raw_notes"], [])
        self.assertEqual(len(result.update["supervisor_messages"]), 1)

    async def test_no_tool_calls_end_supervision(self) -> None:
        state = {
            "supervisor_messages": [AIMessage(content="No more research needed.", tool_calls=[])],
            "research_iterations": 1,
            "research_brief": "Test brief",
        }

        result = await supervisor_tools(state, config={"configurable": {}})

        self.assertEqual(result.goto, END)
        self.assertEqual(result.update["research_brief"], "Test brief")
        self.assertEqual(result.update["notes"], [])


if __name__ == "__main__":
    unittest.main()