# ggplot2 and plotnine style: themes, color, text, and export

These rules come from the blog and talks of Cara Thompson
([cararthompson.com](https://www.cararthompson.com/posts)).
Each section links to its sources.

The rules apply to ggplot2 (4.0 or later) and plotnine (0.15 or later).
plotnine uses the same grammar as ggplot2.
Each rule shows the ggplot2 code first.
A "plotnine" item shows a name or a gap that is different.

## Name changes in plotnine

| ggplot2 | plotnine |
|---------|----------|
| `plot.title.position` | `plot_title_position` (dots become underscores) |
| `colour` | `color` |
| `shape = 21` (circle with fill) | `shape = "o"` |
| `shape = 22` (square with fill) | `shape = "s"` |
| `list(shape = 22)` | `{"shape": "s"}` |
| `legend.justification = 0` | `legend_justification = "left"` |
| `margin(b = 12)` | `{"b": 12, "units": "pt"}` |
| `ggsave("f.png", plot = p, ...)` | `p.save("f.png", dpi = 300)` |
| `scales::number()` | `mizani.labels.label_number()` |

## Theme function

- Write one theme function and add it to each plot: `p + theme_x()`.
  - Keep plot code and theme code separate.
  - Give the function the arguments `base_size` and `palette`.
  - Start from `theme_minimal(base_size = base_size)`.
- Calculate all sizes from `base_size`, so that they change together:
  - geom text: `element_geom(fontsize = base_size * 0.8)`;
  - margins: `plot.margin = margin_auto(base_size * 1.5)`.
- Set geom defaults in the theme with `geom = element_geom(...)`.
  - Use `pointshape` and `pointsize`, not `shape` and `size`.
  - plotnine has no `element_geom()`. Set `shape`, `size`, and `color` in each geom call.
- Align the title with the plot edge: `plot.title.position = "plot"`.
- Put the legend at the top left of the full plot:
  - `legend.position = "top"`;
  - `legend.justification = 0`;
  - `legend.location = "plot"`. plotnine has no `legend_location`.
- Remove grid lines that the reader does not need, for example `panel.grid.minor = element_blank()`.

Sources:
[From basic to Wow every time in no time with your own ggplot2 theme](https://www.cararthompson.com/talks/basic-to-wow-ggplot2/),
[Optimising the use of colours for storytelling in a spaghetti plot](https://www.cararthompson.com/posts/2025-01-14-optimising-colours-in-a-spaghetti-plot/).

## Color

- Keep the palette in a named vector or a dict. Get each color by its name.
- Apply one palette to both aesthetics: `scale_colour_manual(aesthetics = c("colour", "fill"), values = palette)`.
  - plotnine: `scale_color_manual(values = palette, aesthetics = ["color", "fill"])`.
- Give light colors a dark contour.
  - For points, use a shape with a fill, map the group to `fill`, and set `colour` to a dark ink.
  - For bars, set `colour` in `element_geom()`. In plotnine, set `color` in the geom call.
- If the legend keys lose their fill color, use one of these fixes:
  - `guides(fill = guide_legend(override.aes = list(shape = 22)))`;
  - ggplot2 only: `theme(geom = element_geom(pointshape = 22))`.
- Make brand colors with `monochromeR::generate_palette()` (R).
  - To mix a base color with a brand color, set `blend_colour`.
  - To make tints, set `modification = "go_lighter"`.
  - Use a muted mix of the main colors for `na.value`.
  - The palette is a list of hex codes, so you can also use it in plotnine.
- Check the finished plot with `colorblindr::cvd_grid(p)` (R).
  - For plotnine, save the image and check it with a color vision deficiency simulator.

Sources:
[A simple trick for applying accessible colour palettes within dataviz](https://www.cararthompson.com/posts/2026-07-03-accessible-colour-palettes/),
[Adapting ggplot2 legend shapes when using the dark contour trick](https://www.cararthompson.com/posts/2026-07-14-shapes-in-ggplot-legends/),
[Picking semantic colours, then making them accessible and on-brand](https://www.cararthompson.com/posts/2025-07-03-bhf-workshop-how-to-pick-semantically-meaningful-colours/),
[How to make data viz that matches your organisation's branding](https://www.cararthompson.com/posts/2022-01-24-creating-and-applying-bespoke-colour-schemes/creating-and-applying-bespoke-colour-schemes),
[On-brand accessible dataviz](https://www.cararthompson.com/talks/on-brand-accessibility/).

## Emphasis

- To show the focus, map a 0/1 flag to `alpha`.
  - Use `scale_alpha(range = c(0.5, 1))`, so that the other data stays visible.
  - Remove the alpha legend with `guides(alpha = "none")`. In plotnine, use `guides(alpha = None)`.
- To highlight one line, set the colors in the data and use `scale_colour_identity()`.
- For small multiples, use `facet_wrap()` with `gghighlight::gghighlight()` (R only).
- To show a risk zone, shade it with `annotate("rect", alpha = ...)`.
  - Mark the threshold with `geom_vline()`.
  - Label the threshold on the plot.

Sources:
[Using transparency to emphasise the story arc](https://www.cararthompson.com/posts/2022-08-10-todays-rstats-dataviz-make-it/),
[Optimising the use of colours for storytelling in a spaghetti plot](https://www.cararthompson.com/posts/2025-01-14-optimising-colours-in-a-spaghetti-plot/),
[RiskyViz](https://www.cararthompson.com/talks/riskyviz/).

## Text and labels

- For Markdown in titles, use `ggtext::element_markdown()` or `munch::element_md()`.
  - Color words with `<span style='color:...'>`, so that the title also works as a legend.
  - plotnine has no Markdown text. Use a direct label or a legend.
- To add space around a title, set `margin` in the element. Do not add `<br>` tags or empty lines.
- For direct labels, put text at the end of each line.
  - In R, use `ggtext::geom_textbox()`, or `geomtextpath::geom_textline()` on the line.
  - In plotnine, use `geom_text()` or `geom_label()` on the last point.
- For light text on a busy background, use `ggfx::with_outer_glow()` (R only).
  - `expand` and `sigma` control the glow size and blur.
  - Do not add a glow to dark text on a light background.
- Format large numbers with `scales::number()`:
  - `scale_cut = scales::cut_long_scale()` gives `12K` and `1.2M`;
  - `drop0trailing = TRUE` removes `.0`;
  - `big.mark = ","` adds separators.
  - plotnine: `label_number(big_mark = ",")`. For `K` and `M`, set `scale` and `suffix`.
- Wrap long axis labels in the scale, not in the data.

Sources:
[Level Up Your Labels](https://www.cararthompson.com/posts/2022-06-22-it-was-a-privilege-to/),
[How to add space around the title of a ggplot the better way](https://www.cararthompson.com/posts/2022-06-10-todays-i-wish-id-looked/),
[One solution to make text stand out against most backgrounds](https://www.cararthompson.com/posts/2023-01-06-creating-a-dataviz-with-smallish/),
[Formatting numbers for easy readability in R](https://www.cararthompson.com/posts/2024-01-30-formatting-numbers-in-r/),
[Align your axes](https://www.cararthompson.com/posts/2022-07-14-align-your-axes/align-your-axes).

## Fonts and export

- Use a font that is installed on the system. Static `.ttf` files work best.
  - In R, check with `systemfonts::system_fonts()`.
  - To add a weight in R, use `systemfonts::register_variant()` at the top of each script.
- In R, render with `ragg`.
  - In Quarto or R Markdown, use `knitr::opts_chunk$set(dev = "ragg_png", dpi = 300)`.
  - In RStudio, set the graphics backend to AGG.
- When you save, set the size, `dpi` (300 or more), and the background.
  - ggplot2: `ggsave(width = , height = , dpi = , bg = )`.
  - plotnine: `figure_size` and `plot_background = element_rect(fill = )` in the theme, and `p.save(dpi = )`.
- In ggplot2, a fixed coordinate system (`coord_sf()`, `coord_fixed()`) can leave the background short of the image edge.
  - Use this cowplot wrapper to fill the image with the plot background.
  - It reads the full theme, so it also works when the plot has no added theme.

```r
fix_background <- function(plot) {
  background <- calc_element("plot.background", complete_theme(plot@theme))
  background@inherit.blank <- FALSE
  cowplot::plot_grid(plot + theme(plot.background = element_blank())) +
    theme(plot.background = background)
}
```

Sources:
[Getting fonts to work in R](https://www.cararthompson.com/posts/2024-01-12-using-fonts-in-r-for-dataviz/),
[Fixing awkward backgrounds in ggplot2](https://www.cararthompson.com/posts/2025-03-06-fixing-awkward-backgrounds-in-ggplot/).

## Parameterized plot functions

- Calculate limits, color midpoints, and label padding from the full data, not from the filtered subset.
  - Then the plots stay comparable.
- Give each threshold a default value, so that a new input gets a safe value.
  - In R, use `case_when(..., .default = ...)`.
- Make the title and counts from the data, for example with `nrow()`.
- Test the output with a snapshot test. In R, use `vdiffr::expect_doppelganger()`.

Sources:
[RiskyViz](https://www.cararthompson.com/talks/riskyviz/),
[Align your axes](https://www.cararthompson.com/posts/2022-07-14-align-your-axes/align-your-axes).
