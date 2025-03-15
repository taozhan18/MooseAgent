import subprocess


def run_sh_script(script_path, parameter, mpi=1):
    """
    运行一个 .sh 脚本并传入一个参数。

    :param script_path: 脚本文件的路径
    :param parameter: 要传递给脚本的参数
    """
    command = ["mpiexec", "-n", str(mpi), script_path, "-i", parameter]
    result = subprocess.run(command, capture_output=True, text=True)
    # 打印输出
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)


# 示例用法
if __name__ == "__main__":
    script_path = "/home/zt/workspace/mymoose/mymoose-opt"  # 替换为你的脚本路径
    parameter = "/home/zt/workspace/mymoose/simple_diffusion.i"  # 替换为你要传递的参数
    run_sh_script(script_path, parameter)
