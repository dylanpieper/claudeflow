# R figures and tables

The distribution rules come from Cédric Scherer,
[Beyond Bar and Box Plots](https://z3tt.github.io/beyond-bar-and-box-plots)
([source](https://github.com/z3tt/beyond-bar-and-box-plots)).
The code uses ggplot2 4.0 argument names: `linewidth` for lines and `after_stat()` for computed values.

## Choose a distribution chart

- For a small sample, show each point.
  - Use `ggbeeswarm::geom_quasirandom()`, `ggforce::geom_sina()`, or `ggdist::stat_dots(layout = "swarm", side = "both")`.
  - Do not show a violin or a density alone, because its shape is not reliable for few points.
- For a large sample, show the shape with `ggdist` or `ggridges`.
  - Add the data points when they stay readable.
- For a compact view of many points, use a barcode strip.
  - When the value axis is vertical, use `geom_point(shape = 95, size = 20, alpha = .33)`.
  - When the value axis is horizontal, use `shape = 124`.
  - Shape 95 does not turn, so its marks merge into a line on a horizontal value axis.
- To show intervals, use `ggdist::stat_interval(.width = c(.25, .5, .95, 1))`.
  - Add the median as a point with `stat_summary(geom = "point", fun = median)`.
- For many groups or a change over time, use `ggridges::geom_density_ridges(rel_min_height = .01)`.
  - `rel_min_height` cuts the long flat tails.
  - For quartile fills, use `stat_density_ridges(geom = "density_ridges_gradient", calc_ecdf = TRUE, quantiles = 4)` with `fill = factor(after_stat(quantile))`.
  - Do not show quartile lines for a small sample, because they can mislead.

## Box plots, violins, and bars

- Do not use a box plot alone, because it hides a distribution with more than one peak.
  - Put the data points on each box plot.
- To put a box plot in a violin, use a narrow `geom_boxplot(width = .1, coef = 0, outlier.shape = NA)`.
  - Add the median as a point with `stat_summary()`.
- Do not use a dynamite plot (a bar with error bars).
  - A dynamite plot shows only the mean and one spread value per group.
  - If you must show error bars, tell in the caption if they are SD, SE, or a confidence interval.

## Show the sample size in the shape

- For violins, use `geom_violin(scale = "count")`.
- For sina plots, use `ggforce::geom_sina(scale = "count")`.
- For half-eyes, use `ggdist::stat_halfeye(aes(thickness = after_stat(f * n)))`.

## Density bandwidth

- The bandwidth controls the shape of each violin, ridge, and half-eye.
  - A small value adds false peaks.
  - A large value hides real peaks.
- Choose the bandwidth on purpose, and compare the shape with the raw points.
  - Use `bw` in `geom_violin()` and `bandwidth` in `ggridges`.
  - Use `adjust` in `ggdist`, for example `adjust = .33`.
- Tell the value in the caption when it is not the default.

## Raincloud plots

- Put `ggdist::stat_halfeye()` on one side.
- Put a narrow `geom_boxplot(width = .2, outlier.shape = NA)` in the middle.
- Put the points on the other side with `ggdist::stat_dots(side = "left")`.
  - Or, show the points as a barcode strip with `position_nudge()`.
  - Do not use `gghalves::geom_half_point()`, because it fails with ggplot2 4.0.
- Use `justification` or `position_nudge()` to move the layers apart.
- For long group names, put the groups on the y axis: `aes(x = value, y = group)`.
  - ggplot2 and ggdist detect the orientation, so you do not need `coord_flip()`.
  - Order the groups from top to bottom with `forcats::fct_rev()`.

## Layers, colors, and labels

- Put summary layers below the points.
- Use `alpha` so that one layer does not hide another.
- To give points an outline, add a second point layer with `shape = 1` and `colour = "black"`.
  - Give both layers the same `position_jitter(seed = ...)`, so that the outlines align.
- With `geom_boxplot()` and points, set `outlier.shape = NA`, so that each outlier shows only one time.
- For jitter, set a small `width` and `height = 0`, so that the values on the value axis stay correct.
- To make a fill a lighter copy of its group color, use one of these:
  - `aes(colour = group, fill = after_scale(colorspace::lighten(colour, .5)))`;
  - `aes(fill = stage(group, after_scale = colorspace::lighten(fill, .5)))`.
- Do not read `fill` inside `after_scale()` when the layer does not map `fill`.
  - An unmapped fill starts as the geom default, so the group color does not show.
  - The default is white for `geom_boxplot()` and `geom_violin()`, and grey for `geom_col()`.
- Make group labels with the sample size, for example `"{group}\n(n = {n})"`.
- Order the groups with `forcats::fct_reorder(group, value, median)`.
- For color, use `rcartocolor` or `viridis`.

## Interactive and tables

These rules do not come from Scherer.

- For model coefficients, Likert data, and proportions, use `ggstats`.
- For an interactive version of a ggplot2 figure, use `plotly::ggplotly()`.
- For a chart that starts interactive, use `plotly::plot_ly()`.
- For tables, use `gt`.
