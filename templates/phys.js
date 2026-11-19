/**
 * Phys3B1B: Composable physics drawing primitives.
 */
(function (global) {
  const P = global.PALETTE_3B1B;

  function drawLabelPill(ctx, text, x, y, color = P.text, font = "600 13px Inter, 'PingFang SC', sans-serif") {
    ctx.save();
    ctx.font = font;
    const m = ctx.measureText(text);
    const padX = 8, h = 22, w = m.width + padX * 2;
    ctx.fillStyle = P.pillBg;
    ctx.beginPath(); ctx.roundRect(x - w / 2, y - h / 2, w, h, 6); ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.12)"; ctx.lineWidth = 1; ctx.stroke();
    ctx.fillStyle = color; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(text, x, y);
    ctx.restore();
  }

  function drawVector(ctx, x, y, dx, dy, color = P.gold, label = "", progress = 1) {
    const px = x + dx * progress, py = y + dy * progress;
    const len = Math.hypot(px - x, py - y);
    if (len < 2) return;
    ctx.save();
    ctx.shadowColor = color; ctx.shadowBlur = 10;
    ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 2.6; ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(px, py); ctx.stroke();
    const angle = Math.atan2(py - y, px - x);
    const head = Math.min(11, Math.max(6, len * 0.25));
    ctx.beginPath(); ctx.moveTo(px, py);
    ctx.lineTo(px - head * Math.cos(angle - 0.42), py - head * Math.sin(angle - 0.42));
    ctx.lineTo(px - head * Math.cos(angle + 0.42), py - head * Math.sin(angle + 0.42));
    ctx.closePath(); ctx.fill();
    ctx.shadowBlur = 0;
    if (label && progress > 0.35) {
      drawLabelPill(ctx, label, px + 16 * Math.cos(angle), py + 16 * Math.sin(angle), color);
    }
    ctx.restore();
  }

  global.Phys3B1B = { drawLabelPill, drawVector };
})(window);
