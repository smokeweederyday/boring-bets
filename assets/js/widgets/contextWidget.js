import {
  escapeHtml
} from "../engine/colorEngine.js";

export function renderContextWidget({
  container,
  context
}) {
  if (!container) return;

  if (!context) {
    container.innerHTML = `
      <div class="context-empty">
        Context data unavailable.
      </div>
    `;
    return;
  }

  const alerts = normalizeItems(
    context.alerts
  );

  const positives = normalizeItems(
    context.positives
  );

  const negatives = normalizeItems(
    context.negatives
  );

  const information = normalizeItems(
    context.information
  );

  container.innerHTML = `
    <div class="context-header">
      <div>
        <p class="kicker">CONTEXT V2</p>
        <h2>
          ${escapeHtml(
            context.label || "MIXED"
          )}
        </h2>
      </div>

      <div class="context-score">
        <strong>
          ${escapeHtml(
            context.score ?? "—"
          )}
        </strong>

        <span>/100</span>
      </div>
    </div>

    <div class="context-columns context-columns-v2">
      ${renderContextGroup(
        "Alerts",
        alerts,
        "No urgent alerts."
      )}

      ${renderContextGroup(
        "Positive Conditions",
        positives,
        "No positive conditions identified."
      )}

      ${renderContextGroup(
        "Negative Conditions",
        negatives,
        "No negative conditions identified."
      )}

      ${renderContextGroup(
        "Information",
        information,
        "No additional context available."
      )}
    </div>

    <div class="context-future-sources">
      ${renderFutureSource(
        "Travel",
        context.sources?.travel
      )}

      ${renderFutureSource(
        "Trade Deadline",
        context.sources?.trade_deadline
      )}

      ${renderFutureSource(
        "Standings",
        context.sources?.standings
      )}

      ${renderFutureSource(
        "Streaks",
        context.sources?.streaks
      )}

      ${renderFutureSource(
        "Injuries",
        context.sources?.injuries
      )}
    </div>
  `;
}

function normalizeItems(value) {
  return Array.isArray(value)
    ? value
    : [];
}

function renderContextGroup(
  title,
  items,
  emptyMessage
) {
  const body = items.length
    ? items
        .map(item => `
          <article class="context-item context-${escapeHtml(
            item.level || "info"
          )}">
            <div class="context-item-heading">
              <strong>
                ${escapeHtml(
                  item.title || "Context"
                )}
              </strong>

              ${
                item.team
                  ? `
                    <span class="context-team-tag">
                      ${escapeHtml(item.team)}
                    </span>
                  `
                  : ""
              }
            </div>

            <p>
              ${escapeHtml(
                item.summary || ""
              )}
            </p>
          </article>
        `)
        .join("")
    : `
        <p class="context-group-empty">
          ${escapeHtml(emptyMessage)}
        </p>
      `;

  return `
    <section class="context-group">
      <h3>
        ${escapeHtml(title)}
        <span>${items.length}</span>
      </h3>

      <div class="context-list">
        ${body}
      </div>
    </section>
  `;
}

function renderFutureSource(
  label,
  active
) {
  return `
    <span class="${
      active
        ? "context-source-active"
        : "context-source-backlog"
    }">
      ${escapeHtml(label)}
      ·
      ${active ? "LIVE" : "BACKLOG"}
    </span>
  `;
}
