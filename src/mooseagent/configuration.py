import os
from enum import Enum
from dataclasses import dataclass, fields
from typing import Any, Optional, Dict
from langchain_core.runnables import RunnableConfig

DEFAULT_REPORT_STRUCTURE = """Use this structure to create input card for the FEM software moose on the user-provided topic:

1. Introduction (no research needed)
   - Brief overview of the topic area

2. Main Body Sections:
   - Each section should focus on a sub-topic of the user-provided topic

3. Conclusion
   - Aim for 1 structural element (either a list of table) that distills the main body sections
   - Provide a concise summary of the report"""


class SearchAPI(Enum):
    PERPLEXITY = "perplexity"
    TAVILY = "tavily"
    EXA = "exa"
    ARXIV = "arxiv"
    PUBMED = "pubmed"


class PlannerProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"


class WriterProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"


@dataclass(kw_only=True)
class Configuration:
    """The configurable fields for the chatbot."""

    # alignment_model: str = "openai/gpt-4o-mini"
    # review_writer_model: str = "openai/gpt-4o-mini"  # Defaults to claude-3-7-sonnet-latest
    # writer_model: str = "openai/gpt-4o-mini"  # Defaults to claude-3-5-sonnet-latest
    alignment_model: str = "siliconflow/deepseek-ai/DeepSeek-V3"
    review_writer_model: str = "siliconflow/deepseek-ai/DeepSeek-V3"  # Defaults to claude-3-7-sonnet-latest
    writer_model: str = "siliconflow/deepseek-ai/DeepSeek-V3"  # Defaults to claude-3-5-sonnet-latest
    embedding_function: str = "OPENAI"  # "BGE_M3_EmbeddingFunction"  # Defaults to BGE_M3_EmbeddingFunction

    ABSOLUTE_PATH = "E:/vscode/python/Agent/langgraph_learning/mooseagent/src"
    docs_dir: str = os.path.join(ABSOLUTE_PATH, "database")
    DATABASE_NAME: str = "*.md"
    TEMPERATURE: float = 0.1

    # RAG
    top_k: int = 6
    rag_model: str = "openai/gpt-4o-mini"
    rag_json_path: str = os.path.join(ABSOLUTE_PATH, "database", "comment.json")
    batch_size: int = 1  # batch size for adding documents to the vector store
    PERSIST_DIRECTORY: str = os.path.join(ABSOLUTE_PATH, "database", embedding_function + "_faiss")

    # AUTO COMMENT
    use_llm_rag: bool = False
    comment_rag_model: str = "openai/gpt-4o-mini"
    comment_writer_model: str = "openai/gpt-4o-mini"
    dp_json_path: str = os.path.join(ABSOLUTE_PATH, "database", "dp.json")

    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig] = None) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = config["configurable"] if config and "configurable" in config else {}
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name)) for f in fields(cls) if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})
