#!/usr/bin/env python3
"""High-speed parallel 1920x1080 MP4 video exporter for tiaotiao-physics-pure."""
import asyncio
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time


def get_ffmpeg() -> str:
    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        return sys_ff
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def load_timeline(lesson_dir: str) -> dict:
    tl_js = os.path.join(lesson_dir, "build", "timeline.js")
    text = open(tl_js, encoding="utf-8").read()
    m = re.search(r"window\.TIMELINE\s*=\s*(\{.*\})\s*;?\s*$", text, re.S)
    if not m:
        raise RuntimeError(f"无法解析 {tl_js}")
    return json.loads(m.group(1))


async def render_chunk(browser, html_url: str, ffmpeg_exe: str, f0: int, f1: int, fps: int, out_chunk: str, wid: int) -> None:
    page = await browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    await page.goto(html_url, wait_until="load")
    await page.wait_for_timeout(300)
    canvas = page.locator("#c")

    cmd = [
        ffmpeg_exe, "-y", "-loglevel", "error",
        "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg", "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
        "-r", str(fps), out_chunk,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(f0, f1):
        sec = f / fps
        await page.evaluate(f"window.__renderAtTime({sec:.6f})")
        buf = await canvas.screenshot(type="jpeg", quality=92)
        proc.stdin.write(buf)
        if (f - f0) > 0 and (f - f0) % 240 == 0:
            print(f"  [worker {wid}] {f - f0}/{f1 - f0} 帧 ({time.time() - t0:.1f}s)")
    proc.stdin.close()
    ret = proc.wait()
    await page.close()
    if ret != 0:
        raise RuntimeError(f"ffmpeg chunk {wid} exited with {ret}")


async def async_main() -> int:
    if len(sys.argv) < 2:
        print("用法: python3 render_video.py <课题目录> [--fps 20] [--workers 6]")
        return 2
    lesson_dir = os.path.abspath(sys.argv[1])
    fps = 20
    workers = 6
    if "--fps" in sys.argv:
        fps = int(sys.argv[sys.argv.index("--fps") + 1])
    if "--workers" in sys.argv:
        workers = int(sys.argv[sys.argv.index("--workers") + 1])

    from playwright.async_api import async_playwright

    tl = load_timeline(lesson_dir)
    duration = float(tl["duration"])
    total_frames = max(1, int(math.ceil(duration * fps)))
    per = int(math.ceil(total_frames / workers))
    build_dir = os.path.join(lesson_dir, "build")
    ffmpeg_exe = get_ffmpeg()
    html_url = f"file://{os.path.join(lesson_dir, 'index.html')}?mode=video"

    print(f"[1/2] 启动 {workers} 个并行渲染器录制 1920x1080 视频 ({total_frames} 帧, {fps} fps, {duration:.1f}s)...")
    t_start = time.time()
    chunks = []
    async with async_playwright() as p:
        args = ["--allow-file-access-from-files", "--disable-web-security", "--font-render-hinting=none"]
        try:
            browser = await p.chromium.launch(channel="chrome", args=args)
        except Exception:
            browser = await p.chromium.launch(args=args)

        tasks = []
        for i in range(workers):
            f0 = i * per
            f1 = min(total_frames, (i + 1) * per)
            if f0 < f1:
                cfile = os.path.join(build_dir, f"chunk_{i}.mp4")
                chunks.append(cfile)
                tasks.append(render_chunk(browser, html_url, ffmpeg_exe, f0, f1, fps, cfile, i))
        await asyncio.gather(*tasks)
        await browser.close()

    print(f"[2/2] 分片录制完成 ({time.time() - t_start:.1f}s)，正在合并含 BGM/音效的音轨生成 MP4...")
    concat_txt = os.path.join(build_dir, "chunks.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(f"file '{c}'\n")

    out_mp4 = os.path.join(lesson_dir, f"{os.path.basename(lesson_dir)}.mp4")
    mix_wav = os.path.join(build_dir, "mix.wav")
    cmd = [
        ffmpeg_exe, "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", concat_txt,
        "-i", mix_wav,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        out_mp4,
    ]
    subprocess.run(cmd, check=True)
    for c in chunks:
        try:
            os.remove(c)
        except OSError:
            pass
    try:
        os.remove(concat_txt)
    except OSError:
        pass

    size_mb = os.path.getsize(out_mp4) / (1024 * 1024)
    print(f"[OK] 1080p MP4 视频已生成: {out_mp4} ({size_mb:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
