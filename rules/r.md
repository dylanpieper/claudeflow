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

Use the manager the project already has, and never add a second one. Ask before adding a new package manager.

| Manager | Manifest | How to add a package |
|---------|----------|----------------------|
| [`renv`](https://rstudio.github.io/renv/) | `renv.lock` | `renv::install()`, then `renv::snapshot()` |
| [`rv`](https://github.com/A2-ai/rv) | `rproject.toml` | Add to the manifest, then sync |
| [`uvr`](https://github.com/nbafrank/uvr) | `uvr.toml` | Add to the manifest, then sync |
| [`rix`](https://github.com/ropensci/rix) | `default.nix` | Add to the `rix::rix()` call (see below) |
| [`ir`](https://github.com/r-lib/ir) | File header | Add to the header |

- With no manager, use `pak::pak()`.
  - It installs from CRAN, GitHub (`"user/repo"`), and Bioconductor (`"bioc::pkg"`) in one call.
  - With no arguments, it installs the current package's development dependencies (requires a `DESCRIPTION`).
- Never use `install.packages()`, `remotes::install_github()`, or `devtools::install_github()`.
- To make `renv` use pak, add `options(renv.config.pak.enabled = TRUE)` to the project `.Rprofile`, before `source("renv/activate.R")`.
  - Do not create a project `.Renviron`: it masks `~/.Renviron`, which holds tokens and keys.
- With `rix`:
  - Put CRAN and Bioconductor packages in `r_pkgs`, GitHub packages in `git_pkgs`.
  - Rerun the call with `overwrite = TRUE` to regenerate `default.nix`. Never edit `default.nix` by hand.
  - Rebuild with `nix-build` or `nix-shell`.

Choosing a manager for a new project:

- Default to `renv` for packages and `rig` for the R version.
- Use `rv` or `uvr` when dependencies are known up front and install speed matters.
- Use `rix` when every OS must get the same R version and system libraries.
- Use `ir` for a standalone script or Quarto document outside any managed project; it needs no lockfile or project directory.

## Tools

- Format every `.R` file after writing or changing it.
  - Use the project's formatter if it has one; otherwise use Air (`air format <path>`).
  - Air does not format code chunks in R Markdown or Quarto files.
- Use `cli` for console output (e.g. `cli::cli_alert_success()`), not `cat()`, `message()`, or `print()`.
- Clean column names with `janitor::clean_names()`.
- For figures, maps, and tables, use the viz skill.

## Project stack

For complex projects:

| Need | Tool |
|------|------|
| Packages and R version | `renv`, `rig` |
| Paths and settings | `here`, `config` |
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
