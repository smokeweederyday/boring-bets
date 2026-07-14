import {
  renderLineupWidget
} from "./assets/js/widgets/lineupWidget.js";

import {
  buildMlbLineupModule
} from "./assets/js/sports/mlbEngine.js";

async function loadLineup() {
  const status =
    document.getElementById("lineupStatus");

  const details =
    document.getElementById("lineupDetails");

  try {
    const params =
      new URLSearchParams(
        window.location.search
      );

    const gameId =
      params.get("game");

    const side =
      params.get("team") === "away"
        ? "away"
        : "home";

    if (!gameId) {
      throw new Error(
        "No game selected."
      );
    }

    const response =
      await fetch(
        `data/games.json?v=${Date.now()}`
      );

    if (!response.ok) {
      throw new Error(
        "Unable to load matchup."
      );
    }

    const data =
      await response.json();

    const game =
      (data.games || []).find(
        g => g.id === gameId
      );

    if (!game) {
      throw new Error(
        "Game not found."
      );
    }

    const module =
      buildMlbLineupModule({
        game,
        side
      });

    document.title =
      `${module.title} | Boring Bets`;

    const team =
      side === "away"
        ? game.away_team
        : game.home_team;

    document.getElementById(
      "lineupHeader"
    ).innerHTML = `
      <p class="kicker">
        ${team.abbr}
      </p>

      <h1>
        ${module.title}
      </h1>
    `;

    renderLineupWidget({
      container:
        document.getElementById(
          "lineupWidgetContainer"
        ),
      module
    });

    document.getElementById(
      "backToGameLink"
    ).href =
      `game.html?id=${encodeURIComponent(
        gameId
      )}`;

    status.remove();
    details.hidden = false;

  } catch (error) {
    console.error(error);

    status.textContent =
      error.message ||
      "Unable to load lineup.";
  }
}

loadLineup();