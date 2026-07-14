import {
  escapeHtml
} from "../engine/colorEngine.js";

export function renderLineupWidget({
  container,
  module
}) {
  if (!container) return;

  if (!module) {
    container.innerHTML = `
      <div class="module-empty">
        Lineup data unavailable.
      </div>
    `;
    return;
  }

  const players =
    Array.isArray(module.players)
      ? module.players
      : [];

  container.innerHTML = `
    <section class="lineup-widget">
      <div class="module-heading compact-heading">
        <div>
          <span class="data-label ${getLineupStatusClass(
            module.status
          )}">
            ${escapeHtml(
              String(
                module.statusLabel ||
                "Projected Lineup"
              ).toUpperCase()
            )}
          </span>

          <h3>
            ${escapeHtml(
              module.title || "LINEUP"
            )}
          </h3>
        </div>

        <span class="open-data">
          ${escapeHtml(
            module.updatedLabel || ""
          )}
        </span>
      </div>

      <div class="lineup-list">
        ${
          players.length
            ? players
                .map(renderLineupPlayer)
                .join("")
            : `
              <p class="module-note">
                Lineup players have not been added yet.
              </p>
            `
        }
      </div>
    </section>
  `;
}

function renderLineupPlayer(player, index) {
  return `
    <div class="lineup-player-row">
      <span class="lineup-order">
        ${index + 1}
      </span>

      <strong>
        ${escapeHtml(
          player?.name || "Player TBD"
        )}
      </strong>

      <span>
        ${escapeHtml(
          player?.position || "—"
        )}
      </span>

      <span>
        ${escapeHtml(
          player?.bats
            ? `${player.bats}HB`
            : "—"
        )}
      </span>
    </div>
  `;
}

function getLineupStatusClass(status) {
  return status === "confirmed"
    ? "lineup-status-confirmed"
    : "lineup-status-projected";
}