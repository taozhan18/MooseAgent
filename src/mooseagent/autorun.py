import subprocess
import time

script_path = r"E:/vscode/python/Agent/langgraph_learning/mooseagent/src/mooseagent/autocomment.py"

while True:
    try:
        print("正在运行脚本...")
        result = subprocess.run(["python", script_path], check=True)
        print("脚本运行完成")
        break  # 脚本成功运行后退出循环
    except subprocess.CalledProcessError:
        print("脚本运行失败，正在重新启动...")
        time.sleep(10)  # 等待10秒后重新启动
