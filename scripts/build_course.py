#!/usr/bin/env python3
"""
Unified cross-platform course builder for desktop AND mobile (Doubao, WorkBuddy, Qwen).
Always produces:
1. <name>_web.html : lightweight (~40KB) 16:9 interactive Canvas + audio/Web-Speech page
   that opens reliably in mobile WebViews without heavy Base64 MP4 or blob: URLs.
2. <name>.mp4 + <name>_course.html (when playwright + ffmpeg + tts are available):
   native 1080p MP4 video file (playable directly in Doubao mobile!) + full embedded HTML.
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

    # 1. Always build the lightweight mobile-friendly web page (<name>_web.html)
    web_html = os.path.join(lesson_dir, f"{base_name}_web.html")
    subprocess.run([sys.executable, os.path.join(HERE, "build_mobile_html.py"), lesson_dir, web_html], check=True)

    # 2. If video toolchain is available, also build native MP4 + embedded course HTML
    if has_desktop_video_stack():
        mp4_path = os.path.join(lesson_dir, f"{base_name}.mp4")
        course_html = os.path.join(lesson_dir, f"{base_name}_course.html")
        print("[MODE] 检测到视频工具链 → 同时生成原生 1080p MP4 视频与桌面单文件 HTML")
        subprocess.run([sys.executable, os.path.join(HERE, "build_audio.py"), lesson_dir], check=True)
        subprocess.run([sys.executable, os.path.join(HERE, "bundle_single_html.py"), lesson_dir, course_html], check=True)
        print(f"[DELIVERABLES]\n  - 轻量网页: {web_html}\n  - MP4 视频: {mp4_path}\n  - 桌面全包: {course_html}")
    else:
        print(f"[DELIVERABLES] 轻量网页（手机端直接打开）: {web_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
