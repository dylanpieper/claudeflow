# Web figures in React

## plotly.js

- For standard charts, use `react-plotly.js`.
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
