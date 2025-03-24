"""Utility & helper functions."""

import re
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from typing import Dict, List
from datetime import datetime
import requests
import os, sys
import ast
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from typing import List

try:
    import torch
    from transformers import AutoTokenizer, AutoModel
except:
    print("Please install torch and transformers to use BGE_M3_EmbeddingFunction in local.")
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


def load_chat_model(fully_specified_name: str, temperature: float = 0.01) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)
    if provider == "siliconflow":
        try:
            llm = ChatOpenAI(
                model=model,  # 或者换成你对应的模型
                temperature=temperature,
                base_url=os.getenv("SILICONFLOW_API_BASE"),
                api_key=os.getenv("SILICONFLOW_API_KEY"),
            )
            return llm
        except Exception as e:
            raise ValueError(f"SILICONFLOW_API_KEY 错误，请检查 .env 文件。{e}")
    elif provider == "huoshan":
        try:
            llm = ChatDeepSeek(
                model=model,  # 或者换成你对应的模型
                temperature=temperature,
                api_base=os.getenv("HUOSHAN_API_BASE"),
                api_key=os.getenv("HUOSHAN_API_KEY"),
            )
            return llm
        except Exception as e:
            raise ValueError(f"HUOSHAN_API_KEY 错误，请检查 .env 文件。{e}")
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
    if "Created by: MooseAgent" not in code:
        # 创建创作者信息
        current_date = datetime.now().strftime("%Y-%m-%d")
        creator_info = f"# Created by: MooseAgent\n# Date: {current_date}\n"
        # 将描述转换为多行注释
        comment_lines = description.strip().split("\n")
        comment_block = "\n".join(f"# {line}" for line in comment_lines)

        # 合并注释和代码
        combined_string = f"{creator_info}\n{comment_block}\n\n{code}"
        return combined_string
    else:
        return code


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
    def __init__(
        self,
        use_local_model: bool = True,
        local_model_name_or_path: str = "BAAI/bge-m3",  # 根据你实际需要的模型名称/路径调整
    ):
        """
        :param use_local_model: 是否使用本地模型。True 时将使用本地模型，False 时走远程 API
        :param local_model_name_or_path: 本地模型的 Hugging Face repo 名或本地路径
        """

        self.use_local_model = use_local_model

        if self.use_local_model:
            try:
                # 如果在本地推理，这里加载本地模型
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                # 根据 BGE 模型加载对应的 tokenizer、model
                self.tokenizer = AutoTokenizer.from_pretrained(local_model_name_or_path)
                self.model = AutoModel.from_pretrained(local_model_name_or_path)
                self.model.to(self.device)
                self.model.eval()
            except:
                self.use_local_model = False
                raise ValueError("请安装 torch 和 transformers 以使用 BGE_M3_EmbeddingFunction。")
        if not self.use_local_model:
            # 如果使用远程服务，则从环境变量里读取 API URL 和 Key
            self.api_url = os.getenv("SILICONFLOW_BASE")
            self.api_key = os.getenv("SILICONFLOW_API_KEY")
            if not self.api_key:
                raise ValueError("未能获取到 SILICONFLOW_API_KEY 环境变量，请检查 .env 文件。")
            self.model_name = os.getenv("SILICONFLOW_EMBEDDING_MODEL")
            if not self.model_name:
                raise ValueError("未能获取到 SILICONFLOW_EMBEDDING_MODEL 环境变量，请检查 .env 文件。")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if self.use_local_model:
            return [self._embed_single_text_local(t) for t in texts]
        else:
            return self._embed_remote(texts)

    def embed_query(self, text: str) -> List[float]:
        # 复用 embed_documents 的逻辑
        return self.embed_documents([text])[0]

    def _embed_single_text_local(self, text: str) -> List[float]:
        """
        使用本地模型把单条文本转为向量
        """
        inputs = self.tokenizer(text, padding=True, truncation=True, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)

        # 注意：不同的模型可能输出结构不一样，这里以典型的 [CLS] pooling 为例
        # BGE 系列一般会推荐把最后一层的 CLS 向量或 mean pooling 作为 embedding，
        # 可根据自己需要修改。
        # 例如官方推荐使用 mean pooling，就可以用:
        # token_embeddings = outputs.last_hidden_state
        # input_mask_expanded = inputs["attention_mask"].unsqueeze(-1).expand(token_embeddings.size()).float()
        # sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        # sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        # embedding = sum_embeddings / sum_mask
        #
        # 这里简单演示 CLS pooling
        cls_embedding = outputs.last_hidden_state[:, 0, :]

        # 转成 Python list
        return cls_embedding[0].cpu().numpy().tolist()

    def _embed_remote(self, texts: List[str]) -> List[List[float]]:
        """
        走远程服务，把文本发给 API 并返回 embedding
        """
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        data = {"model": self.model_name, "input": texts, "encoding_format": "float"}
        response = requests.post(self.api_url, json=data, headers=headers)
        response.raise_for_status()

        # 取 data 字段再取 embedding
        embeddings = response.json()["data"]
        embeddings = [item["embedding"] for item in embeddings]
        return embeddings


def check_app(inpcard: str, dp_json: dict):
    """Check the application of the inpcard.
    Args:
        inpcard (str): The inpcard to check.
    Returns:
        dict: A dictionary containing the application of the inpcard.
    """
    # 检查inpcard中是否存在app
    # find the documentation of the app used in the input card
    app_list = []
    lines = inpcard.splitlines()
    for line in lines:
        line = line.replace(" type=", " type =")
        if " type =" in line:
            # 提取app名称，假设格式为 type = <appname>
            app_name = line.split(" type =")[-1].strip().split()[0]
            app_list.append(app_name)
    feedback = ""
    for app in app_list:
        doc = dp_json.get(app)
        if doc is None:
            feedback += f"type = {app} is not found in the documentation, please change another application.\n"
    return feedback


class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()
