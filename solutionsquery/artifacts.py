from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List, Sequence

FILE_BLOCK_RE = re.compile(r"```file\s+([^\n`]+)\n(.*?)```", re.DOTALL)


@dataclass
class FileOp:
    path: str
    content: str


def parse_file_blocks(text: str) -> List[FileOp]:
    ops: List[FileOp] = []
    for match in FILE_BLOCK_RE.finditer(text):
        path = match.group(1).strip().strip('"').strip("'")
        content = match.group(2)
        if content.startswith("\n"):
            content = content[1:]
        if path:
            ops.append(FileOp(path=path, content=content))
    return ops


def safe_resolve(root: str, rel_path: str) -> str:
    if not rel_path or rel_path != rel_path.strip() or "\x00" in rel_path:
        raise ValueError(f"Invalid file path: {rel_path!r}")
    if os.path.isabs(rel_path) or rel_path.startswith("~"):
        raise ValueError(f"Absolute paths are not allowed: {rel_path!r}")
    root_abs = os.path.abspath(root)
    target = os.path.abspath(os.path.join(root_abs, rel_path))
    if target != root_abs and not target.startswith(root_abs + os.sep):
        raise ValueError(f"Path escapes the project root: {rel_path!r}")
    return target


def write_file_ops(root: str, ops: Sequence[FileOp]) -> List[str]:
    written: List[str] = []
    for op in ops:
        target = safe_resolve(root, op.path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(op.content)
        written.append(op.path)
    return written
