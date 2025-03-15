import sys
import os
from dotenv import load_dotenv

load_dotenv()
from langgraph.checkpoint.memory import MemorySaver

# sys.path.append("../")
sys.path.append(r"E:/vscode/python/Agent/langgraph_learning/mooseagent/src")
from langchain_community.vectorstores import FAISS
from mooseagent.configuration import Configuration
from langchain_community.document_loaders import JSONLoader
from langchain_core.runnables import RunnableConfig
from langchain_openai import OpenAIEmbeddings
from mooseagent.utils import BGE_M3_EmbeddingFunction
from tqdm import tqdm
import hashlib
import json

config = RunnableConfig()
configuration = Configuration.from_runnable_config(config)
embedding_function = OpenAIEmbeddings() if configuration.embedding_function == "OPENAI" else BGE_M3_EmbeddingFunction()
batch_size = configuration.batch_size
top_k = configuration.top_k
json_file = configuration.rag_json_path

# 用于存储已处理文档的哈希值
processed_hashes = set()

# 如果哈希文件存在，加载已有的哈希值
HASHES_FILE = os.path.join(configuration.PERSIST_DIRECTORY, "hashes.json")
if os.path.exists(HASHES_FILE):
    with open(HASHES_FILE, "r") as f:
        processed_hashes = set(json.load(f))
else:
    # 如果哈希文件不存在，检查向量数据库是否存在
    if os.path.exists(configuration.PERSIST_DIRECTORY):
        vectordb = FAISS.load_local(
            configuration.PERSIST_DIRECTORY,
            embedding_function,
            allow_dangerous_deserialization=True,
        )
        # 假设 vectordb 中的文档内容可以被用来计算哈希
        existing_docs = vectordb.docstore._dict.values()
        for doc in existing_docs:
            # 计算现有文档的哈希值
            doc_hash = hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()
            processed_hashes.add(doc_hash)
    else:
        # 如果向量数据库不存在，初始化一个空的
        vectordb = None

print("加载json文件...")
loader = JSONLoader(file_path=json_file, jq_schema=".[]", text_content=False)
docs = loader.load()
for i in tqdm(range(0, len(docs), batch_size)):
    batch_docs = docs[i : i + batch_size]
    # 过滤掉已经处理过的文档
    filtered_batch = []
    for doc in batch_docs:
        # 计算当前文档的哈希值
        doc_hash = hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()
        if doc_hash not in processed_hashes:
            filtered_batch.append(doc)
            processed_hashes.add(doc_hash)

    if not filtered_batch:
        continue  # 如果批次中没有新文档，跳过
    try:
        if i == 0:
            vectordb = FAISS.from_documents(
                documents=filtered_batch,
                embedding=embedding_function,
            )
        else:
            vectordb.add_documents(documents=filtered_batch)
    except Exception as e:
        print(f"Error processing batch {i//batch_size + 1}: {e}")
        break
# 保存向量数据库
if vectordb:
    vectordb.save_local(configuration.PERSIST_DIRECTORY)
    with open(HASHES_FILE, "w") as f:
        json.dump(list(processed_hashes), f)
    print("向量数据库已更新并保存。")
else:
    print("没有新文档需要添加，向量数据库未更改。")
