## 算法
MooseAgent: 自动化 MOOSE 代理 (集成了一个可以单独使用的 MOOSE 助手模块)
```plaintext
输入 (模拟需求)
需求对齐: 划分模拟任务，确定每个子文件的名称，并描述每个模拟任务中的细节。
### 任务分解
对于 inpcard 在 inpcards 中:
    基于需求定义搜索内容并检索相关的模拟案例。
    架构设计: 基于需求和相关的模拟案例，提供输入卡片的基本结构。
### 多轮迭代错误修正
    执行输入卡片。
    如果 False:
        如果小于最大错误修正次数:
            修改: 基于数据库提供错误原因和修正后的输入卡片
        否则:
            判断是否重复出现相同的错误
            如果 True:
                返回到任务分解步骤并重写输入卡片
            否则:
                修改: 基于数据库提供错误原因和修正后的输入卡片
    否则:
        成功
```

![agentflow](static/agentflow.png)

AutoComment: 输入卡片自动注释代理
```plaintext
1. 随机选择一个未注释的输入卡片。
2. 查询输入卡片相关 APP 的文档。
3. 输入文档和输入卡片。
4. 输出带注释的输入卡片。返回步骤 1。
```
![autocommentflow](static/autocomment.png)
## 开始使用
1. 安装

```bash
conda create -n langgraph python=3.12
pip install requirements.txt
```


2. 创建一个 `.env` 文件

```bash
cp .env.example .env
```
现在我们使用 deepseek 和 openAi 模型，你可以使用[火山](https://console.volcengine.com/) 免费获取你的 api-key。

注意: 将你的路径更改到 .env 文件中的 RUN_PATH。
### 设置模型

`model` 的默认值在 `src/mooseagent/configuration.py`中定义:

```yaml
alignment_model: str = "huoshan/deepseek-v3-241226"
architect_model: str = "huoshan/deepseek-r1-250120"
review_writer_model: str = "huoshan/deepseek-v3-241226"  # Defaults to claude-3-7-sonnet-latest
writer_model: str = "huoshan/deepseek-v3-241226"  # Defaults to claude-3-5-sonnet-latest
extracter_model: str = "openai/gpt-4o-mini" # You can change to deepseek v3 if you don't have openai key.
embedding_function: str = "BGE_M3_EmbeddingFunction"  # "BGE_M3_EmbeddingFunction"  # Defaults to BGE_M3_EmbeddingFunction
```

1. 设置路径: 以下三个路径必须设置为你自己的路径
```yaml
ABSOLUTE_PATH: str = "/home/zt/workspace/MooseAgent/src" # agent src path
MOOSE_DIR: str = "/home/zt/workspace/mymoose/mymoose-opt" # moose opt path
save_dir: str = "/home/zt/workspace/MooseAgent/run_path" # path to save input card and result
```
2. 运行 mooseagent

转到 graph.py 文件，将 topic 更改为你的任务。

```bash
python graph.py
```
如果成功，你可以在 save_dir 中看到结果。运行日志保存在 src/log 中。

## 自动注释
此文件读取 database 文件夹中的 case_name_uncommented.txt。你应该将此文件中的路径更改为你的路径。注释后的代码将保存在 database/comments/ 中，comment.json 也会更新。
```bash
python autocomment.py
```
## 更新数据库
1. 你应该首先更新 src/database 中的 comment.json 或 dp_detail.json。
2. 设置 configuration.py
```yaml
rag_json_path: str = os.path.join(ABSOLUTE_PATH, "database", "comment.json")  # comment.json
batch_size: int = 1  # batch size for adding documents to the vector store
PERSIST_DIRECTORY: str = os.path.join(
    ABSOLUTE_PATH, "database", embedding_function + "_faiss_inpcard"
) # comment.json corresponding to ..._inpcard, dp_detail.json corresponding to ..._dp
```
3. 运行 load_vector_database.py。它将增量更新。
```bash
python load_vector_database.py
```

