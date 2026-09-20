from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .links import normalize
from .render import render_readme


def export_readme(store, output: Path, allow_empty=False):
    rows = store.export_rows()
    # 白名单豁免业务过滤，不豁免安全的文本/URL 输出。
    if any(
        not normalize(row["url"]) or row["type"] not in ("channel", "group", "bot")
        for row in rows
    ):
        raise ValueError("导出资料含无效类型或地址，未覆盖现有文件")
    if not rows and not allow_empty:
        raise ValueError(
            "没有可导出的资料，未覆盖现有目录；确需导出空目录时使用 --allow-empty"
        )
    content = render_readme(rows)
    if (
        not content.endswith("\n")
        or rows
        and "| 名称 | 链接 | 人数 | 简介 |" not in content
    ):
        raise ValueError("导出内容校验失败，未覆盖现有文件")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output.parent, delete=False
        ) as handle:
            temp = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, output)
    finally:
        if temp and temp.exists():
            temp.unlink()
    return len(rows)
