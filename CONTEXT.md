# CONTEXT.md — Auto-Correcting Academic Research Agent
> **Purpose:** This file is the **persistent memory and canonical instruction manual** for all future AI-assisted development sessions on this project. Every Claude session working on this codebase **must read this file first** before generating any code or documentation.

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Project Name** | Auto-Correcting Academic Research Agent |
| **Institutional Context** | Master's Degree — Distributed Systems & Artificial Intelligence, ENSET (École Normale Supérieure de l'Enseignement Technique) |
| **Primary Research Domain** | Graph Convolutional Networks (GCN) for EEG Signal Decoding / Brain-Computer Interfaces (BCI) |
| **Core Framework** | LangGraph (v0.2+) + LangChain + ChromaDB |
| **LLM Backend** | OpenAI GPT-4o (configurable via `.env`) |
| **Python Version** | 3.11+ |
| **Architecture Pattern** | Self-Reflective Agentic RAG (Retrieval-Augmented Generation) with Auto-Correction |

---

## 2. Project Architecture Summary

The system implements a **cyclic, self-correcting RAG pipeline** orchestrated by LangGraph. Unlike linear RAG (Retrieve → Generate), this architecture introduces a feedback loop that evaluates retrieved document quality before synthesis, transforming the query if the corpus is deemed insufficient.

### 2.1 LangGraph Node Inventory

| Node Name | Function | File | Responsibility |
|---|---|---|---|
| `retrieve` | `retrieve()` | `nodes.py` | Queries ChromaDB via MMR search; increments `loop_step` |
| `grade_documents` | `grade_documents()` | `nodes.py` | LLM-grades each document; writes `relevance_decision` |
| `transform_query` | `transform_query()` | `nodes.py` | Rewrites query with domain-specific enrichment |
| `generate` | `generate()` | `nodes.py` | Synthesises academic answer from relevant context |

### 2.2 Edge Topology

```
START → retrieve → grade_documents
                        │
                        ├─[generate]──────────────────► generate → END
                        │
                        └─[transform_query]──► transform_query → retrieve (loop)
```

### 2.3 State Schema (`state.py`)

```python
class AgentState(TypedDict):
    question: str                   # Current (possibly transformed) query
    original_question: str          # Immutable original user query
    documents: List[Document]       # Raw retrieved documents
    graded_documents: List[GradedDocument]  # Annotated with relevance
    generation: Optional[str]       # Final synthesised answer
    loop_step: int                  # Cycle counter (max: 3)
    relevance_decision: Optional[Literal["generate", "transform_query"]]
    error: Optional[str]            # Observability field
```

### 2.4 Safety Mechanisms

- **`MAX_RETRIEVE_ITERATIONS = 3`** (defined in `state.py`): Hard cap on the Retrieve → Grade → Rewrite cycle. Enforced in both `grade_documents` (sets decision to `"generate"`) and `route_after_grading` (redundant override).
- **`RELEVANCE_THRESHOLD = 0.5`**: Minimum fraction of relevant documents required to proceed to generation without query transformation.
- **Structured outputs** via `pydantic.BaseModel` + `llm.with_structured_output()`: Prevents free-text parsing failures in the Grader and Transformer nodes.

---

## 3. File Structure

```
research_agent/
├── state.py          # AgentState TypedDict + constants
├── nodes.py          # All node functions + prompt templates + Pydantic schemas
├── workflow.py       # Graph assembly, routing, CLI entry point
├── CONTEXT.md        # THIS FILE — persistent session memory
├── README.md         # Research-paper-style project documentation
├── .env.example      # Environment variable template
├── requirements.txt  # Python dependencies
└── chroma_db/        # ChromaDB persistence directory (gitignored)
    └── ...
```

---

## 4. Strict Coding Standards

> These rules are **non-negotiable** for all future code contributions to this project.

### 4.1 State Management
- **RULE S-1**: All inter-node data transfer **must** flow through `AgentState`. No node may use module-level globals to pass data to other nodes.
- **RULE S-2**: `AgentState` **must** remain a `TypedDict`. Do **not** convert it to a Pydantic `BaseModel` or a dataclass without a deliberate architectural decision recorded in this file.
- **RULE S-3**: `loop_step` **must only be incremented in the `retrieve` node**. No other node may modify it.
- **RULE S-4**: `original_question` is **immutable after initialisation**. No node may overwrite it.

### 4.2 Node Contracts
- **RULE N-1**: Every node function **must** accept exactly one argument: `state: AgentState`.
- **RULE N-2**: Every node function **must** return a `Dict[str, Any]` containing only the keys it is authorised to modify (partial state update).
- **RULE N-3**: All LLM calls **must** use structured outputs (`llm.with_structured_output(PydanticModel)`) where a schema can be defined. Free-text parsing with regex is forbidden.
- **RULE N-4**: Every node **must** wrap its primary logic in a `try/except` block and populate `state["error"]` on failure rather than raising.

### 4.3 Routing
- **RULE R-1**: All routing logic **must** be implemented via `conditional_edges` with explicit `path_map` dictionaries. No routing logic may be embedded within node functions.
- **RULE R-2**: The `route_after_grading` function is the **sole authoritative router**. If additional routing logic is needed, create a new, explicitly named router function.
- **RULE R-3**: The `MAX_RETRIEVE_ITERATIONS` constant **must** be checked in **both** `grade_documents` (writes the decision) and `route_after_grading` (enforces the decision) for defense-in-depth.

### 4.4 Prompt Engineering
- **RULE P-1**: All prompt templates **must** use `ChatPromptTemplate.from_messages()` with explicit `system` and `human` roles.
- **RULE P-2**: Prompt strings **must** be defined as module-level constants (prefixed `_`) and assembled into chains at module load time (not inside node functions).
- **RULE P-3**: All prompts **must** include explicit domain grounding for GCN/EEG research to prevent the LLM from generating generic responses.

### 4.5 Observability
- **RULE O-1**: Every node **must** emit structured `logger.info()` calls at entry and at key decision points.
- **RULE O-2**: Log messages **must** follow the format: `"NODE:<node_name> | <key>=<value> | ..."`
- **RULE O-3**: All exceptions **must** be logged with `exc_info=True` to capture stack traces.

### 4.6 Code Style
- **RULE C-1**: Type hints are **mandatory** on all function signatures.
- **RULE C-2**: All public functions and classes **must** have NumPy-style docstrings.
- **RULE C-3**: Line length limit: **99 characters**.
- **RULE C-4**: Imports must be organised: stdlib → third-party → local, separated by blank lines.

---

## 5. Environment Configuration

Create a `.env` file at the project root with the following variables:

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (defaults shown)
OPENAI_MODEL=gpt-4o
OPENAI_EMBED_MODEL=text-embedding-3-small
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION=gcn_eeg_papers
RETRIEVER_TOP_K=5
```

---

## 6. Current Project State

**As of initial scaffold generation:**

| Component | Status |
|---|---|
| `state.py` | ✅ Complete — AgentState + GradedDocument + constants |
| `nodes.py` | ✅ Complete — All 4 node functions + 3 Pydantic schemas + prompt templates |
| `workflow.py` | ✅ Complete — Graph assembly + routing + CLI entry point |
| `CONTEXT.md` | ✅ This file |
| `README.md` | ✅ Complete — Research-paper style with Mermaid diagrams |
| **Corpus Ingestion Pipeline** | ❌ Not yet implemented |
| **Evaluation / Benchmarking** | ❌ Not yet implemented |
| **Web / Streamlit UI** | ❌ Not yet implemented |
| **Unit Tests** | ❌ Not yet implemented |

---

## 7. Next Immediate Steps (Priority Ordered)

### STEP 1 — Corpus Ingestion Pipeline (CRITICAL PATH)
**File to create:** `ingest.py`

The vector store is currently empty. Before the agent can run, academic papers must be ingested. Implement:

```python
# ingest.py — skeleton to be implemented
from langchain_community.document_loaders import PyPDFLoader, ArxivLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# Target papers:
# - Defferrard et al. (2016) — Convolutional Neural Networks on Graphs (ChebNet)
# - Kipf & Welling (2017) — Semi-Supervised Classification with GCN
# - Lawhern et al. (2018) — EEGNet
# - Jiang et al. (2019) — EEG-based emotion recognition using GCN
# - Zhao et al. (2021) — EEG Motor Imagery Classification with GCN-based spatial filters
```

**Chunking strategy:** `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)` — calibrated for academic abstracts and method sections.

### STEP 2 — Unit Test Suite
**File to create:** `tests/test_nodes.py`, `tests/test_workflow.py`

Priority test cases:
1. `test_grade_documents_all_relevant` — mock LLM returns all "yes", verify decision = "generate"
2. `test_grade_documents_all_irrelevant` — mock LLM returns all "no", verify decision = "transform_query"
3. `test_loop_step_cap` — verify `loop_step >= MAX_RETRIEVE_ITERATIONS` forces "generate"
4. `test_transform_query_preserves_original` — verify `original_question` is never mutated
5. `test_full_workflow_happy_path` — integration test with mocked retriever

### STEP 3 — Evaluation Framework
**File to create:** `eval/evaluate.py`

Metrics to implement:
- **Faithfulness** (AnswerRelevancyEvaluator from RAGAS): Does the generation stay grounded in the retrieved context?
- **Context Precision / Recall** (RAGAS): Quality of the retrieval stage.
- **Mean Iterations to Generation**: Average `loop_step` at `generate` node entry.
- **Query Drift Score**: Semantic similarity between `original_question` and the final `question` used for generation (via cosine similarity on embeddings).

### STEP 4 — Streamlit Research Dashboard
**File to create:** `app.py`

Key UI components:
- Query input box
- Real-time node execution trace (using `graph.stream()`)
- Document relevance visualisation (bar chart: relevant vs. irrelevant)
- Loop iteration tracker
- Final synthesis display with source citations

---

## 8. Known Limitations and Technical Debt

1. **Singleton Retriever**: `_retriever` in `nodes.py` is a module-level singleton initialised lazily. This is not thread-safe for concurrent requests. Future work should use a retriever factory with connection pooling.
2. **No Caching**: LLM calls are not cached. Integrate `langchain.cache.SQLiteCache` to reduce API costs during development.
3. **ChromaDB Scalability**: ChromaDB with local persistence is appropriate for a research prototype but will not scale beyond ~100K documents. Future production deployment should migrate to a managed vector database (e.g., Pinecone, Weaviate, or pgvector).
4. **Single-Turn Only**: The current architecture processes one question per invocation. Future work should implement multi-turn conversation with `HumanMessage` / `AIMessage` history management.
5. **Hard-coded Domain**: Prompt templates contain explicit GCN/EEG grounding. A configuration layer should abstract domain-specific instructions for reusability.

---

## 9. Key Architectural Decisions (ADR Log)

| ID | Decision | Rationale | Date |
|---|---|---|---|
| ADR-001 | Use `TypedDict` (not Pydantic BaseModel) for `AgentState` | LangGraph's native reducer operates on dict merges; Pydantic adds unnecessary overhead and complicates partial state updates | Initial scaffold |
| ADR-002 | MMR search over pure similarity search | Academic queries on a dense scientific corpus benefit from result diversity; MMR prevents redundant chunk retrieval | Initial scaffold |
| ADR-003 | Structured outputs for Grader and Transformer | Eliminates brittle string parsing; Pydantic validation catches malformed LLM responses at the schema boundary | Initial scaffold |
| ADR-004 | Relevance threshold at 0.5 (fraction) | Conservative threshold appropriate for early-stage corpus; should be re-calibrated after evaluation in STEP 3 | Initial scaffold |
| ADR-005 | Defense-in-depth loop cap | `loop_step` cap enforced in both `grade_documents` AND `route_after_grading` — belt-and-suspenders approach for production safety | Initial scaffold |
