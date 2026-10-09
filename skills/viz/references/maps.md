# Maps

## Tools

- For interactive maps, use Leaflet:
  - the `leaflet` package in R;
  - `folium` in Python;
  - `react-leaflet` in React.
- For geodata, use `sf` in R and `geopandas` in Python.
- To get OpenStreetMap data, use `osmdata` in R or `osmnx` in Python.
- For large extracts, use Overture Maps with the `duckdb-skills:spatial` skill.
  - Overture is a different dataset from OpenStreetMap.
  - Each Overture theme has its own license. Show the attribution that the theme requires.

## OpenStreetMap tiles and services

- Show the attribution "© OpenStreetMap contributors" with a link to the copyright page (ODbL license).
- Use the standard `tile.openstreetmap.org` tiles only for light use, such as a prototype or a small app.
  - Do not download tiles in bulk or prefetch them.
  - For production or heavy use, use a commercial tile provider or host your own tiles.
- For geocoding with Nominatim:
  - send not more than one request each second;
  - send a `User-Agent` that identifies the app;
  - cache the results;
  - do not geocode in bulk with the public server.

## Map design

- Keep coordinates in WGS 84 (EPSG:4326) for Leaflet.
- Project the data to an equal-area or local CRS before you calculate area or distance.
- In a choropleth map, show rates or densities, not raw counts.
  - Use a sequential palette with classed bins.
  - Show a legend.
- For many points, use marker clusters, a hexbin layer, or vector tiles.
