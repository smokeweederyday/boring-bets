async function loadPlay() {
  const status = document.getElementById("playStatus");
  const details = document.getElementById("playDetails");

  try {
    const params = new URLSearchParams(window.location.search);
    const playId = params.get("id");

    if (!playId) {
      throw new Error("No play was selected.");
    }

    const response = await fetch("data/todays-card.json");

    if (!response.ok) {
      throw new Error("Unable to load card data.");
    }

    const data = await response.json();
    const play = data.plays.find(function (item) {
      return item.id === playId;
    });

    if (!play) {
      throw new Error("That play could not be found.");
    }

    const logoBase =
      "https://www.mlbstatic.com/team-logos/team-cap-on-dark";

    document.title = play.play + " | Boring Bets";

    document.getElementById("awayLogo").src =
      logoBase + "/" + play.away_team_id + ".svg";

    document.getElementById("homeLogo").src =
      logoBase + "/" + play.home_team_id + ".svg";

    document.getElementById("awayTeam").textContent =
      play.away_team;

    document.getElementById("homeTeam").textContent =
      play.home_team;

    document.getElementById("playSport").textContent =
      play.sport;

    document.getElementById("playTitle").textContent =
      play.play;

    document.getElementById("playOdds").textContent =
      play.odds;

    document.getElementById("playUnits").textContent =
      play.units;

    document.getElementById("playRating").textContent =
      "★".repeat(play.rating);

    document.getElementById("playHandicapper").textContent =
      play.handicapper;

    document.getElementById("playAnalysis").textContent =
      play.analysis;

    status.style.display = "none";
    details.hidden = false;
  } catch (error) {
    console.error(error);
    status.textContent = error.message;
  }
}

loadPlay();