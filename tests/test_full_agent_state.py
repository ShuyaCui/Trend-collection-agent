import unittest

from deep_research_from_scratch import research_agent_full
from deep_research_from_scratch.state_scope import AgentState


class FullAgentStateSchemaTests(unittest.TestCase):
    def test_full_agent_graph_uses_state_with_final_report(self) -> None:
        self.assertIs(research_agent_full.deep_researcher_builder.state_schema, AgentState)


if __name__ == "__main__":
    unittest.main()
