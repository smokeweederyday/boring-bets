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

    const gameDate =
      String(gameId).slice(0, 10);

    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(
        gameDate
      )
    ) {
      throw new Error(
        "Unable to determine the matchup date."
      );
    }

    const response =
      await fetch(
        `data/games/${encodeURIComponent(
          gameDate
        )}.json?v=${Date.now()}`
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

/* LINEUP_PLAYER_PROFILE_LINKS
   Convert every offensive lineup name into a role-aware
   player profile link without replacing the lineup widget.
*/
async function installLineupPlayerProfileLinks() {
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

  if (!gameId) return;

  const date =
    String(gameId).slice(0, 10);

  try {
    const [
      gamePayload,
      playerPayload
    ] = await Promise.all([
      fetchLineupProfileGameData(
        gameId,
        date
      ),
      fetch(
        `data/players.json?v=${Date.now()}`,
        {
          cache: "no-store"
        }
      )
        .then(response => {
          if (!response.ok) {
            return {
              players: {}
            };
          }

          return response.json();
        })
        .catch(() => ({
          players: {}
        }))
    ]);

    const games =
      Array.isArray(gamePayload)
        ? gamePayload
        : (
            Array.isArray(
              gamePayload?.games
            )
              ? gamePayload.games
              : []
          );

    const game =
      games.find(
        item =>
          String(item?.id) ===
          String(gameId)
      );

    if (!game) return;

    const lineupPlayers =
      game?.lineups?.[side]?.players;

    if (
      !Array.isArray(lineupPlayers) ||
      !lineupPlayers.length
    ) {
      return;
    }

    const profiles =
      playerPayload?.players || {};

    const container =
      document.getElementById(
        "lineupWidgetContainer"
      );

    if (!container) return;

    let updateScheduled = false;

    const applyLinks = () => {
      updateScheduled = false;

      lineupPlayers.forEach(player => {
        linkOffensivePlayerName({
          container,
          player,
          profile:
            profiles[
              String(player?.id)
            ] || null
        });
      });
    };

    const scheduleUpdate = () => {
      if (updateScheduled) return;

      updateScheduled = true;

      requestAnimationFrame(
        applyLinks
      );
    };

    scheduleUpdate();

    new MutationObserver(
      scheduleUpdate
    ).observe(container, {
      childList: true,
      subtree: true
    });
  } catch (error) {
    console.warn(
      "Unable to install lineup player links:",
      error
    );
  }
}

async function fetchLineupProfileGameData(
  gameId,
  date
) {
  const shardPath =
    `data/games/${
      encodeURIComponent(date)
    }.json?v=${Date.now()}`;

  try {
    const shardResponse =
      await fetch(
        shardPath,
        {
          cache: "no-store"
        }
      );

    if (shardResponse.ok) {
      return shardResponse.json();
    }
  } catch {
    // Fall back to the complete game file.
  }

  const fullResponse =
    await fetch(
      `data/games.json?v=${Date.now()}`,
      {
        cache: "no-store"
      }
    );

  if (!fullResponse.ok) {
    throw new Error(
      `Unable to load game ${gameId}.`
    );
  }

  return fullResponse.json();
}

function linkOffensivePlayerName({
  container,
  player,
  profile
}) {
  const playerId =
    player?.id;

  const playerName =
    normalizeLineupPlayerText(
      player?.name
    );

  if (
    !playerId ||
    !playerName
  ) {
    return;
  }

  const signal =
    profile
      ?.roles
      ?.hitting
      ?.signal || {};

  const signalClass =
    signal.class_name ||
    "player-signal-neutral";

  const signalLabel =
    signal.label ||
    "Hitting rating unavailable";

  const matchingNodes = [];

  const walker =
    document.createTreeWalker(
      container,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode(node) {
          const parent =
            node.parentElement;

          if (
            !parent ||
            parent.closest(
              "a, script, style"
            )
          ) {
            return (
              NodeFilter
                .FILTER_REJECT
            );
          }

          const text =
            normalizeLineupPlayerText(
              node.nodeValue
            );

          return text === playerName
            ? NodeFilter.FILTER_ACCEPT
            : NodeFilter.FILTER_REJECT;
        }
      }
    );

  while (
    walker.nextNode()
  ) {
    matchingNodes.push(
      walker.currentNode
    );
  }

  matchingNodes.forEach(node => {
    const anchor =
      document.createElement("a");

    const route =
      new URLSearchParams({
        id: String(playerId),
        role: "hitting"
      });

    anchor.href =
      `player.html?${route.toString()}`;

    anchor.className =
      `lineup-player-profile-link ${signalClass}`;

    anchor.dataset.playerId =
      String(playerId);

    anchor.dataset.playerRole =
      "hitting";

    anchor.title =
      `${playerName} · ${signalLabel}`;

    anchor.setAttribute(
      "aria-label",
      `Open ${playerName} hitting profile`
    );

    anchor.addEventListener(
      "click",
      event => {
        event.stopPropagation();
      }
    );

    node.parentNode.replaceChild(
      anchor,
      node
    );

    anchor.appendChild(node);
  });
}

function normalizeLineupPlayerText(
  value
) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim();
}

if (
  document.readyState === "loading"
) {
  document.addEventListener(
    "DOMContentLoaded",
    installLineupPlayerProfileLinks,
    {
      once: true
    }
  );
} else {
  installLineupPlayerProfileLinks();
}
