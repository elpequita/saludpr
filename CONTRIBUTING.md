# Contributing to SaludPR

Thanks for your interest in helping build a public good for Puerto Rico.

## Ways to contribute

### 🐛 Report a bug or data error
Open an issue with:
- What you saw vs. what you expected
- Screenshot if applicable
- Browser / device if it's a UI issue
- Source link if you're flagging wrong data

### 📊 Suggest a data source
We only use publicly available, traceable data. If you know of a public dataset we should include, open an issue with:
- Link to the source
- What it covers
- Update frequency
- Any access requirements

### 🌐 Improve translations
We aim for natural, accessible Spanish (not machine-translated). If you spot awkward phrasing, open a PR or issue.

### 💻 Code contributions
1. Fork the repo
2. Create a branch (`feat/your-feature` or `fix/issue-description`)
3. Follow the code style (see below)
4. Write or update tests where applicable
5. Open a PR with a clear description

## Code style

- **Python:** `ruff` for lint + format, type hints required on public APIs
- **TypeScript/React:** `eslint` + `prettier`, functional components, hooks
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`)
- **PRs:** One logical change per PR, link related issues

## Data integrity rules

These are non-negotiable:

1. **Every number must be traceable to a public source.** No estimates, no interpolations without clear labeling.
2. **Always cite.** Dashboard elements link to `docs/data-sources.md`.
3. **Document limitations.** If data is self-reported, sparse, or outdated — say so on the chart.
4. **No PII, ever.** We only use aggregated data. Never individual-level records.

## Questions?

Email: carlos.perez@dataurea.com
