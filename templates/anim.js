/**
 * 4 幕纯净全动画模板（tiaotiao-physics-pure）
 */
window.COURSE_TAGS = {
  intro: ["01", "原题审题"],
  method: ["02", "过程与跳跳大招"],
  formula: ["03", "公式推导与验算"],
  outro: ["04", "跳跳避坑指南"],
};

(function () {
  const { draw3B1BProblemBoard, drawChip } = window.Draw3B1B;
  const SC = {};

  SC.intro = (ctx, lt, S) => {
    draw3B1BProblemBoard(ctx, { x: 80, y: 120, w: 1760, h: 300 }, "题目条件与核心设问", [
      { prog: S.P(0.1, 0.5), segments: [{ text: "请在此处填入重排后的题干文字与高亮关键词。", color: "#58C4DD", hiProg: S.P(S.at(1, 0.2), 0.5), bold: true }] },
    ], S.P(0.05, 0.5));
    drawChip(ctx, "关键条件 1", 600, 820, "#58C4DD", S.P(S.at(1, 0.2), 0.5));
    drawChip(ctx, "待求目标", 1320, 820, "#F4D03F", S.P(S.at(2, 0.2), 0.5));
  };

  SC.method = (ctx, lt, S) => {
    draw3B1BProblemBoard(ctx, { x: 960, y: 140, w: 880, h: 720 }, "用跳跳学长的方法破局", [
      { prog: S.P(0.2, 0.6), segments: [{ text: "1. 跳跳学长教你怎么做：先拆清物理过程与临界状态。", color: "#F4D03F", hiProg: 1 }] },
      { prog: S.P(S.at(1, 0.2), 0.6), segments: [{ text: "2. 跳跳大招：直击本题核心二级结论与快速口诀。", color: "#83C167", hiProg: 1 }] },
    ], S.P(0.1, 0.5));
  };

  SC.formula = (ctx, lt, S) => {
    draw3B1BProblemBoard(ctx, { x: 120, y: 140, w: 1680, h: 720 }, "具体公式推导与双验算", [
      { prog: S.P(0.2, 0.6), segments: [{ text: "列出核心物理方程并代入已知数据：", color: "#58C4DD", hiProg: 1 }] },
      { prog: S.P(S.at(1, 0.2), 0.6), segments: [{ text: "双方法验算一致，锁定最终正确答案！", color: "#83C167", hiProg: 1 }] },
    ], S.P(0.1, 0.5));
  };

  SC.outro = (ctx, lt, S) => {
    draw3B1BProblemBoard(ctx, { x: 140, y: 140, w: 1640, h: 720 }, "答案汇总与跳跳的避坑指南", [
      { prog: S.P(0.1, 0.5), segments: [{ text: "✅ 标准答案汇总与考场防坑提醒", color: "#F4D03F", hiProg: 1, bold: true }] },
    ], S.P(0.1, 0.5));
  };

  window.COURSE_SCENES = SC;
})();
