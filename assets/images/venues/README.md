# Universal venue image library

This directory is the canonical home for venue photography across every sport.

Layout:

    assets/images/venues/<sport>/<venue-slug>/

Examples:

    assets/images/venues/baseball/rate-field/
    assets/images/venues/soccer/old-trafford/
    assets/images/venues/tennis/wimbledon-centre-court/
    assets/images/venues/mma/ufc-apex/

Existing MLB folders under `assets/images/stadiums/venues/` remain supported
and are indexed as legacy baseball venue folders. They do not need to be moved
immediately.

Run after adding or replacing photographs:

    python3 scripts/build_venue_image_index.py

The builder creates:

    assets/images/venues/venue-index.json
    assets/js/venue-image-index.js

Every event page can load the shared JavaScript resolver:

    assets/js/venue-image-library.js
