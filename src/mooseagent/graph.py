"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

import asyncio
import json
import sys
import os, re
from dotenv import load_dotenv
import subprocess

load_dotenv()
from langgraph.checkpoint.memory import MemorySaver
from langchain.callbacks import get_openai_callback

# sys.path.append("../")
sys.path.append(r"/home/zt/workspace/MooseAgent/src")
from tqdm import tqdm
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from mooseagent.configuration import Configuration
from mooseagent.state import (
    FlowState,
    ReviewState,
    OneFileState,
    ExtracterFileState,
    InpcardContentState,
)
from mooseagent.utils import load_chat_model, check_app, combine_code_with_description
from mooseagent.prompts import (
    SYSTEM_ALIGNMENT_PROMPT,
    HUMAN_ALIGNMENT_PROMPT,
    SYSTEM_REVIEW_WRITER_PROMPT,
    SYSTEM_ARCHITECT_PROMPT,
    SYSTEM_WRITER_PROMPT,
    # HUMAN_ARCHITECT_PROMPT,
)
from mooseagent.helper import bulid_helper, retriever_input
from langgraph.constants import Send
from langgraph.types import interrupt, Command

helper = bulid_helper()


def align_simulation_description(state: FlowState, config: RunnableConfig):
    """Align the simulation description
    Args:
        state (FlowState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.
    Returns:
        dict: A dictionary containing the model's response
    """

    configuration = Configuration.from_runnable_config(config)
    alignment = load_chat_model(configuration.alignment_model)  # .with_structured_output(ExtracterFileState)
    # similar_cases = retriever.invoke(state["detailed_description"])
    feedback = state.get("feedback", "")
    human_message_alignment = HUMAN_ALIGNMENT_PROMPT.format(requirement=state["requirement"], feedback=feedback)
    alignment_reply = alignment.invoke(
        [
            SystemMessage(content=SYSTEM_ALIGNMENT_PROMPT),
            HumanMessage(content=human_message_alignment),
        ]
    )
    print(alignment_reply.content)
    extracter_file = load_chat_model(configuration.extracter_model).with_structured_output(ExtracterFileState)
    extracter_reply = extracter_file.invoke(
        [
            SystemMessage(
                content="You are a helpful assistant that can extract a list of file name and its detailed description from the text. You should never change the file name and its detailed description."
            ),
            HumanMessage(content=alignment_reply.content),
        ]
    )
    return {"file_list": extracter_reply.file_list}


def human(state: FlowState, config: RunnableConfig):
    # interrupt_message = "---Please confirm if the above simulation description meets your requirements. If pass, please input 'yes'. If not, please input your feedback.---\nYour feedback: "
    # feedback = interrupt(interrupt_message)
    feedback = input(
        "---Please confirm if the above simulation description meets your requirements. If pass, please input 'yes'. If not, please input your feedback.---\nYour feedback: "
    )
    if feedback == "yes":
        return Command(
            goto=[
                Send(
                    "architect_input_card",
                    {
                        "inpcard": file,
                        "dp_json": state["dp_json"],
                    },
                )
                for file in state["file_list"]
            ]
        )
    # If the user provides feedback, regenerate the report plan
    elif isinstance(feedback, str):
        # Treat this as feedback
        return Command(goto="align_simulation_description", update={"feedback": feedback})
    else:
        raise TypeError(f"Interrupt value of type {type(feedback)} is not supported.")


def architect_input_card(state: OneFileState, config: RunnableConfig):
    """Generate the architect of the input card
    Args:
        state (OneFileState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.
    Returns:
        dict: A dictionary containing the model's response
    """
    inpcard = state["inpcard"]
    configuration = Configuration.from_runnable_config(config)
    print(f"---ARCHITECT INPUT CARD---")  #
    similar_cases = retriever_input.invoke(inpcard.description)
    similar_cases = f"Here is some relevant cases for this question:\n{similar_cases}"
    architect = load_chat_model(configuration.architect_model).with_structured_output(InpcardContentState)
    architect_reply = architect.invoke(
        [
            SystemMessage(
                content=SYSTEM_ARCHITECT_PROMPT.format(
                    requirements=inpcard.description,
                    cases=similar_cases,
                )
            ),
            # HumanMessage(content=human_message_architect),
        ]
    )
    inpcard_code = architect_reply.inpcard
    with open(os.path.join(configuration.save_dir, inpcard.file_name), "w", encoding="utf-8") as f:
        f.write(inpcard_code)
    print(f"---ARCHITECT INPUT CARD DONE---")
    return state


def check_onefile(state: OneFileState, config: RunnableConfig):
    configuration = Configuration.from_runnable_config(config)
    inpcard = state["inpcard"]
    with open(os.path.join(configuration.save_dir, inpcard.file_name), "r", encoding="utf-8") as f:
        inpcard_code = f.read()
    check = check_app(inpcard_code, state["dp_json"])
    if check != "":
        return Command(goto="modify", update={"check": check})
    else:
        return Command(goto="run_inpcard")


def modify(state: OneFileState, config: RunnableConfig):
    print(f"---RERITE INPCARD---")
    inpcard = state["inpcard"]
    configuration = Configuration.from_runnable_config(config)
    with open(os.path.join(configuration.save_dir, inpcard.file_name), "r", encoding="utf-8") as f:
        inpcard_code = f.read()
    # print(f"---PRELIMINARY REVIEW INPUT FILE---")  #
    review_writer = load_chat_model(configuration.review_writer_model).with_structured_output(InpcardContentState)

    messages = [
        {
            "role": "user",
            "content": f"Here are some error messages about moose input card: \n{state["check"]}\nThe input card is:\n{inpcard_code}\n",
        }
    ]
    helper_answer = helper.invoke({"messages": messages})
    feedback = helper_answer["messages"][-1].content
    writer_reply = review_writer.invoke(
        [
            SystemMessage(
                content=SYSTEM_WRITER_PROMPT.format(input_card=inpcard_code, feedback=feedback, error=state["check"])
            )
        ]
    )
    inpcard_code = writer_reply.inpcard
    with open(os.path.join(configuration.save_dir, inpcard.file_name), "w", encoding="utf-8") as f:
        f.write(inpcard_code)
    print(f"---RERITE INPCARD DONE---")
    return state


def review_inpcard(state: FlowState, config: RunnableConfig):
    """Review the generated inpcard for quality and completeness.

    Args:
        state (InpcardState): The current state of the inpcard.
        config (RunnableConfig): Configuration for the model run.

    Returns:
        dict: A dictionary containing the review results.
    """
    print(f"---REVIEW INPCARD---")
    configuration = Configuration.from_runnable_config(config)
    all_input_cards = ""
    for inpcard in state["file_list"]:
        with open(os.path.join(configuration.save_dir, inpcard.file_name), "r", encoding="utf-8") as f:
            inpcard_code = f.read()
        all_input_cards += f"-------------------\nThe file name is: {inpcard.file_name}\nThe code of this file is: \n{inpcard_code}-------------------\n\n"
    system_message_review = SYSTEM_REVIEW_WRITER_PROMPT.format(allfiles=all_input_cards, error=state["run_result"])

    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    review_writer = load_chat_model(configuration.review_writer_model)
    review_reply = review_writer.invoke(
        [
            SystemMessage(content=system_message_review),
        ]
    )
    extracter_review = load_chat_model(configuration.extracter_model).with_structured_output(ReviewState)
    extracter_reply = extracter_review.invoke(
        [
            SystemMessage(
                content="You are a helpful assistant that can extract a list of file name and its error information. You should never change the file name and its error information."
            ),
            HumanMessage(content=review_reply.content),
        ]
    )
    print(f"---REVIEW INPCARD DONE---")
    return {"reviews": extracter_reply.files}


def route_review(state: FlowState):
    return_content = []
    for review in state["reviews"]:
        review_name = review.filename
        error = review.error
        for file in state["file_list"]:
            if review_name == file.file_name:
                review_inpcard = file
                break
        onefile_state = {
            "inpcard": review_inpcard,
            "check": error,
            "dp_json": state["dp_json"],
        }
        return_content.append(Send("modify", onefile_state))
    return return_content


def run_inpcard(state: FlowState, config: RunnableConfig):
    configuration = Configuration.from_runnable_config(config)
    """Save the generated inpcard to a file."""
    inpcards = state["file_list"]
    # ? modify in future
    exec_name = inpcards[0].file_name
    """Run the moose simulation."""
    if os.path.exists(os.path.join(configuration.MOOSE_DIR)):
        print(f"Running moose with {exec_name}")
        command = [
            "mpiexec",
            "-n",
            str(configuration.mpi),
            configuration.MOOSE_DIR,
            "-i",
            os.path.join(configuration.save_dir, exec_name),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        # 打印输出
        if result.stderr == "":
            print(f"SUCCESS:\n{result.stdout}")
            return {"run_result": "success"}
        else:
            print(f"ERROR:\n{result.stderr}")
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
        print("The simulation task is completed successfully.")
        return "success"
    else:
        return "fail"


# Build workflow
architect_builder = StateGraph(FlowState)  # v, input=ArchitectInputState, output=ArchitectOutputState)

# Add the nodes
architect_builder.add_node("align_simulation_description", align_simulation_description)
architect_builder.add_node("human", human)
architect_builder.add_node("architect_input_card", architect_input_card)
architect_builder.add_node("modify", modify)
architect_builder.add_node("check_onefile", check_onefile)
architect_builder.add_node("review_inpcard", review_inpcard)
architect_builder.add_node("run_inpcard", run_inpcard)
# Add edges to connect nodes
architect_builder.add_edge(START, "align_simulation_description")
architect_builder.add_edge("align_simulation_description", "human")
architect_builder.add_edge("architect_input_card", "check_onefile")
architect_builder.add_edge("modify", "check_onefile")
architect_builder.add_conditional_edges(
    "run_inpcard",
    route_run_inpcard,
    {  # Name returned by route_joke : Name of next node to visit
        "success": END,
        "fail": "review_inpcard",
    },
)
architect_builder.add_conditional_edges("review_inpcard", route_review, ["modify"])
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
    One-Dimensional Steady-State Heat Conduction
Task Description:
A metallic rod of length L = 1 m has its two ends kept at constant temperatures of 300 K and 350 K, respectively. The thermal conductivity (k) is 10 W/(m·K). Under steady-state conditions, compute the temperature distribution along the rod and output the temperature profile as a function of position.
    """
    with get_openai_callback() as cb:
        # 运行异步主程序
        asyncio.run(graph.ainvoke({"requirement": topic, "dp_json": dp_json}, config=config))
        print("===== Token Usage =====")
        print("Prompt Tokens:", cb.prompt_tokens)
        print("Completion Tokens:", cb.completion_tokens)
        print("Total Tokens:", cb.total_tokens)
    # graph.invoke({"requirement": topic, "dp_json": dp_json}, config=config)
    # stream_graph_updates(topic, dp_json)
