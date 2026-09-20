"""旧命令转到唯一实现，不继续维护 SQLite 运行流程。"""

import sys


def run(command):
    from .cli import main

    args = sys.argv[1:]
    if command == "run" and "--skip-sources" in args:
        command = "collect"
        args = [x for x in args if x != "--skip-sources"]
    print(f"兼容入口：请改用 python -m crawler {command}", file=sys.stderr)
    return main([command] + args)
