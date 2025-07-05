#!/bin/bash

# 这是关键的一步：找到你的 conda.sh 脚本并 source 它
# 这会初始化 conda 的 shell 函数 (比如 conda activate)
# 你的路径可能是 /home/zt/miniforge/etc/profile.d/conda.sh
# 或 /opt/conda/etc/profile.d/conda.sh，请根据你的安装位置进行调整
source "/home/zt/miniforge/etc/profile.d/conda.sh"

# 激活目标环境
conda activate moose

# 执行传递给这个脚本的所有参数
# "$@" 是一个特殊的 shell 变量，代表所有传递进来的参数
# 例如: mpiexec -n 1 /path/to/app -i /path/to/input
exec "$@"
