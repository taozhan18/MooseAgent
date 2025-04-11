## Algorithm
MooseAgent: Automated MOOSE Agent (Integrated with a MOOSE assistant module, which can be used separately)
```plaintext
Input (Simulation Requirements)
Requirement Alignment: Divide simulation tasks, determine the name of each sub-file, and describe the details within each simulation task.
### Task Decomposition
For inpcard in inpcards:
    Define search content based on requirements and retrieve relevant simulation cases.
    Architect: Based on requirements and relevant simulation cases, provide the basic structure of the input card.
### Multi-Round Iterative Error Correction
    Execute the input card.
    If False:
        if less than the maximum number of error corrections:
            modify: Provide the cause of the error and the corrected input card based on the database
        else:
            Determine if the same error is repeated
            If True:
                Return to the task decomposition step and rewrite the input card
            else:
                modify: Provide the cause of the error and the corrected input card based on the database
    Else:
        SUCCESS
```

![agentflow](static/agentflow.png)

AutoComment: Input Card Auto-Comment Agent
```plaintext
1. Randomly select an unannotated input card,
2. Query the documentation for the relevant APP of the input card
3. Input the documentation and the input card
4. Output the annotated input card. Return to step 1
```
![autocommentflow](static/autocomment.png)
## Getting Started
1. Install

```bash
conda create -n langgraph python=3.12
pip install requirements.txt
```


2. Create a `.env` file.

```bash
cp .env.example .env
```
Now we use deepseek and openAi model, you can use [火山](https://console.volcengine.com/) to get your api-key for free.

Note: Change RUN_PATH you .env file to your path.
### Setup Model

The defaults values for `model` are defined in src/mooseagent/configuration.py:

```yaml
alignment_model: str = "huoshan/deepseek-v3-241226"
architect_model: str = "huoshan/deepseek-r1-250120"
review_writer_model: str = "huoshan/deepseek-v3-241226"  # Defaults to claude-3-7-sonnet-latest
writer_model: str = "huoshan/deepseek-v3-241226"  # Defaults to claude-3-5-sonnet-latest
extracter_model: str = "openai/gpt-4o-mini" # You can change to deepseek v3 if you don't have openai key.
embedding_function: str = "BGE_M3_EmbeddingFunction"  # "BGE_M3_EmbeddingFunction"  # Defaults to BGE_M3_EmbeddingFunction
```

3. Set path: the three paths must set to your own path
```yaml
ABSOLUTE_PATH: str = "/home/zt/workspace/MooseAgent/src" # agent src path
MOOSE_DIR: str = "/home/zt/workspace/mymoose/mymoose-opt" # moose opt path
save_dir: str = "/home/zt/workspace/MooseAgent/run_path" # path to save input card and result
```
4. Run mooseagent

go to graph.py file, change the topic to your task.

```bash
python graph.py
```
You can see the result in save_dir if success. The running log is save in src/log

## Autocomment
This file read case_name_uncommented.txt in database folder. You should change the path in this file to your path. And the annotated code will save in database/comments/, the comment.json will also update.
```bash
python autocomment.py
```
## update database
1. You should first update comment.json or dp_detail.json in src/database.
2. set the configuration.py
```yaml
rag_json_path: str = os.path.join(ABSOLUTE_PATH, "database", "comment.json")  # comment.json
batch_size: int = 1  # batch size for adding documents to the vector store
PERSIST_DIRECTORY: str = os.path.join(
    ABSOLUTE_PATH, "database", embedding_function + "_faiss_inpcard"
) # comment.json corresponding to ..._inpcard, dp_detail.json corresponding to ..._dp
```
3. run load_vector_database.py. It will update incrementally.
```bash
python load_vector_database.py
```

