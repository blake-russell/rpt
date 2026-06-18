# CHANGELOG

All notable changes to RPT (Retirement Planning Tool) will be documented in this file.
Versioning follows [Semantic Versioning](https://semver.org/). Releases are automated via
[python-semantic-release](https://python-semantic-release.readthedocs.io/) on pushes to `main`.

---

## v0.1.0 (2026-06-18)

### Initial Release

**Core Modules:**
- 👤 **People** — Household member registry (user, spouse, dependents) with retirement age, life expectancy, and dependent move-out/driving age tracking
- 💰 **Income** — W2 wages, bonuses, annual merit raise schedules, and Social Security benefit estimates (age 62 / FRA / age 70)
- 📈 **Assets** — Investment accounts (Traditional 401k, Roth 401k, IRA, Roth IRA, Brokerage, Crypto) with holdings, live price refresh via yfinance, and monthly contribution tracking
- 🏦 **Debts** — Mortgage, car loan, and student loan tracking with full amortization schedules, escrow support (homeowners insurance + property tax), and primary residence classification
- 👨‍👩‍👧 **Life Events** — Dependent milestones (vehicle, college, move-out, wedding) and household vacation/recurring expense events with annual recurrence support
- 📊 **Budget** — Wells Fargo CSV import (checking + credit card), merchant mapping, expense categorization, duplicate staging, exclusion rules with amount direction filtering
- 🏖️ **Retirement Projections** — Year-by-year cashflow projection with 3-bucket withdrawal strategies (Traditional / Proportional), federal income tax modeling (2025 brackets), Social Security COLA growth, SS federal taxation (IRS Pub 915), and debt service fall-off
- 🤖 **AI Insights** — Coming soon placeholder wired up at `/ai-insights/`

**Key Technical Highlights:**
- Django 6.0 + Bootstrap 5.3 + HTMX + Chart.js (no heavy frontend frameworks)
- SQLite local-first — all data stays on device
- Two-bucket expense system: CPI-inflated consumer expenses + fixed debt service
- Hardcoded 2025 federal tax brackets + SS taxation thresholds (see `.claude/rpt/STATICS.md` for annual update reference)
- `seed_demo` management command for demo household data + WF CSV generation
- CI pipeline: ruff lint → pytest → python-semantic-release (GitHub Actions)
- Windows installer scripts: `INSTALL_UPDATE.bat` + `START.bat` for non-technical users
