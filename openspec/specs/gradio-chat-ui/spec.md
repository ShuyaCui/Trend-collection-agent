## ADDED Requirements

### Requirement: Gradio Blocks chat layout
The app SHALL render a `gr.Blocks` layout with two columns: a chat column (left) and a results panel (right). The chat column SHALL contain a `gr.Chatbot` for message history and a `gr.Textbox` for user input. The results panel SHALL contain a `gr.Markdown` for concept analysis and three `gr.Gallery` components for colors, textures, and decorations.

#### Scenario: App launches and shows empty state
- **WHEN** the Gradio app is launched
- **THEN** the chat column SHALL be empty and the right panel SHALL show placeholder text indicating no recommendations yet

#### Scenario: User submits a query
- **WHEN** the user types a design query and presses Enter or clicks Send
- **THEN** the chatbot SHALL display the user message and the agent's formatted response text, and the right panel SHALL update with concept analysis and material galleries

### Requirement: Multi-turn conversation with thread continuity
The app SHALL preserve conversation history within a browser session using a `gr.State`-stored `thread_id` (UUID) passed to the LangGraph `config["configurable"]["thread_id"]`. Each new session SHALL generate a fresh UUID. A "New Chat" button SHALL reset the thread_id and clear both the chat history and results panel.

#### Scenario: Follow-up query refines recommendations
- **WHEN** a user submits a second message after receiving initial recommendations
- **THEN** the agent SHALL receive the full prior conversation context and the chat history SHALL show both turns

#### Scenario: New Chat resets session
- **WHEN** the user clicks "New Chat"
- **THEN** the chat history SHALL be cleared, the results panel SHALL be reset to empty, and a new thread_id SHALL be generated

### Requirement: Concept analysis display
The app SHALL display the `RecommendationResult.concept_analysis` text in a `gr.Markdown` block at the top of the results panel after each agent response.

#### Scenario: Concept analysis is shown after recommendation
- **WHEN** the agent returns a `RecommendationResult`
- **THEN** the results panel SHALL show the `concept_analysis` text as a markdown heading section before the galleries

### Requirement: Per-dimension material galleries with reference images
For each dimension (颜色, 透明度与质地, 装饰物), the app SHALL display a `gr.Gallery` populated with `(image_path, caption)` tuples. The caption SHALL include the element's Chinese name and reasoning. Only image paths that exist on disk SHALL be included; missing paths SHALL be silently skipped.

#### Scenario: Gallery shows images for recommended colors
- **WHEN** the agent returns color recommendations with reference images
- **THEN** the 颜色 gallery SHALL display those images with element name + reasoning as captions

#### Scenario: Missing image file is skipped gracefully
- **WHEN** an `ImageReference.local_path` does not exist on disk
- **THEN** the image SHALL be omitted from the gallery without raising an error

#### Scenario: No reference images for an element
- **WHEN** an `ElementRecommendation` has an empty `reference_images` list
- **THEN** that element's caption-only text SHALL still appear in the results markdown, and the gallery SHALL simply have fewer images

### Requirement: Source file generation from notebook
The app file `app/material_recommender_app.py` SHALL be generated from a `%%writefile ../app/material_recommender_app.py` cell in `notebooks/9_gradio_app.ipynb`. The notebook SHALL also contain a launch cell (`demo.launch()`). Running the notebook SHALL produce a functional app file.

#### Scenario: Notebook writefile cell generates app file
- **WHEN** the `%%writefile` cell in `notebooks/9_gradio_app.ipynb` is executed
- **THEN** `app/material_recommender_app.py` SHALL be created or overwritten with the current app code

#### Scenario: App can be launched standalone
- **WHEN** `python app/material_recommender_app.py` is run
- **THEN** a Gradio server SHALL start and be accessible at `http://localhost:7860`
