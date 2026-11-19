#!/usr/bin/env python3
"""Physics calculation & verification kernel for tiaotiao-physics-pure."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import math

try:
    import sympy as sp
    HAS_SYMPY = True
except ImportError:
    sp = None
    HAS_SYMPY = False


@dataclass
class MotionSegment:
    t_start: float
    t_end: float
    x0: float
    v0: float
    a: float
    label: str = ""

    def eval_at(self, t: float) -> Tuple[float, float, float]:
        dt = max(0.0, min(t, self.t_end) - self.t_start)
        x = self.x0 + self.v0 * dt + 0.5 * self.a * dt * dt
        v = self.v0 + self.a * dt
        return x, v, self.a


class PiecewiseMotion:
    def __init__(self) -> None:
        self.segments: List[MotionSegment] = []

    def add_segment(self, duration: float, a: float, label: str = "",
                    x0: Optional[float] = None, v0: Optional[float] = None) -> "PiecewiseMotion":
        if not self.segments:
            t_start = 0.0
            cur_x = 0.0 if x0 is None else x0
            cur_v = 0.0 if v0 is None else v0
        else:
            prev = self.segments[-1]
            t_start = prev.t_end
            px, pv, _ = prev.eval_at(prev.t_end)
            cur_x = px if x0 is None else x0
            cur_v = pv if v0 is None else v0
        self.segments.append(MotionSegment(t_start, t_start + duration, cur_x, cur_v, a, label))
        return self

    @property
    def total_time(self) -> float:
        return self.segments[-1].t_end if self.segments else 0.0

    def eval_at(self, t: float) -> Dict[str, Any]:
        if not self.segments:
            return {"t": t, "x": 0.0, "v": 0.0, "a": 0.0, "label": ""}
        for seg in self.segments:
            if t <= seg.t_end + 1e-12:
                x, v, a = seg.eval_at(t)
                return {"t": t, "x": x, "v": v, "a": a, "label": seg.label}
        seg = self.segments[-1]
        x, v, a = seg.eval_at(seg.t_end)
        return {"t": t, "x": x, "v": v, "a": a, "label": seg.label}


def verify_vernier_caliper(
    divisions: int,
    main_mm: int,
    aligned_k: int,
    main_aligned_mm: Optional[int] = None,
    tail_main_mm_floor: Optional[int] = None,
) -> Dict[str, Any]:
    """Exact geometric self-consistency check for a vernier caliper reading."""
    if divisions not in (10, 20, 50):
        raise ValueError(f"Unsupported vernier divisions: {divisions}")
    resolution = 1.0 / divisions
    span_mm = divisions - 1
    pitch_mm = span_mm / divisions
    reading_mm = round(main_mm + aligned_k * resolution, 3)
    expected_aligned_main = round(reading_mm + aligned_k * pitch_mm)
    tail_pos_mm = round(reading_mm + span_mm, 3)

    ok = True
    errors = []
    if main_aligned_mm is not None and main_aligned_mm != expected_aligned_main:
        ok = False
        errors.append(
            f"对齐刻度矛盾: 主尺读 {main_mm}mm + 第{aligned_k}格对齐时，主尺被对齐线必为 {expected_aligned_main}mm，而非 {main_aligned_mm}mm"
        )
    if tail_main_mm_floor is not None and int(math.floor(tail_pos_mm)) != tail_main_mm_floor:
        ok = False
        errors.append(
            f"尾线位置矛盾: 读数 {reading_mm}mm 时副尺尾线应在 {tail_pos_mm}mm (即 {int(math.floor(tail_pos_mm))}mm 右侧)，而非 {tail_main_mm_floor}mm 右侧"
        )
    fmt = f"{reading_mm:.1f}" if divisions == 10 else f"{reading_mm:.2f}"
    return {
        "ok": ok,
        "reading_mm": reading_mm,
        "formatted_mm": fmt,
        "expected_aligned_main_mm": expected_aligned_main,
        "tail_pos_mm": tail_pos_mm,
        "errors": errors,
    }
