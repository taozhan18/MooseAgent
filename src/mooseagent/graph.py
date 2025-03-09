"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

import sys
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import MemorySaver

sys.path.append("../")
from datetime import datetime, timezone
from typing import Dict, List, Literal, cast

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from langgraph.prebuilt import ToolNode

from mooseagent.configuration import Configuration
from mooseagent.state import (
    ArchitectState,
    ArchitectOutputState,
    ReviewArchitectState,
    ReviewWriterState,
    WriterState,
    InpcardState,
)

from mooseagent.self_rag.graph import RAG
from mooseagent.utils import load_chat_model, tran_list_to_str, combine_code_with_description
from mooseagent.prompts import (
    SYSTEM_ARCHITECT_PROMPT,
    SYSTEM_REVIEW_ARCHITECT_PROMPT,
    SYSTEM_WRITER_PROMPT,
    SYSTEM_REVIEW_WRITER_PROMPT,
    SYSTEM_REPORT_PROMPT,
    HUMAN_ARCHITECT_PROMPT,
    HUMAN_REVIEW_ARCHITECT_PROMPT,
    HUMAN_WRITER_PROMPT,
    HUMAN_REVIEW_WRITER_PROMPT,
    HUMAN_REPORT_PROMPT,
)
from dotenv import load_dotenv

load_dotenv()
# Define the function that calls the model


def generate_architect(state: ArchitectState, config: RunnableConfig):
    """Generate the architect of inpcard
    Args:
        state (ArchitectState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.
    Returns:
        dict: A dictionary containing the model's response
    """

    # input
    requirement = state["requirement"]
    feedback = state["feedback"] if state.get("feedback") else ""

    # Get configuration
    configuration = Configuration.from_runnable_config(config)

    architect = load_chat_model(configuration.architect_model).with_structured_output(ArchitectOutputState)
    human_message_architect = HUMAN_ARCHITECT_PROMPT.format(requirement=requirement, feedback=feedback)

    architect_reply = architect.invoke(
        [
            SystemMessage(content=SYSTEM_ARCHITECT_PROMPT),
            HumanMessage(content=human_message_architect),
        ]
    )

    return {
        "overall_description": architect_reply.overall_description,
        "structured_requirements": architect_reply.structured_requirements,
        "retrieve_tasks": architect_reply.retrieval_tasks,
    }


def review_architect(state: ArchitectState, config: RunnableConfig):
    """Review the architect of inpcard
    Args:
        state (ArchitectState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.
    Returns:
        dict: A dictionary containing the model's response
    """
    human_message_review = HUMAN_REVIEW_ARCHITECT_PROMPT.format(
        requirement=state["requirement"],
        structured_requirements=state["structured_requirements"],
        retrieve_tasks=state["retrieve_tasks"],
    )

    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    review_architect = load_chat_model(configuration.review_architect_model).with_structured_output(
        ReviewArchitectState
    )
    review_reply = review_architect.invoke(
        [
            SystemMessage(content=SYSTEM_REVIEW_ARCHITECT_PROMPT),
            HumanMessage(content=human_message_review),
        ]
    )
    is_pass = review_reply.grade_architect
    feedback = review_reply.feedback_architect
    return {"grade_architect": is_pass, "feedback_architect": feedback}


def route_architect(state: ArchitectState):
    """Determine the next node based on the model's output.

    This function checks if the model's last message contains tool calls.

    Args:
        state (State): The current state of the conversation.

    Returns:
        str: The name of the next node to call ("__end__" or "tools").
    """
    return state["grade_architect"]


# async def query_module(module):
#     query = f"please find information how to achieve the following description in {module.name}: {module.description}"
#     return await RAG.invoke({"question": query})  # Run in a separate thread
def query_module(task):
    """同步查询每个模块的信息"""
    query = f"please find information how to achieve the following description in {task}"
    results = []
    # 使用同步调用
    for event in RAG.stream({"question": query}):
        for value in event.values():
            results.append(value)
    return results[-1] if results else None  # 返回最后一个结果


def generate_inpcard(state: WriterState, config: RunnableConfig):
    """Generate the inpcard based on the architect's design.

    Args:
        state (ArchitectState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.

    Returns:
        dict: A dictionary containing the generated inpcard details.
    """
    retrieve_tasks = state["retrieve_tasks"]

    docs = []
    conbine = ""
    for task in retrieve_tasks:
        result = query_module(task)
        conbine += f"The task is: {task}\nThe result is: {result}\n\n"
        if result is not None:
            docs.append(result)
    feedback = state["feedback_inpcard"] if state.get("feedback_inpcard") else ""
    human_message_inpcard = HUMAN_WRITER_PROMPT.format(
        structured_requirements=state["structured_requirements"],
        documentation=state["documentation"],
        feedback=feedback,
    )

    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    generator = load_chat_model(configuration.generate_model).with_structured_output(InpcardState)
    inpcard_reply = generator.invoke(
        [
            SystemMessage(content=SYSTEM_WRITER_PROMPT),
            HumanMessage(content=human_message_inpcard),
        ]
    )
    return {"inpcard": inpcard_reply, "documentation": docs}


def review_inpcard(state: WriterState, config: RunnableConfig):
    """Review the generated inpcard for quality and completeness.

    Args:
        state (InpcardState): The current state of the inpcard.
        config (RunnableConfig): Configuration for the model run.

    Returns:
        dict: A dictionary containing the review results.
    """
    inpcard_details = state["inpcard"]
    human_message_review = HUMAN_REVIEW_WRITER_PROMPT.format(
        structured_requirements=state["structured_requirements"],
        documentation=state["documentation"],
        inpcard=inpcard_details.inpcard,
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
    return {"grade_inpcard": is_pass, "feedback_inpcard": feedback}


def route_inpcard(state: WriterState):
    """Determine the next node based on the model's output.

    This function checks if the model's last message contains tool calls.

    Args:
        state (State): The current state of the conversation.

    Returns:
        str: The name of the next node to call ("__end__" or "tools").
    """
    return state["grade_inpcard"]


def save_inpcard(state: WriterState):
    """Save the generated inpcard to a file."""
    inpcard_details = state["inpcard"]
    with open(inpcard_details.name, "w", encoding="utf-8") as f:
        f.write(inpcard_details.inpcard)
    print(f"Inpcard saved to {inpcard_details.name}")


def run_moose(state: WriterState):
    """Run the moose simulation."""
    inpcard_details = state["inpcard"]
    print(f"Running moose with {inpcard_details.name}")


# Build workflow
architect_builder = StateGraph(ArchitectState)  # v, input=ArchitectInputState, output=ArchitectOutputState)

# Add the nodes
architect_builder.add_node("architect", generate_architect)
architect_builder.add_node("review_architect", review_architect)
architect_builder.add_node("generate_inpcard", generate_inpcard)
architect_builder.add_node("review_inpcard", review_inpcard)
architect_builder.add_node("save_inpcard", save_inpcard)
architect_builder.add_node("run_moose", run_moose)
# Add edges to connect nodes
architect_builder.add_edge(START, "architect")
architect_builder.add_edge("architect", "review_architect")
architect_builder.add_conditional_edges(
    "review_architect",
    route_architect,
    {  # Name returned by route_joke : Name of next node to visit
        "pass": "generate_inpcard",
        "fail": "architect",
    },
)
architect_builder.add_edge("generate_inpcard", "review_inpcard")
architect_builder.add_conditional_edges(
    "review_inpcard",
    route_inpcard,
    {  # Name returned by route_joke : Name of next node to visit
        "pass": "save_inpcard",
        "fail": "generate_inpcard",
    },
)
architect_builder.add_edge("save_inpcard", "run_moose")
architect_builder.add_edge("run_moose", END)
memory = MemorySaver()
graph = architect_builder.compile(checkpointer=memory)
if __name__ == "__main__":
    sys.path.append("E:/vscode/python/Agent/langgraph_learning/mooseagent/src")
    config = {"configurable": {"thread_id": "1"}}

    def stream_graph_updates(user_input: str):
        for event in graph.stream({"requirement": user_input}, config=config):
            for value in event.values():
                print(value)

    topic = """
    Perform steady-state thermomechanical calculations for a Pressurized Water Reactor (PWR) fuel rod. The setup is as follows:
    Geometric Conditions: The fuel pellet is made of UO₂ ceramic with a diameter of 8.192 mm; The cladding is made of Zr4 alloy with an inner diameter of 8.36 mm, an outer diameter of 9.5 mm, and a height of 3657 mm.
    Boundary Conditions: Adiabatic boundary conditions are applied at the top and bottom; The right side is set as an isothermal boundary condition, with an inlet temperature of 293 K and an outlet temperature of 333 K. The temperature in between is linearly interpolated; The gap between the fuel pellet and the cladding is set with an internal pressure of 2 MPa.
    Source Term: The volume heat generation rate in the fuel pellet is set as a cosine distribution along the axial direction and is uniform in the radial direction; The power is 0 at the top and bottom, and reaches a maximum of 2×10⁷ kW/m³ at the center.
    Material Properties: Fuel Pellet Thermal Conductivity: 1/(11.8+0.0238*T) + 8.775*1e-13*T^3 W/(cm·°C), Fuel Pellet Thermal Expansion Coefficient: Isotropic, with the formula: 7.107e-6+5.16e-9*T+3.42e-13*T^2(°C^(-1)); Cladding Thermal Conductivity: 0.15W/(cm·°C); Cladding Thermal Expansion Coefficient: 5.5e-6(°C^(-1)). In all formulas, T represents temperature in °C.
    """

    # 运行异步主程序
    stream_graph_updates(topic)
