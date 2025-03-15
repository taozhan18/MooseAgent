"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

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
from mooseagent.utils import BGE_M3_EmbeddingFunction, tran_dicts_to_str
from mooseagent.state1 import FlowState, AlignmentState, RAGState, ReviewWriterState, InpcardState
from mooseagent.utils import load_chat_model
from mooseagent.prompts1 import (
    SYSTEM_WRITER_PROMPT,
    SYSTEM_REVIEW_WRITER_PROMPT,
    HUMAN_WRITER_PROMPT,
    HUMAN_REVIEW_WRITER_PROMPT,
    ALIGNMENT_PROMPT,
    SYSTEM_RAG_PROMPT,
)

config = RunnableConfig()
configuration = Configuration.from_runnable_config(config)
embedding_function = OpenAIEmbeddings() if configuration.embedding_function == "OPENAI" else BGE_M3_EmbeddingFunction()
batch_size = configuration.batch_size
top_k = configuration.top_k
json_file = configuration.rag_json_path
try:
    vectordb = FAISS.load_local(
        configuration.PERSIST_DIRECTORY, embedding_function, allow_dangerous_deserialization=True
    )
    retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": top_k})
except Exception as e:
    print(f"Error loading vector database: {e}")
    sys.exit(1)
retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_moose_case",
    "Find MOOSE simulation cases that are similar to the input case.",
)
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
    alignment = load_chat_model(configuration.alignment_model).with_structured_output(AlignmentState)
    feedback = ""
    while feedback != "yes":
        system_message_alignment = ALIGNMENT_PROMPT.format(requirement=state["requirement"], feedback=feedback)
        alignment_reply = alignment.invoke(
            [
                SystemMessage(content=system_message_alignment),
            ]
        )
        print(alignment_reply.detailed_description)
        feedback = input(
            "---Please confirm if the above simulation description meets your requirements. If pass, please input 'yes'. If not, please input your feedback.---\n"
        )
    print("---The final simulation task is:---")
    print(alignment_reply.detailed_description)
    print("---Now I will generate the architect of the input card and conduct the simulation.---")
    return {"detailed_description": alignment_reply.detailed_description}


def rag_info(state: FlowState, config: RunnableConfig):
    """RAG the information of the simulation task
    Args:
        state (FlowState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.
    Returns:
        dict: A dictionary containing the model's response
    """
    configuration = Configuration.from_runnable_config(config)
    print(f"---RETRIEVE---")
    # similar_case = retriever.invoke(state["overall_description"])
    system_message_rag = SYSTEM_RAG_PROMPT.format(requirement=state["detailed_description"])
    # rag_agent = load_chat_model(configuration.rag_model, temperature=0.0)  # .with_structured_output(RAGState)
    # rag_agent = rag_agent.bind_tools(tools)
    similar_cases = retriever.invoke(state["detailed_description"])
    # [
    #         SystemMessage(content=system_message_rag),
    #         HumanMessage(content=state["requirement"]),
    #     ]
    # )
    print(f"---RETRIEVE DONE---")
    return {"similar_cases": similar_cases}


def generate_inpcard(state: FlowState, config: RunnableConfig):
    """Generate the inpcard based on the architect's design.

    Args:
        state (ArchitectState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.

    Returns:
        dict: A dictionary containing the generated inpcard details.
    """
    print(f"---GENERATE INPCARD---")
    similar_cases = state["similar_cases"]
    similar_cases_strs = tran_dicts_to_str(similar_cases)

    detailed_description = state["detailed_description"]
    feedback = state["feedback"] if state.get("feedback") else ""
    previous_inpcard = state["inpcard"].inpcard if state.get("inpcard") else ""
    human_message_inpcard = HUMAN_WRITER_PROMPT.format(
        overall_description=detailed_description,
        similar_case=similar_cases_strs,
        previous_inpcard=previous_inpcard,
        feedback=feedback,
    )

    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    generator = load_chat_model(configuration.writer_model).with_structured_output(InpcardState)
    inpcard_reply = generator.invoke(
        [
            SystemMessage(content=SYSTEM_WRITER_PROMPT),
            HumanMessage(content=human_message_inpcard),
        ]
    )
    print(f"---GENERATE INPCARD DONE---")

    """Save the generated inpcard to a file."""
    with open(os.path.join(configuration.save_dir, inpcard_reply.name), "w", encoding="utf-8") as f:
        f.write(inpcard_reply.inpcard)
    print(f"Inpcard saved to {inpcard_reply.name}")

    return {"inpcard": inpcard_reply, "run_result": ""}


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
architect_builder.add_node("rag_info", rag_info)
architect_builder.add_node("generate_inpcard", generate_inpcard)
architect_builder.add_node("review_inpcard", review_inpcard)
architect_builder.add_node("run_inpcard", run_inpcard)
# Add edges to connect nodes
architect_builder.add_edge(START, "align_simulation_description")
architect_builder.add_edge("align_simulation_description", "rag_info")
architect_builder.add_edge("rag_info", "generate_inpcard")
architect_builder.add_edge("generate_inpcard", "review_inpcard")
architect_builder.add_conditional_edges(
    "review_inpcard",
    route_inpcard,
    {  # Name returned by route_joke : Name of next node to visit
        "pass": "run_inpcard",
        "fail": "generate_inpcard",
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
    # graph.invoke({"requirement": topic, "dp_json": dp_json}, config=config)
    stream_graph_updates(topic, dp_json)
