import {
  getRankHeatClass,
  escapeHtml
} from "../engine/colorEngine.js";

/**
 * Renders normalized offense data.
 *
 * This widget does not decide:
 * - which team is shown
 * - which pitcher hand matters
 * - which metrics belong to MLB
 *
 * The sport engine supplies those decisions.
 */
export function renderOffenseWidget({
  container,
  module,
  onTimeframeChange
}) {
  if (!container) return;

  if (!module) {
    container.innerHTML = `
      <div class="module-empty">
        Offense data unavailable.
      </div>
    `;

    return;
  }

  const metrics =
    Array.isArray(module.metrics)
      ? module.metrics
      : [];

  const timeframeSignals =
    module.timeframeSignals || {};

  container.innerHTML = `
    <div
      class="segmented-control offense-timeframe-control"
      role="group"
      aria-label="Offense timeframe"
    >
      ${[
        ["last_7", "7 Days"],
        ["last_30", "30 Days"],
        ["season", "Season"]
      ].map(([timeframe, label]) => {
        const signal =
          timeframeSignals[timeframe]
          || {};

        const signalClass =
          signal.className
          || "offense-signal-neutral";

        const isActive =
          module.activeTimeframe
          === timeframe;

        return `
          <button
            type="button"
            data-offense-timeframe="${timeframe}"
            class="offense-control-signal ${escapeHtml(
              signalClass
            )}${
              isActive
                ? " active"
                : ""
            }"
            aria-pressed="${
              isActive
                ? "true"
                : "false"
            }"
            title="${escapeAttribute(
              signal.label
              || "Offense signal unavailable"
            )}"
          >
            ${label}
          </button>
        `;
      }).join("")}
    </div>

    <a
      class="module-link"
      href="${escapeAttribute(
        module.detailsUrl || "#"
      )}"
    >
      <div class="module-heading compact-heading">
        <div>
          <h3>
            ${escapeHtml(
              module.title || "OFFENSE"
            )}
          </h3>

          <p>
            ${escapeHtml(
              module.context || "Split unavailable"
            )}
            ·
            ${escapeHtml(
              module.opponent || "Starter TBD"
            )}
          </p>
        </div>

        <span class="open-data">
          Projected lineup →
        </span>
      </div>

      <div class="table-scroll">
        <table class="data-table offense-data-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Overall</th>
              <th>Rank</th>
              <th>
                ${escapeHtml(
                  module.context || "Split"
                )}
              </th>
              <th>Rank</th>
              <th>${escapeHtml(module.locationContext || "Game location split")}</th>
              <th>Rank</th>
            </tr>
          </thead>

          <tbody>
            ${
              metrics.length
                ? metrics
                    .map(renderMetricRow)
                    .join("")
                : renderEmptyRow()
            }
          </tbody>
        </table>
      </div>
    </a>
  `;

  container
    .querySelectorAll("[data-offense-timeframe]")
    .forEach(button => {
      button.addEventListener("click", event => {
        event.preventDefault();
        event.stopPropagation();

        onTimeframeChange?.(
          button.dataset.offenseTimeframe
        );
      });
    });
}

function renderMetricRow(metric) {
  const overall =
    metric?.overall || {};

  const split =
    metric?.split || {};

  return `
    <tr>
      <th>
        ${escapeHtml(
          metric?.label || "—"
        )}
      </th>

      ${renderValueCell(
        overall.value,
        overall.rank,
        metric?.type
      )}

      ${renderRankCell(
        overall.rank
      )}

      ${renderValueCell(
        split.value,
        split.rank,
        metric?.type
      )}

      ${renderRankCell(
        split.rank
      )}

      ${renderValueCell(
        metric?.locationSplit?.value,
        metric?.locationSplit?.rank,
        metric?.type
      )}

      ${renderRankCell(
        metric?.locationSplit?.rank
      )}
    </tr>
  `;
}

function renderValueCell(
  value,
  rank,
  type
) {
  const hasValue = value !== null && value !== undefined && value !== "";
  const heatClass = hasValue ? getRankHeatClass(rank, 30) : "metric-missing";
  return `
    <td class="${heatClass}">
      ${escapeHtml(
        formatMetricValue(value, type)
      )}
    </td>
  `;
}

function renderRankCell(rank) {
  const numericRank =
    Number(rank);

  const displayRank =
    Number.isFinite(numericRank)
      ? `${numericRank}`
      : "—";

  const heatClass = Number.isFinite(numericRank)
    ? getRankHeatClass(numericRank, 30)
    : "metric-missing";

  return `
    <td class="rank-cell ${heatClass}">
      ${displayRank}
    </td>
  `;
}

function renderEmptyRow() {
  return `
    <tr>
      <td
        class="metric-missing"
        colspan="7"
      >
        Data unavailable
      </td>
    </tr>
  `;
}

function formatMetricValue(
  value,
  type
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  const number =
    Number(value);

  if (!Number.isFinite(number)) {
    return String(value);
  }

  if (type === "average") {
    return number
      .toFixed(3)
      .replace(/^0/, "");
  }

  if (type === "percent") {
    return `${number.toFixed(1)}%`;
  }

  if (type === "integer") {
    return Math.round(number).toString();
  }

  return number.toFixed(2);
}

function escapeAttribute(value) {
  return escapeHtml(value || "#");
}
