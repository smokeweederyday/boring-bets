(() => {
  "use strict";

  const GRID_SIZE = 5;

  function clamp(value, min = 0, max = 1) {
    return Math.max(min, Math.min(max, Number(value) || 0));
  }

  function seededValue(seed, row, column, offset = 0) {
    let value = (Number(seed) || 17) + row * 101 + column * 47 + offset * 193;
    value = Math.sin(value * 12.9898) * 43758.5453;
    return value - Math.floor(value);
  }

  function emptyMatrix(fill = 0.5) {
    return Array.from({ length: GRID_SIZE }, () => Array.from({ length: GRID_SIZE }, () => fill));
  }

  function prototypeMatrix(seed, profile = "balanced") {
    const matrix = emptyMatrix();
    for (let row = 0; row < GRID_SIZE; row += 1) {
      for (let column = 0; column < GRID_SIZE; column += 1) {
        const centerDistance = Math.hypot(row - 2, column - 2) / Math.hypot(2, 2);
        const noise = seededValue(seed, row, column, profile.length);
        let value = 0.5 + (noise - 0.5) * 0.55;
        if (profile === "batter-damage") value += (1 - centerDistance) * 0.18;
        if (profile === "pitcher-command") value += centerDistance * 0.1 - 0.02;
        if (profile === "live-command") value += (column > 2 ? 0.07 : -0.02) + (row > 2 ? 0.05 : -0.02);
        matrix[row][column] = clamp(value);
      }
    }
    return matrix;
  }

  function normalizeMatrix(matrix) {
    if (!Array.isArray(matrix) || matrix.length !== GRID_SIZE) return emptyMatrix();
    return matrix.map(row => Array.from({ length: GRID_SIZE }, (_, column) => clamp(row?.[column] ?? 0.5)));
  }

  function combine({ batter, pitcher, live, countPressure = 0 }) {
    const batterMatrix = normalizeMatrix(batter);
    const pitcherMatrix = normalizeMatrix(pitcher);
    const liveMatrix = normalizeMatrix(live);
    return batterMatrix.map((row, rowIndex) => row.map((batterValue, columnIndex) => {
      const pitcherValue = pitcherMatrix[rowIndex][columnIndex];
      const liveValue = liveMatrix[rowIndex][columnIndex];
      const batterEdge = (batterValue - 0.5) * 1.1;
      const pitcherEdge = (pitcherValue - 0.5) * 0.95;
      const liveAdjustment = (liveValue - 0.5) * 0.45;
      return Math.max(-1, Math.min(1, batterEdge - pitcherEdge + liveAdjustment + countPressure));
    }));
  }

  function summarize(matrix) {
    let bestBatter = { score: -Infinity, row: 0, column: 0 };
    let bestPitcher = { score: Infinity, row: 0, column: 0 };
    matrix.forEach((row, rowIndex) => row.forEach((score, columnIndex) => {
      if (score > bestBatter.score) bestBatter = { score, row: rowIndex, column: columnIndex };
      if (score < bestPitcher.score) bestPitcher = { score, row: rowIndex, column: columnIndex };
    }));
    return { bestBatter, bestPitcher };
  }

  function zoneLabel(row, column, batterHand = "R") {
    const vertical = ["UP", "UP", "MIDDLE", "DOWN", "DOWN"][row] || "MIDDLE";
    const horizontalRaw = ["INSIDE", "INNER", "MIDDLE", "OUTER", "AWAY"][column] || "MIDDLE";
    const horizontal = batterHand === "L"
      ? ["AWAY", "OUTER", "MIDDLE", "INNER", "INSIDE"][column]
      : horizontalRaw;
    return `${vertical} / ${horizontal}`;
  }

  function buildPrototype({ pitcherId, batterId, batterHand = "R", balls = 0, strikes = 0 }) {
    const pitcher = prototypeMatrix(Number(pitcherId) || 31, "pitcher-command");
    const batter = prototypeMatrix(Number(batterId) || 73, "batter-damage");
    const live = prototypeMatrix((Number(pitcherId) || 31) + (Number(batterId) || 73), "live-command");
    const countPressure = balls > strikes ? 0.05 : strikes > balls ? -0.04 : 0;
    const combined = combine({ batter, pitcher, live, countPressure });
    const summary = summarize(combined);
    return {
      grid_size: GRID_SIZE,
      source_status: "prototype_not_statcast_connected",
      batter,
      pitcher,
      live,
      combined,
      summary: {
        batter_zone: zoneLabel(summary.bestBatter.row, summary.bestBatter.column, batterHand),
        batter_score: summary.bestBatter.score,
        pitcher_zone: zoneLabel(summary.bestPitcher.row, summary.bestPitcher.column, batterHand),
        pitcher_score: summary.bestPitcher.score
      }
    };
  }

  window.BoringBetsHeatMapEngine = {
    GRID_SIZE,
    buildPrototype,
    combine,
    normalizeMatrix,
    summarize,
    zoneLabel
  };
})();
