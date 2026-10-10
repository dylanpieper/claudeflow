# Python figures and tables

For plotnine themes, color, text, fonts, and export, read [grammar-style.md](grammar-style.md).

- For static figures, use `plotnine`. It has the same grammar as ggplot2.
  - Use `seaborn` for a quick statistical plot.
  - Use `matplotlib` only for fine control of a figure.
- For distributions, show the points with `seaborn.stripplot()` or `seaborn.swarmplot()`.
- Put the points on a narrow `seaborn.boxplot(showfliers=False)`.
- For color, use `seaborn.color_palette("colorblind")` or a viridis palette.
- For interactive charts, use `plotly.express`. Keep `render_mode="auto"`, which changes to WebGL for large data.
- For tables, use `great_tables`. It has the same grammar as gt.
