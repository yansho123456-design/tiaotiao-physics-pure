#!/usr/bin/env python3
"""
Zero-dependency Mobile & Cloud-Sandbox Single-File HTML Builder.
Uses ONLY Python 3 standard library (no playwright, no ffmpeg, no edge-tts).
Ideal for Doubao Mobile, WorkBuddy, Qwen, and any restricted sandbox:
- Estimates 1.3x Chinese narration timing (~5.8 chars/sec) into window.TIMELINE
- Embeds 16:9 Canvas engine + scene animations + Base64 assets into one ~50KB HTML
- Plays synchronized voiceover via browser Web Speech API (rate=1.3, zh-CN) + Web Audio SFX
- Supports one-click client-side video recording via Canvas captureStream + MediaRecorder
"""
import base64
import json
import mimetypes
import os
import re
import sys


def file_to_data_uri(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    mime = mime or "application/octet-stream"
    raw = open(path, "rb").read()
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def estimate_timeline(script_data: dict) -> dict:
    """Estimate 1.3x speech durations (~5.8 chars/s + pauses) purely in Python stdlib."""
    cur_t = 0.5
    scenes_out = []
    for s_idx, sc in enumerate(script_data.get("scenes", [])):
        sc_start = cur_t
        if s_idx > 0:
            cur_t += 0.4
        lines_out = []
        for ln in sc.get("lines", []):
            zh = ln["zh"]
            # Count effective spoken units (Chinese chars / digits / words)
            chars = len(re.sub(r"\s+", "", zh))
            dur = max(1.6, round(chars / 5.8, 2))
            line_start = round(cur_t, 3)
            line_end = round(cur_t + dur, 3)
            lines_out.append({"zh": zh, "en": ln.get("en", ""), "start": line_start, "end": line_end})
            cur_t += dur + 0.25
        sc_end = round(cur_t + 0.3, 3)
        cur_t = sc_end
        scenes_out.append({"id": sc["id"], "start": round(sc_start, 3), "end": sc_end, "lines": lines_out})
    return {"duration": round(cur_t + 0.6, 3), "fps": 30, "preview_only": True, "mobile_tts": True, "scenes": scenes_out}


def load_course_tags(anim_js: str) -> dict:
    m = re.search(r"window\.COURSE_TAGS\s*=\s*(\{.*?\});", anim_js, re.S)
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
        print("用法: python3 build_mobile_html.py <课题目录> [输出.html]")
        return 2
    lesson_dir = os.path.abspath(sys.argv[1])
    base_name = os.path.basename(lesson_dir)
    out_html = (
        os.path.abspath(sys.argv[2])
        if len(sys.argv) >= 3
        else os.path.join(lesson_dir, f"{base_name}_mobile.html")
    )

    script_data = json.load(open(os.path.join(lesson_dir, "script.json"), encoding="utf-8"))
    tl = estimate_timeline(script_data)
    engine_js = open(os.path.join(lesson_dir, "engine.js"), encoding="utf-8").read()
    phys_js = open(os.path.join(lesson_dir, "phys.js"), encoding="utf-8").read()
    anim_js = open(os.path.join(lesson_dir, "anim.js"), encoding="utf-8").read()

    # Inline assets/* into anim_js
    assets_dir = os.path.join(lesson_dir, "assets")
    if os.path.isdir(assets_dir):
        for fname in os.listdir(assets_dir):
            fpath = os.path.join(assets_dir, fname)
            if os.path.isfile(fpath):
                anim_js = anim_js.replace(f"assets/{fname}", file_to_data_uri(fpath))

    tl_json = json.dumps(tl, ensure_ascii=False)
    tags = load_course_tags(anim_js)
    chapters = [
        {
            "id": sc["id"],
            "label": f"{tags.get(sc['id'], [sc['id'], sc['id']])[0]} {tags.get(sc['id'], [sc['id'], sc['id']])[1]}",
            "start": sc["start"],
            "end": sc["end"],
        }
        for sc in tl["scenes"]
    ]

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>跳跳物理 · 跨设备课程播放器</title>
  <style>
    :root {{ --bg:#070910; --panel:#12172a; --border:rgba(88,196,221,0.28); --blue:#58C4DD; --gold:#F4D03F; --green:#83C167; --text:#ECEFF4; --muted:#94A3B8; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font-family:'PingFang SC','Microsoft YaHei',sans-serif; min-height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:10px; }}
    .shell {{ width:min(98vw, calc((100vh - 110px) * 16 / 9)); display:flex; flex-direction:column; gap:8px; }}
    .stage {{ width:100%; aspect-ratio:16/9; background:#0c0f1a; border:1px solid var(--border); border-radius:12px; overflow:hidden; box-shadow:0 16px 48px rgba(0,0,0,0.65); }}
    canvas#c {{ width:100%; height:100%; display:block; cursor:pointer; }}
    .bar {{ display:flex; flex-direction:column; gap:8px; padding:10px 14px; background:var(--panel); border:1px solid var(--border); border-radius:10px; }}
    input#seek {{ -webkit-appearance:none; appearance:none; width:100%; height:8px; border-radius:999px; background:rgba(255,255,255,0.16); outline:none; cursor:pointer; }}
    input#seek::-webkit-slider-thumb {{ -webkit-appearance:none; width:18px; height:18px; border-radius:50%; background:var(--gold); border:2px solid #0c0f1a; cursor:grab; }}
    .row {{ display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap; }}
    .left, .right {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
    button {{ background:rgba(88,196,221,0.16); color:var(--blue); border:1px solid rgba(88,196,221,0.4); border-radius:7px; padding:6px 12px; font-size:12.5px; font-weight:600; cursor:pointer; }}
    .chaps {{ display:flex; gap:5px; flex-wrap:wrap; }}
    .chap {{ padding:4px 9px; font-size:12px; border-radius:999px; background:rgba(255,255,255,0.06); color:var(--muted); border:1px solid rgba(255,255,255,0.12); }}
    .chap.cur {{ color:var(--gold); border-color:var(--gold); background:rgba(244,208,63,0.14); }}
    .tm {{ font-size:12.5px; font-variant-numeric:tabular-nums; color:var(--muted); }}
    .rec-btn {{ background:rgba(131,193,103,0.18); color:var(--green); border-color:var(--green); }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="stage"><canvas id="c" width="1920" height="1080"></canvas></div>
    <div class="bar">
      <input id="seek" type="range" min="0" max="1000" value="0" />
      <div class="row">
        <div class="left">
          <button id="play">▶ 播放（含语音）</button>
          <span class="tm" id="tm">00:00 / 00:00</span>
        </div>
        <div class="chaps" id="chapters"></div>
        <div class="right">
          <button id="rec" class="rec-btn">⬇️ 导出视频</button>
        </div>
      </div>
    </div>
  </div>
  <script>window.TIMELINE = {tl_json};</script>
  <script>{engine_js}</script>
  <script>{phys_js}</script>
  <script>{anim_js}</script>
  <script>
    (function () {{
      const tl = window.TIMELINE;
      const chapters = {json.dumps(chapters, ensure_ascii=False)};
      const seek = document.getElementById("seek");
      const tm = document.getElementById("tm");
      const btnPlay = document.getElementById("play");
      const chapBox = document.getElementById("chapters");
      const fmt = (s) => `${{String(Math.floor(s/60)).padStart(2,"0")}}:${{String(Math.floor(s)%60).padStart(2,"0")}}`;

      // Web Audio SFX synthesizer (zero external files)
      let audioCtx = null;
      function playSfx(freq, dur = 0.16) {{
        try {{
          if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          const osc = audioCtx.createOscillator();
          const gain = audioCtx.createGain();
          osc.type = "sine"; osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
          gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + dur);
          osc.connect(gain); gain.connect(audioCtx.destination);
          osc.start(); osc.stop(audioCtx.currentTime + dur);
        }} catch (e) {{}}
      }}

      // Web Speech API 1.3x voiceover sync
      let lastSpokenKey = "";
      function syncSpeech(t, playing) {{
        if (!playing || !("speechSynthesis" in window)) return;
        for (const sc of tl.scenes) {{
          for (let i = 0; i < sc.lines.length; i++) {{
            const ln = sc.lines[i];
            const key = sc.id + "_" + i;
            if (t >= ln.start && t <= ln.start + 0.35 && lastSpokenKey !== key) {{
              lastSpokenKey = key;
              window.speechSynthesis.cancel();
              const u = new SpeechSynthesisUtterance(ln.zh);
              u.lang = "zh-CN";
              u.rate = 1.3;
              window.speechSynthesis.speak(u);
              playSfx(i === 0 ? 520 : 780, 0.14);
            }}
          }}
        }}
      }}

      const chapEls = [];
      chapters.forEach((ch) => {{
        const b = document.createElement("button");
        b.className = "chap"; b.textContent = ch.label;
        b.addEventListener("click", () => {{
          lastSpokenKey = "";
          if ("speechSynthesis" in window) window.speechSynthesis.cancel();
          engine.seek(ch.start + 0.01);
        }});
        chapBox.appendChild(b);
        chapEls.push({{ el: b, start: ch.start, end: ch.end }});
      }});

      let isDragging = false;
      const engine = new CourseEngine3B1B(document.getElementById("c"), {{
        timeline: tl, SC: window.COURSE_SCENES || {{}}, tags: window.COURSE_TAGS || {{}},
        onUpdate(t, dur, playing) {{
          if (!isDragging) seek.value = dur > 0 ? Math.round((t / dur) * 1000) : 0;
          tm.textContent = `${{fmt(t)}} / ${{fmt(dur)}}`;
          btnPlay.textContent = playing ? "⏸ 暂停" : "▶ 播放（含语音）";
          chapEls.forEach((c) => c.el.classList.toggle("cur", t >= c.start && t < c.end));
          syncSpeech(t, playing);
        }},
      }});

      function togglePlay() {{
        if (engine.playing) {{
          engine.pause();
          if ("speechSynthesis" in window) window.speechSynthesis.cancel();
        }} else {{
          lastSpokenKey = "";
          engine.play();
        }}
      }}
      document.getElementById("c").addEventListener("click", togglePlay);
      btnPlay.addEventListener("click", togglePlay);

      seek.addEventListener("pointerdown", () => {{ isDragging = true; engine.pause(); if ("speechSynthesis" in window) window.speechSynthesis.cancel(); }});
      seek.addEventListener("input", () => {{ engine.seek((parseFloat(seek.value) / 1000) * engine.duration); }});
      seek.addEventListener("change", () => {{ isDragging = false; lastSpokenKey = ""; }});

      // Client-side Canvas video export (works without server ffmpeg)
      document.getElementById("rec").addEventListener("click", () => {{
        const canvas = document.getElementById("c");
        if (!canvas.captureStream || !window.MediaRecorder) {{
          alert("当前浏览器不支持直接录屏导出，请用 Chrome/Edge 或使用网页另存为保存本 HTML 文件。");
          return;
        }}
        const stream = canvas.captureStream(24);
        const rec = new MediaRecorder(stream, {{ mimeType: "video/webm" }});
        const chunks = [];
        rec.ondataavailable = (e) => {{ if (e.data.size) chunks.push(e.data); }};
        rec.onstop = () => {{
          const url = URL.createObjectURL(new Blob(chunks, {{ type: "video/webm" }}));
          const a = document.createElement("a"); a.href = url; a.download = "{base_name}.webm"; a.click();
        }};
        engine.seek(0); engine.play(); rec.start();
        setTimeout(() => {{ if (rec.state === "recording") rec.stop(); }}, Math.ceil(tl.duration * 1000) + 300);
      }});

      engine.render();
    }})();
  </script>
</body>
</html>"""
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] 已生成零依赖跨设备 HTML (支持手机豆包/WorkBuddy/千问): {out_html} ({os.path.getsize(out_html)/1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
