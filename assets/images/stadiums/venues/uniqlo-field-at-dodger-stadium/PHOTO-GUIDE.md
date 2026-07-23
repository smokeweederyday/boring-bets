# Venue photo folder guide

This folder is safe to give to a nontechnical photo researcher.

## Naming rule

Use a category name, a two-digit priority number, and an image extension:

    fair-day-01.webp
    fair-day-02.webp
    fair-night-01.webp
    interior-night-01.jpg
    default-01.webp

Priority is deterministic:

- `01` is the primary image.
- `02` is the first fallback.
- `03` is the next fallback.

The website never relies on Finder sorting.

## Safe behavior

- Correctly named images are indexed automatically.
- Incorrectly named images are ignored.
- Missing categories fall back safely.
- Existing unnumbered files remain legacy fallbacks.
- Adding a photo cannot break the page.

## Common categories

Universal:

    default-01.webp
    exterior-day-01.webp
    exterior-night-01.webp
    interior-day-01.webp
    interior-night-01.webp

Outdoor venues:

    fair-day-01.webp
    fair-dusk-01.webp
    fair-night-01.webp
    rain-day-01.webp
    rain-night-01.webp
    storm-night-01.webp
    snow-day-01.webp
    fog-day-01.webp

Baseball rain delays:

    rain-delay-day-01.webp
    rain-delay-dusk-01.webp
    rain-delay-night-01.webp

Retractable roofs:

    open-fair-day-01.webp
    open-fair-night-01.webp
    closed-fair-day-01.webp
    closed-fair-night-01.webp

Tennis examples:

    grass-day-01.webp
    clay-day-01.webp
    hardcourt-night-01.webp
    closed-night-01.webp

Other sports may use additional lowercase hyphenated categories. The page
chooses the category order; this folder only provides ranked photographs.

## Image recommendations

- Landscape orientation.
- Recommended export: 1916 x 821.
- Real venue photography.
- Avoid watermarks and promotional text.
- Record the source and license in `ATTRIBUTION.md` when known.

After adding photos, run:

    python3 scripts/build_venue_image_index.py
