"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

import sys

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


from mooseagent.utils import load_chat_model, tran_list_to_str
from mooseagent.prompts import (
    SYSTEM_ARCHITECT_PROMPT,
    SYSTEM_REVIEW1_PROMPT,
    SYSTEM_INPCARD_PROMPT,
    SYSTEM_REVIEW2_PROMPT,
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

    # Get configuration
    configuration = Configuration.from_runnable_config(config)

    architect = load_chat_model(configuration.architect_model).with_structured_output(ModulesState)
    system_message_architect = SYSTEM_ARCHITECT_PROMPT.format(topic=topic, feedback=feedback)

    architect_reply = architect.invoke(
        [
            SystemMessage(content=system_message_architect),
            HumanMessage(content=""),
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
    overall_architect = modules.overall_architect
    modules_description = tran_list_to_str(modules.modules_description)
    system_message_review = SYSTEM_REVIEW1_PROMPT.format(
        topic=topic, overall_architect=overall_architect, modules=modules_description
    )

    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    review1 = load_chat_model(configuration.review1_model).with_structured_output(ReviewState)
    review_reply = review1.invoke(
        [
            SystemMessage(content=system_message_review),
            HumanMessage(content=""),
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


def generate_inpcard(state: WriterState, config: RunnableConfig):
    """Generate the inpcard based on the architect's design.

    Args:
        state (ArchitectState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.

    Returns:
        dict: A dictionary containing the generated inpcard details.
    """
    modules = state["modules"]
    overall_architect = modules.overall_architect
    modules_description = tran_list_to_str(modules.modules_description)
    feedback = state["feedback_inpcard"] if state.get("feedback_inpcard") else ""
    system_message_inpcard = SYSTEM_INPCARD_PROMPT.format(
        overall_architect=overall_architect, modules=modules_description, feedback=feedback
    )

    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    generator = load_chat_model(configuration.generate_model).with_structured_output(InpcardState)
    inpcard_reply = generator.invoke(
        [
            SystemMessage(content=system_message_inpcard),
            HumanMessage(content=""),
        ]
    )
    return {"inpcard": inpcard_reply}


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
    overall_architect = modules.overall_architect
    modules_description = tran_list_to_str(modules.modules_description)
    system_message_review = SYSTEM_REVIEW2_PROMPT.format(
        inpcard=inpcard_details, overall_architect=overall_architect, modules=modules_description
    )

    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    review2 = load_chat_model(configuration.review2_model).with_structured_output(ReviewState)
    review_reply = review2.invoke(
        [
            SystemMessage(content=system_message_review),
            HumanMessage(content=""),
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
graph = architect_builder.compile()
if __name__ == "__main__":

    def stream_graph_updates(user_input: str):
        for event in graph.stream({"topic": user_input}):
            for value in event.values():
                print(value)

    topic = """
    Perform steady-state thermomechanical calculations for a Pressurized Water Reactor (PWR) fuel rod. The setup is as follows:
    Geometric Conditions: The fuel pellet is made of UO₂ ceramic with a diameter of 8.192 mm; The cladding is made of Zr4 alloy with an inner diameter of 8.36 mm, an outer diameter of 9.5 mm, and a height of 3657 mm.
    Boundary Conditions: Adiabatic boundary conditions are applied at the top and bottom; The right side is set as an isothermal boundary condition, with an inlet temperature of 293 K and an outlet temperature of 333 K. The temperature in between is linearly interpolated; The gap between the fuel pellet and the cladding is set with an internal pressure of 2 MPa.
    Source Term: The volume heat generation rate in the fuel pellet is set as a cosine distribution along the axial direction and is uniform in the radial direction; The power is 0 at the top and bottom, and reaches a maximum of 2×10⁷ kW/m³ at the center.
    Material Properties: Fuel Pellet Thermal Conductivity: 1/(11.8+0.0238*T) + 8.775*1e-13*T^3 W/(cm·°C), Fuel Pellet Thermal Expansion Coefficient: Isotropic, with the formula: 7.107e-6+5.16e-9*T+3.42e-13*T^2(°C^(-1)); Cladding Thermal Conductivity: 0.15W/(cm·°C); Cladding Thermal Expansion Coefficient: 5.5e-6(°C^(-1)). In all formulas, T represents temperature in °C.
    """
    stream_graph_updates(topic)
