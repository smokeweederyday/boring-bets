async function loadCard() {
  try {
    const response = await fetch("data/todays-card.json");
    const data = await response.json();

    document.getElementById("cardDate").textContent =
      "Date: " + data.date;

    document.getElementById("cardUpdated").textContent =
      "Updated: " + data.updated_at;

    const plays = data.plays;

    document.getElementById("totalPlays").textContent =
      plays.length;

    const totalUnits = plays.reduce(
      (sum, play) => sum + play.units,
      0
    );

    document.getElementById("totalUnits").textContent =
      totalUnits.toFixed(2);

    const sports = [...new Set(plays.map(p => p.sport))];

    document.getElementById("totalSports").textContent =
      sports.length;

    const container =
      document.getElementById("playsContainer");

    container.innerHTML = "";

    plays.forEach(play => {

      const stars = "★".repeat(play.rating);

      const card = document.createElement("div");

      card.className = "play-card";
      card.tabIndex = 0;
card.setAttribute("role", "link");

card.addEventListener("click", () => {
  window.location.href =
    `play.html?id=${encodeURIComponent(play.id)}`;
});

card.addEventListener("keydown", event => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    window.location.href =
      `play.html?id=${encodeURIComponent(play.id)}`;
  }
});

      card.innerHTML = `
  <div class="matchup-logos">
    <div class="team-logo away-logo">
      <img
        src="https://www.mlbstatic.com/team-logos/team-cap-on-dark/${play.away_team_id}.svg"
        alt="${play.away_team} logo"
      >
      <span>${play.away_team}</span>
    </div>

    <div class="matchup-at">@</div>

    <div class="team-logo home-logo">
      <img
        src="https://www.mlbstatic.com/team-logos/team-cap-on-dark/${play.home_team_id}.svg"
        alt="${play.home_team} logo"
      >
      <span>${play.home_team}</span>
    </div>
  </div>

  <div class="play-top">
    <span class="sport">${play.sport}</span>
    <span class="stars">${stars}</span>
  </div>

  <h2>${play.play}</h2>

  <p><strong>Game:</strong> ${play.game}</p>
  <p><strong>Odds:</strong> ${play.odds}</p>
  <p><strong>Units:</strong> ${play.units}</p>
  <p>${play.analysis}</p>

  <small>${play.handicapper}</small>
`;

      container.appendChild(card);

    });

    document.getElementById("cardStatus").remove();

  } catch (err) {

    console.error(err);

    document.getElementById("cardStatus").textContent =
      "Unable to load today's card.";

  }
}

loadCard();