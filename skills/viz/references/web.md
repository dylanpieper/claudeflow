# Web figures in React

## Observable Plot

- For static charts and charts with hover only, use `@observablehq/plot`.
  - It uses the same grammar as ggplot2: marks, scales, and facets.
  - It makes an SVG, or a `<figure>` that holds the SVG when the chart has a title, caption, or legend.
  - Apply the color and text rules in `SKILL.md` to it.
- Mount the chart in React:
  - Call `Plot.plot()` in a `useEffect` hook.
  - Append the result to a `useRef` element, and remove it in the cleanup function.
- Make the chart fit its container.
  - The default width is a fixed 640 px.
  - Read the container width with a `ResizeObserver` and give it to the `width` option.
  - Run `Plot.plot()` again when the width changes.
- For hover, use the `tip` mark or the `tip` mark option.
  - The `tip` needs Plot to run in the browser.
- For filters, keep the filter in React state and run `Plot.plot()` again with the filtered data.
  - For brushed or linked views, use D3.
- For a static chart with fixed data, render the SVG on the server or at build time.
  - Give a DOM, such as jsdom or linkedom, to the `document` option of `Plot.plot()`.
  - The page then has no chart JavaScript.
- For access, set the `ariaLabel` and `ariaDescription` options of `Plot.plot()`.

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
