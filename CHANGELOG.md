# CHANGELOG


## v0.1.0 (2026-06-18)

### Features

- Initial release of RPT — Retirement Planning Tool
- Year-by-year retirement projection with federal tax modeling and 3-bucket withdrawal strategies (Traditional and Proportional)
- Income module: W2 wages, bonuses, raise schedules, Social Security estimates
- Assets module: 401(k)/IRA/Roth/Brokerage accounts with yfinance price refresh
- Debts module: full amortization schedules, escrow tracking, equity calculation
- Budget module: Wells Fargo CSV import, merchant categorization, exclusion rules, duplicate detection
- Life Events module: dependent milestones, vacation/travel expenses flowing into projections
- People module: household registry (user, spouse, dependents) driving all projection timelines
- AI Insights module: placeholder for upcoming OpenRouter integration
- Windows easy-install scripts (`INSTALL_UPDATE.bat`, `START.bat`) for non-technical users
- Demo data seeder (`seed_demo` management command)
