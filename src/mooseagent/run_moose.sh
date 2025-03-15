#!/bin/bash

# 检查是否传入了文件路径参数
if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_i_file>"
    exit 1
fi

# 获取传入的文件路径
I_FILE_PATH="$1"

# 检查文件是否存在
if [ ! -f "$I_FILE_PATH" ]; then
    echo "Error: 文件 $I_FILE_PATH 不存在！"
    exit 1
fi
MOOSE_PATH="/home/zt/workspace/mymoose/mymoose-opt"
mpi=1
# 激活 MOOSE 虚拟环境
conda activate moose

echo "运行 MOOSE 模拟..."
# 替换为 MOOSE 的实际运行命令
# 假设运行命令为：moose_app --input <i_file_path>
mpiexec -n $mpi "$MOOSE_PATH" -i "$I_FILE_PATH"
