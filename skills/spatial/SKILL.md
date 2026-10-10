---
name: spatial
description: Rules for spatial data and spatial analysis in R and Python - US Census data, joins between areas, distance and travel time, and spatial clusters. Use when you get, join, or analyze geographic data. For maps, also use the viz skill.
---

# Spatial data and analysis

The sections come from the blog of Kyle Walker
([walker-data.com](https://walker-data.com/blog.html)).
Each section links to its sources.

- For maps, read `references/maps.md` in the viz skill.
- For vector data, use `sf` in R and `geopandas` in Python.
  `geopandas` is an exception to the rule against pandas in `rules/python.md`.

## US Census data

- Get the data and the shapes with Walker's packages:
  - R: `tidycensus::get_acs()` with `geometry = TRUE`, and `tigris` for shapes;
  - Python: `pygris` for shapes, `pygris.data.get_census()` for the Census API, and `pygris.data.get_lodes()` for LODES jobs data.
- Cache the shapes: `options(tigris_use_cache = TRUE)` in R, `cache = True` in Python.
- Use shapes of the same year as the data.
- Remove water from the shapes.
  - Use cartographic boundary files: `cb = TRUE`.
  - In Python, use `pygris.utils.erase_water()`.
  - For Census blocks, remove the water-only blocks: `ALAND20 > 0`.
- For a national map, use smaller files: `resolution = "5m"` in `get_acs()`.
- A child GEOID starts with the GEOID of its parent.
  - For example, the first 11 characters of a block GEOID are its tract GEOID.
  - Aggregate blocks to tracts with this prefix. You do not need a spatial join.
- Show rates, not counts. Divide by a total, for example jobs per 1,000 workers.

Sources:
[National mapping for small areas](https://walker-data.com/posts/national-tract-mapping/),
[Mapping 650,000+ Texas Census blocks with PMTiles](https://walker-data.com/posts/pmtiles-texas-blocks/),
[Analyzing labor markets in Python with LODES data](https://walker-data.com/posts/lodes-commutes/),
[Using your favorite Python packages in ArcGIS Pro](https://walker-data.com/posts/pygris-arcgis/).

## Join small areas to larger areas

- To find the small areas in a larger area, do not overlay polygons on polygons.
  - Get one point in each small area with `sf::st_point_on_surface()`.
  - Filter the points with `sf::st_filter()`, then filter the small areas by their IDs.
  - This prevents errors from borders that do not align.
- To process many areas, split the data into a named list with `split()` and use `purrr::map()`.
- When Census areas are too large, for example block groups in a rural county, build regions from blocks.
  - Use max-p regionalization: `pygeoda.maxp_greedy()` with rook weights.
  - Set a minimum population for each region with `bound_variable` and `min_bound`.
  - Set `random_seed`, and `cpu_threads = 1` for stable results. Compare the results of more than one seed.

Sources:
[Iterative 'mapping' in R](https://walker-data.com/posts/iterative-mapping/),
[Building custom regions from 2020 Census blocks in Python](https://walker-data.com/posts/census-regions/).

## Distance and travel time

- Calculate straight-line distance only in a projected CRS. The units of that CRS are the units of the result.
- In rural areas, straight-line distance can mislead. Use travel time on the road network:
  - R: `mapboxapi::mb_matrix()` and `mb_isochrone()`;
  - Python: `routingpy` with `MapboxOSRM`;
  - without Mapbox: a self-hosted OSRM or Valhalla server.
- The Mapbox Matrix API accepts not more than 25 coordinates in one request. Send the origins in chunks.
- Include facilities outside the study area, for example all hospitals within 100 km of the border.
- Measure from a population-weighted centroid when you can. A geometric centroid is less accurate.
- Travel time changes with traffic.
  - Set a future weekday time: `mb_isochrone(depart_at = "2025-09-11T17:30")`.
  - Compare noon and rush hour.
- To show access from one place, make an accessibility surface:
  - make isochrones at 1-minute steps;
  - convert them to a raster in a projected CRS, with the minimum time in each cell (`fasterize(fun = "min")`).
- When you draw isochrones as polygons, draw the largest first, so the smallest stay visible.
- Mapbox needs an account and an access token. Keep the token in an environment variable.

Sources:
[Distance and proximity analysis in Python](https://walker-data.com/posts/proximity-analysis/),
[Travel-time isochrones with Mapbox, Python, and GeoPandas](https://walker-data.com/posts/python-isochrones/),
[Time-aware isochrones](https://walker-data.com/posts/time-aware-isochrones/),
[Visualizing accessibility surfaces in R](https://walker-data.com/posts/accessibility-surface/).

## Spatial clusters

- To find clusters and spatial outliers, use local Moran's I (LISA).
  - Python: `libpysal` Queen weights and `esda.Moran_Local(seed = )`.
  - Mark each area with a pseudo p-value (`p_sim`) above 0.05 as "Not significant".
- Use the usual LISA colors:
  - high-high red and low-low blue;
  - the outliers in light red and light blue;
  - "Not significant" in light grey.
- Give a LISA map popups or labels. Readers who do not know the area cannot name the clusters on a static map.

Sources:
[Exploratory spatial data analysis with Python](https://walker-data.com/posts/esda-with-python/).

## Large and remote data

- Query a large remote dataset lazily, with `arrow::open_dataset()` or DuckDB.
  - Filter it before you collect it. For Overture Maps, filter by the `bbox` columns.
  - Select only the columns that you need.
- Check how complete a column is in each region.
  For example, Overture building heights are more complete in the United States than in other countries.

Sources:
[Getting and visualizing Overture Maps buildings data in R](https://walker-data.com/posts/overture-buildings/),
[How to visualize millions of parcels on a map](https://walker-data.com/posts/millions-of-parcels/).
