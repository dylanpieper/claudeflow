# Web figures in React

## Observable Plot

- For static charts and charts with hover only, use `@observablehq/plot`. It has the same grammar as ggplot2.
- Apply the color and text rules in `SKILL.md` to Plot charts.
- For a static chart with fixed data, render the SVG on the server or at build time.

## plotly.js

- For charts that need zoom, pan, or 3D, use `react-plotly.js`.
- For more than about 10,000 points, use the WebGL traces (`scattergl`).

## D3

- Let React own the DOM.
  - Use the D3 modules for the calculations: `d3-scale`, `d3-shape`, `d3-array`, and `d3-hierarchy`.
  - Render the SVG in JSX.
- Use `d3-selection` in a `useRef` hook only for zoom, brush, drag, and transitions, which React cannot do.
- Join the data by a stable key, not by the array index.
- Make the figure responsive with a `viewBox`, and use a `ResizeObserver` to get the width.

## Data and access

- The API sends the data in the shape that the chart uses.
  - The frontend does not calculate statistics.
  - The layer rules are in `~/.claude/rules/python.md`.
- Aggregate large data on the server, with DuckDB or PostgreSQL.
- Do not send raw rows that the reader cannot see.
- Make each figure accessible:
  - Give each SVG a `<title>` and a `role="img"` with an `aria-label`.
  - Give an interactive figure keyboard access and a data table as an alternative.
