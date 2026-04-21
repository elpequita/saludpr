# Data Directory

```
data/
├── raw/         # Pristine downloads from sources (gitignored)
├── interim/     # Mid-transformation files (gitignored)
├── processed/   # Final shape ready for DB (gitignored except README)
└── reference/   # Small lookup files committed to git (muni codes, etc.)
```

**Rule:** Raw and processed data is NOT committed to the repo. The ETL pipeline is the source of truth; anyone can reproduce the full dataset by running it.

Small reference files (e.g. municipality ID → name mapping) live in `reference/` and ARE committed.
