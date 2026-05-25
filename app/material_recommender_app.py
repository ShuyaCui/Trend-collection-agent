"""Gradio chat UI for the material recommender agent."""

import os
import uuid
from pathlib import Path

# Must be set before Gradio imports so it uses a writable temp directory.
os.environ.setdefault("GRADIO_TEMP_DIR", str(Path.home() / ".gradio_tmp"))

import gradio as gr
from langchain_core.messages import HumanMessage

from deep_research_from_scratch.material_recommender import recommender_agent
from deep_research_from_scratch.state_recommender import (
    ElementRecommendation,
    RecommendationResult,
)


def _build_gallery(recs: list[ElementRecommendation]) -> list[tuple[str, str]]:
    """Build (image_path, caption) tuples for a gr.Gallery, skipping missing files."""
    items = []
    for elem in recs:
        for img in elem.reference_images:
            p = Path(img.local_path)
            if p.exists():
                caption = f"{elem.element_name}: {elem.reasoning}"
                items.append((str(p), caption))
    return items


def _concept_md(result: RecommendationResult) -> str:
    """Format concept analysis and material card text as markdown."""
    lines = [f"### 概念分析\n{result.concept_analysis}\n"]
    for label, recs in [
        ("颜色", result.colors),
        ("透明度与质地", result.textures),
        ("装饰物", result.decorations),
    ]:
        lines.append(f"### {label}")
        for i, rec in enumerate(recs, 1):
            source = f" *(来源: {rec.source_heading})*" if rec.source_heading else ""
            lines.append(f"{i}. **{rec.element_name}** ({rec.element_name_en})  \n   {rec.reasoning}{source}")
        lines.append("")
    return "\n".join(lines)


def chat_fn(message, history, thread_id):
    """Handle a user chat message and return updated UI state."""
    config = {"configurable": {"thread_id": thread_id}}
    result = recommender_agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )

    agent_text = result["messages"][-1].content
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": agent_text},
    ]

    recs: RecommendationResult | None = result.get("recommendations")
    if recs:
        concept = _concept_md(recs)
        colors = _build_gallery(recs.colors)
        textures = _build_gallery(recs.textures)
        decorations = _build_gallery(recs.decorations)
    else:
        concept = ""
        colors = textures = decorations = []

    return history, concept, colors, textures, decorations


def new_chat_fn():
    """Reset all UI state and start a new session."""
    return [], "", [], [], [], str(uuid.uuid4())


with gr.Blocks(title="材料推荐助手") as demo:
    gr.Markdown("# 🎨 材料推荐助手")

    thread_id_state = gr.State(value=str(uuid.uuid4()))

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

        # Right: results panel
        with gr.Column(scale=1):
            concept_md = gr.Markdown("*等待推荐结果…*")
            with gr.Accordion("颜色参考图", open=True):
                gallery_colors = gr.Gallery(label="颜色", columns=3, height=220)
            with gr.Accordion("质地参考图", open=True):
                gallery_textures = gr.Gallery(label="透明度与质地", columns=3, height=220)
            with gr.Accordion("装饰物参考图", open=True):
                gallery_decorations = gr.Gallery(label="装饰物", columns=3, height=220)

    outputs = [chatbot, concept_md, gallery_colors, gallery_textures, gallery_decorations]

    send_btn.click(
        fn=chat_fn,
        inputs=[msg_box, chatbot, thread_id_state],
        outputs=outputs,
    ).then(lambda: "", outputs=msg_box)

    msg_box.submit(
        fn=chat_fn,
        inputs=[msg_box, chatbot, thread_id_state],
        outputs=outputs,
    ).then(lambda: "", outputs=msg_box)

    new_chat_btn.click(
        fn=new_chat_fn,
        inputs=[],
        outputs=outputs + [thread_id_state],
    )


if __name__ == "__main__":
    demo.launch()
