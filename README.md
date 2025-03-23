# Algorithm

```plaintext
输入（仿真需求）
需求对齐：划分仿真任务，确定每个子文件的名字，对每个仿真任务内的细节进行说明。
For inpcard in inpcards:
    架构师：检索相关仿真案例，给出输入卡基本结构。
    while True:
        语法检测：基于规则的初步检测。
        if pass:
            break
        else:
            modify:
                MOOSE助手：基于数据库给出回答，这里基于错误信息给出修改方法和参考资料
                修改者：基于输入卡和参考资料进行修改
执行者：执行
if pass:
    End.
else:
    定位错误：基于报错信息定位出错文件的名字和具体位置。
    goto modify.
```

## Getting Started
1. Install

```bash
conda create -n langgraph python=3.12
pip install requirements.txt
```
Assuming you have already [installed LangGraph Studio](https://github.com/langchain-ai/langgraph-studio?tab=readme-ov-file#download), to set up:

2. Create a `.env` file.

```bash
cp .env.example .env
```
Now we use deepseek and openAi model, you can use [火山](https://console.volcengine.com/) to get your api-key for free.

### Setup Model

The defaults values for `model` are defined in src/mooseagent/configuration.py:

```yaml
alignment_model: str = "huoshan/deepseek-v3-241226"
architect_model: str = "huoshan/deepseek-r1-250120"
review_writer_model: str = "huoshan/deepseek-v3-241226"  # Defaults to claude-3-7-sonnet-latest
writer_model: str = "huoshan/deepseek-v3-241226"  # Defaults to claude-3-5-sonnet-latest
extracter_model: str = "openai/gpt-4o-mini"
embedding_function: str = "OPENAI"  # "BGE_M3_EmbeddingFunction"  # Defaults to BGE_M3_EmbeddingFunction
```

3. Run mooseagent

go to graph.py file, change the topic to your task.

```bash
python graph.py
```
