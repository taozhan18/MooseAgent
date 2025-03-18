"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

import asyncio
import json
import sys
import os
from dotenv import load_dotenv
import subprocess

load_dotenv()
from langgraph.checkpoint.memory import MemorySaver

# sys.path.append("../")
sys.path.append(r"/home/zt/workspace/MooseAgent/src")
from tqdm import tqdm
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from langgraph.prebuilt import ToolNode
from langchain.tools.retriever import create_retriever_tool
from langchain_community.vectorstores import Chroma, FAISS
from mooseagent.configuration import Configuration
from langchain_openai import OpenAIEmbeddings
from mooseagent.utils import (
    BGE_M3_EmbeddingFunction,
    tran_dicts_to_str,
    extract_files_and_descriptions,
    extract_sub_tasks,
)
from mooseagent.state1 import (
    FlowState,
    RAGState,
    ReviewWriterState,
    InpcardState,
    OneFileState,
    ExtracterFileState,
    ExtracterSubtaskState,
    SubtaskState,
)
from mooseagent.utils import load_chat_model
from mooseagent.prompts1 import (
    SYSTEM_ALIGNMENT_PROMPT,
    HUMAN_ALIGNMENT_PROMPT,
    SYSTEM_WRITER_PROMPT,
    SYSTEM_REVIEW_WRITER_PROMPT,
    HUMAN_WRITER_PROMPT,
    HUMAN_REVIEW_WRITER_PROMPT,
    SYSTEM_RAG_PROMPT,
    SYSTEM_ARCHITECT_PROMPT,
    HUMAN_ARCHITECT_PROMPT,
)
from mooseagent.write_module import bulid_writer_module
from langgraph.constants import Send

config = RunnableConfig()
configuration = Configuration.from_runnable_config(config)
embedding_function = OpenAIEmbeddings() if configuration.embedding_function == "OPENAI" else BGE_M3_EmbeddingFunction()
batch_size = configuration.batch_size
top_k = configuration.top_k
json_file = configuration.rag_json_path
try:
    vectordb_input = FAISS.load_local(
        configuration.input_database_path, embedding_function, allow_dangerous_deserialization=True
    )
    retriever_input = vectordb_input.as_retriever(search_type="similarity", search_kwargs={"k": top_k})
    vectordb_dp = FAISS.load_local(
        configuration.dp_database_path, embedding_function, allow_dangerous_deserialization=True
    )
    retriever_dp = vectordb_dp.as_retriever(search_type="similarity", search_kwargs={"k": top_k})
except Exception as e:
    print(f"Error loading vector database: {e}")
    sys.exit(1)
RAG_input = bulid_writer_module(
    retriever_input,
    "find_similar_MOOSE_input_card",
    "find similar MOOSE simulation input card in the database with a lot of MOOSE simulation cases.",
)
RAG_dp = bulid_writer_module(
    retriever_dp,
    "find_relevant_MOOSE_documentation",
    "find relevant application's documentation of moose in all the moose application documentation database",
)
# retriever_tool = create_retriever_tool(
#     retriever,
#     "retrieve_moose_case",
#     "Find MOOSE simulation cases that are similar to the input case.",
# )
# tools = [retriever_tool]


def align_simulation_description(state: FlowState, config: RunnableConfig):
    """Align the simulation description
    Args:
        state (FlowState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.
    Returns:
        dict: A dictionary containing the model's response
    """

    configuration = Configuration.from_runnable_config(config)
    alignment = load_chat_model(configuration.alignment_model)
    # similar_cases = retriever.invoke(state["detailed_description"])
    feedback = ""
    while feedback != "yes":
        human_message_alignment = HUMAN_ALIGNMENT_PROMPT.format(requirement=state["requirement"], feedback=feedback)
        alignment_reply = alignment.invoke(
            [
                SystemMessage(content=SYSTEM_ALIGNMENT_PROMPT),
                HumanMessage(content=human_message_alignment),
            ]
        )
        print(alignment_reply.content)
        feedback = input(
            "---Please confirm if the above simulation description meets your requirements. If pass, please input 'yes'. If not, please input your feedback.---\nYour feedback: "
        )
    # file_list = extract_files_and_descriptions(alignment_reply.content)  # 提取文件名和描述
    # print("---The final simulation task is:---")
    # print(alignment_reply.detailed_description)
    extracter_file = load_chat_model(configuration.extracter_model).with_structured_output(ExtracterFileState)
    extracter_reply = extracter_file.invoke(
        [
            SystemMessage(
                content="You are a helpful assistant that can extract a list of file name and its detailed description from the text. You should never change the file name and its detailed description."
            ),
            HumanMessage(content=alignment_reply.content),
        ]
    )
    print("---Now I will generate the architect of the input card and conduct the simulation.---")
    return {"file_list": extracter_reply.file_list}
    # Kick off section writing in parallel via Send() API for any sections that do not require research


def route_align(state: FlowState):
    return [
        Send(
            "architect_input_card",
            {
                "description": file.description,
                "file_name": file.file_name,
                "dp_json": state["dp_json"],
            },
        )
        for file in state["file_list"]
    ]


def architect_input_card(state: OneFileState, config: RunnableConfig):
    """Generate the architect of the input card
    Args:
        state (OneFileState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.
    Returns:
        dict: A dictionary containing the model's response
    """
    configuration = Configuration.from_runnable_config(config)
    print(f"---ARCHITECT INPUT CARD---")
    similar_cases = retriever_input.invoke(state["description"])
    human_message_architect = HUMAN_ARCHITECT_PROMPT.format(requirement=state["description"], examples=similar_cases)
    architect = load_chat_model(configuration.architect_model)
    architect_reply = architect.invoke(
        [
            SystemMessage(content=SYSTEM_ARCHITECT_PROMPT),
            HumanMessage(content=human_message_architect),
        ]
    )
    extracter_subtask = load_chat_model(configuration.extracter_model).with_structured_output(ExtracterSubtaskState)
    extracter_reply = extracter_subtask.invoke(
        [
            SystemMessage(
                content="You are a helpful assistant that can extract a list of sub-tasks from the text. Each sub-task has a name, a retrieve value, and a detailed description. You should never change the sub-task name, retrieve value, and detailed description."
            ),
            HumanMessage(content=architect_reply.content),
        ]
    )
    print(architect_reply.content)
    sub_tasks = extracter_reply.sub_tasks
    return {"sub_tasks": sub_tasks}


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
            feedback += f"{app} is not found in the documentation, please change another application.\n"
    return feedback


def write_module(module: SubtaskState, dp_json: dict):
    """Write the module of the input card
    Args:
        module (str): The module to write.
    Returns:
        dict: A dictionary containing the model's response
    """
    module_name = module.name
    retrieve = module.retrieve
    module_description = module.description
    configuration = Configuration.from_runnable_config(config)
    writer = load_chat_model(configuration.writer_model)
    print(f"---WRITE MODULE---")
    if retrieve:
        print(f"---FIND SIMILAR MOOSE INPUT CARD---")
        RAG_input_messages = RAG_input.invoke({"question": module_description})
        similar_cases = RAG_input_messages["final_result"]
        print(f"---FIND RELATED MOOSE DOCUMENTATION---")
        RAG_dp_messages = RAG_dp.invoke({"question": module_description})
        similar_dp = RAG_dp_messages["final_result"]
    else:
        similar_cases = ""
        similar_dp = ""
    feedback = ""
    while True:
        human_message_write = HUMAN_WRITER_PROMPT.format(
            module_name=module_name,
            requirement=module_description,
            similar_cases=similar_cases,
            similar_dp=similar_dp,
            feedback=feedback,
        )

        write_reply = writer.invoke(
            [
                SystemMessage(content=SYSTEM_WRITER_PROMPT),
                HumanMessage(content=human_message_write),
            ]
        )
        feedback = check_app(write_reply.content, dp_json)
        if feedback == "":
            break
    print(f"---WRITE MODULE DONE---")
    return write_reply.content


# async def write_input_card(state: OneFileState, config: RunnableConfig):
#     """Generate the subtask of the input card
#     Args:
#         state (OneFileState): The current state of the conversation.
#         config (RunnableConfig): Configuration for the model run.
#     Returns:
#         dict: A dictionary containing the model's response
#     """
#     configuration = Configuration.from_runnable_config(config)
#     print(f"---WRITE INPUT CARD---")
#     tasks = [write_module(module, state["dp_json"]) for module in state["sub_tasks"]]
#     inpcards = await asyncio.gather(*tasks)
#     inpcard_str = "\n".join([inpcard["inpcard"] for inpcard in inpcards])
#     print(f"---WRITE INPUT CARD DONE---")
#     return {"inpcard": inpcard_str}


def write_input_card(state: OneFileState, config: RunnableConfig):
    """Generate the subtask of the input card
    Args:
        state (OneFileState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.
    Returns:
        dict: A dictionary containing the model's response
    """
    configuration = Configuration.from_runnable_config(config)
    print(f"---WRITE INPUT CARD---")
    codes = []
    for task in state["sub_tasks"]:
        code = write_module(task, state["dp_json"])
        codes.append(code)
    inpcard_str = "\n".join(codes)
    print(f"---WRITE INPUT CARD DONE---")
    return {"inpcard": inpcard_str}


def review_inpcard(state: FlowState, config: RunnableConfig):
    """Review the generated inpcard for quality and completeness.

    Args:
        state (InpcardState): The current state of the inpcard.
        config (RunnableConfig): Configuration for the model run.

    Returns:
        dict: A dictionary containing the review results.
    """
    print(f"---REVIEW INPCARD---")
    inpcard = state["inpcard"]
    inpcard_content = inpcard.inpcard
    # find the documentation of the app used in the input card
    app_list = []
    lines = inpcard_content.splitlines()
    for line in lines:
        line = line.replace(" type=", " type =")
        if " type =" in line:
            # 提取app名称，假设格式为 type = <appname>
            app_name = line.split(" type =")[-1].strip().split()[0]
            app_list.append(app_name)
    rag_info = ""
    for app in app_list:
        doc = state["dp_json"].get(app)
        if doc is not None:
            rag_info += f"# Here is the documentation of {app}\n"
            rag_info += doc
            rag_info += "\n\n"
    similar_cases_strs = tran_dicts_to_str(state["similar_cases"])
    human_message_review = HUMAN_REVIEW_WRITER_PROMPT.format(
        overall_description=state["detailed_description"],
        inpcard=inpcard_content,
        similar_case=similar_cases_strs,
        documentation=rag_info,
        run_result=state["run_result"],
    )

    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    review_writer = load_chat_model(configuration.review_writer_model).with_structured_output(ReviewWriterState)
    review_reply = review_writer.invoke(
        [
            SystemMessage(content=SYSTEM_REVIEW_WRITER_PROMPT),
            HumanMessage(content=human_message_review),
        ]
    )
    is_pass = review_reply.grade
    feedback = review_reply.feedback
    print(f"---REVIEW INPCARD DONE---")
    return {"grade": is_pass, "feedback": feedback}


def route_inpcard(state: FlowState):
    """Determine the next node based on the model's output.

    This function checks if the model's last message contains tool calls.

    Args:
        state (State): The current state of the conversation.

    Returns:
        str: The name of the next node to call ("__end__" or "tools").
    """
    return state["grade"]


def run_inpcard(state: FlowState, config: RunnableConfig):
    configuration = Configuration.from_runnable_config(config)
    """Save the generated inpcard to a file."""
    inpcard = state["inpcard"]
    with open(os.path.join(configuration.save_dir, inpcard.name), "w", encoding="utf-8") as f:
        f.write(inpcard.inpcard)
    print(f"Inpcard saved to {inpcard.name}")
    """Run the moose simulation."""
    if os.path.exists(os.path.join(configuration.MOOSE_DIR)):
        print(f"Running moose with {inpcard.name}")
        command = [
            "mpiexec",
            "-n",
            str(configuration.mpi),
            configuration.MOOSE_DIR,
            "-i",
            os.path.join(configuration.save_dir, inpcard.name),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        # 打印输出
        if result.stderr == "":
            print("SUCCESS:")
            print(result.stdout)
            return {"run_result": "success"}
        else:
            print("ERROR:")
            print(result.stderr)
            return {"run_result": result.stderr}
    else:
        print(f"Moose directory {configuration.MOOSE_DIR} does not exist.")
        return {"run_result": "success"}


def route_run_inpcard(state: FlowState):
    """Determine the next node based on the model's output.

    This function checks if the model's last message contains tool calls.

    Args:
        state (State): The current state of the conversation.
    """
    if state["run_result"] == "success":
        return "success"
    else:
        return "fail"


# Build workflow
architect_builder = StateGraph(FlowState)  # v, input=ArchitectInputState, output=ArchitectOutputState)

# Add the nodes
architect_builder.add_node("align_simulation_description", align_simulation_description)
architect_builder.add_node("architect_input_card", architect_input_card)
architect_builder.add_node("write_input_card", write_input_card)
architect_builder.add_node("review_inpcard", review_inpcard)
architect_builder.add_node("run_inpcard", run_inpcard)
# Add edges to connect nodes
architect_builder.add_edge(START, "align_simulation_description")
architect_builder.add_conditional_edges("align_simulation_description", route_align, ["architect_input_card"])
architect_builder.add_edge("architect_input_card", "write_input_card")
architect_builder.add_edge("write_input_card", "review_inpcard")
architect_builder.add_conditional_edges(
    "review_inpcard",
    route_inpcard,
    {  # Name returned by route_joke : Name of next node to visit
        "pass": "run_inpcard",
        "fail": END,
    },
)
architect_builder.add_conditional_edges(
    "run_inpcard",
    route_run_inpcard,
    {  # Name returned by route_joke : Name of next node to visit
        "success": END,
        "fail": "review_inpcard",
    },
)
memory = MemorySaver()
graph = architect_builder.compile(checkpointer=memory)
if __name__ == "__main__":
    sys.path.append("/home/zt/workspace/MooseAgent/src/")
    config = {"configurable": {"thread_id": "1"}}
    dp_json_path = "/home/zt/workspace/MooseAgent/src/database/dp.json"
    with open(dp_json_path, "r", encoding="utf-8") as file:
        dp_json = json.load(file)

    def stream_graph_updates(user_input: str, dp_json: dict):
        for event in graph.stream({"requirement": user_input, "dp_json": dp_json}, config=config):
            for value in event.values():
                print(value)

    topic = """
    A rectangular plate (2 m × 1 m) is fixed along the left edge and subjected to a uniform tensile stress of 5 MPa on the right edge. The material is linear elastic with Young’s modulus E = 200 GPa and Poisson’s ratio ν = 0.3. The goal is to compute the stress and strain fields in the plate and output the maximum principal stress and strain.
    """

    # 运行异步主程序
    # asyncio.run(graph.ainvoke({"requirement": topic, "dp_json": dp_json}, config=config))
    # graph.invoke({"requirement": topic, "dp_json": dp_json}, config=config)
    stream_graph_updates(topic, dp_json)
