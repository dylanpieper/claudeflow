# R figures and tables

For themes, color, text, fonts, and export, read [grammar-style.md](grammar-style.md).

## Distributions

- For a small sample, show each point with `ggbeeswarm::geom_quasirandom()` or `ggforce::geom_sina()`.
  - Do not show a violin or a density alone.
  - Its shape is not reliable for few points.
- For a large sample, show the shape with `ggdist` or `ggridges`.
  - Useful `ggdist` functions: `stat_halfeye()`, `stat_interval()`, and `geom_dots()`.
  - Add the data points when they stay readable.
- For a raincloud plot:
  - put `ggdist::stat_halfeye()` on one side;
  - put a narrow `geom_boxplot()` in the middle;
  - put the points on the other side with `ggdist::stat_dots(side = "left")`;
  - use `justification` to move the ggdist layers away from the box plot.
- Do not use a box plot alone, because it hides a distribution with more than one peak.
- Put the data points on each box plot.
- Keep the default density bandwidth. If you change `adjust`, tell the value in the caption.

## Layers and labels

- Put summary layers below the points.
- Use `alpha` so that one layer does not hide another.
- With `geom_boxplot()` and points, set `outlier.shape = NA`, so that each outlier shows only one time.
- For jitter, set a small `width` and `height = 0`, so that the values on the value axis stay correct.
- Make group labels with the sample size, for example `"{group}\n(n = {n})"`.
- Order the groups with `forcats::fct_reorder(group, value, median)`.
- For color, use `rcartocolor` or `viridis`.

## Interactive and tables

- For model coefficients, Likert data, and proportions, use `ggstats`.
- For an interactive version of a ggplot2 figure, use `plotly::ggplotly()`.
- For a chart that starts interactive, use `plotly::plot_ly()`.
- For tables, use `gt`.
