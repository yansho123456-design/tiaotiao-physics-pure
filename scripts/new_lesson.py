#!/usr/bin/env python3
"""Initialize a 4-scene pure course video workspace from templates/."""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, "..", "templates")


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python3 scripts/new_lesson.py <课题输出目录>")
        return 2
    out_dir = os.path.abspath(sys.argv[1])
    os.makedirs(os.path.join(out_dir, "assets"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "build"), exist_ok=True)

    for fname in ("index.html", "engine.js", "phys.js", "anim.js", "script.json"):
        src = os.path.join(TEMPLATES, fname)
        dst = os.path.join(out_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)

    print(f"[OK] 已初始化 4 幕纯净全动画课程目录: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
