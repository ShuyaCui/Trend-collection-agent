"""Gradio chat UI for the material recommender agent."""

import base64
import os
from pathlib import Path

# Must be set before Gradio imports so it uses a writable temp directory.
os.environ.setdefault("GRADIO_TEMP_DIR", str(Path.home() / ".gradio_tmp"))

import gradio as gr
from langchain_core.messages import HumanMessage

from deep_research_from_scratch.material_recommender import _build_graph
from deep_research_from_scratch.state_recommender import (
    ElementRecommendation,
    RecommendationResult,
)

# Compiled without checkpointer — we manage message history explicitly via gr.State.
_agent = _build_graph().compile()

_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _img_tag(path: Path) -> str:
    """Return an <img> tag with the image base64-encoded as a data URI."""
    mime = _MIME.get(path.suffix.lower(), "image/jpeg")
    data = base64.b64encode(path.read_bytes()).decode()
    return (
        f'<img src="data:{mime};base64,{data}" '
        f'style="width:110px;height:110px;object-fit:cover;border-radius:6px;margin:2px;flex-shrink:0;">'
    )


def _elem_html(elem: ElementRecommendation) -> str:
    """Render one element as an HTML card: images on the left, text on the right."""
    imgs_html = "".join(
        _img_tag(p)
        for img in elem.reference_images
        if (p := Path(img.local_path)).exists()
    )
    source = (
        f'<br><span style="color:#888;font-size:0.8em;">来源: {elem.source_heading}</span>'
        if elem.source_heading
        else ""
    )
    return (
        f'<div style="display:flex;gap:12px;align-items:flex-start;'
        f'padding:10px;margin-bottom:10px;border:1px solid #e5e7eb;border-radius:8px;background:#fafafa;">'
        f'<div style="display:flex;flex-wrap:wrap;gap:4px;flex-shrink:0;max-width:240px;">{imgs_html}</div>'
        f'<div style="min-width:0;">'
        f'<b>{elem.element_name}</b> <span style="color:#666;">({elem.element_name_en})</span><br>'
        f'<span style="font-size:0.9em;color:#444;">{elem.reasoning}</span>'
        f'{source}'
        f'</div></div>'
    )


def _build_html(label: str, recs: list[ElementRecommendation]) -> str:
    """Build full HTML section for one dimension."""
    if not recs:
        return ""
    cards = "".join(_elem_html(r) for r in recs)
    return f'<h4 style="margin:12px 0 6px;">{label}</h4>{cards}'


def _results_html(result: RecommendationResult) -> str:
    """Render full results panel as HTML."""
    analysis = (
        f'<div style="background:#f0f9ff;padding:10px;border-radius:8px;margin-bottom:12px;">'
        f'<b>概念分析</b><br>{result.concept_analysis}</div>'
    )
    body = (
        _build_html("颜色", result.colors)
        + _build_html("透明度与质地", result.textures)
        + _build_html("装饰物", result.decorations)
    )
    return analysis + body


def chat_fn(message, history, lc_messages):
    """Handle a user chat message and return updated UI state.

    lc_messages is a list of LangChain message objects accumulated across turns.
    We pass the full history + new message to the agent, then store the updated
    history (result["messages"]) back into gr.State for the next turn.
    """
    input_messages = lc_messages + [HumanMessage(content=message)]
    result = _agent.invoke({"messages": input_messages})

    agent_text = result["messages"][-1].content
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": agent_text},
    ]

    recs: RecommendationResult | None = result.get("recommendations")
    html = _results_html(recs) if recs else "<i>无推荐结果</i>"

    # Persist the full accumulated message history for the next turn.
    return history, html, result["messages"]


def new_chat_fn():
    """Reset all UI state and start a new session."""
    return [], "<i>等待推荐结果…</i>", []


with gr.Blocks(title="材料推荐助手") as demo:
    gr.Markdown("# 🎨 材料推荐助手")

    # Stores the accumulated LangChain message list across turns.
    lc_messages_state = gr.State(value=[])

    with gr.Row():
        # Left: chat
        with gr.Column(scale=1):
            chatbot = gr.Chatbot(label="对话", height=600)
            with gr.Row():
                msg_box = gr.Textbox(
                    placeholder="输入设计概念，例如：设计一款以酸奶为概念的沐浴露…",
                    show_label=False,
                    scale=4,
                )
                send_btn = gr.Button("发送", variant="primary", scale=1)
            new_chat_btn = gr.Button("🔄 新对话", variant="secondary")

        # Right: results panel — each element card has images + text side-by-side
        with gr.Column(scale=1):
            results_html = gr.HTML("<i>等待推荐结果…</i>")

    chat_outputs = [chatbot, results_html, lc_messages_state]

    send_btn.click(
        fn=chat_fn,
        inputs=[msg_box, chatbot, lc_messages_state],
        outputs=chat_outputs,
    ).then(lambda: "", outputs=msg_box)

    msg_box.submit(
        fn=chat_fn,
        inputs=[msg_box, chatbot, lc_messages_state],
        outputs=chat_outputs,
    ).then(lambda: "", outputs=msg_box)

    new_chat_btn.click(
        fn=new_chat_fn,
        inputs=[],
        outputs=[chatbot, results_html, lc_messages_state],
    )


if __name__ == "__main__":
    demo.launch()
