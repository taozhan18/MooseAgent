"""Utility & helper functions."""

import re
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


def extract_files_and_descriptions(text):
    """
    从指定格式的文本中提取文件名和描述内容。

    参数:
        text (str): 输入的文本，格式为：
                    <n> files are needed to complete the simulation task.
                    **file_name1:**
                    **Description:** detailed description of the file.

    返回:
        dict: 包含文件名和描述的字典。
    """
    result_dict = {}  # 初始化结果字典
    lines = text.strip().split("\n")  # 按行分割文本
    current_file_name = None  # 当前正在处理的文件名
    current_description = []  # 当前文件的描述内容

    for line in lines:
        line = line.strip()  # 去除行首尾的空白字符
        line = line.replace("#", "").replace("*", "")
        if line.startswith("file_name:"):
            # 如果当前有正在处理的文件名，保存之前的描述
            if current_file_name:
                result_dict[current_file_name] = "\n".join(current_description).strip()

            # 重置当前文件名和描述
            current_file_name = line.split(":", 1)[1].strip()
            current_description = []
        elif line.startswith("Description:"):
            # 开始提取描述内容
            current_description.append(line.split(":", 1)[1].strip())
        elif current_file_name:
            # 如果当前行属于描述的一部分，继续添加到描述中
            current_description.append(line)

    # 保存最后一个文件的描述
    if current_file_name:
        result_dict[current_file_name] = "\n".join(current_description).strip()

    return result_dict


def extract_sub_tasks(text):
    """
    从指定格式的文本中提取子任务信息。

    参数:
        text (str): 输入的文本，格式为：
                    sub_task: Name of the sub-task
                    Retrieve: True of False
                    Description: detailed description of the sub-task.

    返回:
        list: 包含子任务信息的列表，每个子任务是一个字典。
    """
    result = []  # 初始化结果列表
    lines = text.strip().split("\n")  # 按行分割文本
    current_task = {}  # 当前正在处理的子任务信息

    for line in lines:
        line = line.strip()  # 去除行首尾的空白字符
        line = line.replace("#", "").replace("*", "")
        if line.startswith("sub_task:"):
            # 如果当前有正在处理的子任务，保存到结果列表中
            if current_task:
                result.append(current_task)

            # 重置当前子任务信息
            current_task = {"sub_task": line.split(":", 1)[1].strip(), "Retrieve": None, "Description": []}
        elif line.startswith("Retrieve:"):
            # 提取 Retrieve 值
            current_task["Retrieve"] = line.split(":", 1)[1].strip()
        elif line.startswith("Description:"):
            # 开始提取描述内容
            current_task["Description"].append(line.split(":", 1)[1].strip())
        elif current_task and line:
            # 如果当前行属于描述的一部分，继续添加到描述中
            current_task["Description"].append(line)

    # 保存最后一个子任务的描述
    if current_task:
        result.append(current_task)

    # 将描述列表合并为字符串
    for task in result:
        task["Description"] = "\n".join(task["Description"]).strip()

    return result

    return result


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
