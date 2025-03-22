from typing import Annotated, Literal, Sequence
from typing_extensions import TypedDict

from langchain import hub
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from typing import Annotated, Sequence
from langchain_core.messages import BaseMessage
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition
from langchain.tools.retriever import create_retriever_tool

from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

SYSTEM_GRADE_PROMPT = """Your task is to evaluate the relevance of retrieved MOOSE (A multi-physics simulation software) application documents or the input card of MOOSE simulation cases to user questions. \n
Here is the retrieved document: \n\n {context} \n\n
Here is the user question: {question} \n
If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n
Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.
"""
SYSTEM_GENERATE_PROMPT = """Your task is to summarize the input cards of MOOSE APP documents or simulation cases retrieved based on user questions, reduce irrelevant information, and provide core information.
Here is the retrieved document: \n\n {context} \n\n
Here is the user question: {question} \n
When summarizing, please follow the following requirements:
-Carefully analyze user issues and clarify core requirements.
-Filter out content related to user issues from APP documents or input cards (but do not change the original text), and remove irrelevant information.
-For simulation cases, the retrieved content is a JSON file that contains the input_card_name, overall_description, and annotated_input_card. The input card source code is stored in annotated_input_card. PPlease provide at least one complete input card to illustrate the overall architecture of the MOOSE input card file, and select the relevant sections for other input cards. In addition, explain how to effectively utilize these codes to solve specific simulation tasks at hand. For the documentation of MOOSE applications, please highlight the most useful applications and their respective usage methods. In addition, please explain in detail how to apply these applications to solve user queries.

If the retrieved document is simulation cases, you should reply like this:
code1: The original input card (not json format).
Description1: Explain the purpose of the code, how can it be used to solve the user question.
... (Repeat this for all relevant source codes)

If the retrieved document is documentations of moose app, you should reply like this (not json format:
Here are some helpful apps and their usage methods:
app1: The original text of the app and its usage (not json format).
Description1: Explain how to use the app to solve the user question.
... (Repeat this for all relevant apps)
"""
model_str = "gpt-4o-mini"


class AgentState(TypedDict):
    # The add_messages function defines how an update should be processed
    # Default is to replace. add_messages says "append"
    question: str
    rag_type: str
    docs: str
    final_result: str


def bulid_writer_module(retriever, description="", document_prompt=""):
    def agent(state: AgentState):
        """
        Invokes the agent model to generate a response based on the current state. Given
        the question, it will decide to retrieve using the retriever tool, or simply end.

        Args:
            state (messages): The current state

        Returns:
            dict: The updated state with the agent response appended to messages
        """
        docs = ""
        rag_infos = retriever.invoke(state["question"])
        for rag_info in rag_infos:
            docs += rag_info.page_content
            docs += "\n"
        # We return a list, because this will get added to the existing list
        return {"docs": docs}

    def generate(state: AgentState):
        """
        Generate answer

        Args:
            state (messages): The current state

        Returns:
            dict: The updated state with re-phrased question
        """
        print("---GENERATE---")
        question = f"Find information about:\n{state["question"]}"
        docs = state["docs"]
        return {"final_result": docs}
        # LLM
        llm = ChatOpenAI(model_name=model_str, temperature=0)
        # Run
        response = llm.invoke(
            [
                SystemMessage(content=SYSTEM_GENERATE_PROMPT.format(context=docs, question=question)),
                HumanMessage(content=f"The knowledge base you retrieved is {state["rag_type"]}."),
            ]
        )
        return {"final_result": response.content}

    # Define a new graph
    workflow = StateGraph(AgentState)

    # Define the nodes we will cycle between
    workflow.add_node("agent", agent)  # agent
    workflow.add_node("generate", generate)  # Generating a response after we know the documents are relevant
    # Call agent node to decide to retrieve or not
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", "generate")
    workflow.add_edge("generate", END)

    # Compile
    rag_graph = workflow.compile()
    return rag_graph
