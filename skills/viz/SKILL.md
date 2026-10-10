---
name: viz
description: Rules for figures, charts, maps, and tables, and how to choose a tool (ggplot2, plotnine, plotly, D3, Leaflet with OpenStreetMap, gt). Use when you make or change a figure, chart, map, or table in any language.
---

# Visualization

These rules come from two sources:

- Cédric Scherer, [Beyond Bar and Box Plots](https://z3tt.github.io/beyond-bar-and-box-plots);
- Cara Thompson, [blog and talks](https://www.cararthompson.com/posts).

If the `dataviz` skill is available, use it for color and visual design.
These rules override it when they conflict.

## Show the data

- Show the raw data with each summary. Do not show a summary alone.
- Do not use a bar chart with error bars for continuous data.
- Use bar charts only for counts and proportions.
- Put the sample size in each group label, for example `Group A (n = 24)`.
- Order the groups by a value that has a meaning, not by alphabetical order without a reason.
- Use a palette that is safe for color blindness. Give each group the same color in all figures.

## Color and text

- Give light colors a dark contour, so that marks have 3:1 contrast on a light background.
- Show each group with color and one more channel, for example shape.
- Label groups directly on the plot. Then remove the legend.
- Show the focus in a strong color. Make the other data grey or more transparent, but keep it visible.
- Use text colors that are different from data colors. Make the title, subtitle, and body text clearly different.
- Put the units in the tick labels, for example `40 mm`. Then remove the axis title.
- Test the palette for color vision deficiency. Also test the colors between the palette anchors.

## Choose the tool

| Need | R | Python | Web (React) |
|------|---|--------|-------------|
| Static figure | ggplot2 | plotnine, or seaborn and matplotlib | Not applicable |
| Standard interactive chart | plotly | plotly | react-plotly.js |
| Custom interactive graphic | Not applicable | Not applicable | D3 |
| Interactive map | leaflet | folium | react-leaflet |
| Table | gt | great_tables | Not applicable |

- Start with a static figure. Make a figure interactive only when both of these are true:
  - the reader needs hover, zoom, or filter;
  - the output is HTML (Quarto HTML, Shiny, or a web app).
- Use plotly before D3.
  - Use D3 only when plotly cannot make the graphic.
  - Examples: a custom layout, linked views, or custom transitions.
- Give each figure alt text that tells the main result.

## Reference files

Read the file for the tool that you use:

- [references/r.md](references/r.md): ggplot2 distributions, layers, labels, and tables.
- [references/grammar-style.md](references/grammar-style.md): ggplot2 and plotnine themes, color, text, fonts, and export.
- [references/python.md](references/python.md): plotnine, seaborn, plotly, and great_tables.
- [references/web.md](references/web.md): D3 and plotly.js in React.
- [references/maps.md](references/maps.md): Leaflet, OpenStreetMap tiles, and geodata.
