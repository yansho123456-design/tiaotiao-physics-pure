#!/usr/bin/env python3
"""
Portable knowledge-base search script for tiaotiao-physics-pure.
"""
from __future__ import annotations
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.abspath(os.path.join(HERE, ".."))


def resolve_tiaotiao_dir() -> str | None:
    candidates = [
        os.environ.get("TIAOTIAO_PHYSICS_DIR", ""),
        os.path.abspath(os.path.join(SKILL_ROOT, "..", "tiaotiao-physics")),
        os.path.abspath(os.path.join(SKILL_ROOT, "..", "tiaotiao-physics-lab")),
        os.path.expanduser("~/.gemini/config/skills/tiaotiao-physics"),
        os.path.expanduser("~/.gemini/config/skills/tiaotiao-physics-lab"),
    ]
    for c in candidates:
        if c and os.path.exists(os.path.join(c, "references", "INDEX.md")) and os.path.exists(os.path.join(c, "scripts", "find.py")):
            return c
    return None


def main() -> int:
    tdir = resolve_tiaotiao_dir()
    if not tdir:
        print("[ERROR] 未找到跳跳物理知识库。", file=sys.stderr)
        return 1
    find_py = os.path.join(tdir, "scripts", "find.py")
    args = sys.argv[1:]
    if not args:
        print("用法: python3 scripts/search_tiaotiao.py 关键词1 关键词2 [--top 8]")
        return 2
    proc = subprocess.run([sys.executable, find_py] + args, cwd=tdir)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
