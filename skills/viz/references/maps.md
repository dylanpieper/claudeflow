# Maps

The sections that end with "Sources:" come from the blog of Kyle Walker
([walker-data.com](https://walker-data.com/blog.html)).
Walker is the author of `mapgl`, `tidycensus`, `tigris`, `pygris`, `mapboxapi`, `pmtiles`, and `freestiler`.
The first three sections do not come from Walker.

For Census data, distance, and spatial statistics, use the `spatial` skill.

## Tools

- For a small interactive map, use Leaflet:
  - the `leaflet` package in R;
  - `folium` in Python, or `GeoDataFrame.explore()` for a quick view;
  - `react-leaflet` in React.
- For large data, vector tiles, 3D, or layers that change with zoom, read "Large data" below.
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

## Check the data before you map it

- Check each column for missing values before you map it.
  - A missing value can be an empty string or a space, not only `NA`.
  - A zero can mean "none" or "unknown". Do not map a column if you cannot tell which.
  - Do not map a column that has large gaps across the map area.
- Look for stacked geometries: many records that have the same shape.
  - A stack draws as one opaque shape and hides the records below it.
  - Collapse each stack to one feature. Keep a record count and a short list of the values.
- Remove the records that have no geometry.
- In a static map, move apart the points that have the same address with `sf::st_jitter()`.

Sources:
[How to visualize millions of parcels on a map](https://walker-data.com/posts/millions-of-parcels/),
[Circle clusters and heatmaps for dense point data in R](https://walker-data.com/posts/mapgl-dots/).

## Large data

- Use MapLibre GL JS for large data, 3D, and layers that change with zoom:
  - `mapgl` in R (`maplibre()` needs no token; `mapboxgl()` needs a Mapbox token);
  - `pydeck` (deck.gl) in Python.
- A GeoJSON source becomes slow with millions of points or hundreds of thousands of polygons.
  - For data of that size, make vector tiles in one PMTiles file.
  - Load the file with `mapgl::add_pmtiles_source()`.
- Read a large file lazily with DuckDB, for example `duckspatial::ddbs_open_dataset()` in R.
  - Clean the data in the database.
  - Write the result to GeoParquet in EPSG:4326 before you make the tiles.
- Make the tiles with one of these tools:
  - `freestiler::freestile_file()` from a GeoParquet file, or `freestile()` from an `sf` object;
  - `pmtiles::pm_create()`, which uses tippecanoe (GitHub only: `pak::pak("walkerke/pmtiles")`).
- Set the zoom range of the tiles from the data.
  - Set `min_zoom` to the zoom where the features become visible, for example 8 for Census blocks and 10 for parcels.
  - Set `max_zoom = 14`. The map shows the level-14 tiles at higher zooms.
- tippecanoe drops small polygons by default, so the map has holes at low zoom.
  - To keep all features, set `no_tiny_polygon_reduction`, `no_feature_limit`, and `no_tile_size_limit` to `TRUE`.
  - To keep shared borders clean, set `detect_shared_borders = TRUE`.
  - For hover effects and tooltips, set `generate_ids = TRUE`.
- Preview the tiles with `freestiler::view_tiles()` or `pmtiles::pm_view(inspect_features = TRUE)`.
  - The tile server must support HTTP range requests.
  - For a file larger than 1 GB, use `http-server -p 8002 --cors` (Node), not the R server.
- For colors in pydeck, give each feature an RGBA list with values from 0 to 255.

Sources:
[How to visualize millions of parcels on a map](https://walker-data.com/posts/millions-of-parcels/),
[Mapping 650,000+ Texas Census blocks with PMTiles](https://walker-data.com/posts/pmtiles-texas-blocks/),
[Mapping jobs and commutes with 2020 LODES data and deck.gl](https://walker-data.com/posts/lodes-2020/).

## Host and share a map

- Host a PMTiles file on storage that supports HTTP range requests and CORS.
  - GitHub Pages works for small files.
  - For large files, use object storage, for example Cloudflare R2, which has no egress fees.
  - Upload with `pmtiles::pm_upload()` and a bucket helper such as `r2_bucket()`.
- Set the CORS policy of the bucket:
  - methods `GET` and `HEAD`;
  - allowed headers `range` and `if-match`;
  - exposed headers `etag`, `content-range`, and `content-length`.
- For a public map, allow only the origin of your site, not `*`.
- Keep access keys in `~/.Renviron` and read them with `Sys.getenv()`. Do not put keys in code.
- Save the map with `htmlwidgets::saveWidget(selfcontained = FALSE)`.
  Move the HTML file and its folder together.
- To put the map view in the URL, set `hash = TRUE` in `maplibre()`.

Sources:
[How to visualize millions of parcels on a map](https://walker-data.com/posts/millions-of-parcels/),
[Mapping 650,000+ Texas Census blocks with PMTiles](https://walker-data.com/posts/pmtiles-texas-blocks/).

## Layers that change with zoom

- MapLibre simplifies GeoJSON shapes at low zoom, so small polygons disappear.
  - At zoom 3, the default tolerance removes shapes smaller than about 5.6 km.
  - `add_source(tolerance = 0)` keeps all shapes, but the map becomes slow.
- Show a parent geography at low zoom and the small areas at high zoom.
  - For example, show counties with `max_zoom = 7.99` and tracts with `min_zoom = 8`.
  - Use the same color scale for both levels.
- Fade one layer into the next as the reader zooms in:
  `fill_opacity = interpolate(property = "zoom", values = c(10, 11), stops = c(0.85, 0))`.
- Show each legend only at the zooms of its layer: `add_legend(min_zoom = , max_zoom = )` (mapgl 0.5.2 or later).

Sources:
[National mapping for small areas](https://walker-data.com/posts/national-tract-mapping/),
[How to visualize millions of parcels on a map](https://walker-data.com/posts/millions-of-parcels/).

## Dense points

- Do not show many points only as dots. The dots overlap and hide the density.
- Group the points into clusters: `add_circle_layer(cluster_options = cluster_options())`.
  - Clusters split as the reader zooms in.
  - Set `cluster_radius`, `count_stops`, and `color_stops` for the data.
- Or show a heatmap with `add_heatmap_layer()`.
  - The default palette is a rainbow and the default radius is 30 px. Change both.
  - For example, `heatmap_radius = 10` and
    `heatmap_color = interpolate(property = "heatmap-density", values = seq(0, 1, 0.2), stops = c("transparent", viridisLite::viridis(5)))`.
  - Fade the heatmap out between zoom 11 and 14 with `heatmap_opacity`.
  - Show the points from zoom 12.5 with `min_zoom = 12.5`, and give each point a popup.
- For origin-destination flows, aggregate the flows to a larger area first, for example from blocks to tracts.
  Then draw them as arcs, for example with a pydeck `ArcLayer`.

Sources:
[Circle clusters and heatmaps for dense point data in R](https://walker-data.com/posts/mapgl-dots/),
[Mapping jobs and commutes with 2020 LODES data and deck.gl](https://walker-data.com/posts/lodes-2020/).

## Legends, popups, and comparisons in mapgl

- Classify the data with `step_quantile()` or `interpolate_palette(method = "quantile")`.
  Give the result to `add_legend(classification = )`, so the breaks and colors agree.
- To let the reader filter the map from the legend, set `add_legend(interactive = TRUE, layer_id = )`.
- With a layers control, give each legend a `layer_id`. The legend then shows and hides with its layer.
- Build popups with `concat()`, `get_column()`, and `number_format()`.
  - For PMTiles, you cannot make the popup text in R before you map.
  - Use the per-feature expressions `if_else_expr()` and `is_blank()` for empty values.
- To compare two maps, use `compare(m1, m2)`.
  - The default is a swipe slider. For side-by-side maps, set `mode = "sync"`.
  - Use it for two times or two scenarios, for example traffic at noon and at rush hour.
- To let readers save a PNG, add `add_screenshot_control(image_scale = 2)`.
- To make many similar maps, put the data in a named list with `split()`.
  - Make one map for each item with `purrr::map()`.
  - Save each one with `purrr::iwalk()` and `mapview::mapshot()`.

Sources:
[Interactive legends and screenshot export in mapgl](https://walker-data.com/posts/mapgl-interactive-legends/),
[Synced maps and more in mapgl 0.2.1](https://walker-data.com/posts/mapgl-sync-compare/),
[Time-aware isochrones](https://walker-data.com/posts/time-aware-isochrones/),
[Iterative 'mapping' in R](https://walker-data.com/posts/iterative-mapping/).

## Maps in Shiny

- Use `bslib::page_sidebar()`, and put the map in `card(full_screen = TRUE)`.
- When a `conditionalPanel()` depends on an output, set `outputOptions(output, id, suspendWhenHidden = FALSE)`.
- Handle a button with `bindEvent()`.
- To select features in a drawn shape, use one of these:
  - in the browser, `mapgl::turf_filter()`, which is fast after you deploy the app;
  - in R, `get_drawn_features()` and `sf::st_filter()`, for data that is too large for the browser.
- Browser steps can finish in a different order than R expects.
  Wait until the drawn shape exists as a source before you filter with it.

Sources:
[Lasso selection and spatial filtering for your Shiny mapping apps](https://walker-data.com/posts/lasso-selection/),
[Drag-and-drop address geocoding with Mapbox in Shiny](https://walker-data.com/posts/shiny-geocoder/).
