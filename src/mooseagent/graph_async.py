"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

import sys
from langchain_core.prompts import ChatPromptTemplate
import asyncio

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
    ModulesState,
    ArchitectInputState,
    ArchitectOutputState,
    ReviewState,
    InpcardState,
    WriterState,
)

from mooseagent.self_rag.graph import RAG
from mooseagent.utils import load_chat_model, tran_list_to_str, combine_code_with_description
from mooseagent.prompts import (
    HUMAN_ARCHITECT_PROMPT,
    HUMAN_REVIEW1_PROMPT,
    HUMAN_INPCARD_PROMPT,
    HUMAN_REVIEW2_PROMPT,
    SYSTEM_PROMPT,
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
    topic = state["topic"]
    feedback = state["feedback"] if state.get("feedback") else ""
    # docs = RAG.invoke({"question": topic})

    # Get configuration
    configuration = Configuration.from_runnable_config(config)

    architect = load_chat_model(configuration.architect_model).with_structured_output(ModulesState)
    human_message_architect = HUMAN_ARCHITECT_PROMPT.format(topic=topic, feedback=feedback)

    architect_reply = architect.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_message_architect),
        ]
    )

    return {"modules": architect_reply}


def review_architect(state: ArchitectState, config: RunnableConfig):
    """Review the architect of inpcard
    Args:
        state (ArchitectState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.
    Returns:
        dict: A dictionary containing the model's response
    """
    topic = state["topic"]
    modules = state["modules"]
    # docs = state["documents"]
    overall_architect = modules.overall_architect
    modules_description = tran_list_to_str(modules.modules_description)

    human_message_review = HUMAN_REVIEW1_PROMPT.format(
        topic=topic, overall_architect=overall_architect, modules=modules_description
    )

    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    review1 = load_chat_model(configuration.review1_model).with_structured_output(ReviewState)
    review_reply = review1.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_message_review),
        ]
    )
    is_pass = review_reply.grade
    feedback = review_reply.feedback
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
async def query_module(module):
    """异步查询每个模块的信息"""
    query = f"please find information how to achieve the following description in {module.name}: {module.description}"
    results = []
    # 需要将RAG转换为异步流式调用
    async for event in RAG.astream({"question": query}):
        for value in event.values():
            results.append(value)
    return results[-1] if results else None  # 返回最后一个结果


async def generate_inpcard(state: WriterState, config: RunnableConfig):
    """Generate the inpcard based on the architect's design.

    Args:
        state (ArchitectState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.

    Returns:
        dict: A dictionary containing the generated inpcard details.
    """
    modules = state["modules"]
    overall_architect = modules.overall_architect
    modules_description = modules.modules_description

    tasks = [query_module(module) for module in modules_description]
    docs = await asyncio.gather(*tasks)
    docs = [doc for doc in docs if doc is not None]  # 过滤掉None结果
    # modules_description = tran_list_to_str(modules.modules_description)
    # docs = RAG.invoke({"question": combine_code_with_description(overall_architect, modules_description)})
    feedback = state["feedback_inpcard"] if state.get("feedback_inpcard") else ""
    human_message_inpcard = HUMAN_INPCARD_PROMPT.format(
        overall_architect=overall_architect, modules=modules_description, feedback=feedback, documents=docs
    )

    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    generator = load_chat_model(configuration.generate_model).with_structured_output(InpcardState)
    inpcard_reply = generator.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_message_inpcard),
        ]
    )
    return {"inpcard": inpcard_reply, "documents_inpcard": docs}


def review_inpcard(state: WriterState, config: RunnableConfig):
    """Review the generated inpcard for quality and completeness.

    Args:
        state (InpcardState): The current state of the inpcard.
        config (RunnableConfig): Configuration for the model run.

    Returns:
        dict: A dictionary containing the review results.
    """
    inpcard_details = state["inpcard"]
    modules = state["modules"]
    docs = state["documents_inpcard"]
    overall_architect = modules.overall_architect
    modules_description = tran_list_to_str(modules.modules_description)
    human_message_review = HUMAN_REVIEW2_PROMPT.format(
        inpcard=inpcard_details, overall_architect=overall_architect, modules=modules_description, documents=docs
    )

    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    review2 = load_chat_model(configuration.review2_model).with_structured_output(ReviewState)
    review_reply = review2.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
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
    modules = state["modules"]
    overall_architect = modules.overall_architect
    with open(inpcard_details.name, "w", encoding="utf-8") as f:
        f.write(combine_code_with_description(overall_architect, inpcard_details.inpcard))
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
graph = architect_builder.compile()
if __name__ == "__main__":
    sys.path.append("E:/vscode/python/Agent/langgraph_learning/mooseagent/src")

    async def stream_graph_updates(user_input: str):
        async for event in graph.astream({"topic": user_input}):
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
    asyncio.run(stream_graph_updates(topic))
