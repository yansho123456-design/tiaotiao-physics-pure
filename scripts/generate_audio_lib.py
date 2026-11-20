#!/usr/bin/env python3
"""
Generate a royalty-free, zero-copyright shared 3Blue1Brown-style BGM & SFX audio library
into references/audio_lib/ using pure Python standard library (wave, math, struct).
Files generated:
- bgm_3b1b_ambient.wav (32s loopable warm ambient synth/electric-piano chord progression)
- sfx_whoosh.wav       (0.45s soft air transition whoosh)
- sfx_pop.wav          (0.18s crisp harmonic UI pop for condition chips & highlights)
- sfx_write.wav        (0.28s gentle double-note formula reveal chime)
- sfx_ding.wav         (0.85s warm triad bell for final answer lock-in)
"""
import math
import os
import random
import struct
import wave

SR = 24000


def write_wav(path: str, samples: list[float]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        buf = bytearray()
        for s in samples:
            v = max(-0.98, min(0.98, s))
            buf.extend(struct.pack("<h", int(v * 32767)))
        wf.writeframes(bytes(buf))


def soft_tone(freq: float, t: float, env: float) -> float:
    return env * (
        0.68 * math.sin(2 * math.pi * freq * t)
        + 0.22 * math.sin(2 * math.pi * (freq * 2.0) * t) * math.exp(-t * 1.8)
        + 0.10 * math.sin(2 * math.pi * (freq * 3.0) * t) * math.exp(-t * 3.2)
    )


def gen_bgm(path: str) -> None:
    """
    32-second 3Blue1Brown-style contemplative ambient progression:
    Am9 -> Fmaj7 -> Cmaj9 -> G6 (each bar 4 seconds, repeated twice with gentle arpeggio).
    """
    dur = 32.0
    n = int(dur * SR)
    samples = [0.0] * n

    chords = [
        [220.00, 261.63, 329.63, 392.00, 493.88],  # Am9
        [174.61, 220.00, 261.63, 329.63, 440.00],  # Fmaj7/6
        [130.81, 196.00, 246.94, 293.66, 392.00],  # Cmaj9
        [196.00, 246.94, 293.66, 329.63, 392.00],  # G6
    ] * 2

    # Warm pad layer + gentle plucked arpeggio notes
    for idx, ch in enumerate(chords):
        bar_start = idx * 4.0
        for i in range(int(bar_start * SR), min(n, int((bar_start + 4.5) * SR))):
            lt = (i / SR) - bar_start
            # Smooth pad envelope
            pad_env = math.sin(math.pi * min(1.0, lt / 4.5)) ** 1.4 * 0.18
            val = 0.0
            for f in ch[:4]:
                val += 0.25 * math.sin(2 * math.pi * f * (i / SR))
            samples[i] += val * pad_env

        # Arpeggio notes every 0.5s
        arp_order = [0, 1, 2, 4, 3, 2, 1, 3]
        for step_k, note_idx in enumerate(arp_order):
            nt0 = bar_start + step_k * 0.5
            freq = ch[note_idx] * 2.0  # one octave higher for clarity
            note_len = 1.35
            i0 = int(nt0 * SR)
            i1 = min(n, int((nt0 + note_len) * SR))
            for i in range(i0, i1):
                dt = (i - i0) / SR
                attack = min(1.0, dt / 0.03)
                decay = math.exp(-dt * 2.8)
                samples[i] += soft_tone(freq, dt, attack * decay * 0.22)

    write_wav(path, samples)


def gen_pop(path: str) -> None:
    dur = 0.18
    n = int(dur * SR)
    out = []
    for i in range(n):
        t = i / SR
        # Pitch sweep 520Hz -> 880Hz
        f = 520 + 1800 * t
        env = min(1.0, t / 0.008) * math.exp(-t * 24.0)
        out.append(0.55 * env * math.sin(2 * math.pi * f * t))
    write_wav(path, out)


def gen_whoosh(path: str) -> None:
    dur = 0.42
    n = int(dur * SR)
    rng = random.Random(42)
    out = []
    lp = 0.0
    for i in range(n):
        t = i / SR
        env = math.sin(math.pi * (t / dur)) ** 1.8
        # Filtered noise + low sine swell
        alpha = 0.06 + 0.18 * math.sin(math.pi * (t / dur))
        noise = rng.uniform(-1.0, 1.0)
        lp = lp + alpha * (noise - lp)
        swell = 0.35 * math.sin(2 * math.pi * (140 + 90 * (t / dur)) * t)
        out.append(0.45 * env * (lp * 0.7 + swell))
    write_wav(path, out)


def gen_write(path: str) -> None:
    dur = 0.32
    n = int(dur * SR)
    out = [0.0] * n
    notes = [(0.0, 587.33), (0.09, 880.00)]  # D5 -> A5
    for t0, f in notes:
        i0 = int(t0 * SR)
        for i in range(i0, n):
            dt = (i - i0) / SR
            env = min(1.0, dt / 0.01) * math.exp(-dt * 14.0)
            out[i] += soft_tone(f, dt, env * 0.42)
    write_wav(path, out)


def gen_ding(path: str) -> None:
    dur = 0.90
    n = int(dur * SR)
    out = [0.0] * n
    notes = [(0.0, 523.25), (0.07, 659.25), (0.14, 783.99), (0.21, 1046.50)]  # C5-E5-G5-C6
    for t0, f in notes:
        i0 = int(t0 * SR)
        for i in range(i0, n):
            dt = (i - i0) / SR
            env = min(1.0, dt / 0.012) * math.exp(-dt * 5.2)
            out[i] += soft_tone(f, dt, env * 0.32)
    write_wav(path, out)


def main() -> int:
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    lib_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(here, "..", "references", "audio_lib"))
    os.makedirs(lib_dir, exist_ok=True)
    gen_bgm(os.path.join(lib_dir, "bgm_3b1b_ambient.wav"))
    gen_whoosh(os.path.join(lib_dir, "sfx_whoosh.wav"))
    gen_pop(os.path.join(lib_dir, "sfx_pop.wav"))
    gen_write(os.path.join(lib_dir, "sfx_write.wav"))
    gen_ding(os.path.join(lib_dir, "sfx_ding.wav"))
    print(f"[OK] 已生成免费共享 BGM 与音效库: {lib_dir}")
    for f in sorted(os.listdir(lib_dir)):
        print(f"  - {f} ({os.path.getsize(os.path.join(lib_dir, f)) / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
