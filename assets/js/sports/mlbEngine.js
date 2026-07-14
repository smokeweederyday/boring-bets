const MLB_OFFENSE_METRICS = [
  "AVG",
  "wRC+",
  "K%",
  "BB%",
  "OBP",
  "OPS"
];

export function buildMlbOffenseModule({
  game,
  side,
  timeframe = "last_30",
  location = "all"
}) {
  const isAway =
    side === "away";

  const team =
    isAway
      ? game.away_team
      : game.home_team;

  const offense =
    isAway
      ? game.offense?.away
      : game.offense?.home;

  const opposingPitcher =
    isAway
      ? game.pitchers?.home
      : game.pitchers?.away;

  const pitcherHand =
    opposingPitcher?.throws === "L"
      ? "L"
      : opposingPitcher?.throws === "R"
        ? "R"
        : null;

  const period =
    offense?.stats?.[timeframe] || {};

  const selectedLocation =
    period?.[location] ||
    period?.all ||
    {};

  return {
    title:
      `${team?.abbr || offense?.team || "TEAM"} OFFENSE`,

    context:
      pitcherHand
        ? `vs ${pitcherHand}HP`
        : "Starter handedness TBD",

    opponent:
      opposingPitcher?.name ||
      "Starter TBD",

    detailsUrl:
      offense?.details_url || "#",

    metrics:
      MLB_OFFENSE_METRICS.map(metric => {
        const metricData =
          selectedLocation?.[metric] || {};

        return {
          label: metric,
          type:
            getMlbOffenseMetricType(metric),

          overall: {
            value:
              metricData.overall ?? null,

            rank:
              metricData.overall_rank ?? null
          },

          split: {
            value:
              metricData.vs_hand ?? null,

            rank:
              metricData.vs_hand_rank ?? null
          }
        };
      })
  };
}

export function getMlbOffenseMetricType(metric) {
  if (
    metric === "AVG" ||
    metric === "OBP" ||
    metric === "OPS"
  ) {
    return "average";
  }

  if (
    metric === "K%" ||
    metric === "BB%"
  ) {
    return "percent";
  }

  return "integer";
}