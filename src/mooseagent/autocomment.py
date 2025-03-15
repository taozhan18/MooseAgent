import sys
import os
from dotenv import load_dotenv

sys.path.append(r"E:/vscode/python/Agent/langgraph_learning/mooseagent/src")
load_dotenv()

from langgraph.graph import StateGraph, START, END
from langgraph.graph import StateGraph
from typing import TypedDict, List, Literal
import json
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage
from mooseagent.utils import load_chat_model, combine_code_with_description
import random
from langgraph.checkpoint.memory import MemorySaver
from mooseagent.configuration import Configuration

COMMENT_PATH = "E:/vscode/python/Agent/langgraph_learning/mooseagent/src/database/comment.json"
input_card_path = "E:/vscode/python/Agent/langgraph_learning/mooseagent/src/database/case_name_uncommented.txt"
dp_json_path = "E:/vscode/python/Agent/langgraph_learning/mooseagent/src/database/dp.json"
save_every = 3


# 状态定义
class InputCardWorkflowState(TypedDict):
    """
    输入卡工作流状态
    """

    input_card_path: list[str]  # 输入卡路径列表
    dp_json: dict[str, str]  # 文档字典
    input_card_name: str  # 输入卡名称
    inpcard: str  # 输入卡内容
    annotated_input_card: str  # 注释后的输入卡内容
    num_commented: int  # 已注释数量
    max_commented: int  # 最大注释数量
    overall_description: str  # 整体描述
    rag_info: str  # 检索文档信息


class CommentState(BaseModel):
    overall_description: str = Field(description="A more complete and specific simulation requirement.")
    annotated_input_card: str = Field(
        description="The input card for MOOSE simulation tasks with annotations, and the annotation symbol is #. The encoding mode is utf-8",
    )


class RAGState(BaseModel):
    app_used: list[str] = Field(
        description="A list of apps used in the input card, each app is a string without special characters such as spaces."
    )


WRITER_PROMPT = """You are an AI assistant responsible for generating annotations and overall descriptions for the input cards of the finite element simulation software MOOSE. Your task is to carefully analyze the provided input card and generate detailed annotations and overall descriptions as required. Remember never to modify the original input card content, only add comments
The input card name is {input_card_name}. The following are the content of the input card that require annotations.
<Input Card>
{inpcard}
</Input Card>
When generating comments, please follow the following requirements:
1. Annotate each line or key part of the input card, explaining its function, parameter meaning, and possible impact.
2. For each APP used in the input card, explain in detail its role in the current context based on the text content.
When generating an overall description, please follow the following requirements:
1. Briefly outline the main application use in this input card. If it is concrete simulation tasks, describe the grid, physical processes or equations, and boundary conditions of the input card.
2. What apps in MOOSE were mainly used for the input card and what effects were achieved.
Here is the documentation of the apps used in the input card, you can refer to the documentation to help you generate comments:
<Documentation>
{rag_info}
</Documentation>
"""

RAG_PROMPT = """Your task is to extract the app used from the input card of MOOSE. Please carefully read the following MOOSE input card content:
{inpcard}
To accurately extract the app being used, please carefully read the entire input card content. Search for identification or descriptive information related to the APP in the input card, especially 'type = '."""


def adjust_path(s: str):
    """
    调整路径，去除路径中的特殊字符，并替换为下划线。
    """
    substrings = ["E:/vscode/moose\\", "tutorials\\", "modules\\", "examples\\", "test\\tests\\", "unit\\files\\"]
    # 遍历子字符串列表，逐一替换
    for sub in substrings:
        s = s.replace(sub, "")
    s = s.replace("/", "_")
    s = s.replace("\\", "_")
    s = s.replace("//", "_")
    return s


def input_card_selector(state: InputCardWorkflowState, config: RunnableConfig):
    """
    该函数用于随机选择一个输入卡路径，并调整路径。
    通过调用random.choice函数，随机选择一个输入卡路径。
    该函数返回一个包含输入卡名称、内容和注释数量的字典。
    Args:
        state (InputCardWorkflowState): 输入卡工作流状态，包含输入卡路径、名称、内容和注释数量。

    Returns:
        dict: 包含输入卡名称、内容和注释数量的字典。
    """
    while True:
        selected_input_card = random.choice(state["input_card_path"])
        state["input_card_path"].remove(selected_input_card)
        print(f"---current input card: {selected_input_card}---")

        with open(selected_input_card, "r", encoding="utf-8") as file:
            inpcard_content = file.read()
            if len(inpcard_content.splitlines()) > 10:
                break
    selected_input_card = adjust_path(selected_input_card)
    if state.get("num_commented") is None:
        num_commented = 0
    else:
        num_commented = state["num_commented"] + 1
    return {"input_card_name": selected_input_card, "inpcard": inpcard_content, "num_commented": num_commented}


def rag(state: InputCardWorkflowState, config: RunnableConfig):
    """
    该函数用于从输入卡中提取应用程序名称。
    通过调用load_chat_model函数，使用预定义的RAG_PROMPT格式化输入卡内容。
    该函数返回一个包含应用程序名称的字典。
    """
    configuration = Configuration.from_runnable_config(config)
    if configuration.use_llm_rag:
        ### use llm to extract the app used in the input card
        model = load_chat_model(configuration.comment_rag_model).with_structured_output(RAGState)
        system_message = SystemMessage(content=RAG_PROMPT.format(inpcard=state["inpcard"]))
        response = model.invoke([system_message])
        app_list = response.app_used

    else:
        ### use code to extract the app used in the input card
        app_list = []
        lines = state["inpcard"].splitlines()
        for line in lines:
            line = line.replace(" type=", " type =")
            if " type =" in line:
                # 提取app名称，假设格式为 type = <appname>
                app_name = line.split(" type =")[-1].strip().split()[0]
                app_list.append(app_name)
    # find the documentation of the app used in the input card
    rag_info = ""
    for app in app_list:
        doc = state["dp_json"].get(app)
        if doc is not None:
            rag_info += f"# Here is the documentation of {app}\n"
            rag_info += doc
            rag_info += "\n\n"
    return {"rag_info": rag_info}


def writer(state: InputCardWorkflowState, config: RunnableConfig):
    """
    该函数用于生成输入卡的注释，分析输入卡内容并生成详细的注释和整体描述。
    通过调用load_chat_model函数，使用预定义的WRITER_PROMPT格式化输入卡内容。
    该函数返回一个包含整体描述和注释输入卡的字典。

    Args:
        state (InputCardWorkflowState): 输入卡工作流状态，包含输入卡路径、名称、内容和注释数量。

    Returns:
        dict: 包含整体描述和注释输入卡的字典。
    """
    configuration = Configuration.from_runnable_config(config)
    model = load_chat_model(configuration.comment_writer_model).with_structured_output(CommentState)
    system_message = SystemMessage(
        content=WRITER_PROMPT.format(
            inpcard=state["inpcard"], input_card_name=state["input_card_name"], rag_info=state["rag_info"]
        )
    )
    response = model.invoke([system_message])
    return {"overall_description": response.overall_description, "annotated_input_card": response.annotated_input_card}


def save_to_json(state: InputCardWorkflowState):
    """
    该函数用于将输入卡的注释和整体描述保存到JSON文件中。
    通过检查文件是否存在，如果存在则读取现有数据，否则创建新的输出数据。
    该函数返回一个包含输入卡名称、整体描述和注释输入卡的字典。

    Args:
        state (InputCardWorkflowState): 输入卡工作流状态，包含输入卡路径、名称、内容和注释数量。

    Returns:
        dict: 包含输入卡名称、整体描述和注释输入卡的字典。
    """

    # 检查文件是否存在，如果存在则读取现有数据
    if os.path.exists(COMMENT_PATH):
        with open(COMMENT_PATH, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    # 创建新的输出数据
    new_data = {
        "input_card_name": state["input_card_name"],
        "overall_description": state["overall_description"],
        "annotated_input_card": state["annotated_input_card"],
    }

    # 将新数据添加到现有数据中
    existing_data.append(new_data)

    # 将更新后的数据写回文件
    with open(COMMENT_PATH, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)

    # 也保存到txt文件
    text = combine_code_with_description(state["overall_description"], state["annotated_input_card"])
    text_path = COMMENT_PATH.replace(".json", "/" + state["input_card_name"])
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Input card data added to {text_path}")
    # input_card_path = state["input_card_path"].remove(state["input_card_name"])
    if state["num_commented"] % save_every == 0:
        uncommented_input_card_path = ""
        for path in state["input_card_path"]:
            uncommented_input_card_path += path + "\n"
        with open(input_card_path, "w", encoding="utf-8") as file:
            file.write(uncommented_input_card_path)
        print(f"Rewrite the uncommented input card path to {input_card_path}")
    return


def route_comment(state: InputCardWorkflowState):
    if state["input_card_path"] == [] or state["num_commented"] >= state["max_commented"]:
        return "END"
    else:
        return "CONTINUE"


# 构建工作流程
from langgraph.graph import StateGraph, START, END

workflow = StateGraph(InputCardWorkflowState)

workflow = StateGraph(InputCardWorkflowState)
workflow.add_node("input_card_selector", input_card_selector)
workflow.add_node("rag", rag)
workflow.add_node("writer", writer)
workflow.add_node("save_to_json", save_to_json)

workflow.add_edge(START, "input_card_selector")
workflow.add_conditional_edges("input_card_selector", route_comment, {"CONTINUE": "rag", "END": END})
workflow.add_edge("rag", "writer")
workflow.add_edge("writer", "save_to_json")
workflow.add_edge("save_to_json", "input_card_selector")

# 使用示例
if __name__ == "__main__":
    with open(input_card_path, "r", encoding="utf-8") as file:
        input_card_list = [line.strip() for line in file.readlines()]
    with open(dp_json_path, "r", encoding="utf-8") as file:
        dp_json = json.load(file)
    app = workflow.compile()
    result = app.invoke(
        {"input_card_path": input_card_list, "dp_json": dp_json, "max_commented": 400}, {"recursion_limit": 10000}
    )
    # print(result)
