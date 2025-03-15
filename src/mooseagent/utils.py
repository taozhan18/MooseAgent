"""Utility & helper functions."""

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from typing import Dict, List
from datetime import datetime
import requests
import os
import ast
from langchain_openai import ChatOpenAI

# from langchain_core.embeddings import Embeddings
from langchain.embeddings.base import Embeddings


def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


def load_chat_model(fully_specified_name: str, temperature: float = 0.1) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)
    if provider == "siliconflow":
        try:
            llm = ChatOpenAI(
                model_name=model,  # 或者换成你对应的模型
                temperature=temperature,
                base_url=os.getenv("SILICONFLOW_BASE"),
                api_key=os.getenv("SILICONFLOW_API_KEY"),
            )
            return llm
        except Exception as e:
            raise ValueError(f"SILICONFLOW_API_KEY 错误，请检查 .env 文件。{e}")
    else:
        return init_chat_model(model, model_provider=provider, temperature=temperature)


def tran_list_to_str(modules: List[Dict[str, str]]) -> str:
    """Transform a list of modules to a string."""
    modules_str = ""
    for module in modules:
        modules_str += f"{module.name}: \n{module.description}\n\n"
    return modules_str


def tran_dicts_to_str(dict_data: List) -> str:
    """Transform a list of dictionaries to a string."""
    cases_str = ""
    for dict_item in dict_data:
        content = dict_item.page_content
        cases_str += content
    return cases_str


def combine_code_with_description(description: str, code: str) -> str:
    """
    将代码描述和代码合并为一个字符串。
    描述会作为注释添加到代码前面。

    参数:
        description (str): 对代码的整体描述。
        code (str): 原始代码。

    返回:
        str: 合并后的字符串，描述在前，代码在后。
    """
    # 创建创作者信息
    current_date = datetime.now().strftime("%Y-%m-%d")
    creator_info = f"# Created by: MooseAgent\n# Date: {current_date}\n"
    # 将描述转换为多行注释
    comment_lines = description.strip().split("\n")
    comment_block = "\n".join(f"# {line}" for line in comment_lines)

    # 合并注释和代码
    combined_string = f"{creator_info}\n{comment_block}\n\n{code}"
    return combined_string


class BGE_M3_EmbeddingFunction(Embeddings):
    def __init__(self):
        self.api_url = os.getenv("SILICONFLOW_BASE")
        self.api_key = os.getenv("SILICONFLOW_API_KEY")
        if self.api_key is None:
            raise ValueError("未能获取到 SILICONFLOW_API_KEY 环境变量，请检查 .env 文件。")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        data = {"model": os.getenv("SILICONFLOW_EMBEDDING_MODEL"), "input": texts, "encoding_format": "float"}
        response = requests.post(self.api_url, json=data, headers=headers)
        response.raise_for_status()
        embeddings = response.json()["data"]
        embeddings = [embedding["embedding"] for embedding in embeddings]
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]
