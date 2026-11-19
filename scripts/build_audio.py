#!/usr/bin/env python3
"""
Synthesize scene-by-scene 1.3x narration audio + shared BGM + SFX for tiaotiao-physics-pure.
Includes an automatic content guardrail that blocks course-citation leaks (e.g. 必修3, 第55讲, 讲义, 母题)
and meta-jargon (3B1B, 动态重构) while preserving Tiaotiao IP phrases (跳跳学长, 跳跳大招, 跳跳避坑指南).
"""
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

REF_WAV = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "references", "voice_ref", "ref_voice.wav"))
AUDIO_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "references", "audio_lib"))
GEN_LIB_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_audio_lib.py")

FORBIDDEN_PATTERNS = [
    (r"必修\s*[123一二三]", "禁止出现课程模块名（如必修1/2/3）"),
    (r"选修\s*[123一二三]?", "禁止出现课程模块名（如选修）"),
    (r"第\s*\d+\s*讲", "禁止出现具体讲次（如第55讲）"),
    (r"讲义|课上|板书|母题", "禁止出现过去课堂/讲义/板书/母题字样"),
    (r"bixiu|xuanxiu|dongliang|dianci|jiaobian", "禁止出现内部课程代号"),
    (r"3B1B|3Blue1Brown|动态原题|动态重构|矢量重构", "禁止出现风格/技术自述文字"),
]

REPLACEMENTS = [
    (r"v[₀_0]+", "初速度 v 零"),
    (r"v[ₜ_t]+", "末速度 v t"),
    (r"E_p0", "E p 零"),
    (r"E_p", "E p"),
    (r"x_0", "x 零"),
    (r"m/s²|m/s\^2", "米每二次方秒"),
    (r"m/s", "米每秒"),
    (r"Δx", "位移变化量 delta x"),
    (r"Δv", "速度变化量 delta v"),
    (r"Δt", "delta t"),
    (r"μ", "动摩擦因数 miu"),
    (r"ρ", "电阻率 rou"),
    (r"ω", "角速度 omega"),
    (r"θ", "夹角 theta"),
]


def check_guardrails(lesson_dir: str) -> None:
    """Scan script.json and visible string literals in anim.js for forbidden course-citation or meta-jargon leaks."""
    violations = []
    str_lit_re = re.compile(r'(["\'])(?:\\.|(?!\1).)*\1|`(?:\\.|[^`])*`')
    for fname in ("script.json", "anim.js"):
        fpath = os.path.join(lesson_dir, fname)
        if not os.path.exists(fpath):
            continue
        lines = open(fpath, encoding="utf-8").read().splitlines()
        for lineno, line in enumerate(lines, 1):
            targets = [line] if fname == "script.json" else [m.group(0) for m in str_lit_re.finditer(line)]
            for target in targets:
                for pat, reason in FORBIDDEN_PATTERNS:
                    m = re.search(pat, target, re.IGNORECASE)
                    if m:
                        violations.append(f"{fname}:{lineno} 命中「{m.group(0)}」→ {reason}")
    if violations:
        print("[GUARDRAIL BLOCKED] 检测到禁用课程溯源词或技术自述词：", file=sys.stderr)
        for v in violations:
            print("  -", v, file=sys.stderr)
        raise SystemExit(3)


def get_ffmpeg() -> str:
    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        return sys_ff
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def ensure_audio_lib() -> None:
    bgm = os.path.join(AUDIO_LIB, "bgm_3b1b_ambient.wav")
    if not os.path.exists(bgm):
        subprocess.run([sys.executable, GEN_LIB_PY, AUDIO_LIB], check=True)


def normalize_physics_tts(text: str) -> str:
    out = text
    for pat, rep in REPLACEMENTS:
        out = re.sub(pat, rep, out)
    return out


def probe_duration(ffmpeg_exe: str, audio_path: str) -> float:
    proc = subprocess.run([ffmpeg_exe, "-i", audio_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 2.5


def fmt_srt_time(sec: float) -> str:
    ms = int(round((sec % 1) * 1000))
    total = int(sec)
    return f"{total // 3600:02d}:{(total // 60) % 60:02d}:{total % 60:02d},{ms:03d}"


def synth_custom_clone_api(text: str, out_path: str) -> bool:
    endpoint = os.environ.get("TTS_CLONE_ENDPOINT")
    if not endpoint or not os.path.exists(REF_WAV):
        return False
    payload = json.dumps({"text": text, "ref_audio_path": REF_WAV}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("TTS_CLONE_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(out_path, "wb") as f:
            f.write(resp.read())
    return True


async def synth_edge_tts(text: str, out_path: str) -> None:
    import edge_tts
    comm = edge_tts.Communicate(text, "zh-CN-YunxiNeural", rate="+30%")
    await comm.save(out_path)


def postprocess_segment(ffmpeg_exe: str, raw_path: str, final_path: str, extra_atempo: float = 1.0) -> None:
    af = "silenceremove=start_periods=1:start_silence=0.04:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_silence=0.06:start_threshold=-45dB,areverse"
    if abs(extra_atempo - 1.0) > 1e-3:
        af = f"atempo={extra_atempo:.3f}," + af
    subprocess.run([ffmpeg_exe, "-y", "-i", raw_path, "-af", af, "-ar", "24000", "-ac", "1", final_path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python3 build_audio.py <课题目录>")
        return 2
    lesson_dir = os.path.abspath(sys.argv[1])
    check_guardrails(lesson_dir)

    script_path = os.path.join(lesson_dir, "script.json")
    ensure_audio_lib()
    ffmpeg_exe = get_ffmpeg()
    data = json.load(open(script_path, encoding="utf-8"))
    build_dir = os.path.join(lesson_dir, "build")
    seg_dir = os.path.join(build_dir, "segs")
    os.makedirs(seg_dir, exist_ok=True)

    use_cloud = bool(os.environ.get("TTS_CLONE_ENDPOINT"))
    cur_t = 0.5
    timeline_scenes, voice_items, sfx_items, srt_lines = [], [], [], []
    srt_idx = 1

    sfx_map = {
        "whoosh": os.path.join(AUDIO_LIB, "sfx_whoosh.wav"),
        "pop": os.path.join(AUDIO_LIB, "sfx_pop.wav"),
        "write": os.path.join(AUDIO_LIB, "sfx_write.wav"),
        "ding": os.path.join(AUDIO_LIB, "sfx_ding.wav"),
    }

    for s_idx, sc in enumerate(data.get("scenes", [])):
        sc_start = cur_t
        if s_idx > 0:
            sfx_items.append({"file": sfx_map["whoosh"], "start": round(cur_t, 3), "vol": 0.42})
            cur_t += 0.35
        sc_lines = []
        for l_idx, ln in enumerate(sc.get("lines", [])):
            zh = ln["zh"]
            spoken = normalize_physics_tts(ln.get("spoken", zh))
            raw_file = os.path.join(seg_dir, f"{sc['id']}_{l_idx}_raw.mp3")
            seg_file = os.path.join(seg_dir, f"{sc['id']}_{l_idx}.wav")
            if use_cloud:
                synth_custom_clone_api(spoken, raw_file)
                postprocess_segment(ffmpeg_exe, raw_file, seg_file, extra_atempo=1.3)
            else:
                asyncio.run(synth_edge_tts(spoken, raw_file))
                postprocess_segment(ffmpeg_exe, raw_file, seg_file, extra_atempo=1.0)
            dur = probe_duration(ffmpeg_exe, seg_file)
            line_start, line_end = round(cur_t, 3), round(cur_t + dur, 3)
            sc_lines.append({"zh": zh, "en": ln.get("en", ""), "start": line_start, "end": line_end})
            voice_items.append({"file": seg_file, "start": line_start, "vol": 1.0})

            sfx_type = ln.get("sfx")
            if not sfx_type:
                if sc["id"] == "intro" and l_idx > 0:
                    sfx_type = "pop"
                elif sc["id"] == "formula" and l_idx in (0, 1):
                    sfx_type = "write"
                elif sc["id"] == "formula" and l_idx == len(sc["lines"]) - 1:
                    sfx_type = "ding"
            if sfx_type and sfx_type in sfx_map:
                sfx_items.append({"file": sfx_map[sfx_type], "start": round(line_start + 0.08, 3), "vol": 0.38})

            srt_lines.append(f"{srt_idx}\n{fmt_srt_time(line_start)} --> {fmt_srt_time(line_end)}\n{zh}\n")
            srt_idx += 1
            cur_t += dur + 0.22
        sc_end = round(cur_t + 0.25, 3)
        cur_t = sc_end
        timeline_scenes.append({"id": sc["id"], "start": round(sc_start, 3), "end": sc_end, "lines": sc_lines})

    total_dur = round(cur_t + 0.6, 3)
    voice_sfx_wav = os.path.join(build_dir, "voice_sfx.wav")
    all_events = voice_items + sfx_items
    cmd = [ffmpeg_exe, "-y", "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono:d={total_dur}"]
    filters, mix_labels = [], ["[0:a]"]
    for i, item in enumerate(all_events, 1):
        cmd.extend(["-i", item["file"]])
        delay_ms = int(round(item["start"] * 1000))
        filters.append(f"[{i}:a]aresample=24000,volume={item.get('vol', 1.0):.2f},adelay={delay_ms}|{delay_ms}[a{i}]")
        mix_labels.append(f"[a{i}]")
    filters.append(f"{''.join(mix_labels)}amix=inputs={len(all_events) + 1}:normalize=0[aout]")
    cmd.extend(["-filter_complex", ";".join(filters), "-map", "[aout]", "-t", str(total_dur), voice_sfx_wav])
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    bgm_wav = os.path.join(AUDIO_LIB, "bgm_3b1b_ambient.wav")
    mix_wav = os.path.join(build_dir, "mix.wav")
    fade_out_start = max(0.5, total_dur - 2.2)
    bgm_filter = f"[1:a]aresample=24000,volume=0.14,afade=t=in:st=0:d=1.2,afade=t=out:st={fade_out_start:.2f}:d=2.0[bgm];[0:a][bgm]amix=inputs=2:duration=first:normalize=0[out]"
    subprocess.run([ffmpeg_exe, "-y", "-i", voice_sfx_wav, "-stream_loop", "-1", "-i", bgm_wav,
                    "-filter_complex", bgm_filter, "-map", "[out]", "-t", str(total_dur), mix_wav],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    tl_obj = {"duration": total_dur, "fps": 30, "preview_only": False, "scenes": timeline_scenes}
    with open(os.path.join(build_dir, "timeline.js"), "w", encoding="utf-8") as f:
        f.write("window.TIMELINE=" + json.dumps(tl_obj, ensure_ascii=False) + ";\n")
    with open(os.path.join(build_dir, "narration.srt"), "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    print(f"[OK] 禁用词检查通过，已生成 1.3x 人声 + BGM + 音效音轨: {mix_wav} ({total_dur:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
