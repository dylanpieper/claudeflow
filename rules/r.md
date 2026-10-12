---
paths:
  - "**/*.{R,r,Rmd,qmd}"
  - "**/DESCRIPTION"
---

# R

A project `CLAUDE.md` or `AGENTS.md` overrides this file.
These rules override the r-skills, which cover general style, tidyverse, rlang, and package development.

## Code style

- Use `return()` only for early exits, never as the last line of a function.
- Use four dashes for section headings: `# Load data ----`.
- Never rely on partial argument matching.
- Functions called for their side effects return their first argument invisibly.
- In scripts, call functions from attached packages without a prefix.
  - Use `pkg::fn()` only for one or two calls, or to resolve a name conflict.
  - Package code may always use `pkg::fn()`.

## Package management

- If a project already uses another package manager, such as `rv`, `uvr`, `rix`, or `ir`, use it and follow its documentation. Do not add a second one.
- If the project has no package manager, ask before you run `renv::init()`. Until then, use `pak::pak()`.
- In an R package, declare dependencies in `DESCRIPTION` with `usethis::use_package()`. Use `renv` or `pak` only to install them.
- Use [`renv`](https://rstudio.github.io/renv/) for project packages.
  - To add a package: `renv::install()`, then `renv::snapshot()`.
  - To make `renv` use pak, add `options(renv.config.pak.enabled = TRUE)` to the project `.Rprofile`, before `source("renv/activate.R")`.
  - Do not create a project `.Renviron`: it masks `~/.Renviron`, which holds tokens and keys.
- For R and Python in one project, use `renv` for R and `uv` for Python.
  - `uv` keeps the Python packages in `pyproject.toml`, `uv.lock`, and `.venv/`.
  - In R, call `reticulate::use_virtualenv(here::here(".venv"))` before the first Python call.
  - Do not use `renv::use_python()`: it uses `pip` or `conda`, not `uv`. See [renv with Python](https://rstudio.github.io/renv/articles/python.html).
- Outside an `renv` project, use `pak::pak()`.
  - It installs from CRAN, GitHub (`"user/repo"`), and Bioconductor (`"bioc::pkg"`) in one call.
  - With no arguments, it installs the current package's development dependencies (requires a `DESCRIPTION`).
- Never use `install.packages()`, `remotes::install_github()`, or `devtools::install_github()`.

## Paths

- In scripts, analysis projects, and Quarto documents, build paths with `here::here()`.
- Do not use `setwd()` or paths relative to the working directory.
- In package code, read files shipped in `inst/` with `system.file(..., package = , mustWork = TRUE)` or `fs::path_package()`, not `here::here()`.
- Use `fs` for file and directory work (`fs::path()`, `fs::dir_ls()`, `fs::dir_create()`), not base `file.path()`, `list.files()`, or `dir.create()`.
- In a package that does not import `fs`, add it to Imports only when the file work justifies a new dependency.
  Otherwise, use base `file.path()`, `list.files()`, and `dir.create()`.

## Tools

- Format every `.R` file after writing or changing it.
  - Use the project's formatter if it has one; otherwise use Air (`air format <path>`).
  - Air does not format code chunks in R Markdown or Quarto files.
- Use `cli` for console output (e.g. `cli::cli_alert_success()`), not `cat()`, `message()`, or `print()`.
- Clean column names with `janitor::clean_names()`.
- For large data, prefer [`duckplyr`](https://duckplyr.tidyverse.org/) with `dplyr` verbs. `arrow` is also fine.
  - Read files with `read_parquet_duckdb()` or `read_csv_duckdb()`, not into memory first.
  - Convert an existing data frame with `as_duckdb_tibble()`.
  - Write results with `compute_parquet()`.
  - Do not use the deprecated `df_from_*()` or `as_duckplyr_tibble()`.
- Alternatively, use `dplyr` with a `duckdb` connection, for example on an existing `.duckdb` database.
  - Connect with `DBI::dbConnect(duckdb::duckdb(), dbdir = path)` and query with `tbl(con, "table")`.
  - `dbplyr` translates the verbs to SQL. Add `dbplyr`, `DBI`, and `duckdb` to the project dependencies.
  - Call `collect()` only for results that fit in memory.
  - Close the connection with `DBI::dbDisconnect(con)`.
- For figures, maps, and tables, use the viz skill.
- For spatial data and analysis, use the spatial skill.

## Project stack

For complex projects:

| Need | Tool |
|------|------|
| Packages and R version | `renv`, `rig` |
| Paths and settings | `here`, `fs`, `config` |
| Data versioning | `pins` |
| Modules and pipelines | `box`, `targets` |
| Logging and profiling | `logger`, `profvis` |
| Apps | `shiny` with `bslib`, or `shinyreact` |
| Reports | Quarto |

### Layout

- `R/`: functions. All logic lives here; scripts and the pipeline only call them.
- `_targets.R`: the pipeline.
- `config.yml`: settings.
- `data-dict.yaml`: the data contract.

### Modules

- In analysis projects and apps, put reusable code in `box` modules.
- If you use `targets`, keep pipeline functions in `R/` for `tar_source()`. `targets` does not track changes inside `box` modules.
- `box::use()` caches modules for the whole R session. After editing a module, restart R or call `box::reload()` before running tests.

### Apps

- Use `shiny` with `bslib` for dashboards and quick prototypes.
- Use [`shinyreact`](https://posit-dev.github.io/shinyreact/) when the UI needs custom React components or client-side interaction without a server round trip.
  - The server sends only data, via `reactive_output()`.
  - React renders the entire UI from `ui.tsx`, served by `page_react()`.
  - Never build UI in the server.

### Reports

- Use Quarto.
- For PDF output, use `format: typst`, not `format: pdf` (LaTeX) unless already used.

## Package development

- Preserve error context: use `withCallingHandlers()` with `parent = e`, or `rlang::try_fetch()`. Never rethrow inside `tryCatch()`.
- Use `rlang::check_installed()` for suggested dependencies.
- Use `@importFrom` only for operators (e.g. `%||%`), frequently called functions, and tight loops.
- Use `@import` only when unavoidable.
- Build docs with `pkgdown`, with `light-switch: true`. 
- Keep `README.md` short. Put details and instruction in vignettes.
- Use `devtools::check()` before commits
