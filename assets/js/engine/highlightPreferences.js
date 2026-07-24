const STORAGE_KEY =
  "boringBetsGlobalHighlightPreferencesV3";

const MIN_RANGE = 5;
const MAX_RANGE = 100;
const RANGE_STEP = 5;

const DEFAULT_PREFERENCES = Object.freeze({
  range: 25,
  neutralCenter: true
});

const TIER_CLASSES = Object.freeze({
  metric: [
    "metric-elite",
    "metric-good",
    "metric-average",
    "metric-poor",
    "metric-awful"
  ],

  "pitcher-signal": [
    "pitcher-signal-strong-positive",
    "pitcher-signal-positive",
    "pitcher-signal-neutral",
    "pitcher-signal-negative",
    "pitcher-signal-strong-negative"
  ],

  "offense-signal": [
    "offense-signal-strong-positive",
    "offense-signal-positive",
    "offense-signal-neutral",
    "offense-signal-negative",
    "offense-signal-strong-negative"
  ]
});

const TIER_SCORE_ANCHORS = Object.freeze([
  1,
  0.4,
  0,
  -0.4,
  -1
]);


function normalizeRange(value) {
  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return DEFAULT_PREFERENCES.range;
  }

  return Math.max(
    MIN_RANGE,
    Math.min(
      MAX_RANGE,
      Math.round(
        numericValue
      )
    )
  );
}


function normalizeSliderRange(value) {
  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return DEFAULT_PREFERENCES.range;
  }

  return normalizeRange(
    Math.round(
      numericValue
      / RANGE_STEP
    )
    * RANGE_STEP
  );
}

export function getHighlightPreferences() {
  try {
    const stored = JSON.parse(
      localStorage.getItem(
        STORAGE_KEY
      ) || "{}"
    );

    return {
      range:
        normalizeRange(
          stored.range
        ),

      neutralCenter:
        stored.neutralCenter
        !== false
    };

  } catch (error) {
    return {
      ...DEFAULT_PREFERENCES
    };
  }
}


export function saveHighlightPreferences(
  nextPreferences = {}
) {
  const current =
    getHighlightPreferences();

  const normalized = {
    range:
      normalizeRange(
        nextPreferences.range
        ?? current.range
      ),

    neutralCenter:
      nextPreferences.neutralCenter
      ?? current.neutralCenter
  };

  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(
        normalized
      )
    );
  } catch (error) {
    // Continue without persistence.
  }

  applyHighlightPreferencesToDocument(
    normalized
  );

  window.dispatchEvent(
    new CustomEvent(
      "boringbets:highlight-preferences",
      {
        detail: normalized
      }
    )
  );

  return normalized;
}


export function applyHighlightPreferencesToDocument(
  preferences =
    getHighlightPreferences()
) {
  const root =
    document.documentElement;

  root.dataset.highlightRange =
    String(preferences.range);

  root.dataset.highlightNeutral =
    preferences.neutralCenter
      ? "gray"
      : "spectrum";
}


function scaledSignalScore(
  rawScore
) {
  const score =
    Number(rawScore);

  if (!Number.isFinite(score)) {
    return null;
  }

  const preferences =
    getHighlightPreferences();

  const multiplier =
    30 / preferences.range;

  return Math.max(
    -1,
    Math.min(
      1,
      score * multiplier
    )
  );
}


function scoreTierIndex(
  rawScore
) {
  const score =
    scaledSignalScore(
      rawScore
    );

  if (score === null) {
    return null;
  }

  if (score >= 0.6) {
    return 0;
  }

  if (score >= 0.2) {
    return 1;
  }

  if (score > -0.2) {
    return 2;
  }

  if (score > -0.6) {
    return 3;
  }

  return 4;
}


export function getGlobalRankTierClass(
  rank,
  leagueSize = 30
) {
  const numericRank =
    Number(rank);

  const numericLeagueSize =
    Number(leagueSize);

  if (
    !Number.isFinite(numericRank)
    || !Number.isFinite(
      numericLeagueSize
    )
    || numericRank < 1
    || numericLeagueSize < 2
    || numericRank > numericLeagueSize
  ) {
    return "metric-missing";
  }

  const score =
    1
    - (
      2
      * (numericRank - 1)
      / (numericLeagueSize - 1)
    );

  const index =
    scoreTierIndex(
      score
    );

  return index === null
    ? "metric-missing"
    : TIER_CLASSES.metric[index];
}


export function getGlobalSignalTierClass(
  score,
  family
) {
  const classes =
    TIER_CLASSES[family];

  const index =
    scoreTierIndex(
      score
    );

  if (
    !classes
    || index === null
  ) {
    return null;
  }

  return classes[index];
}


function removeTierClasses(
  element,
  family
) {
  const classes =
    TIER_CLASSES[family]
    || [];

  element.classList.remove(
    ...classes
  );
}


function applyRankElement(
  element
) {
  const rawRank =
    String(
      element.dataset.globalRank
      ?? ""
    ).trim();

  const rawLeagueSize =
    String(
      element.dataset.globalLeagueSize
      ?? ""
    ).trim();

  const rank =
    Number(rawRank);

  const leagueSize =
    Number(rawLeagueSize);

  const hasValidRank =
    rawRank !== ""
    && Number.isFinite(rank)
    && rank >= 1
    && Number.isFinite(leagueSize)
    && leagueSize >= rank;

  const benchmarkTier =
    String(
      element.dataset
        .globalBenchmarkTier
      || ""
    ).trim();

  let className =
    "metric-missing";

  if (hasValidRank) {
    className =
      getGlobalRankTierClass(
        rank,
        leagueSize
      )
      || "metric-missing";
  } else if (
    benchmarkTier !== "metric-missing"
    && TIER_CLASSES.metric.includes(
      benchmarkTier
    )
  ) {
    className =
      benchmarkTier;
  }

  removeTierClasses(
    element,
    "metric"
  );

  element.classList.add(
    className
  );

  element.classList.add(
    "global-tier-highlight"
  );
}


function applySignalElement(
  element
) {
  const family =
    element.dataset
      .globalSignalFamily;

  const score =
    element.dataset
      .globalSignalScore;

  const className =
    getGlobalSignalTierClass(
      score,
      family
    );

  if (!className) {
    return;
  }

  removeTierClasses(
    element,
    family
  );

  element.classList.add(
    className
  );

  element.classList.add(
    "global-tier-highlight"
  );
}


function inferExistingSignal(
  element
) {
  if (
    element.dataset
      .globalSignalFamily
  ) {
    return;
  }

  for (
    const [
      family,
      classes
    ]
    of Object.entries(
      TIER_CLASSES
    )
  ) {
    const index =
      classes.findIndex(
        className =>
          element.classList.contains(
            className
          )
      );

    if (index === -1) {
      continue;
    }

    element.dataset
      .globalSignalFamily =
        family;

    element.dataset
      .globalSignalScore =
        String(
          TIER_SCORE_ANCHORS[
            index
          ]
        );

    return;
  }
}


function isExcludedBullpenCell(
  _element
) {
  /*
    Bullpen names, summary metrics, ranks, and
    reliever-stat cells all participate in the
    shared highlighting bar.
  */
  return false;
}


export function applyGlobalTierHighlights(
  root = document
) {
  root
    .querySelectorAll(
      "[data-global-rank]"
    )
    .forEach(element => {
      if (
        isExcludedBullpenCell(
          element
        )
      ) {
        return;
      }

      applyRankElement(
        element
      );
    });

  root
    .querySelectorAll(
      "[data-global-signal-score]"
    )
    .forEach(element => {
      if (
        isExcludedBullpenCell(
          element
        )
      ) {
        return;
      }

      applySignalElement(
        element
      );
    });

  const fallbackSelector = [
    ".pitcher-comparison-card .metric-elite",
    ".pitcher-comparison-card .metric-good",
    ".pitcher-comparison-card .metric-average",
    ".pitcher-comparison-card .metric-poor",
    ".pitcher-comparison-card .metric-awful",

    ".offense-comparison-card .metric-elite",
    ".offense-comparison-card .metric-good",
    ".offense-comparison-card .metric-average",
    ".offense-comparison-card .metric-poor",
    ".offense-comparison-card .metric-awful",

    ".matchup-intelligence-console .metric-elite",
    ".matchup-intelligence-console .metric-good",
    ".matchup-intelligence-console .metric-average",
    ".matchup-intelligence-console .metric-poor",
    ".matchup-intelligence-console .metric-awful",

    ".bullpen-widget-shell .metric-elite",
    ".bullpen-widget-shell .metric-good",
    ".bullpen-widget-shell .metric-average",
    ".bullpen-widget-shell .metric-poor",
    ".bullpen-widget-shell .metric-awful",

    ".pitcher-name-signal",

    ".pitcher-control-signal",
    ".offense-control-signal"
  ].join(",");

  root
    .querySelectorAll(
      fallbackSelector
    )
    .forEach(element => {
      if (
        isExcludedBullpenCell(
          element
        )
      ) {
        return;
      }

      if (
        element.dataset.globalRank
      ) {
        return;
      }

      inferExistingSignal(
        element
      );

      if (
        element.dataset
          .globalSignalScore
      ) {
        applySignalElement(
          element
        );
      }
    });
}


export function initializeHighlightControls({
  rangeInput,
  rangeOutput,
  neutralInput,
  onChange
} = {}) {
  applyHighlightPreferencesToDocument();

  if (
    !rangeInput
    || !neutralInput
  ) {
    return;
  }

  const setValueBox = value => {
    if (!rangeOutput) {
      return;
    }

    rangeOutput.value =
      String(value);
  };

  const updateSliderThumb = value => {
    const normalized =
      normalizeRange(value);

    const progress =
      (
        normalized
        - MIN_RANGE
      )
      / (
        MAX_RANGE
        - MIN_RANGE
      );

    const start = [
      116,
      126,
      121
    ];

    const end = [
      244,
      247,
      245
    ];

    const channels =
      start.map(
        (
          channel,
          index
        ) => {
          return Math.round(
            channel
            + (
              end[index]
              - channel
            )
            * progress
          );
        }
      );

    rangeInput.style.setProperty(
      "--highlight-thumb-color",
      `rgb(${
        channels.join(", ")
      })`
    );
  };

  const syncControls = () => {
    const preferences =
      getHighlightPreferences();

    rangeInput.value =
      String(
        preferences.range
      );

    neutralInput.checked =
      preferences.neutralCenter;

    setValueBox(
      preferences.range
    );

    updateSliderThumb(
      preferences.range
    );
  };

  const commitRange = (
    value,
    {
      snapToSliderStep = false
    } = {}
  ) => {
    const normalized =
      snapToSliderStep
        ? normalizeSliderRange(value)
        : normalizeRange(value);

    rangeInput.value =
      String(normalized);

    setValueBox(
      normalized
    );

    updateSliderThumb(
      normalized
    );

    const preferences =
      saveHighlightPreferences({
        range: normalized
      });

    applyHighlightPreferencesToDocument();

    applyGlobalTierHighlights(
      document
    );

    onChange?.(
      preferences
    );
  };

  syncControls();

  if (
    rangeInput.dataset
      .highlightControlsBound
    === "true"
  ) {
    return;
  }

  rangeInput.dataset
    .highlightControlsBound =
      "true";

  rangeInput.addEventListener(
    "input",
    () => {
      commitRange(
        rangeInput.value,
        {
          snapToSliderStep: true
        }
      );
    }
  );

  if (rangeOutput) {
    rangeOutput.addEventListener(
      "change",
      () => {
        commitRange(
          rangeOutput.value
        );
      }
    );

    rangeOutput.addEventListener(
      "keydown",
      event => {
        if (event.key !== "Enter") {
          return;
        }

        event.preventDefault();

        commitRange(
          rangeOutput.value
        );

        rangeOutput.blur();
      }
    );
  }

  neutralInput.addEventListener(
    "change",
    () => {
      const preferences =
        saveHighlightPreferences({
          neutralCenter:
            neutralInput.checked
        });

      applyHighlightPreferencesToDocument();

      applyGlobalTierHighlights(
        document
      );

      onChange?.(
        preferences
      );
    }
  );

  window.addEventListener(
    "storage",
    event => {
      if (
        event.key !== STORAGE_KEY
      ) {
        return;
      }

      syncControls();

      applyHighlightPreferencesToDocument();

      applyGlobalTierHighlights(
        document
      );
    }
  );
}

applyHighlightPreferencesToDocument();
