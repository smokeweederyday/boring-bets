import {
  escapeHtml
} from "../engine/colorEngine.js";

export function renderPitcherWidget({
  container,
  module,
  onLocationChange
}) {
  if (!container) return;

  if (!module) {
    container.innerHTML = `
      <div class="module-empty">
        Pitcher data unavailable.
      </div>
    `;
    return;
  }

  const metrics = Array.isArray(module.metrics) ? module.metrics : [];
  const columns = Array.isArray(module.columns) ? module.columns : [];

  container.innerHTML = `
    <div class="pitcher-card-link">
      <div class="pitcher-card-heading">
        <div>
          <span class="data-label">
            ${escapeHtml(module.statusLabel || "STARTER TBD")}
          </span>
          <h2>${escapeHtml(module.name || "Starter TBD")}</h2>
          <div class="pitcher-meta-line">
            <p>
              ${escapeHtml(module.team || "—")}
              · ${escapeHtml(module.contextLabel || "")}
              · Age ${escapeHtml(module.age ?? "—")}
              · ${escapeHtml(module.handLabel || "Throws —")}
            </p>
            <span class="pitcher-lineup-inline ${escapeHtml(module.lineupStatusClass || "")}"
              title="${escapeAttribute(module.lineupStatusLabel || "Projected lineup")}">
              ${escapeHtml(module.lineupHandednessLabel || "LHH/RHH unavailable")}
            </span>
          </div>
        </div>
        <a class="open-data" href="${escapeAttribute(module.detailsUrl || "#")}">Full data →</a>
      </div>


      <div class="pitcher-location-control" role="group" aria-label="Pitcher location split">
        ${["all", "home", "away"].map(location => `
          <button
            type="button"
            data-pitcher-location="${location}"
            class="${module.activeLocation === location ? "active" : ""}"
          >${location[0].toUpperCase() + location.slice(1)}</button>
        `).join("")}
      </div>

      <div class="table-scroll">
        <table class="data-table pitcher-data-table pitcher-rank-table">
          <thead>
            <tr class="pitcher-group-heading">
              <th>Metric</th>
              ${columns.map(column => `
                <th>${escapeHtml(column.label)}</th>
              `).join("")}
            </tr>
          </thead>
          <tbody>
            ${metrics.length
              ? metrics.map(renderPitcherMetricRow).join("")
              : renderEmptyRow(columns.length + 1)}
          </tbody>
        </table>
      </div>
    </div>
  `;

  container.querySelectorAll("[data-pitcher-location]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      onLocationChange?.(button.dataset.pitcherLocation);
    });
  });
}

function renderPitcherMetricRow(metric) {
  return `
    <tr>
      <th>${escapeHtml(metric.label || "—")}</th>
      ${(metric.values || []).map(renderPitcherStatCell).join("")}
    </tr>
  `;
}

function renderPitcherStatCell(value) {
  const heatClass = escapeHtml(value.heatClass || "metric-missing");
  const rank = Number(value.rank);
  const poolSize = Number(value.poolSize);
  const hasRank = Number.isFinite(rank);
  const tooltip = hasRank
    ? buildRankTooltip(rank, poolSize, value.contextLabel)
    : (value.contextLabel || "No qualifying league rank for this selection");

  return `
    <td
      class="${heatClass} pitcher-stat-cell"
      title="${escapeAttribute(tooltip)}"
      aria-label="${escapeAttribute(tooltip)}"
    >
      <span class="metric-value">${escapeHtml(value.display || "—")}</span>
    </td>
  `;
}

function buildRankTooltip(rank, poolSize, contextLabel) {
  const poolText = Number.isFinite(poolSize)
    ? `Rank ${rank} among ${poolSize} qualifying MLB pitchers`
    : `Pitcher rank ${rank}`;
  return contextLabel ? `${poolText} · ${contextLabel}` : poolText;
}

function renderEmptyRow(columnCount) {
  return `
    <tr>
      <td class="metric-missing" colspan="${columnCount}">
        Data unavailable
      </td>
    </tr>
  `;
}

function escapeAttribute(value) {
  return escapeHtml(value || "#");
}
