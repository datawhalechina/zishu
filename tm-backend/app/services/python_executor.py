"""
Python 代码执行器
使用 Docker 沙箱环境安全执行 Python 代码
"""
import asyncio
import re
import sys
import platform
from typing import Dict, Any
import subprocess
import shlex


class PythonExecutor:
    """Python 代码执行器（Docker 沙箱）"""

    # 预导入的常用模块（教程代码可以直接使用，无需显式导入）
    PREIMPORTED_MODULES = '''
# 预导入常用模块
import sys
import math
import json
import re
import datetime
import random
import itertools
import collections
from typing import List, Dict, Tuple, Optional, Any
from collections import Counter, defaultdict, OrderedDict
from functools import reduce, partial
from itertools import permutations, combinations

# 尝试导入 pandas 和 numpy（如果已安装）
try:
    import pandas as pd
    import numpy as np
except ImportError:
    pass

# 常用函数和常量
pi = math.pi
e = math.e

'''

    # 获取 Python 可执行文件名（Windows 和 Linux/macOS 不同）
    @staticmethod
    def _get_python_command() -> str:
        """获取 Python 命令"""
        if platform.system() == 'Windows':
            return 'python'
        return 'python3'

    # 危险模块和函数列表
    FORBIDDEN_PATTERNS = [
        r'\bimport\s+os\b',           # import os
        r'\bfrom\s+os\s+import',       # from os import
        r'\bimport\s+subprocess\b',    # import subprocess
        r'\bfrom\s+subprocess\s+import',  # from subprocess import
        r'\bimport\s+sys\b',           # import sys
        r'\bfrom\s+sys\s+import',      # from sys import
        r'\b__import__\s*\(',          # __import__()
        r'\beval\s*\(',                # eval()
        r'\bexec\s*\(',                # exec()
        r'\bcompile\s*\(',             # compile()
        r'\bopen\s*\(',                # open() (文件操作)
        r'\b__builtins__\b',           # __builtins__
    ]

    # 允许的安全模块白名单
    ALLOWED_MODULES = [
        'math', 'random', 'datetime', 'json', 're',
        'collections', 'itertools', 'functools',
        'decimal', 'fractions', 'statistics',
        'string', 'typing', 'dataclasses',
        'enum', 'warnings', 'contextlib',
        'pathlib',  # 允许但只用于纯内存操作
    ]

    def _is_safe_code(self, code: str) -> tuple[bool, str]:
        """
        检查代码是否安全

        Returns:
            (is_safe, error_message)
        """
        # 检查禁止的模式
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                # 检查是否在注释中
                lines = code.split('\n')
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        # 如果行首有 #，则是注释，允许
                        stripped = line.strip()
                        if not stripped.startswith('#'):
                            return False, f'安全限制: 禁止使用危险的函数或模块 (第 {i} 行)'

        # 检查 import 语句，只允许白名单中的模块
        import_pattern = r'(?:import\s+(\w+)|from\s+(\w+)\s+import)'
        for match in re.finditer(import_pattern, code):
            module = match.group(1) or match.group(2)
            if module and module not in self.ALLOWED_MODULES and not module.startswith('_'):
                # 对于不在白名单的模块，检查是否是常用的安全库
                safe_third_party = [
                    'pandas', 'numpy', 'requests', 'matplotlib',
                    'seaborn', 'plotly', 'scipy', 'sklearn',
                    'tensorflow', 'torch', 'keras', 'PIL',
                    'dateutil', 'pytz', 'babel', 'faker',
                ]
                if module not in safe_third_party:
                    return False, f'安全限制: 禁止导入模块 {module}'

        return True, ''

    def _execute_with_docker(self, code: str, timeout: int) -> Dict[str, Any]:
        """
        使用 Docker 容器执行 Python 代码

        Args:
            code: Python 代码
            timeout: 超时时间（秒）

        Returns:
            dict: { stdout, stderr, exitCode }
        """
        # 在用户代码前添加预导入模块
        full_code = self.PREIMPORTED_MODULES + '\n' + code

        try:
            import docker
        except ImportError:
            # Docker SDK 未安装，使用 subprocess 方式
            return self._execute_with_subprocess(full_code, timeout)

        try:
            client = docker.from_env()

            # 运行容器
            result = client.containers.run(
                image='python:3.11-slim',
                command=['python3', '-c', full_code],
                mem_limit='128m',           # 限制内存 128MB
                cpu_period=100000,
                cpu_quota=50000,            # 限制 0.5 CPU
                network_disabled=True,      # 禁用网络
                read_only=True,             # 只读文件系统
                tmpfs={'/tmp': 'size=10m'}, # 临时文件系统
                stdout=True,
                stderr=True,
                remove=True,
                timeout=timeout
            )

            return {
                'stdout': result.decode('utf-8', errors='replace') if result else '',
                'stderr': '',
                'exitCode': 0
            }

        except docker.errors.ContainerError as e:
            stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else '执行错误'
            return {
                'stdout': '',
                'stderr': stderr,
                'exitCode': e.exit_status
            }
        except docker.errors.TimeoutError:
            return {
                'stdout': '',
                'stderr': f'执行超时（{timeout}秒）',
                'exitCode': -1
            }
        except Exception as e:
            # Docker 不可用，回退到 subprocess 方式（注意：full_code 已在上面构造）
            return self._execute_with_subprocess(code, timeout)

    def _execute_with_subprocess(self, code: str, timeout: int) -> Dict[str, Any]:
        """
        使用 subprocess 执行 Python 代码（备用方案）

        Args:
            code: Python 代码
            timeout: 超时时间（秒）

        Returns:
            dict: { stdout, stderr, exitCode }
        """
        # 在用户代码前添加预导入模块
        full_code = self.PREIMPORTED_MODULES + '\n' + code

        python_cmd = self._get_python_command()

        try:
            # 使用 subprocess 运行 Python
            result = subprocess.run(
                [python_cmd, '-c', full_code],
                capture_output=True,
                text=True,
                timeout=timeout,
                # 不继承父进程的环境变量，只保留必要的
                env={
                    'PYTHONPATH': '',
                }
            )

            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exitCode': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                'stdout': '',
                'stderr': f'执行超时（{timeout}秒）',
                'exitCode': -1
            }
        except FileNotFoundError:
            return {
                'stdout': '',
                'stderr': f'Python 解释器未找到: {python_cmd}',
                'exitCode': -1
            }
        except Exception as e:
            return {
                'stdout': '',
                'stderr': f'执行错误: {str(e)}',
                'exitCode': -1
            }

    async def execute(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        """
        执行 Python 代码

        Args:
            code: Python 代码
            timeout: 超时时间（秒）

        Returns:
            dict: { success, stdout, stderr, exitCode }
        """
        # 安全检查
        is_safe, error_msg = self._is_safe_code(code)
        if not is_safe:
            return {
                'success': False,
                'stdout': '',
                'stderr': error_msg,
                'exitCode': 1
            }

        # 在线程池中执行（避免阻塞）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._execute_with_docker(code, timeout)
        )

        result['success'] = result.get('exitCode') == 0
        return result
