const PLAY_LOGO_BASE =
  "https://www.mlbstatic.com/team-logos/team-cap-on-dark";

async function loadPlay() {
  const status =
    document.getElementById("playStatus");

  const details =
    document.getElementById("playDetails");

  try {
    const playId =
      new URLSearchParams(
        window.location.search
      ).get("id");

    if (!playId) {
      throw new Error(
        "No play was selected."
      );
    }

    const cardResponse =
      await fetch(
        `data/todays-card.json?v=${Date.now()}`
      );

    if (!cardResponse.ok) {
      throw new Error(
        "Unable to load card data."
      );
    }

    const cardData =
      await cardResponse.json();

    const play =
      (cardData.plays || []).find(
        item => item.id === playId
      );

    if (!play) {
      throw new Error(
        "That play could not be found."
      );
    }

    const gameId =
      play.game_id ||
      createGameId(play);

    const gameDate =
      play.date ||
      String(gameId).slice(0, 10);

    const gamesResponse =
      await fetch(
        `data/games/${encodeURIComponent(
          gameDate
        )}.json?v=${Date.now()}`
      );

    const gamesData =
      gamesResponse.ok
        ? await gamesResponse.json()
        : { games: [] };

    const game =
      (gamesData.games || []).find(
        item => item.id === gameId
      );

    document.title =
      `${play.play} | Boring Bets`;

    renderPlayHeader(play);
    renderAnalysis(play.analysis);
    renderDeepDiveLink(gameId);
    renderMatchupSnapshot(game);

    status?.remove();

    if (details) {
      details.hidden = false;
    }
  } catch (error) {
    console.error(error);

    if (status) {
      status.textContent =
        error.message ||
        "Unable to load play.";
    }
  }
}

function renderPlayHeader(play) {
  setLogo(
    "awayLogo",
    play.away_team_id,
    play.away_team
  );

  setLogo(
    "homeLogo",
    play.home_team_id,
    play.home_team
  );

  setText(
    "awayTeam",
    play.away_team
  );

  setText(
    "homeTeam",
    play.home_team
  );

  setText(
    "playSport",
    `${play.sport} // ${play.game}`
  );

  setText(
    "playTitle",
    play.play
  );

  setText(
    "playOdds",
    play.odds
  );

  setText(
    "playUnits",
    Number(
      play.units || 0
    ).toFixed(2)
  );

  setText(
    "playRating",
    "★".repeat(
      Number(play.rating || 0)
    )
  );

  setText(
    "playHandicapper",
    play.handicapper
  );
}

function renderAnalysis(value) {
  const analysis =
    document.getElementById(
      "playAnalysis"
    );

  if (!analysis) return;

  analysis.innerHTML = "";

  String(
    value ||
    "Analysis has not been posted."
  )
    .split(/\n\s*\n/)
    .map(text => text.trim())
    .filter(Boolean)
    .forEach(text => {
      const paragraph =
        document.createElement("p");

      paragraph.textContent = text;
      analysis.appendChild(paragraph);
    });
}

function renderDeepDiveLink(gameId) {
  const deepDiveLink =
    document.getElementById(
      "deepDiveLink"
    );

  if (!deepDiveLink) return;

  deepDiveLink.href =
    `game.html?id=${encodeURIComponent(
      gameId
    )}`;
}

function renderMatchupSnapshot(game) {
  if (!game) {
    setText(
      "snapshotStatus",
      "Full matchup data has not been added yet."
    );

    setHtml(
      "snapshotPitching",
      renderMissingSnapshotValue("Pending")
    );

    setHtml(
      "snapshotOffense",
      renderMissingSnapshotValue("Pending")
    );

    setText(
      "snapshotBullpen",
      "Pending"
    );

    setText(
      "snapshotWeather",
      "Pending"
    );

    setText(
      "snapshotMarket",
      "Pending"
    );

    return;
  }

  setText(
    "snapshotStatus",
    buildSnapshotStatus(game)
  );

  setHtml(
    "snapshotPitching",
    formatPitchingSnapshot(game)
  );

  setHtml(
    "snapshotOffense",
    formatOffenseSnapshot(game)
  );

  setText(
    "snapshotBullpen",
    formatBullpenSnapshot(game)
  );

  setText(
    "snapshotWeather",
    formatWeatherSnapshot(game)
  );

  setText(
    "snapshotMarket",
    formatMarketSnapshot(game)
  );
}

function buildSnapshotStatus(game) {
  const lineupStatuses = [
    game.lineups?.away?.status,
    game.lineups?.home?.status
  ];

  const confirmedLineups =
    lineupStatuses.filter(
      value => value === "confirmed"
    ).length;

  const confirmedStarters = [
    game.pitchers?.away?.status,
    game.pitchers?.home?.status
  ].filter(
    value => value === "confirmed"
  ).length;

  const lineupText =
    confirmedLineups === 2
      ? "2 lineups confirmed"
      : confirmedLineups === 1
        ? "1 lineup confirmed"
        : "Projected lineups";

  return (
    `${lineupText} · ` +
    `${confirmedStarters} starters confirmed`
  );
}

function formatPitchingSnapshot(game) {
  const awayPitcher =
    game.pitchers?.away;

  const homePitcher =
    game.pitchers?.home;

  const awayEra =
    awayPitcher?.stats
      ?.season?.all?.era;

  const homeEra =
    homePitcher?.stats
      ?.season?.all?.era;

  return [
    formatPitcherLine(
      awayPitcher,
      awayEra
    ),
    formatPitcherLine(
      homePitcher,
      homeEra
    )
  ].join("");
}

function formatPitcherLine(
  pitcher,
  eraData
) {
  const name =
    pitcher?.name ||
    "Starter TBD";

  const value =
    getMetricValue(eraData);

  const rank =
    getMetricRank(eraData);

  const eraText =
    formatNumber(value, 2);

  const heatClass =
    eraText === "—"
      ? "snapshot-value-missing"
      : snapshotClassFromRank(rank);

  const display =
    eraText === "—"
      ? escapeHtml(name)
      : `${escapeHtml(name)} ${eraText} ERA`;

  return `
    <span class="${heatClass}">
      ${display}
    </span>
  `;
}

function formatOffenseSnapshot(game) {
  const away =
    game.away_team?.abbr || "Away";

  const home =
    game.home_team?.abbr || "Home";

  const awayOpsData =
    game.offense?.away?.stats
      ?.last_30?.all?.OPS;

  const homeOpsData =
    game.offense?.home?.stats
      ?.last_30?.all?.OPS;

  return [
    formatOffenseLine(
      away,
      awayOpsData
    ),
    formatOffenseLine(
      home,
      homeOpsData
    )
  ].join("");
}

function formatOffenseLine(
  team,
  opsData
) {
  const value =
    opsData?.vs_hand ?? null;

  const rank =
    opsData?.vs_hand_rank ?? null;

  const display =
    formatAverage(value);

  const heatClass =
    display === "—"
      ? "snapshot-value-missing"
      : snapshotClassFromRank(rank);

  return `
    <span class="${heatClass}">
      ${escapeHtml(team)} OPS ${display}
    </span>
  `;
}

function formatBullpenSnapshot(game) {
  const away =
    game.away_team?.abbr || "Away";

  const home =
    game.home_team?.abbr || "Home";

  const awayNote =
    game.bullpens?.away?.notes;

  const homeNote =
    game.bullpens?.home?.notes;

  if (!awayNote && !homeNote) {
    return "Workload and quality pending";
  }

  return [
    awayNote
      ? `${away}: ${awayNote}`
      : null,
    homeNote
      ? `${home}: ${homeNote}`
      : null
  ]
    .filter(Boolean)
    .join(" · ");
}

function formatWeatherSnapshot(game) {
  const weather =
    game.weather || {};

  const parts = [];

  if (
    weather.temperature !== null &&
    weather.temperature !== undefined
  ) {
    parts.push(
      `${Math.round(
        Number(weather.temperature)
      )}°`
    );
  }

  if (
    weather.wind_speed !== null &&
    weather.wind_speed !== undefined
  ) {
    const direction =
      weather.wind_direction
        ? `${weather.wind_direction} `
        : "";

    parts.push(
      `${direction}${Number(
        weather.wind_speed
      ).toFixed(1)} mph`
    );
  }

  if (weather.roof) {
    parts.push(
      `Roof ${weather.roof}`
    );
  }

  return parts.length
    ? parts.join(" · ")
    : "Conditions pending";
}

function formatMarketSnapshot(game) {
  const market =
    game.market || {};

  const open =
    market.total_open;

  const current =
    market.total_current;

  if (
    open === null &&
    current === null
  ) {
    return "Prices pending";
  }

  if (
    open !== null &&
    current !== null
  ) {
    return (
      `Total opened ${open} · ` +
      `Current ${current}`
    );
  }

  if (current !== null) {
    return `Current total ${current}`;
  }

  return `Opened ${open}`;
}

function createGameId(play) {
  return [
    play.date,
    String(
      play.away_team || ""
    ).toLowerCase(),
    String(
      play.home_team || ""
    ).toLowerCase()
  ].join("-");
}

function snapshotClassFromRank(rank) {
  const number =
    Number(rank);

  if (!Number.isFinite(number)) {
    return "snapshot-value-neutral";
  }

  if (number <= 10) {
    return "snapshot-value-good";
  }

  if (number <= 20) {
    return "snapshot-value-neutral";
  }

  return "snapshot-value-poor";
}

function getMetricValue(data) {
  if (
    data &&
    typeof data === "object"
  ) {
    return data.value ?? null;
  }

  return data ?? null;
}

function getMetricRank(data) {
  if (
    data &&
    typeof data === "object"
  ) {
    return data.rank ?? null;
  }

  return null;
}

function renderMissingSnapshotValue(value) {
  return `
    <span class="snapshot-value-missing">
      ${escapeHtml(value)}
    </span>
  `;
}

function formatAverage(value) {
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
    return "—";
  }

  return number
    .toFixed(3)
    .replace(/^0/, "");
}

function formatNumber(
  value,
  decimals
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
    return "—";
  }

  return number.toFixed(decimals);
}

function setText(id, value) {
  const element =
    document.getElementById(id);

  if (element) {
    element.textContent =
      value ?? "—";
  }
}

function setHtml(id, value) {
  const element =
    document.getElementById(id);

  if (element) {
    element.innerHTML =
      value || "—";
  }
}

function setLogo(
  id,
  teamId,
  team
) {
  const img =
    document.getElementById(id);

  if (!img) return;

  if (!teamId) {
    img.removeAttribute("src");

    img.alt =
      `${team || "Team"} logo unavailable`;

    return;
  }

  img.src =
    `${PLAY_LOGO_BASE}/${Number(
      teamId
    )}.svg`;

  img.alt =
    `${team || "Team"} logo`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loadPlay();