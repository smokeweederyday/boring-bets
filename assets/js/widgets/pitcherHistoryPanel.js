import {
  applyGlobalTierHighlights
} from "../engine/highlightPreferences.js?v=phase11z-exact-typed-spread3";

const historyCache = new Map();
const gameContextCache = new Map();

let root = null;
let panel = null;
let content = null;
let currentTrigger = null;
let closeTimer = null;
let openTimer = null;
let currentPitcherId = "";

const mobileQuery = window.matchMedia(
  "(max-width: 760px), (hover: none), (pointer: coarse)"
);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatInteger(value) {
  return Number.isFinite(Number(value))
    ? String(Math.round(Number(value)))
    : "–";
}

function formatRate(value) {
  return Number.isFinite(Number(value))
    ? Number(value).toFixed(2)
    : "–";
}

function formatIp(value) {
  const text = String(value ?? "").trim();
  return text || "–";
}

const HISTORY_RANK_KEYS = [
  "ip",
  "hits",
  "runs",
  "earned_runs",
  "walks",
  "strikeouts",
  "home_runs",
  "era",
  "whip"
];

const HISTORY_RANK_LABELS = {
  ip: "IP",
  hits: "H",
  runs: "R",
  earned_runs: "ER",
  walks: "BB",
  strikeouts: "SO",
  home_runs: "HR",
  era: "ERA",
  whip: "WHIP"
};

function normalizeRankInfo(
  row,
  metric
) {
  const raw = row?.ranks?.[metric];

  if (!raw) return null;

  if (Array.isArray(raw)) {
    return {
      rank: Number(raw[0]),
      poolSize: Number(raw[1]),
      year: raw[2],
      basis: String(raw[3] || "")
    };
  }

  return {
    rank: Number(raw.rank),
    poolSize: Number(
      raw.pool_size
      ?? raw.poolSize
    ),
    year:
      raw.year
      ?? raw.season
      ?? "",
    basis: String(raw.basis || "")
  };
}

function historyRankTooltip(
  info,
  metric
) {
  if (!info) return "";

  const label =
    HISTORY_RANK_LABELS[metric]
    || metric;

  if (info.basis === "season") {
    return (
      `Rank ${info.rank} of ` +
      `${info.poolSize} qualifying ` +
      `MLB pitchers in ${info.year} · ` +
      `${label} season ranking`
    );
  }

  if (info.basis === "start") {
    return (
      `Rank ${info.rank} of ` +
      `${info.poolSize} MLB starters ` +
      `in ${info.year} · ` +
      `${label} compared with that ` +
      `season's starter baseline`
    );
  }

  if (
    info.basis === "year-adjusted"
  ) {
    return (
      `Year-adjusted ${label} ranking · ` +
      `Rank ${info.rank} of ` +
      `${info.poolSize}`
    );
  }

  return (
    `Rank ${info.rank} of ` +
    `${info.poolSize}`
  );
}

function rankedHistoryCell(
  row,
  metric,
  display
) {
  const info = normalizeRankInfo(
    row,
    metric
  );

  if (
    !info
    || !Number.isFinite(info.rank)
    || !Number.isFinite(
      info.poolSize
    )
    || info.rank < 1
    || info.poolSize < 2
  ) {
    return `
      <td>
        ${escapeHtml(display)}
      </td>
    `;
  }

  const tooltip =
    historyRankTooltip(
      info,
      metric
    );

  return `
    <td
      class="pitcher-history-ranked-cell"
      data-global-rank="${info.rank}"
      data-global-league-size="${info.poolSize}"
      title="${escapeHtml(tooltip)}"
      aria-label="${escapeHtml(tooltip)}"
    >
      ${escapeHtml(display)}
    </td>
  `;
}

function aggregateHistoryRanks(rows) {
  const ranks = {};

  HISTORY_RANK_KEYS.forEach(
    metric => {
      const values = rows
        .map(row =>
          normalizeRankInfo(
            row,
            metric
          )
        )
        .filter(info =>
          info
          && Number.isFinite(
            info.rank
          )
          && Number.isFinite(
            info.poolSize
          )
          && info.poolSize > 1
        );

      if (!values.length) {
        return;
      }

      const averagePercentile =
        values.reduce(
          (total, info) => {
            const percentile =
              1 - (
                (
                  info.rank - 1
                ) / (
                  info.poolSize - 1
                )
              );

            return total + percentile;
          },
          0
        ) / values.length;

      const syntheticPool = 100;

      const syntheticRank =
        Math.max(
          1,
          Math.min(
            syntheticPool,
            Math.round(
              1
              + (
                1 - averagePercentile
              ) * (
                syntheticPool - 1
              )
            )
          )
        );

      ranks[metric] = {
        rank: syntheticRank,
        pool_size: syntheticPool,
        year: "",
        basis: "year-adjusted"
      };
    }
  );

  return ranks;
}


function createRoot(trigger) {
  const card = trigger?.closest(".pitcher-card-link");

  if (!card) return null;

  root = card.querySelector(".pitcher-history-inline");

  if (!root) {
    root = document.createElement("div");
    root.className =
      "pitcher-history-layer pitcher-history-inline";
    root.hidden = true;

    root.innerHTML = `
      <section
        class="pitcher-history-panel"
        aria-label="Pitcher recent history"
      >
        <div class="pitcher-history-content">
          <p class="pitcher-history-loading">
            Loading recent history…
          </p>
        </div>
      </section>
    `;

    const filterRow =
      card.querySelector(".pitcher-filter-row");

    card.insertBefore(
      root,
      filterRow || null
    );
  }

  const pitcherIdValue =
    pitcherIdFromElement(trigger);

  if (pitcherIdValue) {
    root.id =
      `pitcher-history-inline-${pitcherIdValue}`;

    trigger.setAttribute(
      "aria-controls",
      root.id
    );
  }

  panel =
    root.querySelector(".pitcher-history-panel");

  content =
    root.querySelector(".pitcher-history-content");

  return root;
}

function pitcherIdFromElement(element) {
  const direct = element?.dataset?.pitcherId;

  if (direct) return String(direct);

  const href = String(element?.getAttribute?.("href") || "");
  const match = href.match(/[?&]id=(\d+)/);

  return match ? match[1] : "";
}

async function fetchHistory(pitcherId) {
  if (historyCache.has(pitcherId)) {
    return historyCache.get(pitcherId);
  }

  const request = fetch(
    `data/pitcher-history/${encodeURIComponent(pitcherId)}.json`,
    { cache: "no-store" }
  ).then(response => {
    if (!response.ok) {
      throw new Error("Pitcher history is still being prepared.");
    }

    return response.json();
  });

  historyCache.set(pitcherId, request);
  return request;
}

function currentGameId() {
  return new URLSearchParams(window.location.search).get("id") || "";
}

async function fetchCurrentGame() {
  const gameId = currentGameId();

  if (!gameId) return null;

  if (gameContextCache.has(gameId)) {
    return gameContextCache.get(gameId);
  }

  const date = gameId.slice(0, 10);

  const request = fetch(
    `data/games/${encodeURIComponent(date)}.json?v=${Date.now()}`,
    { cache: "no-store" }
  )
    .then(response => {
      if (!response.ok) return null;
      return response.json();
    })
    .then(documentValue => {
      const games = Array.isArray(documentValue?.games)
        ? documentValue.games
        : [];

      return games.find(game => game?.id === gameId) || null;
    });

  gameContextCache.set(gameId, request);
  return request;
}

function teamAbbr(game, side) {
  const team = game?.[`${side}_team`] || game?.teams?.[side] || {};

  return String(
    team.abbr ||
    team.abbreviation ||
    team.code ||
    ""
  ).toUpperCase();
}

function pitcherId(game, side) {
  return String(
    game?.pitchers?.[side]?.id ||
    game?.[`${side}_pitcher_id`] ||
    ""
  );
}

async function opponentForPitcher(pitcherIdValue) {
  const game = await fetchCurrentGame();

  if (!game) return "";

  if (pitcherId(game, "away") === String(pitcherIdValue)) {
    return teamAbbr(game, "home");
  }

  if (pitcherId(game, "home") === String(pitcherIdValue)) {
    return teamAbbr(game, "away");
  }

  return "";
}

function aggregateRows(rows, label) {
  const totals = {
    wins: 0,
    losses: 0,
    outs: 0,
    hits: 0,
    runs: 0,
    earnedRuns: 0,
    walks: 0,
    strikeouts: 0,
    homeRuns: 0
  };

  rows.forEach(row => {
    totals.wins += Number(row?.wins || 0);
    totals.losses += Number(row?.losses || 0);
    totals.outs += Number(row?.outs || 0);
    totals.hits += Number(row?.hits || 0);
    totals.runs += Number(row?.runs || 0);
    totals.earnedRuns += Number(row?.earned_runs || 0);
    totals.walks += Number(row?.walks || 0);
    totals.strikeouts += Number(row?.strikeouts || 0);
    totals.homeRuns += Number(row?.home_runs || 0);
  });

  const innings = totals.outs / 3;

  return {
    label,
    decision: `${totals.wins}-${totals.losses}`,
    ip: `${Math.floor(totals.outs / 3)}.${totals.outs % 3}`,
    hits: totals.hits,
    runs: totals.runs,
    earned_runs: totals.earnedRuns,
    walks: totals.walks,
    strikeouts: totals.strikeouts,
    home_runs: totals.homeRuns,
    era: innings ? totals.earnedRuns * 9 / innings : null,
    whip: innings ? (totals.hits + totals.walks) / innings : null,
    ranks: aggregateHistoryRanks(rows)
  };
}

function cells(row, firstLabel, opponentLabel = "") {
  return `
    <td class="pitcher-history-sticky-cell">
      ${escapeHtml(firstLabel || "–")}
    </td>
    <td>
      ${escapeHtml(opponentLabel || "")}
    </td>
    <td>
      ${escapeHtml(row?.decision || "–")}
    </td>
    ${rankedHistoryCell(
      row,
      "ip",
      formatIp(row?.ip)
    )}
    ${rankedHistoryCell(
      row,
      "hits",
      formatInteger(row?.hits)
    )}
    ${rankedHistoryCell(
      row,
      "runs",
      formatInteger(row?.runs)
    )}
    ${rankedHistoryCell(
      row,
      "earned_runs",
      formatInteger(
        row?.earned_runs
      )
    )}
    ${rankedHistoryCell(
      row,
      "walks",
      formatInteger(row?.walks)
    )}
    ${rankedHistoryCell(
      row,
      "strikeouts",
      formatInteger(
        row?.strikeouts
      )
    )}
    ${rankedHistoryCell(
      row,
      "home_runs",
      formatInteger(
        row?.home_runs
      )
    )}
    ${rankedHistoryCell(
      row,
      "era",
      formatRate(row?.era)
    )}
    ${rankedHistoryCell(
      row,
      "whip",
      formatRate(row?.whip)
    )}
  `;
}

function seasonRows(rows) {
  return rows.map(row => `
    <tr class="pitcher-history-season-row">
      ${cells(row, row?.season || row?.label)}
    </tr>
  `).join("");
}

function startRows(rows) {
  return rows.map(row => `
    <tr>
      ${cells(
        row,
        row?.date,
        row?.opponent_label || row?.opponent_abbr
      )}
    </tr>
  `).join("");
}

function sectionHeader(label, rows) {
  const summary = aggregateRows(rows, label);

  return `
    <tr class="pitcher-history-section-row">
      ${cells(summary, label)}
    </tr>
  `;
}

function renderHistory(
  data,
  opponentAbbr,
  targetContent = content
) {
  const pitcher = data?.pitcher || {};
  const recentSeasons = Array.isArray(data?.recent_seasons)
    ? data.recent_seasons
    : [];

  const lastStarts = Array.isArray(data?.last_starts)
    ? data.last_starts
    : [];

  const allStarts = Array.isArray(data?.starts)
    ? data.starts
    : [];

  const opponentStarts = opponentAbbr
    ? allStarts
        .filter(row =>
          String(row?.opponent_abbr || "").toUpperCase() === opponentAbbr
        )
        .slice(0, 5)
    : [];

  const handedness = pitcher?.hand
    ? `${String(pitcher.hand).toUpperCase()}HP`
    : "—";

  const details = [
    pitcher?.number ? `#${pitcher.number}` : null,
    pitcher?.age ? `Age ${pitcher.age}` : null,
    handedness,
    pitcher?.record || "0-0",
    `${formatRate(pitcher?.era)} ERA`
  ].filter(Boolean).join(" · ");

  const rookieNote = data?.rookie_candidate
    ? `
      <p class="pitcher-history-rookie-note">
        Only ${formatInteger(data?.career_start_count)} MLB starts available.
        <a
          href="${escapeHtml(pitcher?.minor_league_url || "#")}"
          target="_blank"
          rel="noopener"
        >
          See minor-league stats →
        </a>
      </p>
    `
    : "";

  const opponentSection = opponentAbbr
    ? (
        opponentStarts.length
          ? `
            ${sectionHeader(`Last 5 vs ${opponentAbbr}`, opponentStarts)}
            ${startRows(opponentStarts)}
          `
          : `
            <tr class="pitcher-history-section-label-only">
              <th colspan="12">Last 5 vs ${escapeHtml(opponentAbbr)}</th>
            </tr>
            <tr class="pitcher-history-empty-row">
              <td colspan="12">
                Has never seen ${escapeHtml(opponentAbbr)} as a starter.
              </td>
            </tr>
          `
      )
    : `
      <tr class="pitcher-history-section-label-only">
        <th colspan="12">Last 5 vs opponent</th>
      </tr>
      <tr class="pitcher-history-empty-row">
        <td colspan="12">
          Opponent history is unavailable for this matchup.
        </td>
      </tr>
    `;

  targetContent.innerHTML = `
    <header class="pitcher-history-header">
      <div>
        <a
          class="pitcher-history-name"
          href="${escapeHtml(pitcher?.profile_url || "#")}"
        >
          ${escapeHtml(pitcher?.name || "Pitcher")}
        </a>

        <p>${escapeHtml(details)}</p>
      </div>
    </header>

    <div class="pitcher-history-table-scroll">
      <table class="data-table pitcher-data-table pitcher-history-table">
        <thead>
          <tr>
            <th class="pitcher-history-sticky-cell">Date / Season</th>
            <th>Opp</th>
            <th>DEC</th>
            <th>IP</th>
            <th>H</th>
            <th>R</th>
            <th>ER</th>
            <th>BB</th>
            <th>SO</th>
            <th>HR</th>
            <th>ERA</th>
            <th>WHIP</th>
          </tr>
        </thead>

        <tbody>
          ${seasonRows(recentSeasons)}

          <tr class="pitcher-history-divider">
            <td colspan="12"></td>
          </tr>

          ${
            lastStarts.length
              ? `
                ${sectionHeader("Last 7 GS", lastStarts)}
                ${startRows(lastStarts)}
              `
              : `
                <tr class="pitcher-history-section-label-only">
                  <th colspan="12">Last 7 GS</th>
                </tr>
                <tr class="pitcher-history-empty-row">
                  <td colspan="12">
                    No MLB starts are available.
                  </td>
                </tr>
              `
          }

          <tr class="pitcher-history-divider">
            <td colspan="12"></td>
          </tr>

          ${opponentSection}
        </tbody>
      </table>
    </div>

    ${rookieNote}

    <footer class="pitcher-history-footer">
      <a href="${escapeHtml(pitcher?.profile_url || "#")}">
        View full pitcher page →
      </a>
    </footer>
  `;

  applyGlobalTierHighlights(
    targetContent
  );
}

function positionDesktop(trigger) {
  const triggerRect = trigger.getBoundingClientRect();
  const panelRect = panel.getBoundingClientRect();
  const margin = 12;

  let left = triggerRect.left;
  let top = triggerRect.bottom + 8;

  if (left + panelRect.width > window.innerWidth - margin) {
    left = window.innerWidth - panelRect.width - margin;
  }

  if (left < margin) {
    left = margin;
  }

  if (top + panelRect.height > window.innerHeight - margin) {
    top = Math.max(
      margin,
      triggerRect.top - panelRect.height - 8
    );
  }

  panel.style.left = `${Math.round(left)}px`;
  panel.style.top = `${Math.round(top)}px`;
}

async function openPanel(trigger) {
  const inlineRoot = createRoot(trigger);

  if (!inlineRoot) return;

  const targetContent =
    inlineRoot.querySelector(
      ".pitcher-history-content"
    );

  const pitcherIdValue =
    pitcherIdFromElement(trigger);

  if (!pitcherIdValue || !targetContent) {
    return;
  }

  const alreadyOpen =
    !inlineRoot.hidden &&
    trigger.getAttribute("aria-expanded") === "true";

  if (alreadyOpen) {
    closePanel(inlineRoot, trigger);
    return;
  }

  /*
    Each pitcher owns an independent dropdown.
    Opening one does not close the other.
  */
  inlineRoot.hidden = false;

  trigger.setAttribute(
    "aria-expanded",
    "true"
  );

  trigger.setAttribute(
    "title",
    "Hide recent history"
  );

  targetContent.innerHTML = `
    <p class="pitcher-history-loading">
      Loading recent history…
    </p>
  `;

  try {
    const [historyData, opponent] =
      await Promise.all([
        fetchHistory(pitcherIdValue),
        opponentForPitcher(pitcherIdValue)
      ]);

    if (
      inlineRoot.hidden ||
      trigger.getAttribute("aria-expanded") !== "true"
    ) {
      return;
    }

    renderHistory(
      historyData,
      opponent,
      targetContent
    );

  } catch (error) {
    targetContent.innerHTML = `
      <div class="pitcher-history-error">
        <strong>Recent history unavailable</strong>
        <p>${
          escapeHtml(
            error?.message ||
            "Unable to load recent history."
          )
        }</p>
      </div>
    `;
  }
}

function closePanel(
  targetRoot = null,
  targetTrigger = null
) {
  clearTimeout(closeTimer);
  clearTimeout(openTimer);

  const roots = targetRoot
    ? [targetRoot]
    : Array.from(
        document.querySelectorAll(
          ".pitcher-history-inline"
        )
      );

  roots.forEach(inlineRoot => {
    inlineRoot.hidden = true;
  });

  const triggers = targetTrigger
    ? [targetTrigger]
    : Array.from(
        document.querySelectorAll(
          "[data-pitcher-history-trigger]"
        )
      );

  triggers.forEach(trigger => {
    trigger.setAttribute(
      "aria-expanded",
      "false"
    );

    trigger.setAttribute(
      "title",
      "Show recent history"
    );
  });
}

function cancelClose() {
  clearTimeout(closeTimer);
}

function scheduleClose() {
  if (mobileQuery.matches) return;

  clearTimeout(closeTimer);

  closeTimer = window.setTimeout(() => {
    const active = document.activeElement;

    if (
      panel?.contains(active) ||
      currentTrigger?.contains?.(active)
    ) {
      return;
    }

    closePanel();
  }, 180);
}

function scheduleOpen(trigger) {
  clearTimeout(openTimer);

  openTimer = window.setTimeout(
    () => openPanel(trigger),
    160
  );
}

document.addEventListener("click", event => {
  const trigger = event.target.closest(
    "[data-pitcher-history-trigger]"
  );

  if (!trigger) return;

  event.preventDefault();
  event.stopPropagation();

  openPanel(trigger);
});

document.addEventListener("keydown", event => {
  if (event.key === "Escape") {
    closePanel();
  }
});

window.addEventListener("resize", () => {
  if (
    root &&
    !root.hidden &&
    !mobileQuery.matches &&
    currentTrigger
  ) {
    positionDesktop(currentTrigger);
  }
});
