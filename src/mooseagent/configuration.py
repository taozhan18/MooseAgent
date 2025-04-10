import os
from enum import Enum
from dataclasses import dataclass, fields
from typing import Any, Optional, Dict
from langchain_core.runnables import RunnableConfig


@dataclass(kw_only=True)
class Configuration:
    """The configurable fields for the chatbot."""

    # v3 is unstable in output given format
    alignment_model: str = "huoshan/deepseek-v3-250324"
    architect_model: str = "huoshan/deepseek-r1-250120"
    assistant_model: str = "huoshan/deepseek-v3-250324"
    query_model: str = "huoshan/deepseek-v3-250324"
    rearchitect_model: str = "huoshan/deepseek-v3-241226"
    review_model: str = "huoshan/deepseek-v3-241226"  # Defaults to claude-3-7-sonnet-latest
    writer_model: str = "huoshan/deepseek-v3-241226"  # Defaults to claude-3-5-sonnet-latest
    extracter_model: str = "openai/gpt-4o-mini"
    embedding_function: str = "BGE_M3_EmbeddingFunction"  # "OPENAI"  or "BGE_M3_EmbeddingFunction"

    # DIR
    ABSOLUTE_PATH: str = "/home/zt/workspace/MooseAgent/src"
    MOOSE_DIR: str = "/home/zt/workspace/mymoose/mymoose-opt"
    save_dir: str = "/home/zt/workspace/MooseAgent/run_path/"
    docs_dir: str = os.path.join(ABSOLUTE_PATH, "database")
    DATABASE_NAME: str = "*.md"
    TEMPERATURE: float = 0.1

    # RAG
    top_k: int = 3
    rag_model: str = "openai/gpt-4o-mini"

    # setting for load_vector_database.py
    rag_json_path: str = os.path.join(ABSOLUTE_PATH, "database", "comment.json")  # comment.json
    batch_size: int = 1  # batch size for adding documents to the vector store
    PERSIST_DIRECTORY: str = os.path.join(
        ABSOLUTE_PATH, "database", embedding_function + "_faiss_inpcard"
    )  # database to save

    # database for loading
    dp_database_path: str = os.path.join(ABSOLUTE_PATH, "database", embedding_function + "_faiss_dp")
    input_database_path: str = os.path.join(ABSOLUTE_PATH, "database", embedding_function + "_faiss_inpcard")

    # AUTO COMMENT
    use_llm_rag: bool = False
    comment_rag_model: str = "openai/gpt-4o-mini"
    comment_writer_model: str = "openai/gpt-4o-mini"
    dp_json_path: str = os.path.join(ABSOLUTE_PATH, "database", "dp.json")

    # run
    MAX_ITER: int = 7
    MAX_REARCHITECT = 3
    mpi: int = 1

    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig] = None) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = config["configurable"] if config and "configurable" in config else {}
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name)) for f in fields(cls) if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})
