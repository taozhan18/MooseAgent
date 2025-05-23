"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

import asyncio
import json
import sys
import os, re
from dotenv import load_dotenv
import subprocess
from datetime import datetime

load_dotenv()
run_path = os.getenv("RUN_PATH")
sys.path.append(run_path)

from langgraph.checkpoint.memory import MemorySaver
from langchain_community.callbacks.manager import get_openai_callback

from tqdm import tqdm
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from mooseagent.configuration import Configuration
from mooseagent.state import (
    FlowState,
    FileState,
    ExtracterFileState,
    InpcardContentState,
    ModifyState,
    RearchitechState,
    QueryState,
)
from mooseagent.utils import load_chat_model, check_app, combine_code_with_description, Logger
from mooseagent.prompts import (
    SYSTEM_ALIGNMENT_PROMPT,
    HUMAN_ALIGNMENT_PROMPT,
    SYSTEM_REVIEW_PROMPT,
    SYSTEM_ARCHITECT_PROMPT,
    SYSTEM_WRITER_PROMPT,
    MultiAPP_PROMPT,
    MODIFY_PROMPT,
    REARCHITECT_PROMPT,
    SYSTEM_QUERY_PROMPT,
    # HUMAN_ARCHITECT_PROMPT,
)
from mooseagent.helper import bulid_helper, retriever_input
from langgraph.constants import Send
from langgraph.types import interrupt, Command

configuration = Configuration.from_runnable_config(RunnableConfig())
helper = bulid_helper(configuration.assistant_model)


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
            SystemMessage(content=SYSTEM_ALIGNMENT_PROMPT + MultiAPP_PROMPT),
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
    feedback = "yes"
    # feedback = input(
    #     "---Please confirm if the above simulation description meets your requirements. If pass, please input 'yes'. If not, please input your feedback.---\nYour feedback: "
    # )
    if feedback == "yes":
        return Command(goto="architect", update=state)
    # If the user provides feedback, regenerate the report plan
    elif isinstance(feedback, str):
        # Treat this as feedback
        return Command(goto="align_simulation_description", update={"feedback": feedback})
    else:
        raise TypeError(f"Interrupt value of type {type(feedback)} is not supported.")


async def architect_all(state: FlowState, config: RunnableConfig):
    rearchitect_count = state.get("rearchitect_count", 0) + 1
    print(f"-----ARCHITECT_{rearchitect_count}-----")
    history_error = state.get("history_error", "")
    multiapps = True if len(state["file_list"]) > 1 else False
    tasks = [architect_input_card(file, config, multiapps, history_error) for file in state["file_list"]]
    await asyncio.gather(*tasks)
    return {"rearchitect_count": rearchitect_count}


async def architect_input_card(
    state: FileState, config: RunnableConfig, multiapps: bool = False, history_error: str = ""
):
    """Generate the architect of the input card
    Args:
        state (OneFileState): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.
    Returns:
        dict: A dictionary containing the model's response
    """
    # inpcard = state["inpcard"]
    configuration = Configuration.from_runnable_config(config)
    print(f"---ARCHITECT INPUT CARD---")  #
    # generate query
    queryllm = load_chat_model(configuration.query_model)  # .with_structured_output(QueryState)
    query_reply = await queryllm.ainvoke(
        [
            SystemMessage(content=SYSTEM_QUERY_PROMPT.format(requirements=state.description)),
        ]
    )

    similar_cases = await retriever_input.ainvoke(query_reply.content)
    similar_cases = f"Here is some relevant cases for this question:\n{similar_cases}"
    if multiapps:
        similar_cases += MultiAPP_PROMPT
    # architect
    architect = load_chat_model(configuration.architect_model).with_structured_output(InpcardContentState)
    architect_reply = await architect.ainvoke(
        [
            SystemMessage(
                content=SYSTEM_ARCHITECT_PROMPT.format(
                    requirements=state.description, cases=similar_cases, history_error=history_error
                )
            ),
            # HumanMessage(content=human_message_architect),
        ]
    )
    inpcard_code = architect_reply.inpcard
    if os.path.exists(configuration.save_dir) is False:
        os.makedirs(configuration.save_dir)
    with open(os.path.join(configuration.save_dir, state.file_name), "w", encoding="utf-8") as f:
        f.write(inpcard_code)
    print(f"---ARCHITECT INPUT CARD DONE---")
    return state


def modify(state: FlowState, config: RunnableConfig):
    review_count = state.get("review_count", 0) + 1
    print(f"---REWRITE INPCARD---{review_count}")
    configuration = Configuration.from_runnable_config(config)
    all_input_cards = ""
    for inpcard in state["file_list"]:
        with open(os.path.join(configuration.save_dir, inpcard.file_name), "r", encoding="utf-8") as f:
            inpcard_code = f.read()
        all_input_cards += f"-------------------\nThe file name is: {inpcard.file_name}\nThe description of this file is:\n{inpcard.description}\nThe code of this file is: \n{inpcard_code}-------------------\n\n"
    state["run_result"][-1] = state["run_result"][-1] + "\n" + check_app(all_input_cards, state["dp_json"])
    messages = [
        {
            "role": "user",
            "content": MODIFY_PROMPT.format(
                inpcard_code=all_input_cards,
                error=state["run_result"][-1],
            ),
        }
    ]
    helper_answer = helper.invoke({"messages": messages})
    feedback = helper_answer["messages"][-1].content
    extracter_review = load_chat_model(configuration.extracter_model).with_structured_output(ModifyState)
    extracter_reply = extracter_review.invoke(
        [
            SystemMessage(
                content="You are a helpful assistant that can extract file name, error information and the modified code.  You should never change the origin information."
            ),
            HumanMessage(content=feedback),
        ]
    )
    print(f"The error in file: {extracter_reply.filename}. The reason is that: {extracter_reply.error}")
    reason = state.get("reason", [])
    reason.append(extracter_reply.error)
    inpcard_code = extracter_reply.code
    with open(os.path.join(configuration.save_dir, extracter_reply.filename), "w", encoding="utf-8") as f:
        f.write(extracter_reply.code)
    print(f"---REWRITE INPCARD DONE---")
    return {"review_count": review_count, "run_result": state["run_result"], "reason": reason}


def run_inpcard(state: FlowState, config: RunnableConfig):
    configuration = Configuration.from_runnable_config(config)
    """Save the generated inpcard to a file."""
    inpcards = state["file_list"]
    review_count = state.get("review_count", 0)
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
            return Command(goto="End", update=state)
        else:
            print(f"ERROR:\n{result.stderr}")
            run_result = state.get("run_result", [])
            run_result.append(result.stderr)
            if review_count < configuration.MAX_ITER:
                return Command(goto="modify", update={"run_result": run_result})
            if state["rearchitect_count"] < configuration.MAX_REARCHITECT:
                rearchitect = load_chat_model(configuration.rearchitect_model).with_structured_output(RearchitechState)
                feedback = rearchitect.invoke(
                    [SystemMessage(content=REARCHITECT_PROMPT.format(Error=state["run_result"][-5:]))]
                )
                if "True" in feedback.rearchitect:
                    print("retry")
                    return Command(
                        goto="architect",
                        update={
                            "review_count": 0,
                            "run_result": [],
                            "history_error": feedback.error,
                            "reason": [],
                        },
                    )
                else:
                    print("try to modify again!")
                    return Command(goto="modify", update={"run_result": run_result, "review_count": review_count - 1})
            else:
                print("Up to max iteration.")
                return Command(goto="End")
    else:
        print(f"Moose directory {configuration.MOOSE_DIR} does not exist.")
        return Command(goto="End")


# Build workflow
architect_builder = StateGraph(FlowState)  # v, input=ArchitectInputState, output=ArchitectOutputState)

# Add the nodes
architect_builder.add_node("align_simulation_description", align_simulation_description)
architect_builder.add_node("human", human)
architect_builder.add_node("architect", architect_all)
architect_builder.add_node("modify", modify)
architect_builder.add_node("run_inpcard", run_inpcard)
# Add edges to connect nodes
architect_builder.add_edge(START, "align_simulation_description")
architect_builder.add_edge("align_simulation_description", "human")
architect_builder.add_edge("architect", "run_inpcard")
architect_builder.add_edge("modify", "run_inpcard")
# architect_builder.add_conditional_edges("review_inpcard", route_review, ["modify"])
memory = MemorySaver()
graph = architect_builder.compile(checkpointer=memory)
if __name__ == "__main__":
    config = {"configurable": {"thread_id": "1"}, "recursion_limit": 10000}
    dp_json_path = "database/dp.json"
    with open(os.path.join(run_path, dp_json_path), "r", encoding="utf-8") as file:
        dp_json = json.load(file)

    def stream_graph_updates(user_input: str, dp_json: dict):
        for event in graph.stream({"requirement": user_input, "dp_json": dp_json}, config=config):
            for value in event.values():
                print(value)

    topic = """
 Construct a Moose phase field simulation case to simulate the solidification process of pure metal in a two-dimensional rectangular region. This task will use a phase field model to simulate the transition of solid-liquid phase by solving the coupled evolution equation of phase field variables and temperature field. The boundary condition is to apply a low temperature below the solidification point on one side of the rectangular region to drive solidification, with the initial condition being that the metal is in a liquid state. The goal is to observe the formation and growth of solid phases, as well as the evolution and temperature distribution of solid-liquid interfaces.


You can make the settings a bit rougher to speed up the simulation
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(run_path, f"log/{timestamp}.log")
    sys.stdout = Logger(output_file)
    subprocess.run(["rm", "-r", configuration.save_dir])
    with get_openai_callback() as cb:
        # 运行异步主程序
        result = asyncio.run(graph.ainvoke({"requirement": topic, "dp_json": dp_json}, config=config))
        code_length = 0
        for file in result["file_list"]:
            with open(os.path.join(configuration.save_dir, file.file_name), "r") as f:
                code_length += len(f.read())
        print(code_length)
        print("===== Token Usage =====")
        print("Prompt Tokens:", cb.prompt_tokens)
        print("Completion Tokens:", cb.completion_tokens)
        print("Total Tokens:", cb.total_tokens)
