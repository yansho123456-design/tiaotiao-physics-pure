/**
 * 16:9 (1920x1080) Course Video Engine for tiaotiao-physics-pure.
 */
(function (global) {
  const PALETTE = {
    bg: "#0c0f1a",
    bgPanel: "rgba(18, 23, 42, 0.88)",
    grid: "rgba(88, 196, 221, 0.055)",
    gridMajor: "rgba(88, 196, 221, 0.13)",
    blue: "#58C4DD",
    gold: "#F4D03F",
    red: "#FC6255",
    green: "#83C167",
    purple: "#9A72AC",
    text: "#ECEFF4",
    muted: "#94A3B8",
    pillBg: "rgba(12, 15, 26, 0.88)",
  };

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const smoothstep = (t) => {
    const x = clamp(t, 0, 1);
    return x * x * (3 - 2 * x);
  };
  const easeOutCubic = (t) => 1 - Math.pow(1 - clamp(t, 0, 1), 3);

  class CourseEngine3B1B {
    constructor(canvas, opts = {}) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.timeline = opts.timeline || { duration: 60, fps: 30, scenes: [] };
      this.duration = this.timeline.duration || 60;
      this.scenes = this.timeline.scenes || [];
      this.SC = opts.SC || {};
      this.tags = opts.tags || {};
      this.t = 0;
      this.playing = false;
      this.speed = 1.0;
      this.audioEl = opts.audioEl || null;
      this.onUpdate = opts.onUpdate || null;
      this._lastTs = null;
      this._rafId = null;

      this.setupCanvas();
      window.addEventListener("resize", () => this.setupCanvas());

      global.__renderAtTime = (sec) => {
        this.pause();
        this.t = clamp(sec, 0, this.duration);
        this.render();
      };
    }

    setupCanvas() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.canvas.width = 1920 * dpr;
      this.canvas.height = 1080 * dpr;
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.render();
    }

    play() {
      if (this.playing) return;
      if (this.t >= this.duration - 0.02) this.t = 0;
      this.playing = true;
      this._lastTs = performance.now();
      if (this.audioEl && this.audioEl.src) {
        this.audioEl.currentTime = this.t;
        this.audioEl.playbackRate = this.speed;
        this.audioEl.play().catch(() => {});
      }
      const tick = (now) => {
        if (!this.playing) return;
        if (this.audioEl && this.audioEl.src && !this.audioEl.paused && !this.audioEl.ended) {
          this.t = this.audioEl.currentTime;
        } else {
          const dt = Math.min(0.05, (now - this._lastTs) / 1000) * this.speed;
          this.t += dt;
        }
        this._lastTs = now;
        if (this.t >= this.duration) {
          this.t = this.duration;
          this.pause();
        }
        this.render();
        if (this.playing) this._rafId = requestAnimationFrame(tick);
      };
      this._rafId = requestAnimationFrame(tick);
    }

    pause() {
      this.playing = false;
      if (this._rafId) cancelAnimationFrame(this._rafId);
      if (this.audioEl && !this.audioEl.paused) this.audioEl.pause();
      if (this.onUpdate) this.onUpdate(this.t, this.duration, this.playing);
    }

    seek(t) {
      this.t = clamp(t, 0, this.duration);
      if (this.audioEl && this.audioEl.src) {
        this.audioEl.currentTime = this.t;
      }
      this.render();
    }

    _activeScene() {
      for (const sc of this.scenes) {
        if (this.t >= sc.start && this.t <= sc.end + 1e-6) return sc;
      }
      return this.scenes[this.scenes.length - 1] || null;
    }

    render() {
      const ctx = this.ctx;
      const w = 1920, h = 1080;
      ctx.save();
      ctx.fillStyle = PALETTE.bg;
      ctx.fillRect(0, 0, w, h);

      const step = 60;
      ctx.lineWidth = 1;
      for (let x = 0; x <= w; x += step) {
        ctx.strokeStyle = x % 240 === 0 ? PALETTE.gridMajor : PALETTE.grid;
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
      }
      for (let y = 0; y <= h; y += step) {
        ctx.strokeStyle = y % 240 === 0 ? PALETTE.gridMajor : PALETTE.grid;
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
      }

      const sc = this._activeScene();
      if (sc) {
        const lt = Math.max(0, this.t - sc.start);
        const lines = sc.lines || [];
        const S = {
          scene: sc,
          lt,
          t: this.t,
          at: (idx, offset = 0) => {
            const ln = lines[idx];
            return ln ? (ln.start - sc.start + offset) : 9999;
          },
          P: (t0, dur = 0.65) => smoothstep(dur <= 0 ? (lt >= t0 ? 1 : 0) : (lt - t0) / dur),
        };

        const tag = this.tags[sc.id];
        if (tag) {
          ctx.save();
          ctx.fillStyle = "rgba(88, 196, 221, 0.14)";
          ctx.strokeStyle = PALETTE.blue;
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.roundRect(44, 28, 360, 44, 22);
          ctx.fill();
          ctx.stroke();
          ctx.fillStyle = PALETTE.blue;
          ctx.font = "700 20px 'PingFang SC', sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(`${tag[0]} · ${tag[1]}`, 44 + 180, 50);
          ctx.restore();
        }

        const fn = this.SC[sc.id];
        if (fn) {
          fn(ctx, lt, S, { w, h, P: PALETTE, clamp, lerp, smoothstep, easeOutCubic });
        }

        const activeLine = lines.find((ln) => this.t >= ln.start && this.t <= ln.end + 0.15);
        if (activeLine && activeLine.zh) {
          this._drawSubtitle(ctx, w, h, activeLine.zh);
        }
      }

      ctx.restore();
      if (this.onUpdate) this.onUpdate(this.t, this.duration, this.playing);
    }

    _drawSubtitle(ctx, w, h, text) {
      ctx.save();
      ctx.font = "600 30px 'PingFang SC', 'Microsoft YaHei', sans-serif";
      const tw = ctx.measureText(text).width;
      const boxW = Math.min(w - 140, tw + 76);
      const boxH = 60;
      const bx = (w - boxW) / 2;
      const by = h - 84;
      ctx.fillStyle = "rgba(8, 11, 20, 0.88)";
      ctx.beginPath(); ctx.roundRect(bx, by, boxW, boxH, 14); ctx.fill();
      ctx.strokeStyle = "rgba(88, 196, 221, 0.4)";
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.fillStyle = "#FFFFFF";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(text, w / 2, by + boxH / 2 + 1);
      ctx.restore();
    }
  }

  function draw3B1BProblemBoard(ctx, rect, title, tokenLines, boardProg = 1) {
    if (boardProg <= 0.01) return;
    const { x, y, w, h } = rect;
    ctx.save();
    ctx.globalAlpha = boardProg;
    ctx.fillStyle = "rgba(18, 23, 42, 0.92)";
    ctx.strokeStyle = "rgba(88, 196, 221, 0.45)";
    ctx.shadowColor = "rgba(88, 196, 221, 0.18)";
    ctx.shadowBlur = 22;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, 16);
    ctx.fill();
    ctx.stroke();
    ctx.shadowBlur = 0;

    if (title) {
      ctx.fillStyle = PALETTE.blue;
      ctx.font = "700 24px 'PingFang SC', sans-serif";
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillText(title, x + 28, y + 20);
    }

    const startY = y + (title ? 64 : 26);
    const lineH = 42;
    ctx.font = "500 22px 'PingFang SC', sans-serif";
    ctx.textBaseline = "middle";

    tokenLines.forEach((lineObj, rowIdx) => {
      const rowProg = lineObj.prog !== undefined ? lineObj.prog : 1;
      if (rowProg <= 0.01) return;
      ctx.save();
      ctx.globalAlpha = boardProg * rowProg;
      let curX = x + 28;
      const cy = startY + rowIdx * lineH;
      (lineObj.segments || []).forEach((seg) => {
        const txt = seg.text || "";
        ctx.font = seg.bold ? "700 22px 'PingFang SC', sans-serif" : "500 22px 'PingFang SC', sans-serif";
        const tw = ctx.measureText(txt).width;
        const hi = seg.hiProg !== undefined ? seg.hiProg : 0;
        if (hi > 0.01 && seg.color) {
          ctx.save();
          ctx.globalAlpha = boardProg * rowProg * hi;
          ctx.fillStyle = seg.color + "2E";
          ctx.strokeStyle = seg.color;
          ctx.shadowColor = seg.color;
          ctx.shadowBlur = 10;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.roundRect(curX - 4, cy - 16, tw + 8, 32, 6);
          ctx.fill();
          ctx.stroke();
          ctx.restore();
        }
        ctx.fillStyle = hi > 0.2 && seg.color ? seg.color : (seg.baseColor || PALETTE.text);
        ctx.textAlign = "left";
        ctx.fillText(txt, curX, cy);
        curX += tw + 2;
      });
      ctx.restore();
    });
    ctx.restore();
  }

  function draw3B1BTable(ctx, rect, rows, prog = 1, hiCol = -1, borderColor = PALETTE.blue) {
    if (prog <= 0.01 || !rows.length) return;
    const { x, y, w, h } = rect;
    const nRows = rows.length, nCols = rows[0].length, rowH = h / nRows;
    ctx.save();
    ctx.globalAlpha = prog;
    ctx.fillStyle = "rgba(15, 20, 36, 0.92)";
    ctx.strokeStyle = borderColor;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, 12);
    ctx.fill();
    ctx.stroke();

    const col0W = w * 0.26;
    const colW = (w - col0W) / Math.max(1, nCols - 1);
    const colX = (c) => (c === 0 ? x : x + col0W + (c - 1) * colW);
    const colWidth = (c) => (c === 0 ? col0W : colW);

    for (let r = 1; r < nRows; r++) {
      ctx.strokeStyle = "rgba(88, 196, 221, 0.25)";
      ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(x, y + r * rowH); ctx.lineTo(x + w, y + r * rowH); ctx.stroke();
    }
    for (let c = 1; c < nCols; c++) {
      const cx = colX(c);
      ctx.strokeStyle = "rgba(88, 196, 221, 0.25)";
      ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(cx, y); ctx.lineTo(cx, y + h); ctx.stroke();
    }

    for (let r = 0; r < nRows; r++) {
      for (let c = 0; c < nCols; c++) {
        const cx = colX(c) + colWidth(c) / 2, cy = y + r * rowH + rowH / 2;
        if (c === hiCol && c > 0) {
          ctx.fillStyle = "rgba(244, 208, 63, 0.18)";
          ctx.fillRect(colX(c) + 2, y + r * rowH + 2, colWidth(c) - 4, rowH - 4);
        }
        ctx.fillStyle = c === 0 ? PALETTE.blue : (r === 0 ? PALETTE.gold : PALETTE.text);
        ctx.font = c === 0 ? "700 20px 'PingFang SC', sans-serif" : "700 21px Inter, 'PingFang SC', sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(rows[r][c], cx, cy);
      }
    }
    ctx.restore();
  }

  function drawChip(ctx, text, cx, cy, color = PALETTE.gold, prog = 1) {
    if (prog <= 0.01) return;
    ctx.save();
    ctx.globalAlpha = prog;
    ctx.translate(0, (1 - prog) * 14);
    ctx.font = "700 20px 'PingFang SC', sans-serif";
    const tw = ctx.measureText(text).width;
    const w = tw + 36, h = 42;
    ctx.shadowColor = color;
    ctx.shadowBlur = 14;
    ctx.fillStyle = color + "24";
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.roundRect(cx - w / 2, cy - h / 2, w, h, 21);
    ctx.fill();
    ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.fillStyle = color;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, cx, cy + 1);
    ctx.restore();
  }

  global.CourseEngine3B1B = CourseEngine3B1B;
  global.PALETTE_3B1B = PALETTE;
  global.Draw3B1B = { draw3B1BProblemBoard, draw3B1BTable, drawChip };
})(window);
