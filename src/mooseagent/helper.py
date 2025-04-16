from dotenv import load_dotenv
import sys, os

load_dotenv()
run_path = os.getenv("RUN_PATH")
sys.path.append(run_path)
from langchain_core.runnables import RunnableConfig
from langchain.tools.retriever import create_retriever_tool
from langchain.tools.retriever import create_retriever_tool
from langchain_community.vectorstores import FAISS, Chroma
from mooseagent.configuration import Configuration
from langchain_openai import OpenAIEmbeddings
from mooseagent.utils import BGE_M3_EmbeddingFunction
from mooseagent.utils import load_chat_model
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

config = RunnableConfig()
configuration = Configuration.from_runnable_config(config)
vector_type = configuration.vector_store
embedding_function = OpenAIEmbeddings() if configuration.embedding_function == "OPENAI" else BGE_M3_EmbeddingFunction()
batch_size = configuration.batch_size
top_k = configuration.top_k
json_file = configuration.rag_json_path
try:
    if vector_type.lower() == "faiss":
        vectordb_input = FAISS.load_local(
            configuration.input_database_path, embedding_function, allow_dangerous_deserialization=True
        )
        vectordb_dp = FAISS.load_local(
            configuration.dp_database_path, embedding_function, allow_dangerous_deserialization=True
        )
    elif vector_type.lower() == "chroma":
        vectordb_input = Chroma(
            persist_directory=configuration.input_database_path, embedding_function=embedding_function
        )
        vectordb_dp = Chroma(persist_directory=configuration.dp_database_path, embedding_function=embedding_function)
    else:
        raise ValueError(f"Unsupported vector store type: {vector_type}")

    retriever_input = vectordb_input.as_retriever(search_type="similarity", search_kwargs={"k": top_k})
    retriever_dp = vectordb_dp.as_retriever(search_type="similarity", search_kwargs={"k": top_k})
    # define tools
    tools = [
        create_retriever_tool(
            retriever_input,
            "retrieve_moose_case",
            "Search and return information about MOOSE simulation cases that are relevant to the simulation case you are working on.",
        ),
        create_retriever_tool(
            retriever_dp,
            "retrieve_moose_dp",
            "Search and return information about the document of MOOSE app that are relevant to the simulation case you are working on.",
        ),
    ]
except Exception as e:
    print(f"Error loading vector database: {e}")


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


configuration = Configuration.from_runnable_config(config)

sys_msg = """You are a knowledgeable assistant specializing in Finite Element Method (FEM) software, particularly in MOOSE simulation. Your mission is to locate and provide relevant information on input parameters, techniques, and best practices to ensure accurate and efficient simulations."""


def bulid_helper(model: str):
    def helper(state: State):
        llm = load_chat_model(model).bind_tools(tools)
        return {"messages": [llm.invoke([sys_msg] + state["messages"])]}

    graph_builder = StateGraph(State)
    graph_builder.add_node("helper", helper)
    tool_node = ToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_edge("tools", "helper")
    graph_builder.set_entry_point("helper")
    graph_builder.add_conditional_edges(
        "helper",
        tools_condition,
    )
    return graph_builder.compile()


if __name__ == "__main__":
    graph = bulid_helper()

    def stream_graph_updates(user_input: str):
        for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)

    stream_graph_updates("How to define Dirichlet boundary condition in MOOSE?")
