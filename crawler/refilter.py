#!/usr/bin/env python3
"""旧命令兼容入口，新流程统一使用 python -m crawler refilter。"""
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from crawler.legacy import run
    raise SystemExit(run('refilter'))
