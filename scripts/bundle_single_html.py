#!/usr/bin/env python3
"""Build unified single-file course HTML (<lesson_name>_course.html) for tiaotiao-physics-pure."""
import base64
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_timeline(lesson_dir: str) -> dict:
    tl_js = os.path.join(lesson_dir, "build", "timeline.js")
    text = open(tl_js, encoding="utf-8").read()
    m = re.search(r"window\.TIMELINE\s*=\s*(\{.*\})\s*;?\s*$", text, re.S)
    return json.loads(m.group(1)) if m else {"duration": 60, "scenes": []}


def load_course_tags(lesson_dir: str) -> dict:
    anim_js = os.path.join(lesson_dir, "anim.js")
    if not os.path.exists(anim_js):
        return {}
    text = open(anim_js, encoding="utf-8").read()
    m = re.search(r"window\.COURSE_TAGS\s*=\s*(\{.*?\});", text, re.S)
    if not m:
        return {}
    tags = {}
    for line in m.group(1).splitlines():
        km = re.search(r'(\w+)\s*:\s*\[\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\]', line)
        if km:
            tags[km.group(1)] = [km.group(2), km.group(3)]
    return tags


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python3 bundle_single_html.py <课题目录> [输出单文件.html]")
        return 2
    lesson_dir = os.path.abspath(sys.argv[1])
    base_name = os.path.basename(lesson_dir)
    mp4_path = os.path.join(lesson_dir, f"{base_name}.mp4")

    if not os.path.exists(mp4_path):
        print("[INFO] 正在先渲染 1080p MP4 视频...")
        subprocess.run([sys.executable, os.path.join(HERE, "render_video.py"), lesson_dir], check=True)

    out_html = (
        os.path.abspath(sys.argv[2])
        if len(sys.argv) >= 3
        else os.path.join(lesson_dir, f"{base_name}_course.html")
    )

    tl = load_timeline(lesson_dir)
    tags = load_course_tags(lesson_dir)
    mp4_b64 = base64.b64encode(open(mp4_path, "rb").read()).decode("ascii")

    chapters_data = []
    for sc in tl.get("scenes", []):
        sid = sc["id"]
        t_pair = tags.get(sid, [sid, sid])
        chapters_data.append({"id": sid, "label": f"{t_pair[0]} {t_pair[1]}", "start": sc["start"], "end": sc["end"]})

    chapters_json = json.dumps(chapters_data, ensure_ascii=False)
    dl_filename = f"{base_name}.mp4"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>跳跳学长 · 物理微课讲解视频</title>
  <style>
    :root {{
      --bg: #070910; --panel: #12172a; --border: rgba(88, 196, 221, 0.28);
      --blue: #58C4DD; --gold: #F4D03F; --green: #83C167; --text: #ECEFF4; --muted: #94A3B8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; background: var(--bg); color: var(--text);
      font-family: 'PingFang SC', 'Microsoft YaHei', Inter, sans-serif;
      min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 12px;
    }}
    .player-shell {{ width: min(96vw, calc((100vh - 88px) * 16 / 9)); display: flex; flex-direction: column; gap: 10px; }}
    .stage-frame {{
      width: 100%; aspect-ratio: 16 / 9; background: #0c0f1a; border: 1px solid var(--border);
      border-radius: 12px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.65); position: relative;
    }}
    video#v {{ width: 100%; height: 100%; display: block; background: #0c0f1a; outline: none; }}
    .player-bar {{
      display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 16px;
      background: var(--panel); border: 1px solid var(--border); border-radius: 10px; flex-wrap: wrap;
    }}
    .chap-pills {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    button.chap-pill {{
      padding: 5px 11px; font-size: 12.5px; font-weight: 600; border-radius: 999px;
      background: rgba(255,255,255,0.06); color: var(--muted); border: 1px solid rgba(255,255,255,0.14);
      cursor: pointer; transition: all 0.15s;
    }}
    button.chap-pill:hover {{ background: rgba(88, 196, 221, 0.18); color: var(--text); }}
    button.chap-pill.current {{ color: var(--gold); border-color: var(--gold); background: rgba(244, 208, 63, 0.15); }}
    .right-tools {{ display: flex; align-items: center; gap: 10px; }}
    .hint {{ font-size: 12px; color: var(--muted); }}
    a.dl-btn {{
      text-decoration: none; background: rgba(131, 193, 103, 0.18); color: var(--green);
      border: 1px solid var(--green); padding: 5px 12px; border-radius: 7px; font-size: 12.5px; font-weight: 600;
    }}
  </style>
</head>
<body>
  <div class="player-shell">
    <div class="stage-frame"><video id="v" controls playsinline preload="auto"></video></div>
    <div class="player-bar">
      <div class="chap-pills" id="chapters"></div>
      <div class="right-tools">
        <span class="hint">💡 可直接在画面上<b>右键 → 将视频另存为</b></span>
        <a id="dl-link" class="dl-btn" download="{dl_filename}" href="#">⬇️ 下载 MP4 视频</a>
      </div>
    </div>
  </div>
  <script>
    (function () {{
      const CHAPTERS = {chapters_json};
      const B64_MP4 = "{mp4_b64}";
      const bin = atob(B64_MP4);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const blobUrl = URL.createObjectURL(new Blob([bytes], {{ type: "video/mp4" }}));
      const v = document.getElementById("v");
      v.src = blobUrl;
      document.getElementById("dl-link").href = blobUrl;
      const chapBox = document.getElementById("chapters"), chapEls = [];
      CHAPTERS.forEach((ch) => {{
        const b = document.createElement("button");
        b.className = "chap-pill";
        b.textContent = ch.label;
        b.addEventListener("click", () => {{ v.currentTime = ch.start + 0.05; v.play().catch(() => {{}}); }});
        chapBox.appendChild(b);
        chapEls.push({{ el: b, start: ch.start, end: ch.end }});
      }});
      v.addEventListener("timeupdate", () => {{
        const t = v.currentTime;
        chapEls.forEach((c) => c.el.classList.toggle("current", t >= c.start && t < c.end));
      }});
    }})();
  </script>
</body>
</html>"""
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] 已生成跨设备单文件 HTML: {out_html} ({os.path.getsize(out_html)/(1024*1024):.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
