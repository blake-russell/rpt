# CHANGELOG


## v0.1.1 (2026-06-18)

### Code Style

- Format seed_demo.py
  ([`8f2c3c8`](https://github.com/blake-russell/rpt/commit/8f2c3c82882de540dbf0146505e20059f0176bb9))


## v0.1.0 (2026-06-18)

### Bug Fixes

- Inflate life events with CPI, stop SS at life expectancy, correct cashflow chart
  ([`db043f7`](https://github.com/blake-russell/rpt/commit/db043f74d80f9d0edfa3eadd5b642340919a7657))

- Life event costs (one-time and annual) now inflated to their event year using CPI rate - SS
  benefits stop accruing after a person's life expectancy year - Cashflow chart uses
  total_from_assets instead of required_withdrawals - seed_demo: realistic net pay figures,
  corrected salaries/SS estimates, timezone-aware price timestamp, fixed CSV output path depth,
  single-month CSV

### Chores

- Fix versioning, badge URL, and restore CHANGELOG [skip ci]
  ([`9f6cce3`](https://github.com/blake-russell/rpt/commit/9f6cce347678951164f2221797123032124b6192))

### Features

- Initial alpha release
  ([`e8329b6`](https://github.com/blake-russell/rpt/commit/e8329b682bdde92eb4e8d6e8965c4732413a998d))


## v0.0.0 (2026-06-18)
