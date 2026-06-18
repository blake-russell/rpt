# RPT — Retirement Planning Tool

[![CI](https://github.com/blake-russell/rpt/actions/workflows/ci.yml/badge.svg)](https://github.com/blake-russell/rpt/actions/workflows/ci.yml)
[![Version](https://img.shield.io/badge/version-0.0.0-blue)](https://github.com/blake-russell/rpt/releases)

A local-first, single-household web application for comprehensive retirement planning. RPT helps you track income, investments, debts, and expenses to project whether your retirement savings will last your lifetime — with full tax modeling, withdrawal strategy optimization, and life event planning.

---

## What RPT Does

RPT consolidates all the data points that drive a retirement projection into one place:

- **Income & Wages** — W2 salaries, bonuses, annual merit raises, and Social Security benefit estimates
- **Investment Assets** — 401(k) Traditional, Roth 401(k), IRA, Roth IRA, Brokerage, Crypto, and other accounts with live price refresh via yfinance
- **Debts** — Mortgage, car loans, student loans with full amortization schedules; escrow tracking for insurance and property taxes
- **Budget** — Import Wells Fargo CSV bank exports (checking + credit card) to derive real spending baselines; merchant categorization; exclusion rules
- **Life Events** — Dependent milestones (college, vehicles, weddings), household vacations, and recurring annual expenses that flow into retirement projections
- **Retirement Projections** — Year-by-year cashflow from today through life expectancy, with federal tax modeling, Roth vs Traditional withdrawal strategy, and Social Security COLA growth
- **People** — Central household registry for all persons (user, spouse, dependents)

---

## Modules Overview

| Module | URL | Purpose |
|--------|-----|---------|
| Dashboard | `/` | Net worth snapshot, quick links, getting started guide |
| People | `/people/` | Add/edit/delete household members (user, spouse, dependents) |
| Income | `/income/` | W2 wages, bonuses, raise schedules, Social Security estimates |
| Assets | `/assets/` | Investment accounts, holdings, contributions, price refresh |
| Debts | `/debts/` | Loans with amortization, escrow tracking, primary/investment real estate |
| Life Events | `/life/` | Dependent milestones and household vacation/event expenses |
| Budget | `/budget/` | CSV import, merchant mapping, expense categorization |
| Retirement | `/retirement/` | Full projection table, tax modeling, withdrawal strategy |
| AI Insights | `/ai-insights/` | Coming soon — AI-powered analysis via OpenRouter |
| Settings | `/settings/` | API key configuration |

---

## Getting Started

### Windows (Easy Install)

Two batch scripts are included for non-technical Windows users:

1. **`INSTALL_UPDATE.bat`** — Run this first (and any time you want to update).
   - Checks if Git is installed; offers to install via winget if not
   - Does a `git pull` to update to the latest version
   - Checks if Python 3.13+ is installed; offers to install via winget if not
   - Creates the `.venv` virtual environment
   - Runs `pip install -r requirements.txt`
   - Runs `python manage.py migrate` and `python manage.py check`
   - Creates a default admin account on first run (`admin` / `Rpt@2025!k3`)
   - Shows a reminder to change the password after first login

2. **`START.bat`** — Run this every time you want to use RPT.
   - Runs a Django configuration check
   - Starts the web server at http://127.0.0.1:8000
   - Opens your default browser automatically
   - Prints default login info in the console

> **Important Security Note:** The default admin password is intended for first-time local setup convenience.
> Change it immediately after first login at `/admin/password_change/`.

### Manual Installation (All Platforms)

### Prerequisites

- Python 3.13+
- pip

### Installation

```bash
git clone <repo>
cd RPT
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000 and log in.

### Demo Data (Optional)

To seed the database with a realistic demo household for testing:

```bash
python manage.py seed_demo
```

This creates John & Jane with two kids, full income/assets/debts/life events, and sample WF CSV files at `data/demo_checking.csv` and `data/demo_credit.csv` you can import through the Budget module.

---

## Usage Guide

### Step 1 — Add People

Go to **People** (`/people/`). Add yourself (role: User) with your birth year, planned retirement age, and life expectancy age. Add your spouse if applicable. Add any dependents with their ages and expected move-out age.

> **Why this matters:** Retirement and life event projections derive years automatically from these profiles. The engine uses `birth_year + retirement_age` to determine your retirement year.

### Step 2 — Add Income

Go to **Income** (`/income/`). For each earner:
1. Add a W2 entry with your current employer and annual salary
2. Add a bonus if applicable (flat dollar or % of salary)
3. Add an annual merit raise % (e.g. 3.00 for 3%)
4. Add Social Security estimates from your ssa.gov statement — enter the monthly benefit at age 62, Full Retirement Age (67), and age 70

### Step 3 — Add Assets

Go to **Assets** (`/assets/`). Add each investment account:
- Select the account type carefully: Traditional 401(k) and IRA are **pre-tax**; Roth 401(k) and Roth IRA are **post-tax**
- Add holdings (tickers/symbols) with share count and average cost basis
- Add monthly contribution amounts for ongoing payroll contributions
- Use **Refresh Prices** to fetch current market prices via yfinance

> **Pre-tax vs Post-tax matters:** The retirement engine uses a 3-bucket withdrawal strategy. Roth accounts are drawn last (or proportionally) to maximize tax-free growth.

### Step 4 — Add Debts

Go to **Debts** (`/debts/`). Add each active loan:
- For mortgages: enter property estimated value, expected annual appreciation %, and mark **Is Primary Residence** if it's your home (excludes equity from investable asset totals)
- For escrowed mortgages: check **Is Escrowed** and enter yearly homeowners insurance and property tax amounts — these stay in expenses even after the mortgage is paid off
- For car loans: enter yearly car insurance — this persists after the loan is paid off

> **Why this matters:** Debt service is projected year-by-year and automatically falls off when each loan is paid off, correctly reducing your expenses. Without this, projections dramatically overstate future expenses.

### Step 5 — Add Life Events

Go to **Life Events** (`/life/`). Add:
- **Dependent events** (vehicle purchase, college, move-out, wedding) — entered as the dependent's age when the event occurs
- **Vacation / Travel** — enter a year and optional annual recurrence (e.g. $10,000/year starting in retirement year)

### Step 6 — Import Budget Data

Go to **Budget** (`/budget/`). Select **Wells Fargo** as the banking source, choose Checking or Credit Card, and upload your WF CSV export.

After importing:
1. Map any unmatched merchant descriptions to friendly names and categories
2. Set up exclusion rules for internal transfers (paycheck deposits to savings, 401k contributions, etc.)
3. Review any potential duplicates in the staging area

The budget rolling averages automatically feed into the retirement module as your expense baseline. Non-debt expenses are used for the CPI-inflated consumer expenses bucket.

### Step 7 — Review Retirement Projections

Go to **Retirement** (`/retirement/`). Review the settings panel on the left and adjust as needed:

| Setting | What it controls | Typical range |
|---------|-----------------|---------------|
| Portfolio Growth % | Annual return on investments | 5–7% conservative, 10% optimistic |
| Expenses CPI % | Annual consumer expense growth | 3–4% |
| SS COLA % | Annual Social Security benefit increase | 2–3% (check ssa.gov each October) |
| Healthcare Inflation % | Stored for future healthcare projections | 5–6% |
| Withdrawal Strategy | Order to draw down accounts | Traditional (taxable first) or Proportional |
| Dependent Expense Reduction | % expenses drop when each dependent moves out | 5–15% per dependent |

The **Projection Table** shows year-by-year:
- **Income** — earned wages (pre-retirement) + SS benefits (post claim year)
- **Expenses (Total)** — all expenses including tax; click `*` for life event details
- **Expenses (CPI)** — consumer expenses inflated at your CPI rate
- **Debt Svc** — fixed loan payments, automatically falling off at payoff dates
- **Fed. Tax** — federal income tax on pre-tax withdrawals and taxable SS, deducted from assets
- **From Assets** — total pulled from investment accounts (withdrawals + tax); sub-line shows breakdown
- **Assets (Pre-Tax)** — taxable + tax-deferred account balances
- **Assets (Post-Tax/Roth)** — Roth account balances
- **Net Worth** — total assets minus all debt

**Row colors:**
- 🟡 Yellow = retirement year for either household member
- 🔴 Red = shortfall year (assets fully depleted, expenses exceed all income + savings)

> **Hover over a year** to see the names and ages of all household members in that year.

### Step 8 — Settings (Optional)

Go to **Settings** (`/settings/`) to enter your OpenRouter API key for the upcoming AI Insights module.

---

## Data Privacy

RPT is designed as a **local-first** application:
- All data is stored in a local SQLite database (`db.sqlite3`)
- No data is transmitted to any external service unless you explicitly use the AI Insights feature (which sends anonymized financial summaries to OpenRouter)
- API keys are stored only in the local database, never in code or config files
- The app runs on `localhost` only; not accessible from other machines by default

---

## Technical Stack

- **Framework:** Django 6.0
- **Database:** SQLite (local)
- **Frontend:** Bootstrap 5.3 + HTMX + Chart.js
- **Price data:** yfinance (on-demand, no API key required)
- **AI integration:** OpenRouter API (optional, key required)
- **Forms:** django-crispy-forms with Bootstrap 5 pack

---

## Updating Annual Rate Constants

Several values in the app are based on government-published annual rates that change each year.

Quick checklist (run each October–November):
1. **SS COLA %** — update `DEFAULT_SS_COLA_PCT` in `retirement/models.py` and the Retirement Settings UI
2. **Federal Tax Brackets** — update `FEDERAL_TAX_BRACKETS` and `STANDARD_DEDUCTION` in `retirement/engine.py`
3. **IRS Standard Deduction** — same file as above

---

## Running Tests

```bash
python manage.py test
```

---

## License

Personal use only. Not intended for commercial distribution.
