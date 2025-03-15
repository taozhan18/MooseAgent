from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
import os
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader
from tqdm import tqdm
from mooseagent.configuration import Configuration
from mooseagent.utils import BGE_M3_EmbeddingFunction
from langchain_openai import OpenAIEmbeddings
from langchain_core.runnables import RunnableConfig

config = RunnableConfig()
configuration = Configuration.from_runnable_config(config)
embedding_function = OpenAIEmbeddings() if configuration.embedding_function == "OPENAI" else BGE_M3_EmbeddingFunction()
batch_size = configuration.batch_size


def load_and_split_markdown_docs(docs_dir: str) -> list:
    """加载并切分markdown文档"""
    # 使用DirectoryLoader加载markdown文件
    loader = DirectoryLoader(docs_dir, glob=configuration.DATABASE_NAME, show_progress=True)
    docs = loader.load()

    # 切分文档
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
    split_docs = text_splitter.split_documents(docs)
    return split_docs


def create_vector_store(docs_dir: str) -> Chroma:
    """创建向量数据库"""
    # 检查是否已经存在持久化的向量库
    PERSIST_DIRECTORY = configuration.PERSIST_DIRECTORY
    if os.path.exists(PERSIST_DIRECTORY):
        print("加载已存在的向量库...")
        # 直接加载持久化的向量库
        vectorstore = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            collection_name="rag-chroma",
            embedding_function=embedding_function,
        )
    else:
        print("首次运行，加载文档并创建向量库...")
        # 加载并切分文档
        print("加载并切分文档...")
        split_docs = load_and_split_markdown_docs(docs_dir)
        print("创建向量库...")
        for i in tqdm(range(0, len(split_docs), batch_size)):
            if i == 0:
                # 创建向量库并持久化
                vectorstore = Chroma.from_documents(
                    documents=split_docs[i : i + batch_size],
                    collection_name="rag-chroma",
                    embedding=embedding_function,
                    persist_directory=PERSIST_DIRECTORY,
                )
            else:
                # 添加文档到向量库
                vectorstore.add_documents(
                    documents=split_docs[i : i + batch_size],
                )
        # 持久化向量库
        vectorstore.persist()
    return vectorstore.as_retriever()


retriever = create_vector_store(configuration.docs_dir)


class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""

    binary_score: str = Field(description="Documents are relevant to the question, 'yes' or 'no'")


### Retriever grader
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
structured_llm_grader = llm.with_structured_output(GradeDocuments)

# Prompt
system = """You are a grader assessing relevance of a retrieved document to a user question. \n
    It does not need to be a stringent test. The goal is to filter out erroneous retrievals. \n
    If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),
    ]
)

retrieval_grader = grade_prompt | structured_llm_grader

### Generate
# Prompt
legal_chat_qa_prompt_template = """"
    You are a trained legal research assistant to guide people about relevant legal cases, judgments and court decisions.
    Your name is AdaletGPT.\n
    Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer.
    You must answer in turkish.\n
    If you find the answer, write it in detail and include a list of source links that are **directly** used to derive the final answer.\n
    Do NOT process source links and use  as is.\n
    If you don't know the answer to a question, please do not share false information.\n\n
    Do not include source links that are irrelevant to the final answer\n.

    {context} \n


    Question : {question}\n
    Helpful Answer:
    """
prompt = PromptTemplate.from_template(legal_chat_qa_prompt_template)

# LLM
llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.1)


# Post-processing
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


# Chain
rag_chain = prompt | llm | StrOutputParser()


### Hallucination Grader
# Data model
class GradeHallucinations(BaseModel):
    """Binary score for hallucination present in generation answer."""

    binary_score: str = Field(description="Answer is grounded in the facts, 'yes' or 'no'")


# LLM with function call
llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0.1)
structured_llm_grader = llm.with_structured_output(GradeHallucinations)

# Prompt
system = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts. \n
     Give a binary score 'yes' or 'no'. 'Yes' means that the answer is grounded in / supported by the set of facts."""
hallucination_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Set of facts: \n\n {documents} \n\n LLM generation: {generation}"),
    ]
)

hallucination_grader = hallucination_prompt | structured_llm_grader


### Answer Grader
# Data model
class GradeAnswer(BaseModel):
    """Binary score to assess answer addresses question."""

    binary_score: str = Field(description="Answer addresses the question, 'yes' or 'no'")


# LLM with function call
llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0.1)
structured_llm_grader = llm.with_structured_output(GradeAnswer)

# Prompt
system = """You are a grader assessing whether an answer addresses / resolves a question \n
     Give a binary score 'yes' or 'no'. Yes' means that the answer resolves the question."""
answer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "User question: \n\n {question} \n\n LLM generation: {generation}"),
    ]
)

answer_grader = answer_prompt | structured_llm_grader

### Question Re-writer
# LLM
llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0.1)
# Prompt
system = """You a question re-writer that converts an input question to a better version that is optimized \n
     for vectorstore retrieval. Look at the input and try to reason about the underlying semantic intent / meaning."""
re_write_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        (
            "human",
            "Here is the initial question: \n\n {question} \n Formulate an improved question.",
        ),
    ]
)

question_rewriter = re_write_prompt | llm | StrOutputParser()
