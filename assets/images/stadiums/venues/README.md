# Admin stadium image library

Stadium folders use readable stadium names:

```text
assets/images/stadiums/venues/<stadium-name>/
```

## Weather image meaning

### Normal playable weather

```text
fair-day.webp
fair-night.webp
rain-day.webp
rain-night.webp
storm-day.webp
storm-night.webp
```

A `rain-*` image should show a game-capable rainy stadium scene. It must not be
a tarp-covered infield photograph.

When no normal rain image exists, the site falls back to the fair day/night
photo and applies the outdoor rain effects.

### Rain-delay photographs

Tarp-covered infield photographs must use:

```text
rain-delay-day.webp
rain-delay-dusk.webp
rain-delay-night.webp
```

They are selected only when:

1. The live feed reports a rain/weather delay, suspension, or postponement;
2. An explicit data/admin flag requests a rain-delay photo; or
3. Game-window forecast data shows essentially 100% rain for at least 75% of
   the scheduled game window.

A single 100% hourly forecast does not trigger a tarp photograph.

## Supported explicit data flags

```text
use_rain_delay_photo
rain_delay_photo
rain_delay_likely
tarp_expected
```

These can exist on the game or its weather object.

## Replacing a picture

1. Open the stadium's named folder.
2. Replace the applicable file.
3. Hard-refresh with Command + Option + R.

WebP, JPG, JPEG, and PNG are supported. WebP is preferred.
Recommended size: approximately 1916 × 821.
