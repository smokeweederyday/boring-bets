from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
import json
import sys
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
VENUES_FILE = ROOT / "data" / "venues.json"

MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

OPEN_METEO_FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
)

OPEN_METEO_HISTORY_URL = (
    "https://historical-forecast-api.open-meteo.com/v1/forecast"
)

OPEN_METEO_GEOCODING_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)

HOURLY_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation_probability",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
)

# Direct fallback for venues whose MLB venue response omits coordinates.
# More venues can be added later if MLB's response omits their location.
VENUE_COORDINATE_FALLBACKS: dict[
    int,
    tuple[float, float],
] = {
    2395: (
        37.7786,
        -122.3893,
    ),
}


def get_json(
    url: str,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Boring Bets/1.0"
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        return json.loads(
            response.read()
        )


def load_local_venue_coordinates(
    venue_id: int,
) -> tuple[float | None, float | None]:
    if not VENUES_FILE.exists():
        return None, None

    try:
        raw = json.loads(
            VENUES_FILE.read_text(
                encoding="utf-8"
            )
        )
    except (
        json.JSONDecodeError,
        OSError,
    ):
        return None, None

    venues = (
        raw.get("venues", [])
        if isinstance(raw, dict)
        else raw
    )

    if not isinstance(venues, list):
        return None, None

    for venue in venues:
        if not isinstance(venue, dict):
            continue

        try:
            stored_id = int(
                venue.get("id")
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if stored_id != int(venue_id):
            continue

        return (
            to_float(
                venue.get("latitude")
            ),
            to_float(
                venue.get("longitude")
            ),
        )

    return None, None


def fetch_venue(
    venue_id: int,
) -> dict[str, Any]:
    raw = get_json(
        f"{MLB_API_BASE}/venues/{venue_id}"
    )

    venues = raw.get(
        "venues",
        [],
    )

    if not venues:
        return {}

    return venues[0]


def extract_venue_coordinates(
    venue: dict[str, Any],
) -> tuple[float | None, float | None]:
    location = venue.get(
        "location",
        {},
    )

    coordinates = (
        location.get("defaultCoordinates")
        or venue.get("defaultCoordinates")
        or {}
    )

    latitude = to_float(
        coordinates.get("latitude")
    )

    longitude = to_float(
        coordinates.get("longitude")
    )

    return latitude, longitude


def build_geocoding_queries(
    venue: dict[str, Any],
) -> list[str]:
    location = venue.get(
        "location",
        {},
    )

    venue_name = str(
        venue.get("name") or ""
    ).strip()

    city = str(
        location.get("city") or ""
    ).strip()

    state = str(
        location.get("stateAbbrev")
        or location.get("state")
        or ""
    ).strip()

    queries = []

    if venue_name and city:
        queries.append(
            f"{venue_name}, {city}, {state}".strip(
                ", "
            )
        )

    if city and state:
        queries.append(
            f"{city}, {state}"
        )

    if city:
        queries.append(
            city
        )

    return list(
        dict.fromkeys(
            query
            for query in queries
            if query
        )
    )


def geocode_location(
    query: str,
) -> tuple[
    float | None,
    float | None,
    str | None,
]:
    params = urllib.parse.urlencode(
        {
            "name": query,
            "count": 1,
            "language": "en",
            "format": "json",
        }
    )

    raw = get_json(
        f"{OPEN_METEO_GEOCODING_URL}"
        f"?{params}"
    )

    results = raw.get(
        "results",
        [],
    )

    if not results:
        return None, None, None

    result = results[0]

    return (
        to_float(
            result.get("latitude")
        ),
        to_float(
            result.get("longitude")
        ),
        result.get("timezone"),
    )


def resolve_venue_coordinates(
    venue_id: int,
    venue: dict[str, Any],
) -> tuple[
    float,
    float,
    str | None,
    str,
]:
    latitude, longitude = (
        extract_venue_coordinates(
            venue
        )
    )

    if (
        latitude is not None
        and longitude is not None
    ):
        return (
            latitude,
            longitude,
            None,
            "mlb_venue",
        )

    (
        local_latitude,
        local_longitude,
    ) = load_local_venue_coordinates(
        venue_id
    )

    if (
        local_latitude is not None
        and local_longitude is not None
    ):
        return (
            local_latitude,
            local_longitude,
            None,
            "local_venues_database",
        )

    fallback = (
        VENUE_COORDINATE_FALLBACKS.get(
            venue_id
        )
    )

    if fallback:
        return (
            fallback[0],
            fallback[1],
            None,
            "venue_fallback",
        )

    for query in build_geocoding_queries(
        venue
    ):
        (
            geocoded_latitude,
            geocoded_longitude,
            geocoded_timezone,
        ) = geocode_location(
            query
        )

        if (
            geocoded_latitude is not None
            and geocoded_longitude is not None
        ):
            return (
                geocoded_latitude,
                geocoded_longitude,
                geocoded_timezone,
                f"geocoded:{query}",
            )

    raise ValueError(
        f"Venue {venue_id} has no coordinates "
        "and could not be geocoded."
    )


def fetch_hourly_weather(
    latitude: float,
    longitude: float,
    game_date: str,
) -> dict[str, Any]:
    today = date.today().isoformat()

    base_url = (
        OPEN_METEO_HISTORY_URL
        if game_date < today
        else OPEN_METEO_FORECAST_URL
    )

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(
            HOURLY_VARIABLES
        ),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",

        # MLB game times are stored in UTC. Request UTC hourly
        # timestamps so the nearest-hour comparison is accurate.
        "timezone": "GMT",

        "start_date": game_date,
        "end_date": game_date,
    }

    return get_json(
        f"{base_url}?"
        f"{urllib.parse.urlencode(params)}"
    )


def nearest_hour_index(
    hourly_times: list[str],
    game_time: str,
) -> int | None:
    if not hourly_times:
        return None

    try:
        target = datetime.fromisoformat(
            game_time.replace(
                "Z",
                "+00:00",
            )
        )

        if target.tzinfo is None:
            target = target.replace(
                tzinfo=timezone.utc
            )

        target = target.astimezone(
            timezone.utc
        ).replace(
            tzinfo=None
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    closest_index = None
    closest_distance = None

    for index, raw_time in enumerate(
        hourly_times
    ):
        try:
            candidate = datetime.fromisoformat(
                raw_time
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if candidate.tzinfo is not None:
            candidate = candidate.astimezone(
                timezone.utc
            ).replace(
                tzinfo=None
            )

        distance = abs(
            (
                candidate - target
            ).total_seconds()
        )

        if (
            closest_distance is None
            or distance < closest_distance
        ):
            closest_distance = distance
            closest_index = index

    return closest_index


def hourly_value(
    hourly: dict[str, Any],
    key: str,
    index: int | None,
) -> Any:
    if index is None:
        return None

    values = hourly.get(
        key,
        [],
    )

    if not isinstance(
        values,
        list,
    ):
        return None

    if index >= len(values):
        return None

    return values[index]


def degrees_to_compass(
    degrees: Any,
) -> str | None:
    value = to_float(
        degrees
    )

    if value is None:
        return None

    directions = (
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    )

    index = round(
        value / 22.5
    ) % 16

    return directions[index]


def weather_code_label(
    code: Any,
) -> str:
    value = to_int(
        code
    )

    labels = {
        0: "Clear",
        1: "Mostly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Freezing fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Heavy drizzle",
        61: "Light rain",
        63: "Rain",
        65: "Heavy rain",
        71: "Light snow",
        73: "Snow",
        75: "Heavy snow",
        80: "Rain showers",
        81: "Rain showers",
        82: "Heavy showers",
        95: "Thunderstorms",
        96: "Thunderstorms with hail",
        99: "Severe thunderstorms with hail",
    }

    return labels.get(
        value,
        "Conditions unavailable",
    )


def build_weather_snapshot(
    venue_id: int,
    game_time: str,
    game_date: str,
) -> dict[str, Any]:
    venue = fetch_venue(
        venue_id
    )

    (
        latitude,
        longitude,
        venue_timezone,
        coordinate_source,
    ) = resolve_venue_coordinates(
        venue_id,
        venue,
    )

    weather = fetch_hourly_weather(
        latitude,
        longitude,
        game_date,
    )

    hourly = weather.get(
        "hourly",
        {},
    )

    index = nearest_hour_index(
        hourly.get(
            "time",
            [],
        ),
        game_time,
    )

    if index is None:
        raise ValueError(
            "Weather response did not contain "
            "an hourly value near first pitch."
        )

    weather_code = hourly_value(
        hourly,
        "weather_code",
        index,
    )

    wind_direction_degrees = (
        hourly_value(
            hourly,
            "wind_direction_10m",
            index,
        )
    )

    selected_time = hourly_value(
        hourly,
        "time",
        index,
    )

    return {
        "venue_id": venue_id,
        "venue_name": venue.get(
            "name"
        ),
        "latitude": latitude,
        "longitude": longitude,
        "venue_timezone": venue_timezone,
        "coordinate_source":
            coordinate_source,
        "forecast_time_utc":
            selected_time,
        "temperature": hourly_value(
            hourly,
            "temperature_2m",
            index,
        ),
        "humidity": hourly_value(
            hourly,
            "relative_humidity_2m",
            index,
        ),
        "rain_probability": hourly_value(
            hourly,
            "precipitation_probability",
            index,
        ),
        "precipitation": hourly_value(
            hourly,
            "precipitation",
            index,
        ),
        "wind_speed": hourly_value(
            hourly,
            "wind_speed_10m",
            index,
        ),
        "wind_gust": hourly_value(
            hourly,
            "wind_gusts_10m",
            index,
        ),
        "wind_direction": degrees_to_compass(
            wind_direction_degrees
        ),
        "wind_direction_degrees":
            wind_direction_degrees,
        "weather_code": weather_code,
        "condition": weather_code_label(
            weather_code
        ),
        "source": "Open-Meteo",
        "source_type": (
            "historical_forecast"
            if game_date < date.today().isoformat()
            else "forecast"
        ),
        "details_url": "#",
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


def to_float(
    value: Any,
) -> float | None:
    if value in {
        None,
        "",
        "-",
    }:
        return None

    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def to_int(
    value: Any,
) -> int | None:
    if value in {
        None,
        "",
        "-",
    }:
        return None

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def main() -> None:
    if len(sys.argv) < 4:
        raise SystemExit(
            "Usage: python3 scripts/mlb/weather.py "
            "<venue_id> <game_time_iso> <YYYY-MM-DD>"
        )

    venue_id = int(
        sys.argv[1]
    )

    game_time = sys.argv[2]
    game_date = sys.argv[3]

    snapshot = build_weather_snapshot(
        venue_id,
        game_time,
        game_date,
    )

    print(
        json.dumps(
            snapshot,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
