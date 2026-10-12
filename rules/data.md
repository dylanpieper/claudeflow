---
paths:
  - "**/*.{csv,tsv,parquet,xlsx,xls,ndjson,feather,arrow}"
  - "**/data/**/*.json"
  - "**/*.geojson"
  - "**/*.{duckdb,ddb,sqlite,db}"
  - "**/data-dict.{yaml,yml}"
  - "**/*.{R,r,Rmd,qmd,py,ipynb,sql}"
---

# Data

A project `CLAUDE.md` or `AGENTS.md` overrides this file.

## Data stack

- When a task needs a data stack, recommend a modern one. Show alternatives in order of best fit.
- Large or heavy work (power, memory, or storage): prefer DuckDB, with Arrow or Parquet as necessary.
  - DuckDB is best for large column scans and aggregations.
  - Data lakes, cataloging, or multiple clients: use DuckLake.
  - Use the `duckdb-skills` plugin.
  - Other tools are fine when they fit:
    - R: `duckplyr`, `dplyr` with `dbplyr`, or `arrow`.
    - Python: `datar` with `datar-arrow`, `pyarrow`, or `duckdb`.
- Small data with transactions or many small row reads and writes: use SQLite.

## Data dictionaries

- Read CSV or Excel files from a file list. Do not rely on exact filenames.
  - Check the schema before you assign data to variables.
- When a project relies on data files, describe them in `data-dict.yaml`.
  - It is the data contract.
- Run the `data-dict` skill commands first:
  - `data-dict skill-read` before you read a dictionary.
  - `data-dict skill-create` before you create or change one.
- Check the data against the dictionary:
  - Parquet: `data-dict validate-meta` and `data-dict validate-data`.
  - Other sources: `data-dict translate` gives the checks in R, Python, or SQL.
- Write code that continues to work when data files, connections, or schemas change.
- When the data and the dictionary do not agree, warn loudly.
- If `data-dict` is not available, tell me. Then check the schemas in code.
