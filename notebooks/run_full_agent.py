"""Run the full deep research agent from a Python script.

Usage:
    python run_full_agent.py "What are the latest trends in AI agents?"

The script runs the full pipeline:
1. Scope
2. Research
3. Write

The final report is saved to: ../reports/<thread_id>/report.md
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from utils import disable_langsmith, init_langfuse_tracing

# Make sure the project src is importable when running from notebooks/
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

load_dotenv()

# Remove LangSmith vars so traces go only to Langfuse
disable_langsmith()

from deep_research_from_scratch.research_agent_full import agent  # noqa: E402


async def run(query: str, thread_id: str | None = None) -> str:
    """Invoke the full research agent and return the final report text."""
    thread_id = thread_id or str(uuid.uuid4())
    langfuse_handler = init_langfuse_tracing()

    state = await agent.ainvoke(
        {"messages": [HumanMessage(content=query)]},
        config={
            "configurable": {
                "thread_id": thread_id,
                "scope_model": "azure_openai:GPT-55-2026-04-24",
                "research_model": "azure_openai:GPT-55-2026-04-24",
                "summarization_model": "azure_openai:GPT-55-2026-04-24",
                "compress_model": "azure_openai:GPT-55-2026-04-24",
                "supervisor_model": "azure_openai:GPT-55-2026-04-24",
                "writer_model": "azure_openai:GPT-55-2026-04-24",
                },
            "callbacks": [langfuse_handler],
            "metadata": {
                "entrypoint": "run_full_agent.py",
                "langfuse_session_id": thread_id,
            },
        },
    )

    report = state.get("final_report", "")

    output_dir = REPO_ROOT / "reports" / thread_id
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"Saved report to: {report_path}")
    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    asyncio.run(run(" ".join(sys.argv[1:])))
