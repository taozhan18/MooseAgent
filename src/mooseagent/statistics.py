import asyncio
import json
import os, sys
from typing import Dict, List
from datetime import datetime
import pandas as pd
from langchain_community.callbacks.manager import get_openai_callback
from dotenv import load_dotenv
import subprocess
from datetime import datetime
import subprocess

load_dotenv()
run_path = os.getenv("RUN_PATH")
sys.path.append(run_path)
from mooseagent.graph1 import architect_builder, MemorySaver
from mooseagent.utils import Logger

save_dir: str = "/home/zt/workspace/MooseAgent/run_path"


class ExperimentStats:
    def __init__(self):
        self.success_count = 0
        self.total_tokens = []
        self.completion_tokens = []
        self.prompt_tokens = []
        self.code_lengths = []
        self.iteration_counts = []

    def add_run(self, success: bool, tokens: Dict, code_length: int, iterations: int):
        if success:
            self.success_count += 1
        self.total_tokens.append(tokens["total_tokens"])
        self.completion_tokens.append(tokens["completion_tokens"])
        self.prompt_tokens.append(tokens["prompt_tokens"])
        self.code_lengths.append(code_length)
        self.iteration_counts.append(iterations)

    def get_stats(self, total_runs: int):
        return {
            "success_rate": self.success_count / total_runs,
            "avg_total_tokens": sum(self.total_tokens) / len(self.total_tokens),
            "avg_completion_tokens": sum(self.completion_tokens) / len(self.completion_tokens),
            "avg_prompt_tokens": sum(self.prompt_tokens) / len(self.prompt_tokens),
            "avg_code_length": sum(self.code_lengths) / len(self.code_lengths),
            "avg_iterations": sum(self.iteration_counts) / len(self.iteration_counts),
        }


async def run_experiment(topic: str, n_runs: int = 5):
    stats = ExperimentStats()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 创建实验目录
    experiment_dir = os.path.join(run_path, f"experiments/{timestamp}")
    os.makedirs(experiment_dir, exist_ok=True)

    config = {"configurable": {"thread_id": "1"}, "recursion_limit": 10000}
    dp_json_path = "database/dp.json"
    with open(os.path.join(run_path, dp_json_path), "r", encoding="utf-8") as file:
        dp_json = json.load(file)
    for i in range(n_runs):
        subprocess.run(["rm", "-r", os.path.join(save_dir)])
        # 为每次运行创建单独的日志文件
        run_log = os.path.join(experiment_dir, f"run_{i+1}.log")
        sys.stdout = Logger(run_log)
        print(f"\nStarting run {i+1}/{n_runs}")
        # memory = MemorySaver()
        graph = architect_builder.compile()
        try:
            with get_openai_callback() as cb:
                result = await graph.ainvoke({"requirement": topic, "dp_json": dp_json}, config=config)

                # 计算代码总长度
                code_length = 0
                for file in result["file_list"]:
                    with open(os.path.join(save_dir, file.file_name), "r") as f:
                        code_length += len(f.read())

                # 收集统计数据
                stats.add_run(
                    success=(result.get("run_result") == "success"),
                    tokens={
                        "total_tokens": cb.total_tokens,
                        "completion_tokens": cb.completion_tokens,
                        "prompt_tokens": cb.prompt_tokens,
                    },
                    code_length=code_length,
                    iterations=result.get("review_count", 0),
                )

        except Exception as e:
            print(f"Error in run {i+1}: {str(e)}")
            continue
        finally:
            sys.stdout = sys.__stdout__

    # 计算并保存统计结果
    results = stats.get_stats(n_runs)
    results_df = pd.DataFrame([results])
    results_df.to_csv(os.path.join(experiment_dir, "stats.csv"))

    # 打印统计结果
    print("\n===== Experiment Results =====")
    for metric, value in results.items():
        print(f"{metric}: {value}")

    return results


if __name__ == "__main__":
    for i in range(7, 9):
        with open(os.path.join(run_path, "database/cases", f"case{i+1}.txt"), "r") as f:
            topic = f.read() + "\n" + "You can make the settings a bit rougher to speed up the simulation."
            print("current topic: \n", topic)
            asyncio.run(run_experiment(topic, n_runs=5))
