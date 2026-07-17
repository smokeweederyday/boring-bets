import { escapeHtml } from "../engine/colorEngine.js";

export function renderMatchupWidget({ container, module }) {
  if (!container) return;
  if (!module) {
    container.innerHTML = '<div class="module-empty">Matchup intelligence unavailable.</div>';
    return;
  }

  const lineup = Array.isArray(module.lineup) ? module.lineup : [];
  const notes = Array.isArray(module.notes) ? module.notes : [];

  container.innerHTML = `
    <article class="matchup-intelligence-card">
      <header class="matchup-intelligence-heading">
        <div>
          <span class="data-label">MATCHUP INTELLIGENCE</span>
          <h3>${escapeHtml(module.title || "Pitcher vs lineup")}</h3>
          <p>${escapeHtml(module.contextLabel || "")}</p>
        </div>
        <span class="matchup-lineup-status ${escapeHtml(module.statusClass || "")}">
          ${escapeHtml(module.statusLabel || "Unknown lineup")}
        </span>
      </header>

      <div class="matchup-summary-strip">
        <span><strong>${escapeHtml(module.leftCount ?? 0)}</strong> LHH</span>
        <span><strong>${escapeHtml(module.rightCount ?? 0)}</strong> RHH</span>
        ${module.switchCount ? `<span><strong>${escapeHtml(module.switchCount)}</strong> S*</span>` : ""}
        <span>${escapeHtml(module.completenessLabel || "0/9")}</span>
      </div>

      ${renderCombinedHistory(module.lineupHistory)}

      <ol class="matchup-lineup-order" aria-label="Batting order">
        ${lineup.map(renderHitter).join("") || '<li class="module-empty">Batting order unavailable.</li>'}
      </ol>

      <div class="matchup-comparison-grid">
        ${renderComparison("Pitcher vs LHH", module.pitcherVsLeft)}
        ${renderComparison("Pitcher vs RHH", module.pitcherVsRight)}
        ${renderComparison(module.offenseHandLabel || "Offense vs hand", module.offenseVsHand)}
        ${renderComparison(module.locationHandLabel || "Location vs hand", module.locationVsHand)}
      </div>

      <div class="matchup-notes">
        <h4>What to know</h4>
        ${notes.length
          ? notes.map(note => `<p class="${escapeHtml(note.kind || "neutral")}"><strong>${escapeHtml(note.label)}:</strong> ${escapeHtml(note.text)}</p>`).join("")
          : '<p>No material mismatch identified from the available data.</p>'}
      </div>
    </article>
  `;
}

function renderHitter(player) {
  const bvp = player?.bvp || {};
  const opacity = Number.isFinite(Number(bvp.opacity)) ? Number(bvp.opacity) : 0.22;
  return `
    <li class="matchup-bvp-shell">
      <a
        class="matchup-bvp-row ${escapeHtml(bvp.resultClass || "bvp-missing")}" 
        style="--bvp-bg-opacity:${escapeAttribute(String(opacity))}"
        href="${escapeAttribute(player.detailsUrl || "#")}" 
        aria-label="${escapeAttribute(buildBvpTooltip(player))}"
      >
        <span class="matchup-order-number">${escapeHtml(player.order)}</span>
        <span class="matchup-player-name">${escapeHtml(player.name)}</span>
        <span class="matchup-bat-side ${escapeHtml(player.sideClass || "")}">${escapeHtml(player.sideLabel)}</span>
        <span class="matchup-bvp-hovercard" role="tooltip">
          <strong>${escapeHtml(player.name)}</strong>
          ${bvp.available ? `
            <span>${escapeHtml(bvp.pa)} PA · ${escapeHtml(bvp.strikeouts)} K · ${escapeHtml(bvp.walks)} BB</span>
            <span>AVG ${formatRate(bvp.avg)} · OPS ${formatRate(bvp.ops)}</span>
            <small>${escapeHtml(sampleLabel(bvp.pa))}</small>
          ` : '<span>No recorded batter-vs-pitcher history.</span>'}
        </span>
      </a>
    </li>
  `;
}

function renderCombinedHistory(history = {}) {
  if (!history?.available) {
    return `
      <section class="matchup-lineup-history">
        <span class="data-label">LINEUP HISTORY</span>
        <p class="module-empty">No combined batter-vs-pitcher history available.</p>
      </section>
    `;
  }
  return `
    <section class="matchup-lineup-history">
      <div>
        <span class="data-label">LINEUP HISTORY</span>
        <small>${escapeHtml(history.hittersWithHistory || 0)} hitters with history</small>
      </div>
      <div class="matchup-lineup-history-grid">
        ${historyMetric("PA", history.pa)}
        ${historyMetric("K", history.strikeouts)}
        ${historyMetric("BB", history.walks)}
        ${historyMetric("AVG", formatRate(history.avg))}
        ${historyMetric("OPS", formatRate(history.ops))}
      </div>
    </section>
  `;
}

function historyMetric(label, value) {
  return `<span><small>${escapeHtml(label)}</small><strong>${escapeHtml(value ?? "—")}</strong></span>`;
}

function buildBvpTooltip(player) {
  const bvp = player?.bvp || {};
  if (!bvp.available) return `${player?.name || "Hitter"}. No recorded batter-vs-pitcher plate appearances.`;
  return `${player?.name || "Hitter"}: ${bvp.pa} PA, ${bvp.strikeouts} K, ${bvp.walks} BB, ${formatRate(bvp.avg)} AVG, ${formatRate(bvp.ops)} OPS.`;
}

function sampleLabel(pa) {
  const count = Number(pa) || 0;
  if (count < 5) return "Very small sample";
  if (count < 15) return "Small sample";
  if (count < 30) return "Moderate sample";
  if (count < 50) return "Large sample";
  return "Very large sample";
}

function formatRate(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(3).replace(/^0/, "") : "—";
}

function renderComparison(label, item = {}) {
  return `
    <div class="matchup-comparison-item ${escapeHtml(item.heatClass || "metric-missing")}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(item.summary || "Unavailable")}</strong>
      <small>${escapeHtml(item.detail || "")}</small>
    </div>
  `;
}

function escapeAttribute(value) {
  return escapeHtml(value || "");
}
