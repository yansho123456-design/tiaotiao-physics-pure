#!/usr/bin/env python3
"""
Unified cross-platform course builder for desktop AND mobile sandboxes (Doubao, WorkBuddy, Qwen).
- If desktop tools (edge_tts + playwright + ffmpeg/imageio_ffmpeg) are available:
  builds 1.3x neural voice + 1080p MP4 embedded single-file HTML (<name>_course.html).
- Otherwise (mobile / cloud sandbox):
  automatically falls back to zero-dependency single-file HTML (<name>_course.html)
  using Web Speech API 1.3x voiceover + Web Audio SFX + 16:9 Canvas animation.
"""
import importlib.util
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def has_desktop_video_stack() -> bool:
    has_pw = importlib.util.find_spec("playwright") is not None
    has_tts = importlib.util.find_spec("edge_tts") is not None or bool(os.environ.get("TTS_CLONE_ENDPOINT"))
    has_ff = bool(shutil.which("ffmpeg")) or (importlib.util.find_spec("imageio_ffmpeg") is not None)
    return has_pw and has_tts and has_ff


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python3 scripts/build_course.py <课题目录>")
        return 2
    lesson_dir = os.path.abspath(sys.argv[1])
    base_name = os.path.basename(lesson_dir)
    out_html = os.path.join(lesson_dir, f"{base_name}_course.html")

    if has_desktop_video_stack():
        print("[MODE] 检测到完整桌面视频工具链 → 生成 1080p MP4 内嵌单文件 HTML")
        subprocess.run([sys.executable, os.path.join(HERE, "build_audio.py"), lesson_dir], check=True)
        subprocess.run([sys.executable, os.path.join(HERE, "bundle_single_html.py"), lesson_dir, out_html], check=True)
    else:
        print("[MODE] 检测到手机端/轻量沙盒环境（无 playwright/ffmpeg）→ 自动切换零依赖单文件 HTML 模式")
        subprocess.run([sys.executable, os.path.join(HERE, "build_mobile_html.py"), lesson_dir, out_html], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
